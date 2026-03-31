from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import sqlite3, time, asyncio, hashlib, os

DB = "memorial.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pass(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS memorials (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            last     TEXT NOT NULL,
            first    TEXT NOT NULL,
            mid      TEXT DEFAULT '',
            birth    TEXT, death TEXT,
            loc      TEXT DEFAULT '',
            bury     TEXT DEFAULT '',
            circ     TEXT DEFAULT '',
            descr    TEXT DEFAULT '',
            photo    TEXT DEFAULT '',
            color    TEXT DEFAULT '#4fc3f7',
            pos_x    REAL DEFAULT 0.5,
            pos_y    REAL DEFAULT 0.5,
            likes    INTEGER DEFAULT 0,
            rating   REAL DEFAULT 0,
            approved INTEGER DEFAULT 0,
            grp      TEXT DEFAULT '',
            added_by TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS likes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memorial_id INTEGER, fingerprint TEXT, ts INTEGER
        );
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            email    TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            last_seen INTEGER DEFAULT 0,
            created  INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS colors (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            label TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS map_labels (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            x     REAL NOT NULL,
            y     REAL NOT NULL,
            type  TEXT DEFAULT 'oblast',
            color TEXT DEFAULT 'rgba(160,195,220,0.45)',
            size  INTEGER DEFAULT 145
        );
    """)

    # Admin user
    admin = db.execute("SELECT id FROM users WHERE email='admin@admin.com'").fetchone()
    if not admin:
        db.execute("INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)",
                   ("Admin","admin@admin.com", hash_pass("Admin")))

    # Default colors
    defaults = [
        ("bg",              "#03070e",              "Фон сторінки"),
        ("surface",         "#070d1a",              "Поверхня карток"),
        ("text_primary",    "#d0dce8",              "Основний текст"),
        ("text_secondary",  "#8a9cb0",              "Другорядний текст"),
        ("accent",          "#00c8ff",              "Акцент (синій)"),
        ("yellow",          "#d4a800",              "Жовтий (логотип)"),
        ("yellow2",         "#f0c030",              "Жовтий яскравий"),
        ("neon_blue",       "#00ccff",              "Неон синій (межа країни)"),
        ("neon_yellow",     "#d4a800",              "Неон жовтий (межа областей)"),
        ("oblast_fill",     "#040f1e",              "Заливка областей"),
        ("oblast_stroke",   "rgba(90,110,130,.3)",  "Межі міст/сіл"),
        ("thread_color",    "rgba(0,200,255,1)",    "Нитки між дублікатами"),
        ("map_bg",          "#03070e",              "Фон карти"),
        ("bar_bg",          "rgba(3,7,14,.96)",     "Фон шапки"),
        ("logo_star",       "#f0c030",              "Зірка логотипу"),
        ("logo_text",       "#f0c030",              "Текст логотипу"),
        ("logo_accent",     "#00c8ff",              "Акцент логотипу"),
        ("btn_add_bg",      "#0e2860",              "Кнопка Додати (фон)"),
        ("btn_add_text",    "#a8e0f8",              "Кнопка Додати (текст)"),
        ("card_bg",         "rgba(4,9,18,.98)",     "Фон картки"),
        ("label_opacity",   "0.45",                 "Прозорість підписів областей"),
    ]
    for key, val, label in defaults:
        db.execute("INSERT OR IGNORE INTO colors (key,value,label) VALUES (?,?,?)", (key,val,label))

    # Default map labels
    if db.execute("SELECT COUNT(*) FROM map_labels").fetchone()[0] == 0:
        labels = [
            ("Закарпатська",      700,  4400, "oblast"),
            ("Львівська",        1500,  3700, "oblast"),
            ("Волинська",        1950,  2100, "oblast"),
            ("Івано-Франківська",2650,  5200, "oblast"),
            ("Чернівецька",      2900,  5650, "oblast"),
            ("Тернопільська",    3430,  3150, "oblast"),
            ("Рівненська",       3440,  1600, "oblast"),
            ("Хмельницька",      4030,  3100, "oblast"),
            ("Житомирська",      4800,  2000, "oblast"),
            ("Вінницька",        4790,  4600, "oblast"),
            ("Одеська",          5560,  6200, "oblast"),
            ("Київська",         6200,  2200, "oblast"),
            ("Кіровоградська",   6300,  5000, "oblast"),
            ("Черкаська",        7180,  3900, "oblast"),
            ("Полтавська",       7960,  3200, "oblast"),
            ("Чернігівська",     6800,  1400, "oblast"),
            ("Миколаївська",     7220,  6100, "oblast"),
            ("Херсонська",       8810,  6600, "oblast"),
            ("Дніпропетровська", 8510,  5200, "oblast"),
            ("Сумська",          8920,   900, "oblast"),
            ("Запорізька",       9770,  5700, "oblast"),
            ("Харківська",      10280,  3500, "oblast"),
            ("Донецька",        11400,  6000, "oblast"),
            ("Луганська",       12100,  4100, "oblast"),
        ]
        db.executemany(
            "INSERT INTO map_labels (name,x,y,type) VALUES (?,?,?,?)",
            labels
        )

    # Default memorials
    if db.execute("SELECT COUNT(*) FROM memorials").fetchone()[0] == 0:
        db.executemany("""
            INSERT INTO memorials
            (last,first,mid,birth,death,loc,bury,circ,descr,color,pos_x,pos_y,likes,rating,approved,grp,added_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            ("Шевченко","Олег","Миколайович","1985-03-14","2022-03-01",
             "Херсон","Херсон, Центральний цвинтар","Ракетний удар",
             "Майор ЗСУ, захисник Херсона. Нагороджений орденом посмертно.",
             "#4fc3f7",0.630,0.720,142,5.2,1,"Херсон-1","Марія Шевченко"),
            ("Іваненко","Сергій","Петрович","1990-07-22","2022-04-15",
             "Маріуполь, Азовсталь","Маріуполь","Прямий контакт",
             "Захисник Маріуполя, боєць полку Азов. 82 дні оборони.",
             "#c8b060",0.847,0.730,389,8.1,1,"Маріуполь-1","Наталія Іваненко"),
            ("Іваненко","Сергій","Петрович","1990-07-22","2022-04-15",
             "Маріуполь","Маріуполь","Прямий контакт",
             "Боєць 36-ї бригади. Захисник Маріуполя.",
             "#ffd54f",0.851,0.736,210,6.4,1,"Маріуполь-1","Максим Сидоренко"),
            ("Коваль","Андрій","Олексійович","1978-11-05","2022-08-20",
             "Харків","Харків, Лісове кладовище","Артилерія",
             "Підполковник ЗСУ, 25 років служби.",
             "#a5d6a7",0.782,0.400,78,3.9,1,"","Тетяна Коваль"),
            ("Мельник","Василь","Іванович","1995-01-30","2023-01-10",
             "Бахмут, 93-тя бригада","Бахмут","Міна",
             "Молодший лейтенант, оборона Бахмута.",
             "#ef9a9a",0.820,0.590,210,6.4,1,"Бахмут-1","Іван Мельник"),
            ("Мельник","Василь","Іванович","1995-01-30","2023-01-10",
             "Бахмут","Бахмут","Міна","Герой оборони Бахмута.",
             "#ff8a65",0.825,0.596,89,4.1,1,"Бахмут-1","Школа №5"),
            ("Власенко","Григорій","Петрович","1969-01-12","2022-03-25",
             "Буча","Київ, Берківське кладовище","Прямий контакт",
             "Ветеран АТО, загинув у боях за Бучу.",
             "#c8b060",0.475,0.295,891,11.4,1,"Київ-1","Олена Власенко"),
            ("Власенко","Григорій","Петрович","1969-01-12","2022-03-25",
             "Буча","Київ","Прямий контакт","Захисник Бучі.",
             "#ffd54f",0.470,0.302,234,6.8,1,"Київ-1","Меморіал Бучі"),
            ("Саченко","Олег","Михайлович","1976-07-09","2022-04-28",
             "Чернігів","Чернігів, Яцево","Ракетний удар",
             "Льотчик-ас, Герой України посмертно.",
             "#c8b060",0.490,0.220,743,10.6,1,"Чернігів-1","ВПС України"),
            ("Саченко","Олег","Михайлович","1976-07-09","2022-04-28",
             "Чернігів","Чернігів","Ракетний удар","Герой-льотчик.",
             "#ffd54f",0.494,0.228,312,7.2,1,"Чернігів-1","Аеропорт Чернігів"),
            ("Гаврилюк","Тарас","Михайлович","1993-08-27","2023-02-28",
             "Кремінна","Луганська обл.","Артилерія",
             "Стрілець 53-ї бригади.",
             "#ce93d8",0.865,0.400,167,5.8,1,"","Родина Гаврилюків"),
            ("Литвин","Іван","Олегович","1980-02-14","2022-06-30",
             "Лисичанськ","Лисичанськ","Прямий контакт",
             "Командир взводу, прикривав відхід підрозділу.",
             "#ef9a9a",0.840,0.440,445,8.9,1,"","Людмила Литвин"),
            ("Петренко","Роман","Андрійович","1997-09-11","2023-07-04",
             "Куп'янськ","Куп'янськ","Міна",
             "Наймолодший у роті. Загинув під час розмінування.",
             "#a5d6a7",0.790,0.340,523,9.2,1,"","Батьки"),
            ("Романенко","Олександр","Юрійович","1975-04-03","2022-11-14",
             "Миколаїв","Миколаїв","Ракетний удар",
             "Капітан ВМС, загинув під час ракетного удару.",
             "#80cbc4",0.516,0.668,98,4.1,1,"","ВМС України"),
            ("Лисенко","Денис","Юрійович","1992-04-07","2023-08-11",
             "Роботине","Запорізька обл.","Авіабомба",
             "Учасник контрнаступу 2023.",
             "#ff8a65",0.750,0.680,412,8.4,1,"","Бойові побратими"),
            ("Стець","Маркіян","Ярославович","1988-09-29","2023-01-28",
             "Соледар","Дрогобич","Міна",
             "Прикарпатець, батько двох дітей.",
             "#c8b060",0.180,0.490,321,7.5,1,"","Марʼяна Стець"),
            ("Зінченко","Антон","Васильович","1994-06-03","2023-06-15",
             "Лиман","Лиман","Снайпер",
             "Розвідник, загинув під час розвідки позицій.",
             "#4fc3f7",0.790,0.470,145,5.3,1,"","Розвідувальна рота"),
            ("Хоменко","Артем","Вікторович","1990-01-25","2023-02-14",
             "Вугледар","Вугледар","Авіабомба",
             "Знищив 4 одиниці бронетехніки до загибелі.",
             "#a5d6a7",0.800,0.650,345,7.7,1,"","112-а бригада"),
            ("Панченко","Леонід","Ігорович","1979-03-31","2022-09-18",
             "Херсон","Херсон","Артилерія",
             "Морський піхотинець, тримав позицію на Дніпрі.",
             "#4fc3f7",0.625,0.730,178,5.7,1,"Херсон-1","Морська піхота"),
            ("Тищенко","Михайло","Олексійович","1985-10-14","2023-11-07",
             "Кремінна","Кремінна","Снайпер",
             "Командир відділення у лісах поблизу Кремінної.",
             "#ce93d8",0.860,0.430,234,6.6,1,"","Кремінська громада"),
        ])

    db.commit()
    db.close()

# ── APP ──────────────────────────────────────────────
app = FastAPI(title="Зоряна Памʼять API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup(): init_db()

# ── Static files ──────────────────────────────────────
@app.get("/")
def index(): return FileResponse("index.html")

@app.get("/admin")
def admin_page(): return FileResponse("admin.html")

@app.get("/Style.css")
def css_file(): return FileResponse("Style.css", media_type="text/css")

@app.get("/ukraine-map.svg")
def svg_map(): return FileResponse("ukraine-map.svg", media_type="image/svg+xml")

# ── WebSocket онлайн ──────────────────────────────────
connected: set[WebSocket] = set()
online_users: dict = {}  # ws -> {user_id, name}

async def broadcast(data: dict):
    dead = set()
    for ws in connected:
        try: await ws.send_json(data)
        except: dead.add(ws)
    connected.difference_update(dead)

@app.websocket("/ws/online")
async def ws_online(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    await broadcast({"online": len(connected)})
    try:
        while True:
            msg = await asyncio.wait_for(ws.receive_text(), timeout=60)
            # Клієнт може надіслати своє імʼя
            if msg.startswith("user:"):
                online_users[id(ws)] = msg[5:]
    except: pass
    finally:
        connected.discard(ws)
        online_users.pop(id(ws), None)
        await broadcast({"online": len(connected)})

# ── Schemas ───────────────────────────────────────────
class PersonIn(BaseModel):
    last:str; first:str; mid:Optional[str]=""
    birth:Optional[str]=None; death:Optional[str]=None
    loc:Optional[str]=""; bury:Optional[str]=""
    circ:Optional[str]=""; descr:Optional[str]=""
    photo:Optional[str]=""; color:Optional[str]="#4fc3f7"
    pos_x:float; pos_y:float; grp:Optional[str]=""
    added_by:Optional[str]=""

class PersonUpdate(BaseModel):
    last:Optional[str]=None; first:Optional[str]=None; mid:Optional[str]=None
    birth:Optional[str]=None; death:Optional[str]=None
    loc:Optional[str]=None; bury:Optional[str]=None
    circ:Optional[str]=None; descr:Optional[str]=None
    photo:Optional[str]=None; color:Optional[str]=None
    pos_x:Optional[float]=None; pos_y:Optional[float]=None
    approved:Optional[int]=None; grp:Optional[str]=None

class UserReg(BaseModel):
    name:str; email:str; password:str

class UserLogin(BaseModel):
    email:str; password:str

class ColorUpdate(BaseModel):
    key:str; value:str

class LabelUpdate(BaseModel):
    id:int; x:float; y:float; color:Optional[str]=None; size:Optional[int]=None

# ── AUTH helper ───────────────────────────────────────
def get_user(email:str, password:str):
    db=get_db()
    row=db.execute("SELECT * FROM users WHERE email=? AND password=?",
                   (email.lower(), hash_pass(password))).fetchone()
    db.close()
    return dict(row) if row else None

def get_admin(email:str, password:str):
    u=get_user(email,password)
    if not u or not u['is_admin']: return None
    return u

# ── PUBLIC API ────────────────────────────────────────
@app.get("/api/people")
def get_people():
    db=get_db()
    rows=db.execute("SELECT * FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.get("/api/search")
def search(q:str):
    if len(q)<2: return []
    db=get_db(); like=f"%{q}%"
    rows=db.execute("""SELECT * FROM memorials WHERE approved=1
        AND (last LIKE ? OR first LIKE ? OR mid LIKE ? OR loc LIKE ? OR bury LIKE ?)
        ORDER BY rating DESC LIMIT 10""", (like,)*5).fetchall()
    db.close(); return [dict(r) for r in rows]

@app.get("/api/stats")
def get_stats():
    db=get_db()
    total=db.execute("SELECT COUNT(*) FROM memorials WHERE approved=1").fetchone()[0]
    likes=db.execute("SELECT COALESCE(SUM(likes),0) FROM memorials WHERE approved=1").fetchone()[0]
    db.close(); return {"total":total,"likes":likes}

@app.get("/api/colors")
def get_colors():
    db=get_db()
    rows=db.execute("SELECT key,value,label FROM colors").fetchall()
    db.close(); return {r["key"]:{"value":r["value"],"label":r["label"]} for r in rows}

@app.get("/api/labels")
def get_labels():
    db=get_db()
    rows=db.execute("SELECT * FROM map_labels ORDER BY id").fetchall()
    db.close(); return [dict(r) for r in rows]

@app.post("/api/people")
def add_person(p:PersonIn):
    db=get_db()
    db.execute("""INSERT INTO memorials
        (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,pos_x,pos_y,grp,added_by,approved)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
        (p.last,p.first,p.mid,p.birth,p.death,p.loc,p.bury,
         p.circ,p.descr,p.photo,p.color,p.pos_x,p.pos_y,p.grp,p.added_by))
    db.commit()
    new_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return {"ok":True,"id":new_id,"message":"Надіслано на модерацію. Дякуємо!"}

@app.post("/api/like/{mid}")
def like(mid:int, fp:Optional[str]="anon"):
    now=int(time.time()); db=get_db()
    if db.execute("SELECT COUNT(*) FROM likes_log WHERE memorial_id=? AND fingerprint=? AND ts>?",
                  (mid,fp,now-2)).fetchone()[0]:
        db.close(); return {"ok":False,"reason":"cooldown"}
    db.execute("INSERT INTO likes_log (memorial_id,fingerprint,ts) VALUES (?,?,?)",(mid,fp,now))
    db.execute("UPDATE memorials SET likes=likes+1 WHERE id=?",(mid,))
    db.commit()
    row=db.execute("SELECT likes FROM memorials WHERE id=?",(mid,)).fetchone()
    db.close(); return {"ok":True,"likes":row["likes"] if row else 0}

@app.post("/api/auth/register")
def register(u:UserReg):
    if len(u.password)<6: raise HTTPException(400,"Пароль мінімум 6 символів")
    db=get_db()
    if db.execute("SELECT id FROM users WHERE email=?",(u.email,)).fetchone():
        db.close(); raise HTTPException(400,"Email вже зареєстрований")
    db.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
               (u.name.strip(),u.email.lower(),hash_pass(u.password)))
    db.commit()
    row=db.execute("SELECT id,name,email,is_admin FROM users WHERE email=?",(u.email,)).fetchone()
    db.close(); return {"ok":True,"user":dict(row)}

@app.post("/api/auth/login")
def login(u:UserLogin):
    db=get_db()
    row=db.execute("SELECT id,name,email,is_admin,is_banned FROM users WHERE email=? AND password=?",
                   (u.email.lower(),hash_pass(u.password))).fetchone()
    db.close()
    if not row: raise HTTPException(401,"Невірний email або пароль")
    if row["is_banned"]: raise HTTPException(403,"Акаунт заблоковано")
    # Оновимо last_seen
    db2=get_db()
    db2.execute("UPDATE users SET last_seen=? WHERE email=?",(int(time.time()),u.email.lower()))
    db2.commit(); db2.close()
    return {"ok":True,"user":dict(row)}

# ── ADMIN API ─────────────────────────────────────────
class AdminAuth(BaseModel):
    email:str; password:str

def require_admin(email:str, password:str):
    u=get_admin(email,password)
    if not u: raise HTTPException(403,"Доступ заборонено")
    return u

@app.get("/api/admin/pending")
def pending(email:str, password:str):
    require_admin(email,password)
    db=get_db()
    rows=db.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY rowid DESC").fetchall()
    db.close(); return [dict(r) for r in rows]

@app.post("/api/admin/approve/{mid}")
def approve(mid:int, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    db.execute("UPDATE memorials SET approved=1 WHERE id=?",(mid,))
    db.commit(); db.close(); return {"ok":True}

@app.delete("/api/admin/memorial/{mid}")
def delete_memorial(mid:int, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    db.execute("DELETE FROM memorials WHERE id=?",(mid,))
    db.commit(); db.close(); return {"ok":True}

@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid:int, p:PersonUpdate, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    fields=[]
    vals=[]
    for f,v in p.dict(exclude_none=True).items():
        fields.append(f"{f}=?"); vals.append(v)
    if not fields: return {"ok":False}
    vals.append(mid)
    db.execute(f"UPDATE memorials SET {','.join(fields)} WHERE id=?",vals)
    db.commit(); db.close(); return {"ok":True}

@app.get("/api/admin/users")
def get_users(email:str, password:str):
    require_admin(email,password)
    db=get_db()
    rows=db.execute("SELECT id,name,email,is_admin,is_banned,last_seen,created FROM users ORDER BY id DESC").fetchall()
    db.close()
    now=int(time.time())
    result=[]
    for r in rows:
        d=dict(r)
        d["online"]=(now-r["last_seen"])<120
        result.append(d)
    return result

@app.post("/api/admin/ban/{uid}")
def ban_user(uid:int, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    db.execute("UPDATE users SET is_banned=1 WHERE id=?",(uid,))
    db.commit(); db.close(); return {"ok":True}

@app.post("/api/admin/unban/{uid}")
def unban_user(uid:int, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    db.execute("UPDATE users SET is_banned=0 WHERE id=?",(uid,))
    db.commit(); db.close(); return {"ok":True}

@app.put("/api/admin/color")
def update_color(c:ColorUpdate, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    db.execute("UPDATE colors SET value=? WHERE key=?",(c.value,c.key))
    db.commit(); db.close(); return {"ok":True}

@app.put("/api/admin/colors/batch")
def update_colors_batch(colors:List[ColorUpdate], email:str, password:str):
    require_admin(email,password)
    db=get_db()
    for c in colors:
        db.execute("UPDATE colors SET value=? WHERE key=?",(c.value,c.key))
    db.commit(); db.close(); return {"ok":True}

@app.put("/api/admin/label/{lid}")
def update_label(lid:int, l:LabelUpdate, email:str, password:str):
    require_admin(email,password)
    db=get_db()
    fields=[]; vals=[]
    for f,v in {"x":l.x,"y":l.y}.items():
        if v is not None: fields.append(f"{f}=?"); vals.append(v)
    if l.color: fields.append("color=?"); vals.append(l.color)
    if l.size:  fields.append("size=?");  vals.append(l.size)
    if fields:
        vals.append(lid)
        db.execute(f"UPDATE map_labels SET {','.join(fields)} WHERE id=?",vals)
        db.commit()
    db.close(); return {"ok":True}

@app.get("/api/admin/stats")
def admin_stats(email:str, password:str):
    require_admin(email,password)
    db=get_db()
    total=db.execute("SELECT COUNT(*) FROM memorials").fetchone()[0]
    approved=db.execute("SELECT COUNT(*) FROM memorials WHERE approved=1").fetchone()[0]
    pending=db.execute("SELECT COUNT(*) FROM memorials WHERE approved=0").fetchone()[0]
    users=db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    likes=db.execute("SELECT COALESCE(SUM(likes),0) FROM memorials").fetchone()[0]
    db.close()
    return {"total":total,"approved":approved,"pending":pending,"users":users,"likes":likes,"online":len(connected)}
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory=".", html=True), name="static")