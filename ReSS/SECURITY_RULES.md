# SECURITY_RULES.md — Правила безпеки проекту "Зоряна Пам'ять"

> Дата: 09.04.2026  
> Статус: Обов'язково до виконання перед публічним запуском

---

## ЗМІСТ

1. [Поточні критичні вразливості](#1-поточні-критичні-вразливості)
2. [Захист від атак на сервер (DDoS, brute force)](#2-захист-від-атак-на-сервер)
3. [Захист бази даних](#3-захист-бази-даних)
4. [Захист API](#4-захист-api)
5. [Автентифікація і паролі](#5-автентифікація-і-паролі)
6. [Захист від ін'єкцій і XSS](#6-захист-від-ін'єкцій-і-xss)
7. [HTTPS і мережева безпека](#7-https-і-мережева-безпека)
8. [Захист файлів і сервера](#8-захист-файлів-і-сервера)
9. [Моніторинг і реагування](#9-моніторинг-і-реагування)
10. [Інтеграція з порталом ДІЯ — правила безпеки](#10-інтеграція-з-порталом-дія)
11. [Чек-лист перед запуском](#11-чек-лист-перед-запуском)

---

## 1. Поточні критичні вразливості

Наведені нижче проблеми існують прямо зараз у коді і потребують **негайного виправлення**:

### КРИТИЧНО
| # | Файл | Проблема | Ризик |
|---|------|----------|-------|
| 1 | `Paskal.py:23` | `SHA256` для паролів замість bcrypt | Злом усіх паролів за лічені хвилини при витоку DB |
| 2 | `Paskal.py:85-88` | Стандартний пароль адміна `admin@admin.com / Admin` | Перший хакер ввійде в адмінку без зусиль |
| 3 | `Paskal.py` | CORS: `allow_origins=["*"]` — дозволено всі домени | CSRF-атаки з будь-якого сайту |
| 4 | `Paskal.py` | Відсутній rate limiting на всіх ендпоінтах | DDoS, brute force, спам в базі |
| 5 | `Paskal.py` | Admin-ендпоінти приймають email/password у кожному запиті | Перехоплення credentials в мережі |
| 6 | `Paskal.py` | Поле `photo` — URL без перевірки | SSRF-атака (сервер робить запит на внутрішні адреси) |
| 7 | `index.html` | Прийом photo URL без sanitization | Завантаження шкідливого контенту |
| 8 | `Paskal.py` | Відсутня пагінація — `/api/people` повертає всі 500+ записів | Легкий DoS через повторні запити |

### СЕРЙОЗНО
| # | Проблема | Ризик |
|---|----------|-------|
| 9 | Немає логування помилок та підозрілої активності | Злом непомітний |
| 10 | Файл `memorial.db` доступний через веб-сервер | Повне скачування бази |
| 11 | Немає обмеження розміру полів у формі | Переповнення бази, DoS |
| 12 | Відсутня валідація email при реєстрації | Спам-акаунти, підроблені акаунти |
| 13 | `search_logs` записує кожен запит без обмеження | Заповнення диску |

---

## 2. Захист від атак на сервер

### 2.1 Rate Limiting (обмеження запитів)

Встановити бібліотеку `slowapi` і додати ліміти:

```python
# pip install slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Ліміти для ендпоінтів:
@app.post("/api/auth/login")
@limiter.limit("5/minute")          # Максимум 5 спроб входу на хвилину
async def login(...): ...

@app.post("/api/auth/register")
@limiter.limit("3/hour")            # Максимум 3 реєстрації за годину з 1 IP

@app.post("/api/people")
@limiter.limit("10/hour")           # Максимум 10 нових меморіалів за годину

@app.get("/api/search")
@limiter.limit("30/minute")         # Максимум 30 пошукових запитів на хвилину

@app.post("/api/like/{id}")
@limiter.limit("20/minute")         # Захист від накрутки лайків
```

### 2.2 Захист від DDoS через nginx

Якщо сервіс за nginx, додати в конфіг:

```nginx
# /etc/nginx/nginx.conf
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_conn_zone $binary_remote_addr zone=conn:10m;

server {
    # Загальний ліміт для API
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        limit_conn conn 5;
    }

    # Суворий ліміт для входу
    location /api/auth/ {
        limit_req zone=login burst=3;
    }

    # Максимальний розмір тіла запиту
    client_max_body_size 2M;
}
```

### 2.3 Пагінація для `/api/people`

```python
# Замість повернення всіх записів — сторінки:
@app.get("/api/people")
async def get_people(page: int = 1, limit: int = 50):
    if limit > 100:
        limit = 100  # Максимум 100 за раз
    offset = (page - 1) * limit
    ...
```

### 2.4 Тайм-аути запитів

```python
# uvicorn запуск з тайм-аутами:
# python -m uvicorn Paskal:app --timeout-keep-alive 30 --limit-concurrency 100
```

---

## 3. Захист бази даних

### 3.1 Захист файлу memorial.db

Файл бази даних **не повинен** бути доступний через HTTP. Переконайтесь:

```python
# Paskal.py — НЕ монтувати папку де знаходиться DB як статику
# НЕПРАВИЛЬНО:
# app.mount("/", StaticFiles(directory="."), name="root")

# База має лежати ПОЗА веб-директорією, наприклад:
DB = "../data/memorial.db"  # Папка data не доступна через HTTP
```

Або заборонити через nginx:
```nginx
location ~* \.(db|sqlite|sql|bak|log)$ {
    deny all;
    return 404;
}
```

### 3.2 Регулярні резервні копії

```bash
# Резервна копія бази щодня (cron або Task Scheduler Windows):
# 0 3 * * * cp /path/to/memorial.db /backups/memorial_$(date +%Y%m%d).db

# Зберігати останні 30 копій, старіші видаляти автоматично
```

### 3.3 Обмеження розміру полів

```python
class MemorialCreate(BaseModel):
    last:  str = Field(..., max_length=100)
    first: str = Field(..., max_length=100)
    mid:   str = Field("",  max_length=100)
    birth: str = Field("",  max_length=20)
    death: str = Field("",  max_length=20)
    loc:   str = Field("",  max_length=300)
    bury:  str = Field("",  max_length=300)
    circ:  str = Field("",  max_length=500)
    descr: str = Field("",  max_length=2000)
    photo: str = Field("",  max_length=500)
    grp:   str = Field("",  max_length=100)
```

### 3.4 Обмеження логів пошуку

```python
# Зберігати лише останні N записів, щоб диск не переповнювався:
def log_search(query, count):
    db.execute("INSERT INTO search_logs (query, results_count) VALUES (?,?)", (query, count))
    # Видаляти старі записи якщо більше 10000
    db.execute("DELETE FROM search_logs WHERE id IN (SELECT id FROM search_logs ORDER BY id DESC LIMIT -1 OFFSET 10000)")
    db.commit()
```

---

## 4. Захист API

### 4.1 JWT-токени замість передачі пароля

Зараз адмін-запити передають email+password при кожному запиті — це небезпечно.

**Виправлення — JWT-авторизація:**

```python
# pip install python-jose[cryptography]
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.environ.get("JWT_SECRET")  # Зберігати в .env, НЕ в коді!
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

def create_token(user_id: int, is_admin: bool) -> str:
    payload = {
        "sub": str(user_id),
        "admin": is_admin,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Невірний токен")

# Захищений ендпоінт:
@app.get("/api/admin/users")
async def admin_users(token: str = Header(...)):
    payload = verify_token(token)
    if not payload.get("admin"):
        raise HTTPException(status_code=403)
    ...
```

### 4.2 CORS — обмежити лише ваш домен

```python
# Paskal.py — ЗАМІНИТИ allow_origins=["*"] на:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://zoryana-pamyat.ua",       # ваш продакшн-домен
        "https://www.zoryana-pamyat.ua",
        "http://localhost:8000",            # тільки для розробки
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 4.3 Захист photo URL від SSRF

```python
import re
from urllib.parse import urlparse

ALLOWED_IMAGE_HOSTS = [
    "i.imgur.com", "upload.wikimedia.org",
    "sun9-*.userapi.com", "*.cloudfront.net",
    # Додати дозволені хостинги фото
]

def validate_photo_url(url: str) -> bool:
    if not url:
        return True
    try:
        parsed = urlparse(url)
        # Заборонити внутрішні IP-адреси (SSRF-захист)
        if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
            return False
        # Заборонити приватні мережі
        if re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", parsed.hostname or ""):
            return False
        # Дозволити тільки https
        if parsed.scheme != "https":
            return False
        return True
    except:
        return False
```

### 4.4 Валідація вхідних даних

```python
import html

def sanitize_text(text: str) -> str:
    """Очистити від HTML-тегів і небезпечних символів"""
    if not text:
        return ""
    # Видалити HTML теги
    text = html.escape(text.strip())
    # Обмежити небезпечні символи
    return text[:2000]  # максимальна довжина
```

### 4.5 Security Headers

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # CSP — Content Security Policy (важливо!)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # WebGL потребує inline
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' https: data:; "
            "connect-src 'self' wss:;"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## 5. Автентифікація і паролі

### 5.1 Замінити SHA256 на bcrypt

```python
# pip install bcrypt
import bcrypt

def hash_pass(password: str) -> str:
    """Безпечне хешування через bcrypt (замість SHA256)"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_pass(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ВАЖЛИВО: після переходу на bcrypt —
# скинути паролі всіх існуючих користувачів через email
```

### 5.2 Змінити дані адміністратора

```python
# ОБОВ'ЯЗКОВО змінити стандартний акаунт:
# - Email: замість admin@admin.com — унікальний приватний email
# - Password: мінімум 16 символів, велика/мала літера, цифри, спецсимволи
# Наприклад: "Zirka2024!Mem#7k"

# В init_db() — не створювати адміна автоматично в production:
if os.environ.get("ENV") != "production":
    # Тільки в режимі розробки
    create_default_admin()
```

### 5.3 Блокування після невдалих спроб

```python
# Зберігати в базі або Redis кількість невдалих спроб:
@app.post("/api/auth/login")
async def login(data: LoginData):
    # Перевірити кількість спроб за останні 15 хвилин
    attempts = db.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE ip=? AND ts > ?",
        (request.client.host, int(time.time()) - 900)
    ).fetchone()[0]

    if attempts >= 5:
        raise HTTPException(429, "Забагато спроб. Спробуйте через 15 хвилин.")

    # Логувати кожну спробу
    db.execute("INSERT INTO login_attempts (ip, ts) VALUES (?,?)",
               (request.client.host, int(time.time())))
```

### 5.4 Нова таблиця для спроб входу

```sql
CREATE TABLE IF NOT EXISTS login_attempts (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    ip  TEXT NOT NULL,
    ts  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip_ts ON login_attempts(ip, ts);
```

---

## 6. Захист від ін'єкцій і XSS

### 6.1 SQL — параметризовані запити (вже є, перевірити)

```python
# ПРАВИЛЬНО (параметризований запит — захист від SQL Injection):
db.execute("SELECT * FROM memorials WHERE id = ?", (memorial_id,))

# НЕПРАВИЛЬНО (вразливо до SQL Injection):
db.execute(f"SELECT * FROM memorials WHERE id = {memorial_id}")  # НІКОЛИ так!

# Перевірити весь код — жодного f-string або конкатенації в SQL-запитах!
```

### 6.2 XSS — екранування вводу

```python
# Всі текстові поля що відображаються на фронтенді —
# обов'язково через html.escape() перед збереженням в базу

# АБО на фронтенді — ніколи не використовувати innerHTML з даними з API:
# НЕБЕЗПЕЧНО: element.innerHTML = data.name
# БЕЗПЕЧНО:   element.textContent = data.name
```

### 6.3 Перевірка типів ID

```python
# Всі ID-параметри в маршрутах перевіряти:
@app.post("/api/like/{memorial_id}")
async def like(memorial_id: int):  # int — FastAPI автоматично відхилить нечисловий ID
    if memorial_id <= 0:
        raise HTTPException(400, "Невірний ID")
```

---

## 7. HTTPS і мережева безпека

### 7.1 HTTPS — обов'язково

Перед публічним запуском:
- Отримати SSL-сертифікат (Let's Encrypt — безкоштовно)
- Увімкнути HSTS-заголовок
- Перенаправляти HTTP → HTTPS

```nginx
server {
    listen 80;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    ssl_certificate     /etc/letsencrypt/live/your-domain.ua/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.ua/privkey.pem;

    # Сучасні протоколи тільки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # HSTS — браузер запам'ятає що завжди потрібен HTTPS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### 7.2 Приховати версію сервера

```nginx
server_tokens off;  # Не показувати nginx version в заголовках
```

```python
# Uvicorn — не показувати версію:
app = FastAPI(docs_url=None, redoc_url=None)  # Вимкнути /docs в production
```

### 7.3 Firewall — відкрити тільки потрібні порти

```bash
# Дозволити тільки:
# 443 (HTTPS)
# 80  (HTTP → редирект на HTTPS)
# 22  (SSH — тільки з вашого IP!)
# Все інше — заблокувати, включно з портом 8000!
```

---

## 8. Захист файлів і сервера

### 8.1 .env файл для секретів

```bash
# Створити файл .env (НІКОЛИ не додавати в git!)
JWT_SECRET=ваш_дуже_довгий_секретний_ключ_мінімум_32_символи
ADMIN_EMAIL=ваш_приватний@email.ua
ADMIN_PASSWORD=SuperSecretPass123!
DB_PATH=/var/data/memorial.db
ENV=production
```

```python
# Paskal.py:
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET не встановлено!")
```

```gitignore
# .gitignore — додати:
.env
*.db
*.sqlite
venv/
__pycache__/
*.log
```

### 8.2 Заборонити доступ до системних файлів

```nginx
# Заборонити через nginx:
location ~ /\. {
    deny all;  # Приховані файли (.env, .git тощо)
}

location ~* \.(py|pyc|db|sqlite|sql|log|env|bak|cfg|ini)$ {
    deny all;
    return 404;
}

location /.git {
    deny all;  # Ніколи не відкривати git репозиторій!
}
```

### 8.3 Мінімальні права доступу

```bash
# Файли проекту — мінімальні права:
chmod 640 memorial.db       # Читати тільки власник і група
chmod 600 .env              # Тільки власник
chmod 755 /var/www/project  # Директорія

# Запускати сервер від окремого непривілейованого користувача:
useradd -r -s /bin/false zoryana
chown -R zoryana:zoryana /var/www/project
sudo -u zoryana uvicorn Paskal:app
```

---

## 9. Моніторинг і реагування

### 9.1 Логування підозрілої активності

```python
import logging

# Налаштувати логер:
logging.basicConfig(
    filename="/var/log/zoryana/security.log",
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s"
)

security_log = logging.getLogger("security")

# Логувати підозрілі події:
def log_security(event: str, ip: str, detail: str = ""):
    security_log.warning(f"[{event}] IP={ip} {detail}")

# Приклади подій для логування:
# - Невдалий вхід (5+ разів)
# - Запит до неіснуючого адмін-ендпоінту
# - Невалідні токени
# - Підозрілі пошукові запити (SQL-ін'єкції)
# - Масові запити з одного IP
```

### 9.2 Алерти при критичних подіях

Налаштувати сповіщення на email або Telegram при:
- 10+ невдалих входів за 5 хвилин
- Спроби зламати адмін-панель
- Аномальне навантаження на базу
- Помилки 500 в серверних логах

### 9.3 Регулярний аудит

- Щомісяця переглядати логи безпеки
- Перевіряти список користувачів — видаляти неактивних
- Оновлювати залежності (`pip list --outdated`)
- Перевіряти чи не з'явились нові CVE для FastAPI, uvicorn

---

## 10. Інтеграція з порталом ДІЯ

### 10.1 Загальна архітектура ДІЯ.Sign / ДІЯ.ID

Портал **ДІЯ** надає авторизацію через:
- **OAuth 2.0 + OpenID Connect** (стандартний протокол)
- **ДІЯ.Sign** — цифровий підпис документів
- **ДІЯ.ID** — верифікація особи через мобільний застосунок

**Важливо:** Інтеграція з ДІЯ вимагає офіційної реєстрації на порталі [id.gov.ua](https://id.gov.ua) та отримання `client_id` і `client_secret`.

### 10.2 Технічна схема авторизації через ДІЯ

```
Користувач                  Ваш сервер              ДІЯ-сервер (id.gov.ua)
    |                           |                           |
    |-- Натискає "Увійти ДІЯ" ->|                           |
    |                           |-- /oauth/authorize ------>|
    |<--- Redirect на ДІЯ ------|                           |
    |-- Авторизується в ДІЯ ----------------------->--------|
    |<-- Redirect на ваш callback з code ------------------|
    |                           |<-- code від користувача --|
    |                           |-- POST /oauth/token ----->|
    |                           |<-- access_token + id_token|
    |                           |-- Верифікувати токен ---->|
    |                           |-- Отримати дані юзера --->|
    |<-- Ваш JWT-токен сесії ---|                           |
```

### 10.3 Зміни в базі даних для ДІЯ

```sql
-- Додати поля до таблиці users:
ALTER TABLE users ADD COLUMN diia_id TEXT UNIQUE;        -- Унікальний ID від ДІЯ
ALTER TABLE users ADD COLUMN diia_verified INTEGER DEFAULT 0;  -- Верифіковано через ДІЯ
ALTER TABLE users ADD COLUMN real_name TEXT DEFAULT '';  -- Справжнє ПІБ з ДІЯ
ALTER TABLE users ADD COLUMN auth_method TEXT DEFAULT 'password'; -- 'password' або 'diia'

-- Окрема таблиця для OAuth сесій:
CREATE TABLE IF NOT EXISTS oauth_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    state      TEXT NOT NULL UNIQUE,   -- CSRF-захист OAuth
    user_id    INTEGER,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    expires_at INTEGER NOT NULL        -- Короткий час життя (10 хвилин)
);
```

### 10.4 Backend — реалізація OAuth через ДІЯ

```python
import secrets
import httpx  # pip install httpx

DIIA_CLIENT_ID     = os.environ.get("DIIA_CLIENT_ID")
DIIA_CLIENT_SECRET = os.environ.get("DIIA_CLIENT_SECRET")
DIIA_REDIRECT_URI  = "https://your-domain.ua/api/auth/diia/callback"

DIIA_AUTH_URL  = "https://id.gov.ua/connect/authorize"
DIIA_TOKEN_URL = "https://id.gov.ua/connect/token"
DIIA_USERINFO  = "https://id.gov.ua/connect/userinfo"

@app.get("/api/auth/diia")
async def diia_login():
    """Перенаправити користувача на ДІЯ"""
    # State — захист від CSRF-атак (обов'язково!)
    state = secrets.token_urlsafe(32)

    # Зберегти state в базі (видаляється після використання)
    db.execute(
        "INSERT INTO oauth_sessions (state, expires_at) VALUES (?,?)",
        (state, int(time.time()) + 600)  # 10 хвилин
    )
    db.commit()

    params = {
        "response_type": "code",
        "client_id": DIIA_CLIENT_ID,
        "redirect_uri": DIIA_REDIRECT_URI,
        "scope": "openid profile",  # Мінімально необхідні права!
        "state": state,
    }
    url = DIIA_AUTH_URL + "?" + "&".join(f"{k}={v}" for k,v in params.items())
    return {"redirect_url": url}


@app.get("/api/auth/diia/callback")
async def diia_callback(code: str, state: str):
    """Обробити повернення від ДІЯ"""

    # 1. Перевірити state (захист від CSRF)
    session = db.execute(
        "SELECT * FROM oauth_sessions WHERE state=? AND expires_at > ?",
        (state, int(time.time()))
    ).fetchone()

    if not session:
        raise HTTPException(400, "Невірний або протермінований state")

    # Видалити використаний state (одноразовий!)
    db.execute("DELETE FROM oauth_sessions WHERE state=?", (state,))

    # 2. Обміняти code на токен
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(DIIA_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DIIA_REDIRECT_URI,
            "client_id": DIIA_CLIENT_ID,
            "client_secret": DIIA_CLIENT_SECRET,
        })

    if token_resp.status_code != 200:
        raise HTTPException(400, "Помилка отримання токена від ДІЯ")

    tokens = token_resp.json()
    access_token = tokens["access_token"]

    # 3. Отримати дані користувача
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            DIIA_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    diia_user = user_resp.json()
    diia_id = diia_user.get("sub")  # Унікальний ID від ДІЯ

    # 4. Знайти або створити користувача
    user = db.execute(
        "SELECT * FROM users WHERE diia_id=?", (diia_id,)
    ).fetchone()

    if not user:
        # Новий користувач через ДІЯ
        db.execute(
            "INSERT INTO users (name, email, password, diia_id, diia_verified, auth_method) VALUES (?,?,?,?,1,'diia')",
            (diia_user.get("name", ""), diia_user.get("email", ""), "", diia_id)
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE diia_id=?", (diia_id,)).fetchone()

    # 5. Видати JWT-токен вашого сервісу
    token = create_token(user["id"], bool(user["is_admin"]))
    return {"token": token, "name": user["name"]}
```

### 10.5 Що ЗАБОРОНЕНО при роботі з ДІЯ

| Заборона | Причина |
|----------|---------|
| Зберігати дані паспорта, ІПН, РНОКПП | Порушення Закону про персональні дані |
| Передавати дані ДІЯ третім особам | Умови використання ДІЯ API |
| Кешувати access_token ДІЯ на сервері | Токен має короткий час життя, кеш = вразливість |
| Логувати тіло відповіді від ДІЯ | Особисті дані не мають потрапляти в логи |
| Зберігати `id_token` ДІЯ в базі | Тільки `sub` (анонімний ID) |
| Запитувати зайві scope | Тільки мінімально необхідні: `openid profile` |

### 10.6 Необхідні зміни при впровадженні ДІЯ

1. **Політика конфіденційності** — додати на сайт, описати які дані збираються
2. **Згода на обробку даних** — чекбокс при першій авторизації
3. **Право на видалення** — ендпоінт `DELETE /api/account` для видалення акаунту
4. **Шифрування персональних даних** — справжні імена з ДІЯ шифрувати в базі
5. **Окремий .env для продакшн** — окремі `DIIA_CLIENT_ID/SECRET` для тест і prod середовищ

```python
# Шифрування справжнього імені (з ДІЯ):
from cryptography.fernet import Fernet  # pip install cryptography

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")  # В .env!
fernet = Fernet(ENCRYPTION_KEY)

def encrypt_name(name: str) -> str:
    return fernet.encrypt(name.encode()).decode()

def decrypt_name(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()
```

---

## 11. Чек-лист перед запуском

### Критичні (обов'язкові)
- [ ] Замінити SHA256 → bcrypt для паролів
- [ ] Змінити пароль адміна (не `Admin`, мінімум 16 символів)
- [ ] Налаштувати HTTPS / SSL-сертифікат
- [ ] Закрити порт 8000, всі запити через nginx на 443
- [ ] Налаштувати CORS — тільки ваш домен
- [ ] Перенести `memorial.db` поза веб-директорію
- [ ] Заборонити доступ до `.py`, `.db`, `.env` файлів через HTTP
- [ ] Додати rate limiting на login (5/хв) та реєстрацію (3/год)
- [ ] Вимкнути `/docs` і `/redoc` (FastAPI API-документацію) в production
- [ ] Всі секрети перенести в `.env` (JWT_SECRET, паролі, ключі)
- [ ] Додати `.env` і `*.db` в `.gitignore`

### Важливі (рекомендовані)
- [ ] Замінити email/password в адмін-запитах на JWT-токени
- [ ] Додати блокування IP після 5 невдалих спроб входу
- [ ] Налаштувати автоматичні бекапи бази (щодня)
- [ ] Додати логування підозрілої активності
- [ ] Пагінація `/api/people` (не повертати всі 500+ записів за раз)
- [ ] Валідація photo URL (захист від SSRF)
- [ ] Додати Security Headers middleware
- [ ] Обмежити розмір полів у Pydantic-моделях

### Для ДІЯ-інтеграції
- [ ] Зареєструватися на id.gov.ua і отримати credentials
- [ ] Додати поля `diia_id`, `diia_verified` в таблицю users
- [ ] Реалізувати OAuth 2.0 flow з перевіркою state
- [ ] Зашифрувати персональні дані з ДІЯ (real_name)
- [ ] Додати Політику конфіденційності на сайт
- [ ] Додати ендпоінт видалення акаунту
- [ ] Окремі credentials ДІЯ для тест і production середовищ

---

## Корисні посилання

- [ДІЯ API документація](https://api.diia.gov.ua) — офіційна документація інтеграції
- [id.gov.ua](https://id.gov.ua) — реєстрація OAuth-клієнта
- [OWASP Top 10](https://owasp.org/Top10/) — 10 найпоширеніших вразливостей
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) — офіційна документація
- [Let's Encrypt](https://letsencrypt.org) — безкоштовні SSL-сертифікати
- [Закон України про захист персональних даних](https://zakon.rada.gov.ua/laws/show/2297-17)

---

*Документ складено на основі аналізу коду проекту. Оновлювати при кожній зміні архітектури.*
