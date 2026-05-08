# CLAUDE.md — Зоряна Памʼять (Zoryana Memory)

> Цей файл читається Claude Code на початку кожної сесії. При зміні структури проекту — оновлювати цей файл.

---

## 1. ЗАГАЛЬНИЙ ОПИС

**Зоряна Памʼять** — українська меморіальна платформа, де зберігаються відомості про загиблих захисників України. Сайт відображає інтерактивну карту з маркерами-зірками, картками осіб, пошуком, соціальними функціями (лайки), адміністративною панеллю.

- **Prod URL**: локальний dev (`localhost`), prod через Nginx → Gunicorn
- **Розрахункове навантаження**: до **500 одночасних відвідувачів**
- **База даних**: MySQL/MariaDB, схема `zoryana_pamyat` (PhpMyAdmin)
- **Старий файл `memorial.db` (SQLite) — НЕ ВИКОРИСТОВУЄТЬСЯ, ігнорувати**

---

## 2. ТЕХНІЧНИЙ СТЕК

| Компонент | Технологія | Деталі |
|-----------|-----------|--------|
| Backend | FastAPI (Python) | Async, Pydantic validation |
| ASGI Server | Uvicorn | Dev: `uvicorn Paskal:app --reload --port 8000` |
| Prod Server | Gunicorn + UvicornWorker | 8 воркерів, `gunicorn.conf.py` |
| Database | MySQL/MariaDB | utf8mb4_unicode_ci, DB: `zoryana_pamyat` |
| Кеш | Redis | Опціональний, TTL 60с, авто-деградація якщо відсутній |
| Auth | bcrypt (12 rounds) + Google OAuth + Дія | Cookies 7 днів |
| Frontend | HTML5 + Vanilla JS | Без фреймворків |
| CSS | CSS Custom Properties | Темна/світла теми |
| Анімація | WebGL (fluid simulation) | Дим, хвилі, ефекти |
| Моніторинг | Prometheus + Grafana | `/metrics` endpoint |
| Конфігурація | `.env` файл | DB, OAuth, Redis credentials |

---

## 3. СТРУКТУРА ФАЙЛІВ

```
treetex/
├── Paskal.py            # Весь backend (FastAPI, ~5500+ рядків)
├── index.html           # Головна публічна сторінка (~1MB)
├── admin.html           # Адмін-панель (~1.3MB)
├── Style.css            # Глобальні стилі (36KB)
├── script.js            # Frontend JS (53KB)
├── faq.html / rules.html / terms.html
├── ukraine-map.svg      # Інтерактивна SVG карта (883KB)
├── favicon.ico
├── iconfont.ttf         # Кастомний шрифт іконок
├── gunicorn.conf.py     # Prod налаштування
├── migrations.sql       # Індекси та міграції БД
├── setup_awards.py      # Скрипт масового завантаження зображень нагород + заповнення awards_catalog
├── requirements.txt     # Python залежності
├── .env                 # Секрети (не комітити!)
├── .env.example         # Шаблон .env
├── start.bat / start.sh # Запуск
├── zoryna.service       # systemd
├── zoryna-nginx.conf    # Nginx конфіг
├── img/
│   ├── foto_false.png   # Placeholder фото
│   ├── novidio.gif      # Video placeholder
│   ├── social/          # Іконки соцмереж (PNG, 8 штук)
│   ├── awards/          # Зображення нагород — 31+ PNG, локальні (завантажені з Wikimedia)
│   └── ranks/           # Погони звань — 21 PNG (UA_shoulder_mark_01..17 + 4 генеральські)
├── js/
│   ├── sea.js           # Анімація хвиль
│   └── dat.gui.min.js   # GUI контроли
├── fonts/uicons/        # Flaticon UIcons (woff2, woff, css) — ЛОКАЛЬНІ
├── Doc/                 # SVG діаграми архітектури
├── logs/security.log    # Лог безпеки
├── CLAUDE.md            # Цей файл (читати ПЕРШИМ!)
├── DATABASE.md          # Детальна схема БД (всі таблиці, колонки, індекси)
├── MASTER_GUIDE.md      # Гайд розгортання
├── SECURITY_RULES.md    # Політики безпеки
└── PRODUCTION.md        # Чеклист продакшн
```

---

## 4. БАЗА ДАНИХ (MySQL: zoryana_pamyat)

### Таблиці

#### `memorials` — основна таблиця записів
```sql
id INT PRIMARY KEY AUTO_INCREMENT
last, first, mid VARCHAR(100)     -- ПІБ / позивний
birth, death VARCHAR(20)          -- дати
loc VARCHAR(300)                  -- місце загибелі
bury VARCHAR(300)                 -- поховання
circ VARCHAR(500)                 -- обставини
descr TEXT                        -- опис
photo VARCHAR(500)                -- URL фото
color VARCHAR(20)                 -- колір маркера (hex/rgba)
pos_x, pos_y DOUBLE               -- позиція на карті (0.0–1.0)
likes INT, rating DOUBLE
approved TINYINT(0=pending, 1=pub)
grp VARCHAR(100)                  -- позивний/підрозділ
added_by, video_url VARCHAR
rank, position VARCHAR(100)       -- звання, посада
unit VARCHAR(200)                 -- підрозділ
```

**Індекси**: `FULLTEXT (last,first,mid,grp,loc,descr)`, `idx_approved_rating`, `idx_rating_likes`

#### `users` — акаунти
```sql
id, name, email UNIQUE, password (bcrypt)
first_name, last_name, middle_name VARCHAR(100)  -- ПІБ (незмінні після реєстрації)
nickname VARCHAR(100) UNIQUE                     -- нік (змінюваний, лише латиниця)
phone VARCHAR(20)                                -- +380XXXXXXXXX
role VARCHAR(20)  -- 'admin' | 'moder' | 'user'
is_banned, ban_until, last_seen, notes
```

#### `likes_log` — дедублікація лайків
```sql
memorial_id, fingerprint VARCHAR(128), ts
INDEX (memorial_id, fingerprint, ts)
```

#### `colors` — конфігурація теми та налаштувань
```sql
key VARCHAR(50) PRIMARY KEY, value TEXT, label VARCHAR(200)
-- 60+ ключів: кольори, соцмережі, smoke, sea, icons, admin_*
```

#### `map_labels` — підписи областей
```sql
id, name, x DOUBLE, y DOUBLE, type, color, size INT
```

#### `cities` — міста на карті
```sql
id, name, pos_x, pos_y DOUBLE, tier INT, color
-- 400+ міст України
```

#### `memorial_awards` — нагороди (прив'язані до конкретного меморіалу)
```sql
id, memorial_id FK, name, img_file VARCHAR(300), award_date, descr, sort_order
-- img_file = локальна назва файлу (напр. "order_courage_1.png") → /img/awards/{file}
```

#### `awards_catalog` — каталог всіх нагород (єдине джерело)
```sql
id INT AUTO_INCREMENT PRIMARY KEY
name        VARCHAR(200) NOT NULL
img_file    VARCHAR(200) NOT NULL        -- файл в img/awards/
category    VARCHAR(30)  DEFAULT 'military'  -- hero|order|cross|medal|badge
description TEXT
sort_order  INT DEFAULT 0
UNIQUE KEY uq_img (img_file)
-- Заповнюється через setup_awards.py (31+ нагород)
-- API: GET /api/awards/catalog
```

#### `search_logs` — аналітика пошуку
```sql
id, query, results_count, created_at
```

---

## 5. API ENDPOINTS

### Публічні (без автентифікації)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/` | index.html |
| GET | `/admin` | admin.html |
| GET | `/api/people?page=1&limit=50` | Список меморіалів (кешується 60с) |
| GET | `/api/memorial/{id}` | Деталі запису |
| GET | `/api/search?q=NAME` | Пошук (FULLTEXT, limit 50) |
| GET | `/api/stats` | Статистика |
| GET | `/api/colors` | Налаштування теми |
| GET | `/api/labels` | Підписи карти |
| GET | `/api/cities` | Міста |
| POST | `/api/like/{id}` | Лайк (fingerprint dedup) |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus метрики |

### Авторизація
| Метод | Endpoint | Опис |
|-------|----------|------|
| POST | `/api/auth/register` | Реєстрація |
| POST | `/api/auth/login` | Вхід (cookie) |
| POST | `/api/auth/logout` | Вихід |
| GET | `/api/auth/me` | Поточний користувач (повертає розширені поля) |
| PUT | `/api/auth/profile` | Оновити профіль (нік, email, телефон, пароль — не ФІО) |
| GET | `/api/auth/google` | Google OAuth |
| GET | `/api/auth/diia` | Дія OAuth |

### Адмін (Basic Auth або cookie `admin_session`)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/admin/memorials?page=1&limit=500` | **Всі** записи з пагінацією (для адмін-панелі) |
| GET | `/api/admin/pending` | Черга модерації |
| POST | `/api/admin/approve/{id}` | Схвалити |
| DELETE | `/api/admin/memorial/{id}` | Видалити |
| PUT | `/api/admin/memorial/{id}` | Редагувати |
| POST | `/api/admin/memorial` | Створити |
| GET/PUT/POST/DELETE | `/api/admin/city/*` | Міста |
| GET/PUT | `/api/admin/label/*` | Підписи |
| PUT | `/api/admin/color` | Колір |
| PUT | `/api/admin/colors/batch` | Кольори batch |
| GET/POST/DELETE | `/api/admin/users/*` | Юзери |
| GET | `/api/admin/export/csv` | Експорт CSV |
| POST | `/api/admin/import/apply` | Імпорт CSV |
| GET | `/api/admin/stats` | Статистика адмін |
| GET | `/api/admin/server-stats` | CPU/RAM |

### Каталог нагород (публічний)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/awards/catalog` | Список нагород з `awards_catalog` (name, img_file, category, description, sort_order) |

---

## 6. АВТЕНТИФІКАЦІЯ І БЕЗПЕКА

### Методи входу
1. **Email + пароль** → bcrypt 12 rounds, cookie `admin_session` (7 днів)
2. **Google OAuth 2.0** → auto-create/login
3. **Дія (UA eID)** → державна авторизація

### Захист від атак
| Механізм | Реалізація |
|----------|-----------|
| SQL Injection | Параметризовані запити PyMySQL (`%s`) |
| XSS | `html.escape()` на всіх входах, `_sanitize_text()` |
| SVG Injection | `_sanitize_svg()` — видаляє script, on*, foreignObject, use |
| CSRF | CORS middleware з allowed origins |
| Brute-force | 5 невдалих спроб → lockout 15хв (per IP:email) |
| Rate Limit | 60 req/IP/60с публічні; 10 невдалих auth/IP/300с admin |
| SSRF | Блокує `localhost`, `127.x`, `10.x`, `192.168.x` в photo URL |
| Secure Headers | `X-Content-Type-Options`, `X-Frame-Options: DENY`, CSP |
| Session | `secrets.token_hex(32)`, max 50000, авто-очищення |

### CSP Policy
```
default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net;
img-src 'self' data: https: blob:; frame-src youtube.com youtube-nocookie.com
```

### Сесії (in-memory)
- Зберігаються в `_sessions` dict з `threading.Lock()`
- TTL 604800с (7 днів), авто-purge кожні ~1000 запитів
- Ліміт 50,000 записів (evict старі якщо перевищено)

---

## 7. ПРОДУКТИВНІСТЬ (до 500 users онлайн)

### Gunicorn (prod)
```python
workers = min((2 * cpu_count()) + 1, 8)  # 8 воркерів макс
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
max_requests = 1000      # Prevent memory leaks
keepalive = 5
bind = "127.0.0.1:8000"  # За Nginx
```

### DB Connection Pool
```python
maxconnections = 50      # Макс з'єднань
mincached = 5            # Завжди активних
maxcached = 20           # Кешованих
```

### Redis Cache
- `/api/people` кешується 60с (ключ `people:p{page}:l{limit}`)
- Flush при змінах (import, edit)
- Якщо Redis недоступний — прозора деградація

### Індекси БД (критичні для продуктивності)
```sql
FULLTEXT (last, first, mid, grp, loc, descr)  -- пошук
INDEX idx_approved_rating (approved, rating DESC)  -- /api/people
INDEX idx_rating_likes (rating DESC, likes DESC)   -- сортування
```

### Оптимізації для 500 concurrent users
- **Nginx**: Reverse proxy, gzip, статика напряму
- **Uvicorn async**: Не блокує на I/O
- **Redis**: Знімає навантаження пошуку/списків з MySQL
- **Пагінація**: max 100 на сторінку (default 50)
- **Lazy purge**: Сесії чистяться кожні ~1000 req (не кожен)

---

## 8. ЗАПУСК (DEV)

```bash
# Windows
start.bat

# або вручну
cd D:\OSPanel\OpenServer\domains\localhost\treetex
venv\Scripts\activate
uvicorn Paskal:app --reload --port 8000

# Redis (окремо, опціонально)
start-redis.bat
```

**URL**: `http://127.0.0.1:8000`
**Адмін**: `http://127.0.0.1:8000/admin`

### Змінні середовища (.env)
```
DB_HOST, DB_USER, DB_PASS, DB_NAME=zoryana_pamyat
REDIS_URL=redis://localhost:6379
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
DIIA_CLIENT_ID, DIIA_CLIENT_SECRET
OAUTH_REDIRECT_BASE=http://127.0.0.1:8000
SECRET_KEY=...
```

---

## 9. КЛЮЧОВІ ОСОБЛИВОСТІ FRONTEND

### index.html (головна)
- Інтерактивна SVG карта України з pan/zoom (0.4x–12x)
- Маркери-зірки (WebGL animated) на місцях загибелі
- Пошук з fuzzy matching (Cyrillic + Latin transliteration)
- Картки меморіалів (phase 1: основне, phase 2: деталі)
- Соціальні мережі: `#social-bar` (fixed, bottom-center, 8 мереж)
- Ефект диму WebGL (`smoke_*` налаштування)
- Хвилі моря (`sea.js`, SVG overlay)
- Кнопка fullscreen (`#btn-fs`)
- Теми: `loadColors()` → CSS variables

### admin.html (адмін)
- SVG іконки (inline sprite, `#ico-*`) — **без зовнішніх шрифтів**
- Секції: stats, mem, pend, users, mapeditor, social, colors, smoke, photo, sea, icons, cities
- Drag-and-drop: nav order, social networks order
- Chart.js: запити за 24 год
- BroadcastChannel: синхронізація між вкладками
- Теми: темна/світла, змінюється через `toggleAdminTheme()`
- **"Всі записи" (sec-mem)**: клієнтська пагінація (`allPeople`/`filteredPeople`), пошук (`memDoSearch`), перемикач рядків 10/25/50/100/200/Всі (`memSetPageSize`)
- **"Користувачі" (sec-users)**: клієнтська пагінація (`_usersData`/`_filteredUsers`/`_usersPage`/`_usersPageSize`), пошук+фільтри за роллю/статусом, перемикач рядків 10/25/50/100/Всі (`usersSetPageSize`), кнопки Вперед/Назад (`usersPage`)
- **Нагороди**: `AWARDS_DATA_ADM` завантажується з `/api/awards/catalog` при старті (`_loadAwardsCatalog`)
- **Погони**: `RANK_POGON_IMG` → локальні PNG у `img/ranks/` (не Wikimedia!)
- **Зображення нагород**: `_wikiImg()` → `/img/awards/{file}` (не Wikimedia CDN!)

### Соціальні мережі (8 штук)
- Facebook, Twitter/X, Instagram, YouTube, Telegram, TikTok, LinkedIn, Viber
- Іконки: PNG у `img/social/`
- Налаштування в `colors` таблиці: `social_{id}`, `social_{id}_url`, `social_order`
- Порядок: drag-and-drop в адмінці → `social_order` (comma-separated)

---

## 10. КОНФІГУРАЦІЯ (таблиця `colors`)

Ключові групи налаштувань:
- **Кольори UI**: `bg`, `accent`, `text_primary`, `neon_blue`, тощо
- **Карта**: `oblast_fill`, `neon_yellow`, `label_opacity`, `city_border`
- **Zoom**: `zoom_min`, `zoom_max`, `city_border_zoom`
- **Smoke**: `smoke_enabled`, `smoke_density`, `smoke_opacity`, тощо
- **Sea**: `sea_enabled`, `sea_wave_color`, `sea_svg_content`, тощо
- **Іконки**: `icon_logo` (`★`), `icon_likes` (`⭐`), `icon_people` (`👥`)
- **Соцмережі**: `social_facebook`, `social_facebook_url`, `social_order`
- **Admin**: `admin_theme`, `admin_nav_order`, `admin_logo_url`
- **Фото на карті**: `map_photo_url`, `map_photo_opacity`, `map_photo_blend`

---

## 11. ПРАВИЛА РОБОТИ ДЛЯ CLAUDE

### При старті нової задачі — ОБОВ'ЯЗКОВО
1. Прочитати **всі MD файли** проекту: `CLAUDE.md`, `DATABASE.md`, `MASTER_GUIDE.md`, `SECURITY_RULES.md`, `PRODUCTION.md`
2. Під час роботи **оновлювати MD файли** при зміні архітектури, нових ендпоінтів, таблиць, файлів
3. Перевірити актуальність через читання `Paskal.py` / HTML файлів перед правками

### Що НЕ змінювати без явного запиту
- Структуру БД (таблиці, колонки) — тільки через `migrations.sql`
- `.env` файл — містить секрети
- `memorial.db` — старий SQLite, **не використовувати**
- Налаштування Gunicorn/Nginx без узгодження
- Алгоритм рейтингу (`rating` field logic)
- Систему сесій (in-memory, thread-safe)

### Безпека (обов'язково)
- Всі user inputs через `_sanitize_text()` або `html.escape()`
- SQL тільки параметризовані запити (`cursor.execute(sql, (params,))`)
- Фото URL валідувати через `_V.chkUrl()` / приватні IP блокувати
- SVG через `_sanitize_svg()`
- Не додавати нових ендпоінтів без rate limiting

### Frontend
- SVG іконки в admin.html — inline sprite (`#ico-*`), не fonticons
- CSS через `var(--variable)` для підтримки тем
- `applySocialLinks()` викликати після `loadColors()` в index.html
- `BroadcastChannel('zoryana_colors')` для синхронізації між вкладками

### При зміні MD файлів
- `CLAUDE.md` — при зміні структури проекту, стеку, ендпоінтів, таблиць БД, правил роботи
- `DATABASE.md` — при зміні схеми БД (нові таблиці, колонки, індекси)
- `MASTER_GUIDE.md` — деталі деплою та налаштування
- `SECURITY_RULES.md` — аудит безпеки

### Нагороди та зображення
- Зображення нагород: `img/awards/*.png` — локальні, завантажені через `setup_awards.py`
- Погони звань: `img/ranks/*.png` — локальні PNG (UA_shoulder_mark_01..17 + 4 генеральські)
- Щоб додати нові нагороди: 1) Покласти PNG в `img/awards/` 2) Вставити запис в `awards_catalog` через setup_awards.py або SQL
- **НЕ використовувати Wikimedia CDN** для нагород і погонів — тільки локальні файли

---

## 12. ВІДОМІ ОСОБЛИВОСТІ ТА ОБМЕЖЕННЯ

| Особливість | Деталь |
|-------------|--------|
| Сесії in-memory | Не переживають рестарт сервера. При prod масштабуванні → Redis sessions |
| Redis опціональний | Без Redis — кеш відсутній, все йде в MySQL |
| `memorial.db` | Старий SQLite файл, НЕ використовується, залишений для референсу |
| SVG карта | 883KB — велика, в prod кешувати через Nginx |
| admin.html | ~1.3MB — великий файл, ЗАВЖДИ читати перед правкою |
| `colors` таблиця | Використовується для ВСІХ налаштувань (не тільки кольорів) |
| Fingerprint likes | Ненадійний (VPN обходить), але достатній для базового захисту |
| Google OAuth | Redirect URI має бути точним (в Google Console) |

---

## 13. МОНІТОРИНГ ТА ЛОГИ

- **`/health`** — JSON: uptime, db status, redis status, cpu%, memory%
- **`/metrics`** — Prometheus format
- **`logs/security.log`** — Auth failures, rate limits, admin actions
- **Grafana**: `grafana-dashboard.json` — дашборд запитів
- **Prometheus**: `prometheus.yml` — scrape config

---

## 14. ДЕПЛОЙ (ПРОДАКШН)

```bash
# Nginx (zoryna-nginx.conf) → Gunicorn (port 8000)
# systemd (zoryna.service)

sudo systemctl start zoryna
sudo systemctl reload nginx

# або
./deploy.sh
```

Детальніше: `MASTER_GUIDE.md`, `PRODUCTION.md`

---

*Оновлено: 2026-05-08. Версія проекту: v2.1*
