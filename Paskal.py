"""
Зоряна Пам'ять — FastAPI Backend (MySQL edition)
Запуск: python -m uvicorn Paskal:app --reload --port 8000
БД:     MySQL / MariaDB (налаштування у .env)
"""
import os, time, asyncio, hashlib
from typing import Optional, List

import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB

try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# ── MySQL Config (з .env) ────────────────────────────────
_DB_CFG = {
    "host":     os.getenv("DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit":  False,
}
_DB_NAME = os.getenv("DB_NAME", "zoryana_pamyat")

# ── Connection Pool ──────────────────────────────────────
# Ініціалізується після init_db() щоб БД точно існувала
_POOL: PooledDB | None = None

def _init_pool():
    global _POOL
    _POOL = PooledDB(
        creator=pymysql,
        maxconnections=20,   # макс. одночасних з'єднань
        mincached=2,         # мін. з'єднань у режимі очікування
        maxcached=10,        # макс. з'єднань у режимі очікування
        blocking=True,       # чекати вільне з'єднання (не кидати помилку)
        host=_DB_CFG["host"],
        port=_DB_CFG["port"],
        user=_DB_CFG["user"],
        password=_DB_CFG["password"],
        database=_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def get_db():
    """Повертає з'єднання з пулу."""
    if _POOL is None:
        # fallback до прямого з'єднання якщо пул ще не готовий (init_db)
        cfg = {**_DB_CFG, "database": _DB_NAME}
        return pymysql.connect(**cfg)
    return _POOL.connection()


def hash_pass(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


# ── Ініціалізація БД ─────────────────────────────────────
def init_db():
    # Спочатку підключаємось без БД — щоб створити її, якщо не існує
    raw = pymysql.connect(
        host=_DB_CFG["host"], port=_DB_CFG["port"],
        user=_DB_CFG["user"], password=_DB_CFG["password"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    with raw.cursor() as c:
        c.execute(
            f"CREATE DATABASE IF NOT EXISTS `{_DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    raw.commit()
    raw.close()

    db = get_db()
    with db.cursor() as c:
        # ── memorials ──────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS memorials (
                id       INT PRIMARY KEY AUTO_INCREMENT,
                last     VARCHAR(100) NOT NULL,
                first    VARCHAR(100) NOT NULL,
                mid      VARCHAR(100) DEFAULT '',
                birth    VARCHAR(20)  DEFAULT NULL,
                death    VARCHAR(20)  DEFAULT NULL,
                loc      VARCHAR(300) DEFAULT '',
                bury     VARCHAR(300) DEFAULT '',
                circ     VARCHAR(500) DEFAULT '',
                descr    TEXT         DEFAULT NULL,
                photo    VARCHAR(500) DEFAULT '',
                color    VARCHAR(20)  DEFAULT '#4fc3f7',
                pos_x    DOUBLE       DEFAULT 0.5,
                pos_y    DOUBLE       DEFAULT 0.5,
                likes    INT          DEFAULT 0,
                rating   DOUBLE       DEFAULT 0,
                approved TINYINT      DEFAULT 0,
                grp      VARCHAR(100) DEFAULT '',
                added_by VARCHAR(100) DEFAULT '',
                INDEX idx_approved (approved),
                INDEX idx_name     (last, first),
                INDEX idx_search   (last(50), first(50), grp(50), loc(100))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # ── likes_log ─────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS likes_log (
                id          INT PRIMARY KEY AUTO_INCREMENT,
                memorial_id INT,
                fingerprint VARCHAR(128),
                ts          INT,
                INDEX idx_likes (memorial_id, fingerprint, ts)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── users ─────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id        INT PRIMARY KEY AUTO_INCREMENT,
                name      VARCHAR(100) NOT NULL,
                email     VARCHAR(120) NOT NULL UNIQUE,
                password  VARCHAR(255) NOT NULL,
                is_admin  TINYINT DEFAULT 0,
                is_banned TINYINT DEFAULT 0,
                last_seen INT     DEFAULT 0,
                created   INT     DEFAULT (UNIX_TIMESTAMP())
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # ── colors ────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS colors (
                `key`   VARCHAR(50)  PRIMARY KEY,
                value   TEXT         NOT NULL,
                label   VARCHAR(200) DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Миграция: расширяем value если ещё VARCHAR(100)
        c.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'colors'
              AND COLUMN_NAME  = 'value'
        """)
        row = c.fetchone()
        if row:
            dtype = list(row.values())[0] if isinstance(row, dict) else row[0]
            if dtype.lower() != 'text':
                c.execute("ALTER TABLE colors MODIFY COLUMN value TEXT NOT NULL")

        # ── map_labels ────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS map_labels (
                id    INT PRIMARY KEY AUTO_INCREMENT,
                name  VARCHAR(100) NOT NULL,
                x     DOUBLE NOT NULL,
                y     DOUBLE NOT NULL,
                type  VARCHAR(20)  DEFAULT 'oblast',
                color VARCHAR(50)  DEFAULT 'rgba(160,195,220,0.45)',
                size  INT          DEFAULT 145
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── search_logs ───────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                query         VARCHAR(200) NOT NULL,
                results_count INT          DEFAULT 0,
                created_at    INT          DEFAULT (UNIX_TIMESTAMP())
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    # ── Admin user ──────────────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT id FROM users WHERE email=%s", ("admin@admin.com",))
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (name,email,password,is_admin) VALUES (%s,%s,%s,1)",
                ("Admin", "admin@admin.com", hash_pass("Admin"))
            )

    # ── Default colors ──────────────────────────────────
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
        ("oblast_fill",     "#0d2240",              "Заливка областей"),
        ("oblast_stroke",   "#1e4a7a",              "Межі областей"),
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
        ("glow_color",      "#ffd700",              "Колір свічення меж областей"),
        ("glow_spread",     "28",                   "Розсіювання меж областей (px, 6–120)"),
        ("glow_outer_color","#ffd700",              "Колір зовнішнього свічення країни"),
        ("glow_outer_spread","55",                  "Розсіювання зовнішнього свічення (px, 10–200)"),
        ("zoom_min",              "0.4",      "Мінімальний зум карти"),
        ("zoom_max",              "12",       "Максимальний зум карти"),
        ("city_border",           "rgba(40,110,180,.55)", "Колір меж районів при збільшенні"),
        ("city_border_zoom",      "2.5",      "Зум для появи меж районів"),
        ("smoke_density",         "0.995",    "Дим — затухання густини (0.8–1.0)"),
        ("smoke_velocity",        "0.98",     "Дим — затухання швидкості (0.8–1.0)"),
        ("smoke_splat_radius",    "0.22",     "Дим — радіус хмари (0.1–1.0)"),
        ("smoke_splat_force",     "14000",    "Дим — сила (1000–15000)"),
        ("smoke_curl",            "35",       "Дим — завихрення (0–50)"),
        ("smoke_opacity",         "0.85",     "Дим — прозорість (0.1–1.0)"),
        ("smoke_color_from",      "#0057B7",  "Дим — колір від"),
        ("smoke_color_to",        "#00BFFF",  "Дим — колір до"),
        ("use_cookies",           "1",        "Зберігати налаштування користувача в куках (1=так, 0=ні)"),
        ("map_photo_url",         "",         "Фото на карті — URL зображення (порожньо = вимкнено)"),
        ("map_photo_opacity",     "0.35",     "Фото на карті — прозорість (0.05–0.5)"),
        ("map_photo_blend",       "normal",   "Фото на карті — режим змішування (normal / screen / overlay / soft-light / luminosity)"),
        ("map_photo_feather",     "55",       "Фото на карті — розмитість країв % (20–80)"),
    ]
    with db.cursor() as c:
        for key, val, label in defaults:
            c.execute(
                "INSERT IGNORE INTO colors (`key`,value,label) VALUES (%s,%s,%s)",
                (key, val, label)
            )
        # Синхронізуємо кольори областей із новою схемою (як в адмінці)
        c.execute("UPDATE colors SET value=%s WHERE `key`='oblast_fill'  AND value IN ('#03070e','#040f1e')", ("#0d2240",))
        c.execute("UPDATE colors SET value=%s WHERE `key`='oblast_stroke' AND value IN ('rgba(90,110,130,.3)','rgba(90,110,130,0.3)')", ("#1e4a7a",))

    # ── Default map labels ───────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM map_labels")
        if c.fetchone()["cnt"] == 0:
            labels = [
                ("Закарпатська",      700,  4400),
                ("Львівська",        1500,  3700),
                ("Волинська",        1950,  2100),
                ("Івано-Франківська",2650,  5200),
                ("Чернівецька",      2900,  5650),
                ("Тернопільська",    3430,  3150),
                ("Рівненська",       3440,  1600),
                ("Хмельницька",      4030,  3100),
                ("Житомирська",      4800,  2000),
                ("Вінницька",        4790,  4600),
                ("Одеська",          5560,  6200),
                ("Київська",         6200,  2200),
                ("Кіровоградська",   6300,  5000),
                ("Черкаська",        7180,  3900),
                ("Полтавська",       7960,  3200),
                ("Чернігівська",     6800,  1400),
                ("Миколаївська",     7220,  6100),
                ("Херсонська",       8810,  6600),
                ("Дніпропетровська", 8510,  5200),
                ("Сумська",          8920,   900),
                ("Запорізька",       9770,  5700),
                ("Харківська",      10280,  3500),
                ("Донецька",        11400,  6000),
                ("Луганська",       12100,  4100),
                ("АР Крим",          9700,  8100),
            ]
            c.executemany(
                "INSERT INTO map_labels (name,x,y,type) VALUES (%s,%s,%s,'oblast')",
                labels
            )

    # ── Ensure АР Крим label exists (для існуючих БД) ────
    with db.cursor() as c:
        c.execute("SELECT id FROM map_labels WHERE name=%s", ("АР Крим",))
        if not c.fetchone():
            c.execute(
                "INSERT INTO map_labels (name,x,y,type) VALUES (%s,%s,%s,'oblast')",
                ("АР Крим", 9700, 8100)
            )

    # ── Seed memorials ───────────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials")
        if c.fetchone()["cnt"] == 0:
            seed = [
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
            ]
            c.executemany("""
                INSERT INTO memorials
                (last,first,mid,birth,death,loc,bury,circ,descr,color,pos_x,pos_y,likes,rating,approved,grp,added_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, seed)

    db.commit()
    db.close()


# ── Visit tracking ───────────────────────────────────────
_visits_hourly: dict = {}   # {hour_ts: count}
_request_count: int  = 0
_server_start: float = time.time()

# ── APP ──────────────────────────────────────────────────
app = FastAPI(title="Зоряна Памʼять API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def track_visits(request, call_next):
    global _request_count
    _request_count += 1
    hour = int(time.time() // 3600) * 3600
    _visits_hourly[hour] = _visits_hourly.get(hour, 0) + 1
    # Keep only last 48h to avoid memory leak
    cutoff = hour - 48 * 3600
    for k in [k for k in _visits_hourly if k < cutoff]:
        del _visits_hourly[k]
    return await call_next(request)

# Статичні файли (img)
app.mount("/img", StaticFiles(directory="img"), name="img")
app.mount("/js",  StaticFiles(directory="js"),  name="js")

@app.on_event("startup")
def startup():
    init_db()
    _init_pool()


# ── Static routes ─────────────────────────────────────────
@app.get("/")
def index(): return FileResponse("index.html")

@app.get("/admin")
def admin_page(): return FileResponse("admin.html")

@app.get("/Style.css")
def css_file(): return FileResponse("Style.css", media_type="text/css")

@app.get("/ukraine-map.svg")
def svg_map(): return FileResponse("ukraine-map.svg", media_type="image/svg+xml")

@app.get("/rules.html")
def rules_page(): return FileResponse("rules.html")

@app.get("/terms.html")
def terms_page(): return FileResponse("terms.html")

@app.get("/faq.html")
def faq_page(): return FileResponse("faq.html")


# ── WebSocket онлайн ─────────────────────────────────────
connected: set = set()
online_users: dict = {}

async def broadcast(data: dict):
    dead = set()
    for ws in connected:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    connected.difference_update(dead)

@app.websocket("/ws/online")
async def ws_online(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    await broadcast({"online": len(connected)})
    try:
        while True:
            msg = await asyncio.wait_for(ws.receive_text(), timeout=60)
            if msg.startswith("user:"):
                online_users[id(ws)] = msg[5:]
    except Exception:
        pass
    finally:
        connected.discard(ws)
        online_users.pop(id(ws), None)
        await broadcast({"online": len(connected)})


# ── Schemas ───────────────────────────────────────────────
class PersonIn(BaseModel):
    last: str; first: str; mid: Optional[str] = ""
    birth: Optional[str] = None; death: Optional[str] = None
    loc: Optional[str] = ""; bury: Optional[str] = ""
    circ: Optional[str] = ""; descr: Optional[str] = ""
    photo: Optional[str] = ""; color: Optional[str] = "#4fc3f7"
    pos_x: float; pos_y: float; grp: Optional[str] = ""
    added_by: Optional[str] = ""

class PersonUpdate(BaseModel):
    last: Optional[str] = None; first: Optional[str] = None
    mid: Optional[str] = None; birth: Optional[str] = None
    death: Optional[str] = None; loc: Optional[str] = None
    bury: Optional[str] = None; circ: Optional[str] = None
    descr: Optional[str] = None; photo: Optional[str] = None
    color: Optional[str] = None; pos_x: Optional[float] = None
    pos_y: Optional[float] = None; approved: Optional[int] = None
    grp: Optional[str] = None

class UserReg(BaseModel):
    name: str; email: str; password: str

class UserLogin(BaseModel):
    email: str; password: str

class ColorUpdate(BaseModel):
    key: str; value: str

class LabelUpdate(BaseModel):
    id: int; x: float; y: float
    name:  Optional[str] = None
    color: Optional[str] = None; size: Optional[int] = None


# ── AUTH helpers ──────────────────────────────────────────
def get_user(email: str, password: str):
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email.lower(), hash_pass(password))
        )
        row = c.fetchone()
    db.close()
    return row

def get_admin(email: str, password: str):
    u = get_user(email, password)
    if not u or not u["is_admin"]:
        return None
    return u

def require_admin(email: str, password: str):
    u = get_admin(email, password)
    if not u:
        raise HTTPException(403, "Доступ заборонено")
    return u


# ── Пошук: нормалізація та scoring ───────────────────────
def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','є':'ye',
        'ж':'zh','з':'z','и':'i','і':'i','й':'y','к':'k','л':'l',
        'м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
        'у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
        'щ':'shch','ю':'yu','я':'ya','ь':'','ї':'yi','ё':'yo',
    }
    return "".join(translit.get(ch, ch) for ch in s)

def _fuzzy_score(text: str, query: str) -> float:
    t, q = _normalize(text), _normalize(query)
    if not t or not q: return 0.0
    if t == q: return 1.0
    if t.startswith(q): return 0.92
    if q in t: return 0.80
    for word in t.split():
        if word.startswith(q): return 0.75
        if q in word: return 0.65
    if len(q) >= 2:
        matches = sum(1 for c in q if c in t)
        ratio = matches / max(len(q), len(t))
        if ratio > 0.6:
            return ratio * 0.55
    return 0.0

def _score_person(row: dict, q: str) -> float:
    fields = [
        (row.get("last", ""),  2.0),
        (row.get("first", ""), 1.8),
        (row.get("mid", ""),   1.2),
        (row.get("grp", ""),   1.5),
        (row.get("loc", ""),   1.3),
        (row.get("bury", ""),  1.0),
        (row.get("circ", ""),  0.8),
        (row.get("descr", ""), 0.6),
    ]
    best = max((_fuzzy_score(v, q) * w for v, w in fields), default=0.0)
    full = f"{row.get('last','')} {row.get('first','')} {row.get('mid','')}".strip()
    return max(best, _fuzzy_score(full, q) * 2.0)


# ── PUBLIC API ────────────────────────────────────────────

@app.get("/api/people")
def get_people():
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT * FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC"
        )
        rows = c.fetchall()
    db.close()
    return rows

@app.get("/api/search")
def search(q: str = ""):
    q = q.strip()
    if len(q) < 2:
        return []
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM memorials WHERE approved=1")
        rows = c.fetchall()

    scored = []
    for r in rows:
        score = _score_person(r, q)
        if score > 0.3:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("rating") or 0)))

    results = []
    for score, r in scored[:10]:
        results.append({
            "id":       r["id"],
            "name":     f"{r['last']} {r['first']} {r.get('mid','') or ''}".strip(),
            "last":     r["last"],
            "first":    r["first"],
            "mid":      r.get("mid", "") or "",
            "callsign": r.get("grp", "") or "",
            "location": r.get("loc", "") or "",
            "bury":     r.get("bury", "") or "",
            "color":    r.get("color", "#4fc3f7"),
            "x":        r.get("pos_x", 0.5),
            "y":        r.get("pos_y", 0.5),
            "likes":    r.get("likes", 0),
            "score":    round(score, 3),
        })

    # Логуємо запит (обмежуємо до 10000 записів)
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO search_logs (query, results_count, created_at) VALUES (%s,%s,%s)",
                (q, len(results), int(time.time()))
            )
            # Видаляємо старі записи щоб не переповнювати
            c.execute("""
                DELETE FROM search_logs
                WHERE id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM search_logs ORDER BY id DESC LIMIT 10000
                    ) AS t
                )
            """)
        db.commit()
    except Exception:
        pass
    db.close()
    return results

@app.post("/api/search/log")
def search_log(data: dict):
    try:
        q   = str(data.get("query", ""))[:200]
        cnt = int(data.get("results_count", 0))
        db  = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT INTO search_logs (query, results_count, created_at) VALUES (%s,%s,%s)",
                (q, cnt, int(time.time()))
            )
        db.commit()
        db.close()
    except Exception:
        pass
    return {"ok": True}

@app.get("/api/search/stats")
def search_stats():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM search_logs")
        total = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM search_logs WHERE results_count=0")
        empty = c.fetchone()["cnt"]
        c.execute("""
            SELECT query, COUNT(*) AS cnt FROM search_logs
            GROUP BY LOWER(TRIM(query)) ORDER BY cnt DESC LIMIT 10
        """)
        top = c.fetchall()
        c.execute(
            "SELECT query, results_count, created_at FROM search_logs ORDER BY id DESC LIMIT 20"
        )
        recent = c.fetchall()
    db.close()
    return {
        "total_searches": total,
        "empty_results":  empty,
        "top_queries":    [{"query": r["query"], "count": r["cnt"]} for r in top],
        "recent":         recent,
    }

@app.get("/api/stats")
def get_stats():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1")
        total = c.fetchone()["cnt"]
        c.execute("SELECT COALESCE(SUM(likes),0) AS s FROM memorials WHERE approved=1")
        likes = c.fetchone()["s"]
    db.close()
    return {"total": total, "likes": likes}

@app.get("/api/colors")
def get_colors():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT `key`, value, label FROM colors")
        rows = c.fetchall()
    db.close()
    return {r["key"]: {"value": r["value"], "label": r["label"]} for r in rows}

@app.get("/api/labels")
def get_labels():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM map_labels ORDER BY id")
        rows = c.fetchall()
    db.close()
    return rows

@app.post("/api/people")
def add_person(p: PersonIn):
    db = get_db()
    with db.cursor() as c:
        c.execute("""
            INSERT INTO memorials
            (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,pos_x,pos_y,grp,added_by,approved)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
        """, (p.last, p.first, p.mid, p.birth, p.death, p.loc, p.bury,
              p.circ, p.descr, p.photo, p.color, p.pos_x, p.pos_y, p.grp, p.added_by))
        new_id = c.lastrowid
    db.commit()
    db.close()
    return {"ok": True, "id": new_id, "message": "Надіслано на модерацію. Дякуємо!"}

@app.post("/api/like/{mid}")
def like(mid: int, fp: Optional[str] = "anon"):
    now = int(time.time())
    fp  = (fp or "anon")[:64]
    db  = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT COUNT(*) AS cnt FROM likes_log WHERE memorial_id=%s AND fingerprint=%s AND ts>%s",
            (mid, fp, now - 2)
        )
        if c.fetchone()["cnt"]:
            db.close()
            return {"ok": False, "reason": "cooldown"}
        c.execute(
            "INSERT INTO likes_log (memorial_id,fingerprint,ts) VALUES (%s,%s,%s)",
            (mid, fp, now)
        )
        c.execute("UPDATE memorials SET likes=likes+1 WHERE id=%s", (mid,))
        db.commit()
        c.execute("SELECT likes FROM memorials WHERE id=%s", (mid,))
        row = c.fetchone()
    db.close()
    return {"ok": True, "likes": row["likes"] if row else 0}

@app.post("/api/auth/register")
def register(u: UserReg):
    if len(u.password) < 6:
        raise HTTPException(400, "Пароль мінімум 6 символів")
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id FROM users WHERE email=%s", (u.email,))
        if c.fetchone():
            db.close()
            raise HTTPException(400, "Email вже зареєстрований")
        c.execute(
            "INSERT INTO users (name,email,password) VALUES (%s,%s,%s)",
            (u.name.strip(), u.email.lower(), hash_pass(u.password))
        )
        db.commit()
        c.execute(
            "SELECT id,name,email,is_admin FROM users WHERE email=%s", (u.email,)
        )
        row = c.fetchone()
    db.close()
    return {"ok": True, "user": row}

@app.post("/api/auth/login")
def login(u: UserLogin):
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,email,is_admin,is_banned FROM users WHERE email=%s AND password=%s",
            (u.email.lower(), hash_pass(u.password))
        )
        row = c.fetchone()
    if not row:
        db.close()
        raise HTTPException(401, "Невірний email або пароль")
    if row["is_banned"]:
        db.close()
        raise HTTPException(403, "Акаунт заблоковано")
    with db.cursor() as c:
        c.execute("UPDATE users SET last_seen=%s WHERE email=%s",
                  (int(time.time()), u.email.lower()))
    db.commit()
    db.close()
    return {"ok": True, "user": row}


# ── ADMIN API ─────────────────────────────────────────────

@app.get("/api/admin/pending")
def pending(email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC")
        rows = c.fetchall()
    db.close()
    return rows

@app.post("/api/admin/approve/{mid}")
def approve(mid: int, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE memorials SET approved=1 WHERE id=%s", (mid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/admin/memorial/{mid}")
def delete_memorial(mid: int, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("DELETE FROM memorials WHERE id=%s", (mid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid: int, p: PersonUpdate, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    fields, vals = [], []
    for f, v in p.dict(exclude_none=True).items():
        fields.append(f"`{f}`=%s")
        vals.append(v)
    if not fields:
        db.close()
        return {"ok": False}
    vals.append(mid)
    with db.cursor() as c:
        c.execute(f"UPDATE memorials SET {','.join(fields)} WHERE id=%s", vals)
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/api/admin/users")
def get_users(email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,email,is_admin,is_banned,last_seen,created FROM users ORDER BY id DESC"
        )
        rows = c.fetchall()
    db.close()
    now = int(time.time())
    for r in rows:
        r["online"] = (now - (r["last_seen"] or 0)) < 120
    return rows

@app.post("/api/admin/ban/{uid}")
def ban_user(uid: int, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE users SET is_banned=1 WHERE id=%s", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.post("/api/admin/unban/{uid}")
def unban_user(uid: int, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE users SET is_banned=0 WHERE id=%s", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/color")
def update_color(c_body: ColorUpdate, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') "
            "ON DUPLICATE KEY UPDATE value=%s",
            (c_body.key, c_body.value, c_body.value)
        )
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/colors/batch")
def update_colors_batch(colors: List[ColorUpdate], email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        for col in colors:
            c.execute(
                "INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') "
                "ON DUPLICATE KEY UPDATE value=%s",
                (col.key, col.value, col.value)
            )
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/label/{lid}")
def update_label(lid: int, lbl: LabelUpdate, email: str, password: str):
    require_admin(email, password)
    db = get_db()
    fields, vals = ["x=%s", "y=%s"], [lbl.x, lbl.y]
    if lbl.name  is not None: fields.append("name=%s");  vals.append(lbl.name)
    if lbl.color is not None: fields.append("color=%s"); vals.append(lbl.color)
    if lbl.size  is not None: fields.append("size=%s");  vals.append(lbl.size)
    vals.append(lid)
    with db.cursor() as c:
        c.execute(f"UPDATE map_labels SET {','.join(fields)} WHERE id=%s", vals)
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/api/admin/stats")
def admin_stats(email: str, password: str):
    require_admin(email, password)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials");              total    = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1"); approved = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=0"); pend     = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM users");                  users    = c.fetchone()["cnt"]
        c.execute("SELECT COALESCE(SUM(likes),0) AS s FROM memorials"); likes    = c.fetchone()["s"]
    db.close()
    return {
        "total": total, "approved": approved, "pending": pend,
        "users": users, "likes": likes, "online": len(connected),
    }


@app.get("/api/admin/server-stats")
def server_stats(email: str, password: str):
    require_admin(email, password)
    # CPU / RAM
    if _HAS_PSUTIL:
        cpu   = round(_psutil.cpu_percent(interval=0.2), 1)
        mem   = _psutil.virtual_memory()
        ram_p = round(mem.percent, 1)
        ram_gb_used  = round(mem.used  / 1024**3, 2)
        ram_gb_total = round(mem.total / 1024**3, 1)
    else:
        cpu = ram_p = ram_gb_used = ram_gb_total = None

    # Uptime
    uptime_sec = int(time.time() - _server_start)
    h, r = divmod(uptime_sec, 3600)
    m, s = divmod(r, 60)
    uptime_str = f"{h}г {m:02d}х {s:02d}с"

    # Visits last 24h (per hour)
    now_hour = int(time.time() // 3600) * 3600
    visits_24h = []
    for i in range(23, -1, -1):
        ts = now_hour - i * 3600
        visits_24h.append({"ts": ts, "count": _visits_hourly.get(ts, 0)})

    return {
        "cpu":          cpu,
        "ram_percent":  ram_p,
        "ram_used_gb":  ram_gb_used,
        "ram_total_gb": ram_gb_total,
        "online":       len(connected),
        "uptime":       uptime_str,
        "total_requests": _request_count,
        "visits_24h":   visits_24h,
    }
