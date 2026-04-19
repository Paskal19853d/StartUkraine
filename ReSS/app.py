"""
Зоряна Пам'ять — Secure FastAPI Backend (ReSS edition)
Запуск: cd ReSS && python -m uvicorn app:app --reload --port 8000
"""
import os, time, sqlite3, asyncio, re, html as html_lib
from pathlib import Path
from datetime import datetime, timedelta

HERE = Path(__file__).parent.resolve()

from typing import Optional, List
from urllib.parse import urlparse

import bcrypt
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Load .env from the ReSS directory regardless of working directory
load_dotenv(dotenv_path=HERE / ".env")

# ── Config (from .env) ──────────────────────────────────
JWT_SECRET       = os.environ.get("JWT_SECRET", "CHANGE_THIS_SECRET_MIN_32_CHARS_!!!")
ALGORITHM        = "HS256"
TOKEN_EXPIRE_H   = int(os.environ.get("TOKEN_EXPIRE_HOURS", "8"))
DB_PATH          = os.environ.get("DB_PATH", str(HERE.parent / "memorial.db"))
ALLOWED_ORIGINS  = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8001,http://127.0.0.1:8001,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

# ── Rate limiter ────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ─────────────────────────────────────────────────
app = FastAPI(
    title="Зоряна Пам'ять API",
    version="2.1-secure",
    docs_url=None,      # Вимкнено в production
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security Headers Middleware ─────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]          = "DENY"
        response.headers["X-XSS-Protection"]         = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"]   = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' https: data:; "
            "connect-src 'self' ws: wss:;"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── DB ──────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Password utils (bcrypt) ─────────────────────────────
def hash_pass(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_pass(p: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), hashed.encode())
    except Exception:
        return False

def hash_pass_legacy(p: str) -> str:
    """SHA256 — для перевірки старих паролів при міграції"""
    import hashlib
    return hashlib.sha256(p.encode()).hexdigest()

# ── JWT ─────────────────────────────────────────────────
def create_token(user_id: int, is_admin: bool) -> str:
    payload = {
        "sub":   str(user_id),
        "admin": bool(is_admin),
        "exp":   datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Недійсний або протермінований токен")

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Необхідна авторизація")
    return decode_token(authorization[7:])

def get_admin_user(authorization: Optional[str] = Header(None)) -> dict:
    payload = get_current_user(authorization)
    if not payload.get("admin"):
        raise HTTPException(status_code=403, detail="Доступ заборонено")
    return payload

# ── Photo URL validation (SSRF protection) ─────────────
PRIVATE_IP_RE = re.compile(
    r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|127\.|0\.0\.0\.0|localhost)",
    re.IGNORECASE,
)

def validate_photo_url(url: str) -> bool:
    if not url or not url.strip():
        return True
    try:
        p = urlparse(url.strip())
        if p.scheme not in ("https",):
            return False
        host = p.hostname or ""
        if PRIVATE_IP_RE.match(host):
            return False
        if not host or "." not in host:
            return False
        return True
    except Exception:
        return False

# ── Input sanitization ──────────────────────────────────
def sanitize(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    return html_lib.escape(str(text).strip())[:max_len]

# ── DB Init ─────────────────────────────────────────────
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
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            memorial_id INTEGER,
            fingerprint TEXT,
            ts          INTEGER
        );
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            email     TEXT NOT NULL UNIQUE,
            password  TEXT NOT NULL,
            is_admin  INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            last_seen INTEGER DEFAULT 0,
            created   INTEGER DEFAULT (strftime('%s','now'))
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
        CREATE TABLE IF NOT EXISTS search_logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            query         TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            created_at    INTEGER DEFAULT (strftime('%s','now'))
        );
        CREATE TABLE IF NOT EXISTS login_attempts (
            id  INTEGER PRIMARY KEY AUTOINCREMENT,
            ip  TEXT NOT NULL,
            ts  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_login_ip_ts ON login_attempts(ip, ts);
        CREATE INDEX IF NOT EXISTS idx_likes_log ON likes_log(memorial_id, fingerprint, ts);
        CREATE INDEX IF NOT EXISTS idx_memorials_approved ON memorials(approved);
    """)

    # Default admin — password from .env (bcrypt)
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@memorial.ua")
    admin_pass  = os.environ.get("ADMIN_PASS",  "ChangeMe_Admin2024!")
    existing = db.execute("SELECT id FROM users WHERE is_admin=1").fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (name,email,password,is_admin) VALUES (?,?,?,1)",
            ("Admin", admin_email, hash_pass(admin_pass))
        )

    # Default colors
    defaults = [
        ("bg",           "#03070e",           "Фон сторінки"),
        ("surface",      "#070d1a",           "Поверхня карток"),
        ("text_primary", "#d0dce8",           "Основний текст"),
        ("text_secondary","#8a9cb0",          "Другорядний текст"),
        ("accent",       "#00c8ff",           "Акцент (синій)"),
        ("yellow",       "#d4a800",           "Жовтий (логотип)"),
        ("yellow2",      "#f0c030",           "Жовтий яскравий"),
        ("neon_blue",    "#00ccff",           "Неон синій (межа країни)"),
        ("neon_yellow",  "#d4a800",           "Неон жовтий (межа областей)"),
        ("oblast_fill",  "#040f1e",           "Заливка областей"),
        ("oblast_stroke","rgba(90,110,130,.3)","Межі міст/сіл"),
        ("thread_color", "rgba(0,200,255,1)", "Нитки між дублікатами"),
        ("map_bg",       "#03070e",           "Фон карти"),
        ("bar_bg",       "rgba(3,7,14,.96)",  "Фон шапки"),
        ("logo_star",    "#f0c030",           "Зірка логотипу"),
        ("logo_text",    "#f0c030",           "Текст логотипу"),
        ("logo_accent",  "#00c8ff",           "Акцент логотипу"),
        ("btn_add_bg",   "#0e2860",           "Кнопка Додати (фон)"),
        ("btn_add_text", "#a8e0f8",           "Кнопка Додати (текст)"),
        ("card_bg",      "rgba(4,9,18,.98)",  "Фон картки"),
        ("label_opacity","0.45",              "Прозорість підписів областей"),
    ]
    for key, val, label in defaults:
        db.execute(
            "INSERT OR IGNORE INTO colors (key,value,label) VALUES (?,?,?)",
            (key, val, label)
        )

    # Default map labels
    if db.execute("SELECT COUNT(*) FROM map_labels").fetchone()[0] == 0:
        labels = [
            ("Закарпатська",700,4400),("Львівська",1500,3700),
            ("Волинська",1950,2100),("Івано-Франківська",2650,5200),
            ("Чернівецька",2900,5650),("Тернопільська",3430,3150),
            ("Рівненська",3440,1600),("Хмельницька",4030,3100),
            ("Житомирська",4800,2000),("Вінницька",4790,4600),
            ("Одеська",5560,6200),("Київська",6200,2200),
            ("Кіровоградська",6300,5000),("Черкаська",7180,3900),
            ("Полтавська",7960,3200),("Чернігівська",6800,1400),
            ("Миколаївська",7220,6100),("Херсонська",8810,6600),
            ("Дніпропетровська",8510,5200),("Сумська",8920,900),
            ("Запорізька",9770,5700),("Харківська",10280,3500),
            ("Донецька",11400,6000),("Луганська",12100,4100),
        ]
        db.executemany(
            "INSERT INTO map_labels (name,x,y,type) VALUES (?,?,?,'oblast')",
            labels
        )

    db.commit()
    db.close()

# ── Schemas ─────────────────────────────────────────────
class PersonIn(BaseModel):
    last:  str         = Field(..., min_length=1, max_length=100)
    first: str         = Field(..., min_length=1, max_length=100)
    mid:   str         = Field("",  max_length=100)
    birth: Optional[str] = Field(None, max_length=20)
    death: Optional[str] = Field(None, max_length=20)
    loc:   str         = Field("",  max_length=300)
    bury:  str         = Field("",  max_length=300)
    circ:  str         = Field("",  max_length=200)
    descr: str         = Field("",  max_length=2000)
    photo: str         = Field("",  max_length=500)
    color: str         = Field("#4fc3f7", max_length=20)
    pos_x: float       = Field(0.5, ge=0.0, le=1.0)
    pos_y: float       = Field(0.5, ge=0.0, le=1.0)
    grp:   str         = Field("",  max_length=100)
    added_by: str      = Field("",  max_length=100)

class PersonUpdate(BaseModel):
    last:  Optional[str]   = Field(None, max_length=100)
    first: Optional[str]   = Field(None, max_length=100)
    mid:   Optional[str]   = Field(None, max_length=100)
    birth: Optional[str]   = Field(None, max_length=20)
    death: Optional[str]   = Field(None, max_length=20)
    loc:   Optional[str]   = Field(None, max_length=300)
    bury:  Optional[str]   = Field(None, max_length=300)
    circ:  Optional[str]   = Field(None, max_length=200)
    descr: Optional[str]   = Field(None, max_length=2000)
    photo: Optional[str]   = Field(None, max_length=500)
    color: Optional[str]   = Field(None, max_length=20)
    pos_x: Optional[float] = Field(None, ge=0.0, le=1.0)
    pos_y: Optional[float] = Field(None, ge=0.0, le=1.0)
    approved: Optional[int] = None
    grp:  Optional[str]    = Field(None, max_length=100)

class UserReg(BaseModel):
    name:     str = Field(..., min_length=2, max_length=80)
    email:    str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=128)

class UserLogin(BaseModel):
    email:    str = Field(..., max_length=120)
    password: str = Field(..., max_length=128)

class ColorUpdate(BaseModel):
    key:   str = Field(..., max_length=50)
    value: str = Field(..., max_length=100)

class LabelUpdate(BaseModel):
    id:    int
    x:     float
    y:     float
    color: Optional[str] = Field(None, max_length=50)
    size:  Optional[int] = None

# ── Startup ─────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()

# ── Static & SVG ────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(str(HERE / "index.html"))

@app.get("/admin")
def admin_page():
    return FileResponse(str(HERE / "admin.html"))

@app.get("/style.css")
def css_file():
    return FileResponse(str(HERE / "style.css"), media_type="text/css")

@app.get("/ukraine-map.svg")
def svg_map():
    return FileResponse(str(HERE.parent / "ukraine-map.svg"), media_type="image/svg+xml")

# ── WebSocket online ────────────────────────────────────
connected: set = set()

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
                pass  # name received, ignore for privacy
    except Exception:
        pass
    finally:
        connected.discard(ws)
        await broadcast({"online": len(connected)})

# ── PUBLIC API ───────────────────────────────────────────

@app.get("/api/people")
@limiter.limit("60/minute")
def get_people(request: Request, page: int = 1, limit: int = 100):
    limit = min(limit, 200)
    offset = (max(page, 1) - 1) * limit
    db = get_db()
    rows = db.execute(
        "SELECT * FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    total = db.execute(
        "SELECT COUNT(*) FROM memorials WHERE approved=1"
    ).fetchone()[0]
    db.close()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}

@app.get("/api/stats")
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM memorials WHERE approved=1").fetchone()[0]
    likes = db.execute("SELECT COALESCE(SUM(likes),0) FROM memorials WHERE approved=1").fetchone()[0]
    db.close()
    return {"total": total, "likes": likes}

@app.get("/api/colors")
def get_colors():
    db = get_db()
    rows = db.execute("SELECT key,value,label FROM colors").fetchall()
    db.close()
    return {r["key"]: {"value": r["value"], "label": r["label"]} for r in rows}

@app.get("/api/labels")
def get_labels():
    db = get_db()
    rows = db.execute("SELECT * FROM map_labels ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]

# ── Search ───────────────────────────────────────────────
def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','є':'ye',
        'ж':'zh','з':'z','и':'i','і':'i','й':'y','к':'k','л':'l',
        'м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
        'у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
        'щ':'shch','ю':'yu','я':'ya','ь':'','ї':'yi','ё':'yo',
    }
    return "".join(translit.get(c, c) for c in s)

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

@app.get("/api/search")
@limiter.limit("30/minute")
def search(request: Request, q: str = ""):
    q = q.strip()[:100]
    if len(q) < 2:
        return []
    db = get_db()
    rows = db.execute("SELECT * FROM memorials WHERE approved=1").fetchall()

    scored = []
    for row in rows:
        r = dict(row)
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

    # Log search (trim old records)
    try:
        db.execute(
            "INSERT INTO search_logs (query, results_count, created_at) VALUES (?,?,?)",
            (q, len(results), int(time.time()))
        )
        db.execute(
            "DELETE FROM search_logs WHERE id IN "
            "(SELECT id FROM search_logs ORDER BY id DESC LIMIT -1 OFFSET 10000)"
        )
        db.commit()
    except Exception:
        pass
    db.close()
    return results

@app.post("/api/like/{mid}")
@limiter.limit("20/minute")
def like(request: Request, mid: int, fp: Optional[str] = "anon"):
    if mid <= 0:
        raise HTTPException(400, "Невірний ID")
    fp = (fp or "anon")[:64]
    now = int(time.time())
    db = get_db()
    if db.execute(
        "SELECT COUNT(*) FROM likes_log WHERE memorial_id=? AND fingerprint=? AND ts>?",
        (mid, fp, now - 2)
    ).fetchone()[0]:
        db.close()
        return {"ok": False, "reason": "cooldown"}
    db.execute(
        "INSERT INTO likes_log (memorial_id,fingerprint,ts) VALUES (?,?,?)",
        (mid, fp, now)
    )
    db.execute("UPDATE memorials SET likes=likes+1 WHERE id=?", (mid,))
    db.commit()
    row = db.execute("SELECT likes FROM memorials WHERE id=?", (mid,)).fetchone()
    db.close()
    return {"ok": True, "likes": row["likes"] if row else 0}

# ── AUTH ─────────────────────────────────────────────────
@app.post("/api/auth/register")
@limiter.limit("3/hour")
def register(request: Request, u: UserReg):
    email = u.email.lower().strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(400, "Невірний формат email")
    db = get_db()
    if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
        db.close()
        raise HTTPException(400, "Email вже зареєстрований")
    db.execute(
        "INSERT INTO users (name,email,password) VALUES (?,?,?)",
        (sanitize(u.name, 80), email, hash_pass(u.password))
    )
    db.commit()
    row = db.execute(
        "SELECT id,name,email,is_admin FROM users WHERE email=?", (email,)
    ).fetchone()
    db.close()
    user = dict(row)
    token = create_token(user["id"], bool(user["is_admin"]))
    return {"ok": True, "token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "is_admin": user["is_admin"]}}

@app.post("/api/auth/login")
@limiter.limit("5/minute")
def login(request: Request, u: UserLogin):
    ip = request.client.host if request.client else "unknown"
    now = int(time.time())
    db = get_db()

    # Check login attempts (block after 5 fails in 15 min)
    attempts = db.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE ip=? AND ts>?",
        (ip, now - 900)
    ).fetchone()[0]
    if attempts >= 5:
        db.close()
        raise HTTPException(429, "Забагато спроб входу. Спробуйте через 15 хвилин.")

    email = u.email.lower().strip()
    row = db.execute(
        "SELECT id,name,email,is_admin,is_banned,password FROM users WHERE email=?",
        (email,)
    ).fetchone()

    if not row:
        db.execute("INSERT INTO login_attempts (ip,ts) VALUES (?,?)", (ip, now))
        db.commit()
        db.close()
        raise HTTPException(401, "Невірний email або пароль")

    # Try bcrypt first, fallback to SHA256 (legacy migration)
    stored_pass = row["password"]
    valid = verify_pass(u.password, stored_pass)
    if not valid:
        # Legacy SHA256 check + upgrade to bcrypt
        if stored_pass == hash_pass_legacy(u.password):
            valid = True
            db.execute("UPDATE users SET password=? WHERE id=?",
                       (hash_pass(u.password), row["id"]))
            db.commit()

    if not valid:
        db.execute("INSERT INTO login_attempts (ip,ts) VALUES (?,?)", (ip, now))
        db.commit()
        db.close()
        raise HTTPException(401, "Невірний email або пароль")

    if row["is_banned"]:
        db.close()
        raise HTTPException(403, "Акаунт заблоковано")

    # Clean old attempts + update last_seen
    db.execute("DELETE FROM login_attempts WHERE ip=? AND ts<?", (ip, now - 900))
    db.execute("UPDATE users SET last_seen=? WHERE id=?", (now, row["id"]))
    db.commit()
    db.close()

    token = create_token(row["id"], bool(row["is_admin"]))
    return {
        "ok": True,
        "token": token,
        "user": {
            "id":       row["id"],
            "name":     row["name"],
            "email":    row["email"],
            "is_admin": row["is_admin"],
        }
    }

@app.post("/api/people")
@limiter.limit("10/hour")
def add_person(request: Request, p: PersonIn, authorization: Optional[str] = Header(None)):
    # Require auth
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Необхідна авторизація для додавання запису")
    try:
        payload = decode_token(authorization[7:])
    except Exception:
        raise HTTPException(401, "Недійсний токен")

    # Validate photo URL
    if p.photo and not validate_photo_url(p.photo):
        raise HTTPException(400, "Фото: дозволено лише https:// посилання на зовнішні ресурси")

    db = get_db()
    db.execute(
        """INSERT INTO memorials
        (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,pos_x,pos_y,grp,added_by,approved)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
        (
            sanitize(p.last, 100), sanitize(p.first, 100), sanitize(p.mid, 100),
            p.birth, p.death,
            sanitize(p.loc, 300), sanitize(p.bury, 300), sanitize(p.circ, 200),
            sanitize(p.descr, 2000), p.photo.strip() if p.photo else "",
            p.color, p.pos_x, p.pos_y,
            sanitize(p.grp, 100), sanitize(p.added_by, 100)
        )
    )
    db.commit()
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return {"ok": True, "id": new_id, "message": "Надіслано на модерацію. Дякуємо!"}

# ── ADMIN API (JWT-protected) ────────────────────────────

def _admin(authorization: Optional[str] = Header(None)) -> dict:
    return get_admin_user(authorization)

@app.get("/api/admin/pending")
def pending(adm: dict = Depends(_admin)):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM memorials WHERE approved=0 ORDER BY rowid DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/approve/{mid}")
def approve(mid: int, adm: dict = Depends(_admin)):
    db = get_db()
    db.execute("UPDATE memorials SET approved=1 WHERE id=?", (mid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/admin/memorial/{mid}")
def delete_memorial(mid: int, adm: dict = Depends(_admin)):
    db = get_db()
    db.execute("DELETE FROM memorials WHERE id=?", (mid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid: int, p: PersonUpdate, adm: dict = Depends(_admin)):
    if p.photo is not None and p.photo and not validate_photo_url(p.photo):
        raise HTTPException(400, "Невалідний URL фото")
    db = get_db()
    fields, vals = [], []
    for f, v in p.dict(exclude_none=True).items():
        fields.append(f"{f}=?")
        vals.append(v)
    if not fields:
        return {"ok": False, "reason": "no fields"}
    vals.append(mid)
    db.execute(f"UPDATE memorials SET {','.join(fields)} WHERE id=?", vals)
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/api/admin/users")
def get_users(adm: dict = Depends(_admin)):
    db = get_db()
    rows = db.execute(
        "SELECT id,name,email,is_admin,is_banned,last_seen,created FROM users ORDER BY id DESC"
    ).fetchall()
    db.close()
    now = int(time.time())
    result = []
    for r in rows:
        d = dict(r)
        d["online"] = (now - r["last_seen"]) < 120
        result.append(d)
    return result

@app.post("/api/admin/ban/{uid}")
def ban_user(uid: int, adm: dict = Depends(_admin)):
    db = get_db()
    db.execute("UPDATE users SET is_banned=1 WHERE id=?", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.post("/api/admin/unban/{uid}")
def unban_user(uid: int, adm: dict = Depends(_admin)):
    db = get_db()
    db.execute("UPDATE users SET is_banned=0 WHERE id=?", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/color")
def update_color(c: ColorUpdate, adm: dict = Depends(_admin)):
    db = get_db()
    db.execute("UPDATE colors SET value=? WHERE key=?", (c.value, c.key))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/colors/batch")
def update_colors_batch(colors: List[ColorUpdate], adm: dict = Depends(_admin)):
    db = get_db()
    for c in colors:
        db.execute("UPDATE colors SET value=? WHERE key=?", (c.value, c.key))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/label/{lid}")
def update_label(lid: int, l: LabelUpdate, adm: dict = Depends(_admin)):
    db = get_db()
    fields, vals = ["x=?", "y=?"], [l.x, l.y]
    if l.color:
        fields.append("color=?")
        vals.append(l.color)
    if l.size:
        fields.append("size=?")
        vals.append(l.size)
    vals.append(lid)
    db.execute(f"UPDATE map_labels SET {','.join(fields)} WHERE id=?", vals)
    db.commit()
    db.close()
    return {"ok": True}

@app.get("/api/admin/stats")
def admin_stats(adm: dict = Depends(_admin)):
    db = get_db()
    total    = db.execute("SELECT COUNT(*) FROM memorials").fetchone()[0]
    approved = db.execute("SELECT COUNT(*) FROM memorials WHERE approved=1").fetchone()[0]
    pending  = db.execute("SELECT COUNT(*) FROM memorials WHERE approved=0").fetchone()[0]
    users    = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    likes    = db.execute("SELECT COALESCE(SUM(likes),0) FROM memorials").fetchone()[0]
    searches = db.execute("SELECT COUNT(*) FROM search_logs").fetchone()[0]
    db.close()
    return {
        "total": total, "approved": approved, "pending": pending,
        "users": users, "likes": likes, "online": len(connected),
        "searches": searches,
    }

@app.get("/api/admin/search_stats")
def search_stats(adm: dict = Depends(_admin)):
    db = get_db()
    top = db.execute(
        "SELECT query, COUNT(*) as cnt FROM search_logs "
        "GROUP BY LOWER(TRIM(query)) ORDER BY cnt DESC LIMIT 20"
    ).fetchall()
    db.close()
    return {"top_queries": [{"query": r[0], "count": r[1]} for r in top]}

# ── Static mount (last, lowest priority) ────────────────
app.mount("/js",  StaticFiles(directory=str(HERE.parent / "js")),  name="js")
app.mount("/img", StaticFiles(directory=str(HERE.parent / "img")), name="img")
