from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, time, asyncio

DB = "memorial.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

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
            circ     TEXT DEFAULT '',
            descr    TEXT DEFAULT '',
            photo    TEXT DEFAULT '',
            color    TEXT DEFAULT '#4fc3f7',
            pos_x    REAL DEFAULT 0.5,
            pos_y    REAL DEFAULT 0.5,
            likes    INTEGER DEFAULT 0,
            rating   REAL DEFAULT 0,
            approved INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS likes_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memorial_id INTEGER, fingerprint TEXT, ts INTEGER
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created INTEGER DEFAULT (strftime('%s','now'))
        );
    """)
    if db.execute("SELECT COUNT(*) FROM memorials").fetchone()[0] == 0:
        db.executemany("""
            INSERT INTO memorials
            (last,first,mid,birth,death,loc,circ,descr,color,pos_x,pos_y,likes,rating,approved)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
            ("Шевченко","Олег","Миколайович","1985-03-14","2022-03-01",
             "Херсон","Ракетний удар","Майор ЗСУ, захисник Херсона.",
             "#4fc3f7",0.630,0.690,142,5.2,1),
            ("Іваненко","Сергій","Петрович","1990-07-22","2022-04-15",
             "Маріуполь","Прямий контакт","Боронив Маріуполь до останнього.",
             "#c8b060",0.847,0.730,389,8.1,1),
            ("Коваль","Андрій","Олексійович","1978-11-05","2022-08-20",
             "Харків","Артилерія","Підполковник, 25 років служби.",
             "#a5d6a7",0.782,0.400,78,3.9,1),
            ("Мельник","Василь","Іванович","1995-01-30","2023-01-10",
             "Бахмут","Міна","Молодий офіцер, оборона Бахмута.",
             "#ef9a9a",0.820,0.590,210,6.4,1),
            ("Власенко","Григорій","Петрович","1969-01-12","2022-03-25",
             "Київ","Прямий контакт","Ветеран, прийшов добровольцем.",
             "#c8b060",0.475,0.295,891,11.4,1),
        ])
    db.commit()
    db.close()

app = FastAPI(title="Зоряна Памʼять API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

# ── Статичні файли ────────────────────────────────────
@app.get("/")
def index():
    return FileResponse("index.html")

@app.get("/ukraine-map.svg")
def svg_map():
    return FileResponse("ukraine-map.svg", media_type="image/svg+xml")

# ── WebSocket: реальний онлайн ─────────────────────────
connected: set[WebSocket] = set()

async def broadcast(data: dict):
    dead = set()
    for ws in connected:
        try:
            await ws.send_json(data)
        except:
            dead.add(ws)
    connected.difference_update(dead)

@app.websocket("/ws/online")
async def ws_online(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    await broadcast({"online": len(connected)})
    try:
        while True:
            await asyncio.wait_for(ws.receive_text(), timeout=60)
    except (WebSocketDisconnect, asyncio.TimeoutError, Exception):
        pass
    finally:
        connected.discard(ws)
        await broadcast({"online": len(connected)})

# ── Schemas ───────────────────────────────────────────
class PersonIn(BaseModel):
    last:  str
    first: str
    mid:   Optional[str] = ""
    birth: Optional[str] = None
    death: Optional[str] = None
    loc:   Optional[str] = ""
    circ:  Optional[str] = ""
    descr: Optional[str] = ""
    photo: Optional[str] = ""
    color: Optional[str] = "#4fc3f7"
    pos_x: float
    pos_y: float

class UserReg(BaseModel):
    name: str; email: str; password: str

class UserLogin(BaseModel):
    email: str; password: str

# ── API ───────────────────────────────────────────────
@app.get("/api/people")
def get_people():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.get("/api/search")
def search(q: str):
    if len(q) < 2: return []
    db = get_db()
    like = f"%{q}%"
    rows = db.execute("""
        SELECT * FROM memorials WHERE approved=1
        AND (last LIKE ? OR first LIKE ? OR mid LIKE ? OR loc LIKE ?)
        ORDER BY rating DESC LIMIT 8
    """, (like,)*4).fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.get("/api/stats")
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM memorials WHERE approved=1").fetchone()[0]
    likes = db.execute("SELECT COALESCE(SUM(likes),0) FROM memorials WHERE approved=1").fetchone()[0]
    db.close()
    return {"total": total, "likes": likes}

@app.post("/api/people")
def add_person(p: PersonIn):
    db = get_db()
    db.execute("""
        INSERT INTO memorials
        (last,first,mid,birth,death,loc,circ,descr,photo,color,pos_x,pos_y,approved)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)
    """, (p.last,p.first,p.mid,p.birth,p.death,
          p.loc,p.circ,p.descr,p.photo,p.color,p.pos_x,p.pos_y))
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return {"ok": True, "id": new_id, "message": "Надіслано на модерацію. Дякуємо!"}

@app.post("/api/like/{mid}")
def like(mid: int, fp: Optional[str] = "anon"):
    now = int(time.time())
    db  = get_db()
    if db.execute(
        "SELECT COUNT(*) FROM likes_log WHERE memorial_id=? AND fingerprint=? AND ts>?",
        (mid, fp, now-2)
    ).fetchone()[0]:
        db.close()
        return {"ok": False, "reason": "cooldown"}
    db.execute("INSERT INTO likes_log (memorial_id,fingerprint,ts) VALUES (?,?,?)", (mid,fp,now))
    db.execute("UPDATE memorials SET likes=likes+1 WHERE id=?", (mid,))
    db.commit()
    row = db.execute("SELECT likes FROM memorials WHERE id=?", (mid,)).fetchone()
    db.close()
    return {"ok": True, "likes": row["likes"] if row else 0}

@app.post("/api/auth/register")
def register(u: UserReg):
    if len(u.password) < 6:
        raise HTTPException(400, "Пароль мінімум 6 символів")
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (u.email,)).fetchone():
        db.close(); raise HTTPException(400, "Email вже зареєстрований")
    db.execute("INSERT INTO users (name,email,password) VALUES (?,?,?)",
               (u.name.strip(), u.email.strip().lower(), u.password))
    db.commit()
    row = db.execute("SELECT id,name,email FROM users WHERE email=?", (u.email,)).fetchone()
    db.close()
    return {"ok": True, "user": dict(row)}

@app.post("/api/auth/login")
def login(u: UserLogin):
    db  = get_db()
    row = db.execute(
        "SELECT id,name,email FROM users WHERE email=? AND password=?",
        (u.email.strip().lower(), u.password)
    ).fetchone()
    db.close()
    if not row: raise HTTPException(401, "Невірний email або пароль")
    return {"ok": True, "user": dict(row)}

@app.get("/api/admin/pending")
def pending():
    db = get_db()
    rows = db.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY rowid DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/approve/{mid}")
def approve(mid: int):
    db = get_db()
    db.execute("UPDATE memorials SET approved=1 WHERE id=?", (mid,))
    db.commit(); db.close()
    return {"ok": True}
