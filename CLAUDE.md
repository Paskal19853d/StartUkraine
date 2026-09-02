# CLAUDE.md — Зоряна Памʼять (Zoryana Memory)

> Цей файл читається Claude Code на початку кожної сесії. При зміні структури проекту — оновлювати цей файл.
>
> **Пов'язана документація:** [SKILL.md](SKILL.md) (постійні навички: безпека + адаптив, читати ЗАВЖДИ) · [DATABASE.md](DATABASE.md) (повна схема БД) · [MASTER_GUIDE.md](MASTER_GUIDE.md) (гайд розгортання) · [SECURITY_RULES.md](SECURITY_RULES.md) (політики безпеки) · [PRODUCTION.md](PRODUCTION.md) (чекліст продакшн) · [SESSION_CHANGES.md](SESSION_CHANGES.md) (швидкий чекліст деплою останньої сесії — файли + SQL по кожній зміні)

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
| Auth | bcrypt (12 rounds) + Google OAuth | Cookies 7 днів |
| Frontend | HTML5 + Vanilla JS | Без фреймворків |
| CSS | CSS Custom Properties | Темна/світла теми |
| Анімація | WebGL (fluid simulation) | Дим, хвилі, ефекти |
| Моніторинг | Prometheus + Grafana | `/metrics` endpoint |
| Конфігурація | `.env` файл | DB, OAuth, Redis credentials |

---

## 3. СТРУКТУРА ФАЙЛІВ

```
treetex/
├── Paskal.py            # Весь backend (FastAPI, ~6100+ рядків)
├── seo_utils.py         # Транслітерація KMU 2010, make_slug(), gen_seo_*()
├── templates/
│   └── memorial.html    # Jinja2 шаблон SSR-сторінки для Googlebot
├── index.html           # Головна публічна сторінка (~1MB)
├── admin.html           # Адмін-панель (~1.3MB)
├── Style.css            # Глобальні стилі (36KB)
├── script.js            # Frontend JS (53KB)
├── card.html            # Публічна картка меморіалу (dark gold theme)
├── profile.html         # Публічний профіль користувача /user/{nickname}
├── faq.html / rules.html / terms.html
├── how-to-add.html      # Інструкція "Як додати загиблого" (та сама doc-* дизайн-система, img/how-to-add/)
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
├── lang_engine.py       # i18n движок: t(), get_all(), get_languages(), invalidate_cache()
├── js/
│   ├── i18n.js          # Клієнтська локалізація: window.LANG, t(), applyI18n(), switchLang()
│   ├── sea.js           # Анімація хвиль
│   └── dat.gui.min.js   # GUI контроли
├── fonts/uicons/        # Flaticon UIcons (woff2, woff, css) — ЛОКАЛЬНІ
├── Doc/                 # SVG діаграми архітектури
├── logs/security.log    # Лог безпеки
├── CLAUDE.md            # Цей файл (читати ПЕРШИМ!)
├── SKILL.md             # Постійні навички: безпека + адаптивний дизайн (читати ЗАВЖДИ)
├── DATABASE.md          # Детальна схема БД (всі таблиці, колонки, індекси)
├── MASTER_GUIDE.md      # Гайд розгортання
├── SECURITY_RULES.md    # Політики безпеки
├── PRODUCTION.md        # Чеклист продакшн
└── SESSION_CHANGES.md   # Швидкий чекліст деплою останньої сесії (файли + SQL, доповнює журнал змін)
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
slug VARCHAR(220) UNIQUE          -- SEO slug: ivan-petrenko-42 (auto-generated)
```

**Індекси**: `FULLTEXT (last,first,mid,grp,loc,descr)`, `idx_approved_rating`, `idx_rating_likes`, `idx_slug (UNIQUE)`

#### `users` — акаунти
```sql
id, name, email UNIQUE, password (bcrypt)
first_name, last_name, middle_name VARCHAR(100)  -- ПІБ (незмінні після реєстрації)
nickname VARCHAR(100) UNIQUE                     -- нік (змінюваний, укр/лат/цифри/_ .-; авто-генерується якщо NULL)
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

#### `ad_video_views` — сервер-перевірене "показано сьогодні" для модуля «Відео-попап»
```sql
id INT PRIMARY KEY AUTO_INCREMENT
visitor_id VARCHAR(64)             -- значення cookie zp_vid (UUID4, анонімний)
seen_at    INT                     -- unix timestamp показу
INDEX idx_visitor_seen (visitor_id, seen_at)
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
| GET | `/api/device-status` | Доступ за пристроєм: `{desktop, tablet, mobile, block_msg}` |
| GET | `/api/ad-video/status` | Відео-попап: чи показувати зараз (`{show: bool}`), видає cookie `zp_vid` |
| POST | `/api/ad-video/seen` | Відео-попап: фіксує показ для поточного `zp_vid` |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus метрики |

### Авторизація
| Метод | Endpoint | Опис |
|-------|----------|------|
| POST | `/api/auth/register` | Реєстрація |
| POST | `/api/auth/login` | Вхід (cookie) |
| POST | `/api/auth/logout` | Вихід |
| GET | `/api/auth/check-availability?type=nick\|email&value=X[&exclude_uid=Y]` | Real-time перевірка доступності ніку/email. Rate limit 30/хв/IP. Повертає `{available: bool, reason?: str}` |
| GET | `/api/auth/me` | Поточний користувач (повертає розширені поля) |
| PUT | `/api/auth/profile` | Оновити профіль (нік, email, телефон, пароль — не ФІО) |
| GET | `/api/auth/google` | Google OAuth |

### Профіль користувача (публічний)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/user/{nickname}` | profile.html (публічна сторінка) |
| GET | `/api/user/{nickname}` | JSON: display_name, role, created, count, memorials[] (тільки approved, is_banned=0) |

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
| GET | `/api/admin/project-cost` | Дані модуля вартості: proj_* ключі + live stats (users, views, bots, mems) |
| POST | `/api/admin/project-cost/refresh-rate` | Примусово оновити курс USD/UAH з НБУ API |
| POST | `/api/admin/upload/ad-preview` | Завантажити прев'ю-картинку для модуля «Відео-попап» (PNG/JPG/WEBP, до 2 МБ) |

### Каталог нагород (публічний)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/awards/catalog` | Список нагород з `awards_catalog` (name, img_file, category, description, sort_order) |

### SEO (публічні + адмін)
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/memorial/{slug}` | SSR-сторінка меморіалу (для Googlebot + шеринг). Jinja2 render, Redis TTL 300s |
| GET | `/api/memorial/by-slug/{slug}` | JSON картки за slug (для SPA) |
| GET | `/sitemap.xml` | XML sitemap всіх схвалених меморіалів. Redis TTL 600s |
| GET | `/robots.txt` | Allow /memorial/, Disallow /admin /api/ |
| GET | `/api/admin/seo-dashboard` | Статистика slug, лог Google Indexing API |
| POST | `/api/admin/seo/regenerate-slugs` | Перегенерувати порожні slug |
| POST | `/api/admin/seo/ping-google` | Відправити URL до Google Indexing API |
| GET | `/api/admin/seo/analyze/{mid}` | SEO score + рекомендації для однієї картки |
| GET | `/api/admin/seo/scores` | Всі картки відсортовані за SEO score (worst first) |
| POST | `/api/admin/seo/check-broken-links` | Запустити перевірку битих фото URL (background thread) |
| GET | `/api/admin/seo/broken-links` | Список битих фото посилань з `seo_broken_links` |
| GET | `/api/admin/seo/duplicates` | Групи меморіалів з однаковим ПІБ |
| POST | `/api/admin/seo/snapshot` | Зберегти знімок SEO score розподілу в `seo_score_history` |
| GET | `/api/admin/seo/score-history` | Історія знімків SEO балів (для Chart.js) |

**Slug формат:** `{first}-{last}-{id}` — транслітерація KMU 2010, суфікс id гарантує унікальність.  
**Google Indexing API:** активується через `.env`: `GOOGLE_INDEXING_KEY_FILE=google-service-account.json`, `SITE_BASE_URL=https://yoursite.ua`  
**Sitemap:** включає `xmlns:image` (фото) та `xmlns:video` (YouTube відео) блоки.

---

## 6. АВТЕНТИФІКАЦІЯ І БЕЗПЕКА

### Методи входу
1. **Email + пароль** → bcrypt 12 rounds, cookie `admin_session` (7 днів)
2. **Google OAuth 2.0** → auto-create/login

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
- Секції: stats, mem, pend, users, mapeditor, social, colors, smoke, photo, sea, icons, cities, **projcost**
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
- **Пристрої**: `device_desktop_enabled`, `device_tablet_enabled`, `device_mobile_enabled` (1=так, 0=ні), `device_block_msg` (текст заглушки)
- **Вартість проекту**: `proj_cost_server_usd`, `proj_cost_domains_usd`, `proj_cost_ai_usd`, `proj_cost_other_usd`, `proj_cost_months`, `proj_usd_rate` (НБУ, авто), `proj_usd_rate_updated` (timestamp), `proj_cost_per_user_usd` (CPM, default 1.0)
- **Підказки сайту**: `tour_enabled` (1=так, 0=ні — вимикає онбординг-тур для нових відвідувачів), `tour_video_enabled` (1=так, 0=ні — окремо вимикає показ відео-вікна, не видаляючи URL), `tour_video_url` (посилання на відео-інструкцію, показується замість туру коли `tour_enabled=0` і `tour_video_enabled=1`; YouTube → вбудований iframe, інше → кнопка-посилання)
- **Відео-попап (реклама)**: `ad_video_enabled` (1=так, 0=ні), `ad_video_url` (YouTube), `ad_video_title` (назва над плеєром), `ad_video_preview_url` (URL прев'ю-картинки), `ad_video_channel_url` (посилання на канал), `ad_video_channel_btn` (текст кнопки каналу), `ad_video_freq_days` (частота показу одному відвідувачу, днів)

---

## 11. ПРАВИЛА РОБОТИ ДЛЯ CLAUDE

### При старті нової задачі — ОБОВ'ЯЗКОВО
1. Прочитати **всі MD файли** проекту: `CLAUDE.md`, `SKILL.md`, `DATABASE.md`, `MASTER_GUIDE.md`, `SECURITY_RULES.md`, `PRODUCTION.md`, `SESSION_CHANGES.md`
2. Під час роботи **оновлювати MD файли** при зміні архітектури, нових ендпоінтів, таблиць, файлів
3. Перевірити актуальність через читання `Paskal.py` / HTML файлів перед правками

### Після кожного блоку змін — ОБОВ'ЯЗКОВО
4. **Писати список змінених файлів** в кінці відповіді (назва файлу + короткий опис що змінено)
5. **Вимоги користувача додавати в MD файли** — кожне нове правило / вимогу / обмеження фіксувати в `CLAUDE.md` (секція 11) та у feedback memory (`memory/feedback_code_rules.md`)

### Що НЕ змінювати без явного запиту
- Структуру БД (таблиці, колонки) — **НЕ через migrations.sql** (він не виконується автоматично). Зміни в БД робити напряму: через PhpMyAdmin або Python-скрипт з pymysql (root:root на 127.0.0.1:3306)
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
- **ОБОВ'ЯЗКОВО**: у nav-item і sec-title ЗАБОРОНЕНО емодзі. Тільки `<svg class="adm-ico"><use href="#ico-NAME"/></svg>`. Приклад: `<span class="nav-ico"><svg class="adm-ico"><use href="#ico-search"/></svg></span>` та `<div class="sec-title"><svg class="adm-ico"><use href="#ico-search"/></svg> Заголовок</div>`
- **ОБОВ'ЯЗКОВО**: у кнопках (`.btn`) ЗАБОРОНЕНО емодзі. Тільки SVG спрайт: `<button class="btn"><svg class="adm-ico"><use href="#ico-NAME"/></svg> Текст</button>`
- Наявні іконки спрайту: `#ico-stats`, `#ico-doc`, `#ico-hourglass`, `#ico-users`, `#ico-auth`, `#ico-email`, `#ico-palette`, `#ico-share`, `#ico-smoke`, `#ico-waves`, `#ico-star`, `#ico-photo`, `#ico-city`, `#ico-candle`, `#ico-search`, `#ico-check`, `#ico-cross`, `#ico-edit`, `#ico-trash`, `#ico-plus`, `#ico-map`
- **Кнопки CSS**: базовий `.btn` — чорний фон `#111318`. `.btn-p` — чорний фон з синьою рамкою (`border-color:rgba(0,136,187,.6);color:#a8e0f8`). `.btn-r/g/b` — чорний фон зі своїм кольором рамки/тексту
- CSS через `var(--variable)` для підтримки тем
- `applySocialLinks()` викликати після `loadColors()` в index.html
- `BroadcastChannel('zoryana_colors')` для синхронізації між вкладками

### При зміні MD файлів
- `CLAUDE.md` — при зміні структури проекту, стеку, ендпоінтів, таблиць БД, правил роботи
- `DATABASE.md` — при зміні схеми БД (нові таблиці, колонки, індекси)
- `MASTER_GUIDE.md` — деталі деплою та налаштування
- `SECURITY_RULES.md` — аудит безпеки

### Модуль "Вартість проекту" (sec-projcost)
- **Endpoint**: `GET /api/admin/project-cost` — повертає `proj_*` ключі + live stats (users_total, users_24h, views_today, views_yesterday, bots_24h, bots_24h_uniq, top_bots, mem_approved)
- **Збереження**: через стандартний `PUT /api/admin/colors/batch`
- **Курс USD/UAH**: daemon thread `_currency_rate_loop()` оновлює кожні 23г через НБУ API (`bank.gov.ua`)
- **JS функції**: `projCostLoad()`, `projCostSave()`, `projCostCalc()`, `projCostRefreshRate()`
- **Ринкова вартість** (фіксовані константи в JS): розробка з нуля $45k–$80k, готовий проект з кодом $30k–$70k
- **CPM метрика**: `proj_cost_per_user_usd` — вартість одного користувача в $, враховується в оцінці аудиторії
- **КРИТИЧНО — SQL IN з Python list**: `c.execute("...IN (%s,%s)", keys)` де keys — list НЕКОРЕКТНО (PyMySQL передає весь list як 1 параметр). Правильно: `ph = ",".join(["%s"]*len(keys)); c.execute(f"...IN ({ph})", keys)`
- **КРИТИЧНО — fetch в адмінці**: ЗАВЖДИ додавати `credentials:'include'` при cookie-автентифікації (AP=''), інакше 403

### Нагороди та зображення
- Зображення нагород: `img/awards/*.png` — локальні, завантажені через `setup_awards.py`
- Погони звань: `img/ranks/*.png` — локальні PNG (UA_shoulder_mark_01..17 + 4 генеральські)
- Щоб додати нові нагороди: 1) Покласти PNG в `img/awards/` 2) Вставити запис в `awards_catalog` через setup_awards.py або SQL
- **НЕ використовувати Wikimedia CDN** для нагород і погонів — тільки локальні файли

### ✅ ВИПРАВЛЕНО (2026-08-15) — Дим (WebGL fluid, `js/script.js`) вантажив пристрої
Аудит виявив 5 незалежних причин підвисань/навантаження від ефекту диму. Виправлено пункти 1-4 (структурні фікси в коді); пункт 5 (адмін quality-preset) — окреме рішення, НЕ виконано, підтвердження обсягу відкладено.

**Причини (для довідки):**
1. rAF-цикл ніколи не зупинявся, навіть коли дим "вимкнено" — `update()` безумовно викликав `requestAnimationFrame(update)`. `applyBloom()`/`applySunrays()` в `render()` виконувались завжди, незалежно від `PAUSED`.
2. `SIM_RESOLUTION`/`PRESSURE_ITERATIONS`/`BLOOM`/`SUNRAYS` — однакові на мобільних і десктопі, `isMobile()` знижував лише `DYE_RESOLUTION`.
3. `devicePixelRatio` не капнутий у `scaleByPixelRatio()` — на телефонах dpr 2.5-3.5 роздував площу canvas у 6-12 разів.
4. **[найсерйозніша, знайдена в поглибленому аудиті]** Витік WebGL-ресурсів — `resizeFBO()`/`initFramebuffers()` перестворювали текстури/framebuffer'и без `gl.deleteTexture`/`gl.deleteFramebuffer`, GPU-пам'ять накопичувально росла при кожному resize (ховання/поява адресного рядка при скролі на мобільних — часта подія).

**Що зроблено (js/script.js, index.html):**
- Нові helper-функції `disposeFBO()`/`disposeDoubleFBO()` — звільняють GPU-текстуру+framebuffer перед заміною. Застосовані в `resizeFBO()`, `resizeDoubleFBO()`, `initFramebuffers()` (divergence/curl/pressure), `initBloomFramebuffers()`, `initSunraysFramebuffers()`.
- `update()` тепер повністю зупиняє rAF-цикл (`return` без `requestAnimationFrame`), коли `config.PAUSED` або `document.hidden` — цикл "засинає" замість молотити невидимий canvas. Новий `window._fluidResume()` "розбуджує" цикл ззовні; викликається з `_applySmokeState()` (index.html) при увімкненні диму, з zoom-pause `setTimeout` (index.html:~3440), і автоматично на `visibilitychange` при поверненні на вкладку.
- `isMobile()`-блок (js/script.js:~378) додатково знижує `SIM_RESOLUTION`→96, `PRESSURE_ITERATIONS`→14, `BLOOM_ITERATIONS`→5, вимикає `SUNRAYS` на мобільних (найдорожчі параметри; `DYE_RESOLUTION`/кольори/splat — джерело візуальної якості — не чіпались).
- `scaleByPixelRatio()` капає `devicePixelRatio` до 1.5 на мобільних / 2 на десктопі (`Math.min`).
- Перевірено headless Chrome screenshot: дим рендериться візуально ідентично, 0 JS-помилок у консолі.

### ✅ ВИПРАВЛЕНО (2026-08-15) — Дим інколи не з'являвся при завантаженні (курсор нерухомий)
Окрема, давня проблема (не пов'язана з фіксом продуктивності вище). Симптом: якщо курсор при завантаженні сторінки вже нерухомо стояв у вікні браузера — дим міг взагалі не бути видимим; якщо курсор заходив у вікно ззовні — дим з'являвся.

**Причина**: `pointerPrototype()` (js/script.js) ініціалізує вказівник з координатами `(0,0)` (кут canvas). Видимий splat генерується лише коли `mousemove` дає ненульову дельту координат (`updatePointerMoveData()`). Якщо миша не рухається після завантаження — `mousemove` не спрацьовує жодного разу, і єдине джерело диму лишаються початкові `multipleSplats()` зі старту скрипта, які з часом дисипують без підживлення. Коли курсор заходить у вікно ззовні — перша `mousemove`-подія дає велику дельту (від кута 0,0 до реальної позиції) → потужний видимий splat, тому дим "запускається".

**Рішення**: новий `igniteSmoke()` (js/script.js, поруч з `multipleSplats()`) — послідовність `splat()`-викликів вздовж дуги з ненульовою дотичною швидкістю (імітує плавний природний мазок миші, а не хаотичні точки). Експортований як `window.igniteSmoke`. Викликається з `_applySmokeState()` (index.html) **кожного разу**, коли стан диму переходить з вимкненого в увімкнений (новий модульний прапорець `_smokeWasOn`) — покриває і перше завантаження сторінки, і ручне увімкнення через тумблер `toggleSmoke()`. Не дублюється при повторних викликах `_applySmokeState()` (їх 3: `loadColors()`, `toggleSmoke()`, `window.onload`), бо прапорець оновлюється лише коли ignite реально відбувся.

Перевірено headless Chrome screenshot **без будь-якого симульованого руху курсора** — дим тепер видимий одразу, помітно потужніший спрямований вихровий ефект замість слабкого фонового серпанку. 0 JS-помилок у консолі.

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
| `portfolio/index.html` | Статистика (total/likes) оновлюється з `/api/stats` кожні 30 хв через `setInterval` |
| faq/terms/rules | Є прихований блок "Мінімальна ціна проєкту" (`display:none`) — отримує курс з `/api/colors` → `proj_usd_rate` → $30,000 × rate |
| admin.html showSec | Кожна секція реєструє свою функцію завантаження прямо в `showSec(id)` через `if(id==='X') Xload()` |

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

*Оновлено: 2026-07-02. Версія проекту: v2.2*

---

## 16. i18n — ЛОКАЛІЗАЦІЯ

### Архітектура
- **Єдине джерело правди**: MySQL таблиці `languages` + `i18n_translations`
- **Backend модуль**: `lang_engine.py` — `t()`, `get_all()`, `get_languages()`, `invalidate_cache()`
- **Кеш**: `lru_cache` у пам'яті + Redis TTL 300с, авто-інвалідація при збереженні
- **Frontend**: `js/i18n.js` — `window.LANG.t(key, vars?)`, `applyI18n()`, `switchLang(lang)`
- **Мова**: cookie `lang` (1 рік) → Accept-Language → `uk` (fallback)
- **Fallback**: якщо ключ відсутній у lang → підставляється uk

### HTML атрибути для перекладу
| Атрибут | Що перекладає |
|---------|--------------|
| `data-i18n="key"` | `textContent` |
| `data-i18n-html="key"` | `innerHTML` |
| `data-i18n-placeholder="key"` | `placeholder` |
| `data-i18n-hint="key"` | `data-hint` (для `.zp-hint`) |
| `data-i18n-aria="key"` | `aria-label` |
| `data-i18n-title="key"` | `title` |

### Перемикач мови `#lang-toggle`
- CSS: точний патерн `#map-mode-toggle` / `.mmt-thumb`
- Клас `lang-en` на `<html>` при англійській мові
- Синхронізація між вкладками через `BroadcastChannel('zoryana_lang')`

### API endpoints
| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/langs` | Активні мови |
| GET | `/api/i18n/{lang}` | Словник для lang (з fallback uk) |
| GET | `/api/admin/i18n/langs` | Всі мови (адмін) |
| POST | `/api/admin/i18n/lang` | Додати/оновити мову |
| GET | `/api/admin/i18n/keys?lang=uk&section=ui` | Ключі для редагування |
| PUT | `/api/admin/i18n/key` | Зберегти один ключ |
| PUT | `/api/admin/i18n/batch` | Пакетне збереження |

### Секції ключів
| Секція | Вміст |
|--------|-------|
| `ui` | Кнопки, мітки, загальні елементи |
| `map` | Карта, маркери, підписи |
| `card` | Картка меморіалу |
| `admin` | Адмін-панель |
| `auth` | Авторизація, профіль |
| `errors` | Повідомлення про помилки |

### Правила роботи з i18n
- **НЕ хардкодити** тексти інтерфейсу напряму в HTML/JS — використовувати `data-i18n` або `LANG.t()`
- Нові ключі додавати через `PUT /api/admin/i18n/batch` або напряму в PhpMyAdmin
- При зміні перекладів — `invalidate_cache()` викликається автоматично в ендпоінтах
- Секція `uk` обов'язкова для кожного ключа (це fallback для всіх мов)
- Зміни БД i18n — через PhpMyAdmin SQL або ендпоінти (НЕ через `init_db`)

---

## 15. ЖУРНАЛ ЗМІН

### v3.24 (2026-09-02) — Фікс: налаштування чату («Чат активний» тощо) не зберігались через кеш браузера + жорсткіша обробка помилок збереження
- Користувач (role=admin, підтверджено) повідомив що перемикач «Чат активний» не зберігається в БД
- Знайдено 2 реальні проблеми в `js/chat-admin.js`:
  1. `<script src="/js/chat-admin.js">` в `admin.html` не мав версіонуючого `?v=N` параметра (на відміну від `i18n.js?v=2`, `chat.js?v=2`) — браузер міг роками кешувати стару версію файлу і не підхопити фікси з v3.23 (`credentials:'include'`, обробку помилок) навіть після деплою нових файлів на прод
  2. `chatSaveSettings()` не перевіряла `response.ok` перед парсингом JSON — при 403/500 з не-JSON тілом (напр. від проміжного nginx/прокси) `.then(r=>r.json())` міг кинути виняток без зрозумілого повідомлення користувачу, або тихо піти в `else`-гілку без деталей статус-коду
- Виправлено: `admin.html` — `chat-admin.js?v=2` (форсує оновлення кешу браузера). `js/chat-admin.js` — `chatSaveSettings()` тепер явно перевіряє `r.ok`+`r.status`, показує `HTTP {status}` в повідомленні про помилку якщо сервер не дав `detail`, і додає `authH()`-заголовки (Basic Auth fallback) на випадок сесії через Basic Auth замість cookie — той самий патерн, що вже використовується в інших save-функціях адмінки (`ptAdd`/`ptDelete` тощо)
- Перевірено: `require_admin` на `PUT /api/admin/colors/batch` — коректний рівень доступу (той самий ендпоінт для ВСІХ batch-налаштувань сайту, свідомо `admin`-only; змінювати на `require_moder` для одного лише чату означало б розширити права модераторів на весь ендпоінт — цього НЕ зроблено, бо не було явного запиту)
- Файли: `admin.html`, `js/chat-admin.js`
- Синтаксис перевірено (`node -c`) — помилок нема
- **Дія користувача**: після заливки файлів на прод — примусово оновити сторінку адмінки (Ctrl+F5 / очистити кеш), щоб гарантовано підхопити нову версію `chat-admin.js`

### v3.23 (2026-09-02) — Фікс: перемикач «Чат активний» не ховав FAB-кнопку чату на мобільних + не синхронізувався між вкладками
- Перемикач `chat_enabled` вже існував в адмінці (розділ «Чат» → вкладка «Налаштування», з v3.19) і вже коректно ховав десктопну панель `#micro-chat` (клас `.mc-hidden`) — але мав 2 незакриті пробіли:
  1. Мобільна плаваюча кнопка `#mc-fab` (окремий DOM-елемент поза `#micro-chat`) ніколи не перевіряла `chat_enabled` — залишалась видимою й клікабельною навіть при вимкненому чаті (клік не відкривав панель через `!important` в `.mc-hidden`, тобто кнопка була "мертвою", а не прихованою)
  2. `chatSaveSettings()` (`js/chat-admin.js`) не викликала `_broadcastColors()` після збереження — зміна `chat_enabled` не долітала до вже відкритих вкладок публічного сайту без перезавантаження сторінки (і не мала `credentials:'include'` — за правилом проєкту це потрібно для cookie-автентифікації, інакше 403)
- `index.html`: новий `window._applyChatFabVisibility()` (в блоці «FAB кнопки для мобільного») — ховає/показує `#mc-fab` за `chat_enabled`; викликається (а) одразу при визначенні (покриває перше завантаження — `_mcInit()` з `js/chat.js` виконується РАНІШЕ, ніж цей блок встигає визначити функцію, тому прямий виклик всередині `_mcInit()` там не спрацював би без цього) і (б) в `_onColorsBC()` при отриманні `chat_enabled` через BroadcastChannel
- `js/chat.js`: `_mcInit()` викликає `window._applyChatFabVisibility?.()` для сумісності (спрацює на повторних викликах, напр. SPA-подібних переходах)
- `js/chat-admin.js`: `chatSaveSettings()` — додано `credentials:'include'`, оновлення локального кешу `window.COLORS`, виклик `_broadcastColors(payload)` (той самий патерн, що вже застосований в `saveWMSettings()` тощо, v3.19)
- `admin.html`: уточнено опис перемикача — «Показувати мікро-чат і кнопку чату на сайті (десктоп + мобільна версія)»
- Файли: `index.html`, `js/chat.js`, `js/chat-admin.js`, `admin.html`
- Синтаксис перевірено (`node -c`) — помилок нема

### v3.22 (2026-09-02) — Повне видалення інтеграції «Дія» (Diia eID)
- **Причина**: авторизація/реєстрація через Дія більше не використовується — видалено повністю з коду, конфігурації та БД
- `Paskal.py`: видалено ендпоінти `GET /api/auth/diia` та `GET /api/auth/diia/callback` (весь OAuth-flow: обмін коду на токен, запит userinfo, `_oauth_login_or_create`), видалено конфіг-змінні `DIIA_CLIENT_ID`, `DIIA_CLIENT_SECRET`, `DIIA_AUTH_URL`, `DIIA_TOKEN_URL`, `DIIA_USERINFO_URL`
- `index.html`, `mobile.html`: видалено кнопку «Продовжити з Дія» в модалці авторизації (`#mauth`) та обробку `oauth_error` кодів `diia_*`
- `admin.html`: оновлено коментар (згадка «Google/Дія» → «Google»); власної кнопки Дія в адмінці не було
- `Style.css`, `img/Style.css`: видалено CSS-класи `.oauth-diia`, `.diia-row`, `.diia-unavail`
- `.env.example`: видалено рядки `DIIA_CLIENT_ID=`/`DIIA_CLIENT_SECRET=`
- Нова SQL-міграція `migrations_remove_diia.sql` — видаляє 7 мертвих i18n-ключів (`auth.continue_diia`, `diia.unavailable`, `errors.oauth_diia_*`) з таблиці `i18n_translations` (uk+en). Старі міграції (`migrations_i18n_index_pass2.sql`, `migrations_i18n_index_full_coverage.sql`), де ці ключі вперше додавались, НЕ редагувались — це історичний журнал, вже виконаний на проді
- Не чіпались: історичний запис `### v3.3` нижче в цьому журналі (згадує Дія в контексті OAuth-редіректу `?next=admin` — це опис вже виконаної роботи минулої сесії, не поточний стан коду); слово «дія»/«Дія користувача» в інших місцях документації — звичайне українське слово («дія» = «дозвіл»/«ужиток»), не бренд Diia
- Синтаксис перевірено (`ast.parse` для Paskal.py, `node -c` для inline JS index.html/admin.html/mobile.html) — помилок нема
- **Дія користувача**: виконати `migrations_remove_diia.sql` в PhpMyAdmin після заливки файлів; додатково опційно — прибрати `DIIA_CLIENT_ID`/`DIIA_CLIENT_SECRET` з `.env` на проді (не обов'язково, код їх більше не читає)

### v3.21 (2026-09-02) — Універсалізація: категорії людей (військовий/цивільний/поза війною) + режим додавання free/request
- **Мета**: розширити систему з «картки загиблого військовослужбовця» до «універсальної сторінки пам'яті людини» — підтримка військових, цивільних загиблих від війни, і людей, які померли з інших причин (хвороба, старість, нещасний випадок). Паралельно — перемикач в адмінці «безкоштовне самостійне додавання / додавання по заявці через кол-центр» з реальним серверним блокуванням
- Технічне завдання користувача — `StepbyStep.md` (написане під WordPress+Polylang; реалізовано через наявні аналоги проєкту — FastAPI+MySQL, власна i18n-система, універсальна таблиця `colors`, без нових зовнішніх залежностей)
- **Нові колонки `memorials`** (SQL-міграція `migrations_universal_memory.sql`): `category` VARCHAR(20) default `'military'` (`military`/`civilian_war`/`civilian`), `death_reason` VARCHAR(40) — код причини (залежить від category), `war_related` TINYINT default 1 (похідне від category, але зберігається окремо), `citizenship`/`nationality` VARCHAR(30) — коди країн/національностей, `created_by_uid` INT NULL — user_id визначається СЕРВЕРОМ з `admin_session` cookie (ніколи з тіла запиту), `show_creator` TINYINT default 0. Стара колонка `added_by` (VARCHAR, вільний текст) НЕ чіпалась — лишається для сумісності. Явний `UPDATE` проставляє існуючим записам `category='military', war_related=1` — старі військові картки виглядають ідентично до змін
- **Довідники причин смерті/громадянства/національності** — прості строкові коди зашиті в `<select>` (як вже було для поля `circ`), без нових lookup-таблиць. Онлайн-оплата НЕ реалізована (лише toggle free/request)
- **Backend (Paskal.py)**: нова функція `_validate_category_fields()` — єдина точка правди: перевіряє category, приводить war_related, звіряє death_reason з допустимим набором саме для цієї category (інакше → `'other'`). Нові хелпери `_get_optional_user()`/`_get_optional_user_id()` — читають `admin_session` cookie без вимоги ролі admin/moder (на відміну від `require_moder`), не кидають виняток якщо не залогинений. `POST /api/people` — на початку перевіряє `add_person_mode` з `colors`; якщо `request` і користувач не admin/moder → `HTTPException(403, {code, message_uk, message_en, phone})`. `_MEMORIAL_COL_MAP`, `PersonIn`/`PersonUpdate`, `update_memorial`, `admin_add_person` розширені новими полями. Explicit SELECT у `GET /api/people` розширено
- **Адмінка (admin.html)**: нова секція «Додавання людей» (`sec-addmode`, deferred-save за зразком `sec-device` — toggle free/request, поле телефону, 2 textarea uk/en). Нова іконка `#ico-phone` в SVG-спрайті. Edit/create-modal розширені полями категорії/причини/громадянства/національності/show_creator + read-only «Додав / Автор (uid)». Список «Всі записи» — нова колонка «Категорія» + dropdown-фільтр (`#mem-f-category`). «На модерації» — бейджі нових полів у превью
- **Публічна форма (index.html, `#madd`)**: нові поля категорія/причина смерті (динамічний список залежно від категорії)/громадянство/національність/toggle «показувати моє ім'я» (видимий лише залогиненим). `openAdd()` перевіряє режим free/request — при `request` форма замінюється повідомленням+кнопкою `tel:`. `submitAdd()` обробляє 403 з об'єктом (`detail.code==='add_person_request_mode'`)
- **card.html універсалізація** (`fillPage()`, 6 місць): фолбек імені, рядок звання (приховується повністю для non-military замість військового фолбеку), лейбл+sub-текст дати смерті, лейбл місця, timeline title, video-caption — всі умовні за `category`
- **SEO** (`seo_utils.py`, `_build_memorial_seo` в Paskal.py, `templates/memorial.html`, sitemap.xml): `gen_seo_title`/`gen_seo_description`/`gen_seo_keywords` — умовні формулювання/фолбеки за category (military="Герой України", civilian_war="Пам'ять про загиблого", civilian="Сторінка пам'яті"). JSON-LD `memberOf: MilitaryOrganization` лише для military; `nationality` в JSON-LD тепер бере реальне `citizenship` замість завжди "Україна". `templates/memorial.html` — лейбл «Загинув»/«Місце загибелі» став умовним (`death_label`/`loc_label` з контексту). sitemap.xml — `image:title`/`image:caption` умовні за категорією
- **i18n**: нова SQL-міграція `migrations_i18n_universal_memory.sql` — ~90 ключів (uk+en): category.*, death_reason.* (військові+цивільні-від-війни+невоєнні), citizenship.*, nationality.* (14 значень), show_creator.label, adm.addmode.*, nav.addmode, adm.mem.col_category
- Файли: `Paskal.py`, `index.html`, `admin.html`, `card.html`, `seo_utils.py`, `templates/memorial.html`, нові `migrations_universal_memory.sql` + `migrations_i18n_universal_memory.sql`
- Синтаксис перевірено: `ast.parse` (Paskal.py, seo_utils.py), `node -c` для всіх inline-скриптів index.html/admin.html/card.html — помилок нема
- **Не перевірено функціонально/скріншотами** — потребує виконання SQL-міграцій на проді перед будь-яким тестуванням (весь backend спирається на нові колонки). Рекомендовано користувачу: 1) виконати `migrations_universal_memory.sql` і `migrations_i18n_universal_memory.sql` в PhpMyAdmin, 2) перевірити стару військову картку (має виглядати ідентично), 3) додати тестовий цивільний запис (`civilian_war`/`civilian`) і перевірити картку/SEO, 4) перевірити перемикач free/request в адмінці (розділ «Додавання людей»)

### v3.20 (2026-09-01) — Фікс: карта світу показувала "API KEY REQUIRED" (CARTO тепер вимагає ключ)
- Проблема: CARTO (провайдер тайлів `basemaps.cartocdn.com` для стилів Dark Matter/Positron) з 2026 року вимагає безкоштовний API-ключ у query-параметрі URL — без нього тайли показують водяний знак "API KEY REQUIRED" замість карти. Зовнішня зміна політики CARTO, не баг коду
- Фікс 1 (адмінка, `sec-worldmap`): нове поле "CARTO API-ключ" + кнопка "Застосувати до пресетів" — адмін вставляє ключ, отриманий на [carto.com/basemaps/apikey](https://carto.com/basemaps/apikey/) (email+домен, без реєстрації акаунта, ключ приходить миттєво), тоді обирає пресет стилю (Dark Matter/Positron) — ключ автоматично підставляється в URL. Оновлено `_WM_PRESETS` (admin.html) на новий формат CARTO без `{s}`-субдоменів: `https://basemaps.cartocdn.com/rastertiles/{style}/{z}/{x}/{y}.png?key=...` (старий формат `{s}.basemaps.cartocdn.com/...` — той, що зараз віддає "API KEY REQUIRED"). OpenStreetMap-пресет ключа не потребує, лишився без змін
- Фікс 2 (`index.html`, `_initMaddMap()`): карта вибору точки у формі "Додати запис" мала **окремий захардкожений** старий CARTO URL (не пов'язаний з адмінкою) — той самий баг, але невидимий через `worldmap_tile_url`. Тепер читає той самий `getC('worldmap_tile_url')`, що й основна карта світу — єдине джерело, зміна ключа в адмінці одразу діє в обох місцях
- **Не є регресією для існуючих сайтів з уже правильним `worldmap_tile_url`** — фікс лише додає зручний UI для підстановки ключа й синхронізує друге місце використання URL, не змінює логіку читання/збереження
- Файли: `admin.html`, `index.html`
- Синтаксис перевірено (`node -c`) — помилок нема
- **Дія користувача обов'язкова**: отримати безкоштовний CARTO-ключ і застосувати через адмінку (розділ "Карта світу") — або переключитись на пресет OpenStreetMap, який ключа не потребує взагалі

### v3.19 (2026-08-23) — Адмінка: відкладене збереження замість миттєвого (5 модулів)
- Проблема: у частині модулів адмінки зміна поля (тумблер/select/число) зберігалась в БД одразу через `onchange`/`onblur` — без можливості переглянути й підтвердити зміни перед застосуванням, без єдиної точки "Зберегти"/"Скасувати"
- Пройдено послідовно 5 модулів, у кожному прибрано `onchange`-автозбереження, додано/уніфіковано пару кнопок **Зберегти** (batch PUT) / **Скасувати** (перечитує сервер):
  1. **Пристрої** (`sec-device`) — 4 тумблери (ПК/планшет/смартфон/кнопка кави) тепер лише в `saveDeviceSettings()`; видалено мертву `saveDeviceSetting()` (одиничну)
  2. **Реєстрація та авторизація** (`sec-authreg`) — 7 полів (2 тумблери, 2 select, тумблер email-підтвердження, мін. довжина пароля, текст привітання) — раніше не мали кнопки "Зберегти" ВЗАГАЛІ, тепер нова `saveRegSettings()` + кнопки додано
  3. **Карта світу** (`sec-worldmap`) — `worldmap_enabled`/`worldmap_default`/`worldmap_tile_url` + окремий тумблер "міста України" (`cities_ua_enabled`, раніше `saveCitiesUaEnabled`) об'єднано в нову `saveWMSettings()`; пресети стилів тайлів (`_wmPreset`) тепер лише заповнюють поле, не зберігають; **збережено критичну деталь** зі старої `saveWMSetting()` — оновлення локального кешу `COLORS[key]` + `_broadcastColors()` (синхронізація кольорів між вкладками через BroadcastChannel), інакше зламалась би
  4. **Google OAuth** (`sec-google`) — тумблер "Увімкнути вхід через Google" (`reg_allow_google`) долучено до вже наявної `_saveGoogleBatch()` (раніше окрема миттєва `_saveGoogleToggle()`, видалена)
  5. **Чат → Налаштування** (`sec-chat`, вкладка "Налаштування") — 3 поля (`chat_enabled`/`chat_history_count`/`chat_poll_interval`) — нова `chatSaveSettings()` (js/chat-admin.js) замість миттєвої `chatSaveCfg()` (видалена), нова кнопка "Зберегти"/"Скасувати" (використовує вже наявну `chatLoadSettings()`)
- **Свідомо НЕ чіпались** (не є "формою налаштувань" за суттю): **Іконки** (`sec-icons`, за прямим запитом користувача); **Кольори** (`sec-colors`) — вже має власну debounce-архітектуру (`pendColors`/`_autoSaveToDb`, 1.5с після паузи) з live-preview карти, ризиковано ламати; **Щільність зірок** (`sec-density`) — sandbox-калькулятор з live-формулою (`den-decay-preview`), range-слайдери синхронізовані з number-полями; **Редактор карти** (`sec-mapeditor`) — drag-and-drop, кожен рух миші це дія; таблиці з побудовими записами (**Міста**, **Друзі/Партнери**, **Спадщина**, **Чат-боти**) — кожен рядок є окремим записом БД, не "налаштуванням"; **Онлайн/Dev-режим** (шапка адмінки) — це перемикачі стану, не форма; **звукові сповіщення чату** (`snd-join`/`snd-leave`/`snd-chat`) — локальні браузерні preferences адміна (localStorage через `js/admin-sounds.js`), не серверні `colors`
- Файли: `admin.html`, `js/chat-admin.js`
- Синтаксис перевірено (`node -c`) — помилок нема
- Не перевірено функціонально/скріншотами (диск C: критично заповнений) — рекомендовано користувачу перевірити на проді: змінити поле в кожному з 5 модулів, переконатись що зміна НЕ застосовується без кліку "Зберегти", і що "Скасувати" коректно повертає попередній стан

### v3.18 (2026-08-23) — Підказки сайту: окремий вимикач вікна відео-туру (незалежно від URL)
- Проблема: розділ "Підказки сайту" мав лише 2 стани — тур увімкнено, або тур вимкнено+відео (якщо URL заповнений). Якщо адмін тимчасово не має готового відео, єдиний спосіб прибрати відео-вікно — стерти `tour_video_url`, втративши значення
- Новий ключ `colors`: `tour_video_enabled` (дефолт `"1"` — без регресії для вже налаштованих сайтів)
- `index.html` (`_tourStart()`): відео-вікно показується лише коли **і** `tour_video_url` заповнений, **і** `tour_video_enabled !== '0'`
- `admin.html` (`sec-tour`): новий тогл "Показувати відео-вікно" між основним тоглом туру і полем URL; `_tourToggleUI()` тепер ховає/показує обидва рядки (тогл відео + поле URL) разом, коли тур увімкнено; `loadTourSettings()`/`saveTourSettings()` розширені новим ключем
- `Paskal.py`: новий рядок у seed-списку `colors`
- Нова SQL-міграція: `migrations_tour_video_toggle.sql`
- Синтаксис перевірено (`node -c`, `ast.parse`) — помилок нема

### v3.17 (2026-08-22) — Новий модуль «Відео-попап» (реклама): адмінка + БД + серверна безпека
- Нова адмін-категорія `sec-adv` («Реклама») — спливаюче вікно з YouTube-відео на index.html, показується кожному відвідувачу не частіше заданої адміном частоти (днів), займає ~50% екрана
- **Сервер-перевірена ідентифікація відвідувача** (не тільки localStorage) — нова анонімна non-auth cookie `zp_vid` (UUID4, `httponly`, `samesite=lax`, `secure` в проді, max_age 400 днів), видається при першому виклику `GET /api/ad-video/status`. Нова таблиця `ad_video_views (id, visitor_id, seen_at)` зберігає факт показу — `MAX(seen_at)` звіряється з `now - freq_days*86400`
- **Звук лише після кліка** — автовідтворення зі звуком без дії користувача блокується браузерами завжди (не залежить від YouTube чи власного хостингу — підтверджено користувачу окремо). Реалізовано: прев'ю-картинка (завантажується адміном вручну, `POST /api/admin/upload/ad-preview`, копія `upload_logo()`) з play-кнопкою → клік користувача замінює на `<iframe autoplay=1>` (без mute) — звук стартує як прямий наслідок кліка, не порушує browser autoplay policy
- Нові backend-ендпоінти (Paskal.py): `GET /api/ad-video/status` (публічний, rate-limit `advstatus:{ip}` 30/60с, видає cookie, звіряє `ad_video_enabled`+`ad_video_freq_days` на сервері — не покладається на клієнтський кеш `/api/colors`), `POST /api/ad-video/seen` (публічний, rate-limit `advseen:{ip}` 10/60с, INSERT в `ad_video_views`), `POST /api/admin/upload/ad-preview` (require_moder, magic-bytes перевірка, ліміт 2 МБ)
- Нові ключі `colors`: `ad_video_enabled`, `ad_video_url`, `ad_video_title`, `ad_video_preview_url`, `ad_video_channel_url`, `ad_video_channel_btn`, `ad_video_freq_days` — читання/збереження через наявні `GET /api/colors`/`PUT /api/admin/colors/batch`, нових read/write ендпоінтів для налаштувань не додавалось
- **Серверна валідація** додана прямо в `update_colors_batch()` для цих ключів (раніше цей batch-ендпоінт приймав значення без перевірки): `ad_video_url` → `_validate_yt_url()` (вже існує), `ad_video_channel_url` → `_validate_photo_url()` (SSRF/hostname-блокування, generic http(s)-перевірка — переюзана, не тільки для фото), `ad_video_title`/`ad_video_channel_btn` → `_sanitize_text(150)`
- `index.html`: нова модалка `#ad-video-modal` (`z-index:9990`, узгоджено з фіксом `.mov` з v3.14), `_adVideoCheck()`/`_showAdVideo()`/`_closeAdVideo()`, виклик `setTimeout(_adVideoCheck, 2500)` в init-послідовності (після туру, щоб не накладались дві модалки на старті)
- `admin.html`: нова іконка `#ico-ad` (мегафон) в SVG-спрайті, nav-item «Реклама» (після «Підказки»), секція `sec-adv` (toggle, поля URL/назва/прев'ю з file-upload+preview/канал/частота), `loadAdVideoSettings()`/`saveAdVideoSettings()`/`uploadAdVideoPreview()`
- Нова SQL-міграція: `migrations_ad_video.sql` (CREATE TABLE `ad_video_views` + 7 рядків `colors`)
- Синтаксис усіх inline-скриптів index.html/admin.html перевірено (`node -c`), Paskal.py — `ast.parse` — помилок нема
- **Не перевірено функціонально/скріншотами** — диск C: критично заповнений (задокументовано в CLAUDE.md). Рекомендовано користувачу перевірити на проді після деплою: увімкнути модуль в адмінці, заповнити всі поля (включно з прев'ю-картинкою), відкрити сайт у приватному вікні браузера (без cookie `zp_vid`) — попап має з'явитись через ~2.5с після завантаження; клік на прев'ю запускає відео зі звуком; повторне відкриття сторінки в межах заданої частоти — попап більше не з'являється

### v3.16 (2026-08-22) — Promo-сторінка (/promo/): реальна статистика замість статичних чисел + оновлено копірайт
- Проблема 1: `promo/index.html` (лендинг для реклами/шерингу) показував захардкоджені статичні числа "128" (у пам'яті) і "14 142" (зірок) — не оновлювались ніколи
- Фікс 1: додано `id="stat-total"`/`id="stat-likes"` на відповідні `.stat .n` елементи + новий JS-блок в кінці `<script>`, що підтягує реальні дані з уже наявного публічного `GET /api/stats` (`{total, likes, visitors_24h}`, Paskal.py) — той самий `fmtN()`-патерн (тис. скорочення), що вже використовується в `portfolio/index.html` для тієї ж мети. Третій стат-блок "online / щодня" — статичний текст, не число, не чіпався
- Проблема 2: копірайт в шапці і футері promo-сторінки — `© 2026 TREETEX NPO` (стара назва бренду розробника)
- Фікс 2: замінено в обох місцях (шапка `.npo`, футер `.footer`) на `© 2026 ТМ «ЗОРЯНА ПАМ'ЯТЬ»` — посилання на `/portfolio/` збережено за явним запитом користувача
- Файл: лише `promo/index.html`
- Синтаксис inline-скрипта перевірено (`node -c`) — помилок нема. Не перевірено скріншотами (диск C: критично заповнений)

### v3.15 (2026-08-22) — Фікс: #partners-layer і #kyiv-clock перекривали форму додавання загиблого (регресія від v3.14)
- Проблема: після v3.14 (підняття `.mov` до z-index:9990) з'явилась нова колізія — `#partners-layer` (рекламні блоки партнерів, index.html) на десктопі отримував **той самий** inline `z-index:9990`, що й модалки, а `#kyiv-clock` (цифровий годинник Київ, `silence-module.css`) мав `z-index:9998` — **вище** за модалки. Обидва елементи — fixed, рендеряться поза стеком модалки, тому при рівному/вищому z-index і пізнішому порядку в DOM перекривали форму додавання загиблого (та інші модалки)
- Фікс: `#partners-layer` inline z-index (index.html, `initPartners()`) — `9990` → `890` (десктоп; мобільний варіант `1580` не чіпався, там `#partners-layer` і так `display:none` через mobile.css). `#kyiv-clock` (`silence-module.css`) — `9998` → `890`. Обидва — декоративні оверлеї поверх карти, логічно мають бути нижче БУДЬ-ЯКОЇ модалки, а не вище
- `#silence-overlay` (повноекранний режим «Хвилина мовчання», z-index:9999) не чіпався — це навмисно системний оверлей верхнього рівня, як preloader/rotate-overlay
- Файли: `index.html` (inline z-index партнерів), `silence-module.css` (`#kyiv-clock`)
- Не перевірено скріншотами (диск C: критично заповнений) — рекомендовано перевірити на проді: відкрити форму додавання загиблого при активних партнерах і/або увімкненому годиннику — обидва більше не мають перекривати модалку

### v3.14 (2026-08-22) — Фікс: модальні вікна (.mov/.mo) перекривались шапкою та іншими fixed-блоками
- Проблема: контент модалок (`.mo`, всередині оверлея `.mov`) мав `z-index:900` (Style.css) — нижче за шапку сайту `#topbar` (9500), випадаючий пошук `#sdrop`/`#mob-sw-input #sdrop` (9000/9501), тултіп кнопки кави (9995), кнопку мікро-чату `#mc-fab` (1600), панель мікро-чату (1590), соцбар (1000) — усі ці fixed-елементи малювались ПОВЕРХ відкритої модалки й перекривали її частини
- Фікс: `.mov` z-index піднято з `900` → `9990` (Style.css) — вище всіх перелічених fixed-блоків, але нижче системних оверлеїв верхнього рівня (`#hint-toast`/`#preloader`/`#rotate-overlay`: 99999, `#too-small-overlay`: 100000 — свідомо НЕ чіпались, це критичні системні стани, повинні лишатись понад усім, включно з модалками)
- Той самий фікс дзеркально застосовано в `mobile.css` (`.mov{z-index:1200}` → `9990`) — мобільна версія має власний override цього правила (модалки там — нижні листи, `align-items:flex-end`); на мобільному `#topbar` взагалі прихований (`display:none`), але `#m-chat-panel` (повноекранна панель чату, 9500) та інші fixed-елементи так само могли перекривати модалку
- Файли: `Style.css`, `mobile.css` — лише значення `z-index` у правилі `.mov`, жодної іншої логіки не чіпали
- Не перевірено скріншотами (диск C: критично заповнений) — рекомендовано користувачу перевірити на проді: відкрити будь-яку модалку (форма додавання, редагування профілю, інфо-вікна) і переконатись що шапка/пошук/кнопка чату більше не перекривають її вміст

### v3.13 (2026-08-22) — Фікс підвисань диму саме над картою України (не дим — карта)
- Проблема: дим (WebGL fluid, вже глибоко оптимізований раніше) підвисає САМЕ коли курсор рухається над картою — раніше здавалось що причина в самому димі, але аудит показав що дим тут не винен
- Причина: дим і карта незалежно слухають `mousemove` на `window` — кожен рух миші паралельно тригерить обидва обробники. Дим сам дешевий (rAF-throttled). Але під час перетягування карти (`drag`) `mousemove`-обробник карти (index.html) виконував синхронну не-throttled роботу на КОЖНІЙ сирій події (без rAF-gate): оновлення `tr.x/tr.y`, `clampTr()`, і зайвий `document.getElementById('tip').style.display='none'` — а паралельно `_startCanvasLoop()` (незалежний rAF-цикл, перемальовує всі зіркові маркери з `/api/map-points`, БЕЗ пагінації) прискорюється до ~30fps саме під час драгу. WebGL-симуляція диму при цьому продовжує повноцінно рендеритись — на відміну від zoom (`wheel`-обробник), де дим вже давно ставиться на паузу (`window._fluidConfig.PAUSED=true` на 120мс) саме для звільнення GPU
- Фікс (лише `index.html`, `js/script.js` не чіпався — дим сам по собі вже оптимальний):
  1. `mousedown` на карті (старт драгу) — застосовано той самий прецедент, що вже є для `wheel`/zoom: `window._fluidConfig.PAUSED=true` (без авто-відновлення по таймеру — знімається явно на `mouseup`, бо драг триває невідомо скільки, на відміну від миттєвого скролу колеса)
  2. `mouseup` (кінець драгу) — `window._fluidConfig.PAUSED=false` + `window._fluidResume()`, лише якщо драг справді був (`was===true`) — простий ховер без драгу дим не паузить
  3. Прибрано зайвий `document.getElementById('tip').style.display='none'` з драг-гілки `mousemove` (виконувався на КОЖНІЙ сирій події без throttle) — перенесено в `mousedown` (виконується один раз при вході в драг, тултіп і так вже прихований далі)
- Touch-обробники (`touchstart`/`touchmove`/`touchend`, мобільні) свідомо НЕ чіпались — там дим при свайпі одним пальцем навпаки активується (`_touchSplat`, ефект "дим від пальця") — це осмислене UX-рішення, не проблема продуктивності (мобільні й так отримують знижені quality-параметри через `isMobile()`)
- `hit()` (O(n) скан `people` для тултіпа при ховері) та `_startCanvasLoop()` (перемальовка маркерів) залишені без змін — вже rAF-throttled/time-capped там, де це мало сенс; основний виграш дає саме пауза WebGL-симуляції на час драгу, а не оптимізація цих скенів
- Синтаксис index.html перевірено (`node -c`) — помилок нема
- **Не перевірено функціонально/скріншотами** — диск C: користувача критично заповнений (задокументовано в CLAUDE.md), headless Chrome нестабільний за цих умов. Рекомендовано користувачу самостійно перевірити на проді: потягнути карту мишею — підвисання диму має зникнути або суттєво зменшитись; простий ховер без драгу — поведінка (тултіп, дим) без змін

### v3.12 (2026-08-22) — Нова адмін-категорія «Підказки сайту»: увімкнення/вимкнення онбординг-туру + відео-інструкція
- Новий розділ адмінки `sec-tour` ("Підказки") — перемикач `tour_enabled` (вмикає/вимикає онбординг-тур для нових відвідувачів) і поле `tour_video_url` (відео-інструкція, показується замість туру, коли він вимкнений)
- Зберігання — без нової таблиці БД, через уже наявну універсальну `colors` (2 нові ключі: `tour_enabled` default `"1"`, `tour_video_url` default `""`), стандартний `PUT /api/admin/colors/batch`, читання через публічний `GET /api/colors` — нових ендпоінтів не додавалось
- `admin.html`: нова іконка `#ico-tour` (play-в-колі) в SVG-спрайті; nav-item "Підказки" (після "Пристрої"); секція `sec-tour` за точним зразком `sec-device` (`.rg-row`/`.rg-toggle`); `loadTourSettings()`/`saveTourSettings()`/`_tourToggleUI()` — поле `tour-video-url` приховується/показується залежно від стану тогла (`_tourToggleUI`, показує поле лише коли тур ВИМКНЕНО — відео замінює тур, не доповнює)
- `index.html`: `_tourStart()` тепер спершу перевіряє `getC('tour_enabled','1')` — якщо `'0'`, замість `_tourShow(0)` викликає новий `_showTourVideo(url)` (за наявності `tour_video_url`) або одразу виставляє `zp_tour_done=1` (якщо відео не задане — нічого не показуємо повторно). Новий `#zp-tour-video-modal` (full-screen overlay, той самий `dev-modal`-патерн: `position:fixed;inset:0;backdrop-filter:blur`) + `_showTourVideo()`/`_closeTourVideo()` — розпізнає YouTube через вже наявний `_ytExtractId()` (вбудований iframe), інакше показує кнопку-посилання "Дивитись відео" (той самий фолбек що в card.html для не-YouTube `video_url`)
- Нові i18n ключі (`tour` секція, тільки для публічної модалки відео): `tour.video.title`, `tour.video.watch` (uk+en)
- Нова SQL-міграція: `migrations_tour_video.sql` (2 рядки `colors` + 4 рядки `i18n_translations`)
- Синтаксис усіх inline-скриптів index.html/admin.html перевірено (`node -c`) та Paskal.py (`ast.parse`) — помилок нема
- **Не перевірено функціонально/скріншотами** — диск C: користувача заповнений (9MB вільних зі 107GB на момент розробки), headless Chrome нестабільний за цих умов. Рекомендовано користувачу самостійно перевірити на проді після деплою: (1) увімкнений тур (дефолт) — поведінка не змінилась; (2) вимкнений тур + YouTube-посилання — при першому візиті з'являється модалка з вбудованим відео; (3) вимкнений тур без посилання — нічого не показується

### v3.11 (2026-08-22) — Онбординг-тур: фікс регресій після деплою v3.10 (картка не відкривалась + мобільні підказки без стрілок)
- Проблема 1 (десктоп): крок "Картка" — bubble з'являлась і підсвічувала `#card`, але бічна панель з фото/описом взагалі не відкривалась
- Причина 1: кроки "Зірки"/"Картка" (v3.10) перевіряли `window.people`, а `people` оголошена як `let people = [...]` на верхньому рівні окремого `<script>` (index.html:2570) — за специфікацією ECMAScript top-level `let`/`const` НЕ створюють властивість `window` (на відміну від `var`), тому `window.people` завжди `undefined`, і умови `!window.people`/`window.people && ...` завжди хибні незалежно від реального стану даних
- Фікс 1: прибрано `window.` префікс в обох `onShow` — `people` резолвиться напряму через lexical scope (тур-скрипт лежить пізніше в тому самому документі)
- Проблема 2 (мобільні): підказки для кроків усередині `#topbar` (`#logo`, `#search`/`#btn-search-mob`, `#lang-toggle`, `#map-mode-bar`, `#btn-add`) показувались без стрілки, впритул до краю екрана, не вказуючи на реальне місце кнопки
- Причина 2: `#topbar` на мобільних має `overflow-x:auto` (Style.css:631,644) — горизонтальний скрол шапки. `_tourElVisible()` перевіряє лише `offsetParent`/ненульові розміри `getBoundingClientRect()` — обидві умови проходять, навіть якщо елемент технічно існує, але зараз прокручений за межі видимої частини шапки. `_tourShow()` рахував позицію bubble від таких "хибно видимих" координат → clamp-захист притискав bubble до краю екрана, стрілка вказувала в порожнечу
- Фікс 2: у `_tourShow()`, одразу після резолву `targetEl` (перед підсвіткою й обчисленням позиції bubble) — якщо `targetEl` всередині `#topbar` і його `getBoundingClientRect()` виходить за межі рект `#topbar`, викликається `targetEl.scrollIntoView({inline:'center', block:'nearest', behavior:'instant'})` (без анімації, щоб одразу читати актуальні координати після скролу)
- Файл: тільки `index.html` (блок онбординг-туру), нових i18n ключів/SQL не потрібно
- **Не перевірено функціонально/скріншотами** — диск C: користувача був заповнений до 9MB вільних (100%) на момент розробки, headless Chrome нестабільний/недоступний за цих умов (той самий блокер, що й у v3.10). Синтаксис усіх inline-скриптів index.html перевірено (`node -c`) — помилок нема. Обидва фікси випливають напряму з підтвердженої специфікації JS (`let`/`window`) та підтвердженого CSS (`#topbar{overflow-x:auto}`), не є здогадками — але рекомендовано користувачу самостійно пройти тур на проді (десктоп: картка відкривається з випадковим записом; мобільний: bubble зі стрілкою точно на кнопці для кожного кроку в шапці) і підтвердити

### v3.10 (2026-08-22) — Онбординг-тур: якісні фікси (крок "Зірки", "Картка", новий крок "Мова")
- Проблема 1: крок "Зірки на карті" (`el: null`) не мав ні затемнення фону, ні стрілки-вказівника — фон карти лишався незатемненим (затемнення реалізоване через `.zp-tour-hl { box-shadow: 0 0 0 9999px ... }` на підсвіченому елементі — без елемента нема кому застосувати клас), яскраві зіркові маркери карти "просвічували" крізь bubble без контрасту
- Проблема 2: крок "Картка" відкривав завжди `people[0]` (не випадковий) і міг взагалі не відкрити бічну панель через гонку станів — `people` вантажиться асинхронно, а тур стартує через фіксований `setTimeout(1800)` від завантаження сторінки
- Проблема 3: не було кроку про перемикач мови (`#lang-toggle`)
- Рішення (index.html, `_TOUR_STEPS`/`_tourShow()`):
  - `_tourShow()` тепер дозволяє `step.onShow()` повертати DOM-елемент — він стає `targetEl` для підсвітки/стрілки замість стандартного `probeEl` (для кроків без штатного `el`-селектора)
  - Крок "Зірки": `onShow` бере випадковий запис з `people`, переводить `pos_x`/`pos_y` в реальні екранні координати через вже наявну `w2s()` (враховує поточний zoom/pan карти), створює тимчасовий якірний `<div id="zp-tour-anchor">` на цій позиції — отримує `.zp-tour-hl` (затемнення+підсвітка) і слугує ціллю для `arrowDir:'bottom'`. Якщо `people` ще порожній або точка поза видимою областю екрана — `onShow` повертає `null`, крок деградує до старого центрованого вигляду (без крашу)
  - Прибирання якірного div — на початку `_tourShow()` для наступного кроку (`document.getElementById('zp-tour-anchor')?.remove()`), поруч зі зняттям `.zp-tour-hl` з попереднього елемента
  - Крок "Картка": `Math.random()` замість `people[0]`; `onShow` тепер поллить (до 15×200мс ≈ 3с) появу `people`, замість одноразової перевірки й мовчазного пропуску
  - Новий крок "Мова" (`el:'#lang-toggle'`, `arrowDir:'top'`) — одразу після кроку "Пошук"; нові i18n ключі `tour.lang.title`/`tour.lang.text` (`migrations_i18n_tour_lang.sql`)
- Перевірено CDP-автоматизацією (текстові запити стану — без скріншотів, оскільки диск C: у сесії користувача був заповнений на 100%, що спричиняло крах GPU-процесу Chrome): всі кроки десктопного туру пройдено послідовно, `#lang-toggle`/`#search`/`#zoom`/`#btn-add`/`#logo`/`#treetex-npo` підсвічуються коректно, `#map-mode-bar` (вимкнений в тестовому середовищі) коректно пропускається
- **Не перевірено візуально** (скріншотами) через нестачу дискового простору під час розробки — рекомендовано користувачу самостійно пройти тур на проді після деплою і підтвердити, що затемнення/стрілка на кроці "Зірки" виглядають як очікувалось

### v3.9 (2026-08-22) — Онбординг-тур: повний тур тепер працює на мобільних/планшетах
- Проблема: на мобільних/планшетах (`pointer:coarse`) весь 10-кроковий тур свідомо замінювався ОДНІЄЮ окремою підказкою про горизонтальний скрол шапки (`_tourMobileTopbar()`) — далі тур не показувався
- Причина: `_tourStart()` мала ранній `return` для touch-пристроїв; крім того, крок "Пошук" (`#search`) прихований на мобільних (`display:none`, замінюється `#btn-search-mob`), а `#map-mode-bar` прихований завжди коли `worldmap_enabled=0` — без skip-логіки такі кроки показали б biпозиціоновану/зламану bubble
- Прибрано `pointer:coarse` розгалуження в `_tourStart()` — той самий 10-кроковий `_TOUR_STEPS` тепер запускається на всіх пристроях
- Крок "Пошук" (`el`) тепер функція: `#btn-search-mob` на touch, `#search` на mouse/desktop
- Новий `_tourElVisible()` — перевіряє видимість цільового елемента (в DOM, не `display:none`, ненульові розміри; враховує `position:fixed`) перед показом кроку; невидимі кроки (`#map-mode-bar` при вимкненій worldmap) автоматично пропускаються через `_tourShow(idx+1)`, без зламаних підказок
- Підтримка `step.skipIf`/`step.customContent`/`step.customPosition` в `_TOUR_STEPS` — гнучкі кроки без цільового елемента (напр. новий topbar-scroll крок)
- Підказка про горизонтальний скрол топбару (`← ◈ →`) тепер **останній крок головного туру** (замість окремого ізольованого виклику `_tourMobileTopbar()`, яку видалено) — з'являється лише на touch (`skipIf`), використовує ті самі i18n ключі `tour.mobtopbar.*`
- Позиціонування bubble: `bW`/`bH` тепер адаптивні під ширину viewport (`Math.min(280, vW-28)`), fallback-перемикання `left/right`→`top/bottom` коли збоку не вистачає місця на вузьких екранах
- Перевірено CDP-автоматизацією (headless Chrome, реальна touch-емуляція через `Emulation.setDeviceMetricsOverride`/`setTouchEmulationEnabled`) — всі 10 кроків пройдено послідовно на 375px viewport, `#search`→`#btn-search-mob` заміна підтверджена, `#map-mode-bar` коректно пропущено, фінальний topbar-крок відображається повністю в межах екрана, 0 JS-помилок

### v3.8 (2026-08-15) — Дим: гарантований запуск при завантаженні (не залежить від курсора)
- Проблема: дим інколи не з'являвся при завантаженні сторінки — залежало від того, чи курсор рухався одразу після старту
- Причина: `pointerPrototype()` (js/script.js) стартує з координатами `(0,0)`; видимий splat генерується лише при `mousemove` з ненульовою дельтою координат — нерухома миша не генерує подій взагалі, тому дим тримався лише на початкових `multipleSplats()`, які з часом гаснуть без підживлення
- Новий `igniteSmoke()` (js/script.js, `window.igniteSmoke`) — кілька `splat()` вздовж дуги з ненульовою дотичною швидкістю, імітує природний мазок миші
- Викликається з `_applySmokeState()` (index.html) при кожному переході диму вимкнено→увімкнено (новий прапорець `_smokeWasOn`) — і при першому завантаженні, і при ручному вмиканні тумблером `toggleSmoke()`
- Перевірено headless screenshot без симуляції руху курсора — дим тепер гарантовано видимий одразу

### v3.7 (2026-08-15) — Фікс продуктивності диму (WebGL fluid, `js/script.js`)
- Повний аудит виявив 4 незалежні причини підвисань/навантаження на CPU/GPU (детально — секція 11, підрозділ "✅ ВИПРАВЛЕНО — Дим")
- **Найсерйозніша знахідка**: витік WebGL-ресурсів — `resizeFBO()`/`initFramebuffers()` перестворювали текстури/framebuffer'и без `gl.deleteTexture`/`gl.deleteFramebuffer`, GPU-пам'ять накопичувально росла з кожним resize (часта подія на мобільних — ховання адресного рядка при скролі)
- Новий `disposeFBO()`/`disposeDoubleFBO()` — застосовано в `resizeFBO`, `resizeDoubleFBO`, `initFramebuffers`, `initBloomFramebuffers`, `initSunraysFramebuffers`
- rAF-цикл (`update()`) тепер повністю зупиняється при `config.PAUSED`/`document.hidden`, замість того щоб молотити невидимий canvas щокадру — новий `window._fluidResume()` для "пробудження"
- `isMobile()`-блок знижує `SIM_RESOLUTION`(96)/`PRESSURE_ITERATIONS`(14)/`BLOOM_ITERATIONS`(5), вимикає `SUNRAYS` — найдорожчі параметри симуляції, не візуальні (DYE_RESOLUTION/кольори/splat не чіпались)
- `scaleByPixelRatio()` капає `devicePixelRatio` (1.5 мобільні / 2 десктоп) — некапнутий dpr 2.5-3.5 на телефонах роздував canvas у 6-12 разів
- Перевірено: headless Chrome screenshot підтверджує візуальну якість диму не змінилась, 0 JS-помилок у консолі
- Не виконано (окреме рішення, потребує підтвердження): адмін-керований quality-preset (`smoke_quality: high|medium|low` в `colors`)

### v3.6 (2026-08-13) — Модуль "Друзі та партнери": окреме посилання для підпису
- Проблема: адмін намагався вставити посилання прямо в поле "Підпис під зображенням" HTML-тегом `<a href>` — не працювало, бо `caption` рендериться через `textContent` (свідомий XSS-захист), тег виводився як сирий текст
- Рішення: нова колонка `partners.caption_url` (VARCHAR(500), міграція через `ALTER TABLE` в `init_db()`, автоматично на старті) — підпис тепер може вести на власне посилання, незалежне від посилання картинки (`link_url`)
- `index.html` `renderPartners()`: контейнер партнера змінено з `<a>` на `<div>` (бо картинка й підпис можуть вести на різні URL — вкладати `<a>` в `<a>` не можна за HTML-специфікацією); картинка і підпис тепер окремі `<a>`-елементи всередині
- Якщо `caption_url` порожній — підпис автоматично успадковує `link_url` картинки (зворотна сумісність зі старими партнерами); якщо посилань немає взагалі — підпис лишається звичайним нередагованим текстом
- Admin.html: нове поле "Посилання підпису (куди веде клік на текст)" (`#pm-caption-link`) в модалці "Редагувати партнера", одразу під "Підпис під зображенням"
- Paskal.py: `PartnerCreate`/`PartnerUpdate` моделі + `POST/PUT /api/admin/partner` — новий параметр `caption_url` (без `_sanitize_text()`, як і `link_url`/`image_url` — це URL, не текст)
- Нова SQL-міграція для прода: `migrations_partners_caption_url.sql` (ALTER TABLE + фікс даних партнера "Українська Діаспора")

### v3.5 (2026-08-11) — Нова публічна сторінка how-to-add.html: "Як додати загиблого"
- Нова сторінка `how-to-add.html` — покрокова інструкція для волонтерів/рекламного відділу (не технічних користувачів), як через публічний сайт додати меморіальний запис
- Стиль повністю узгоджений з `faq.html`/`terms.html`/`rules.html` — та сама "паперовий документ" дизайн-система (`.doc-*` класи, inline CSS, PT Serif + Roboto Condensed, монохромна палітра, watermark, sidebar `.doc-nav`), четвертий пункт у `.doc-nav__list` на всіх чотирьох doc-сторінках
- Контент: 5 кроків (`.doc-section`, той самий патерн що в terms.html) — вхід через Google, відкриття форми, заповнення (з `.doc-table` обов'язкових/необов'язкових полів, звірено з реальною валідацією `submitAdd()` в index.html), позначка на карті (обов'язково), відправка на модерацію
- Новий CSS-компонент `.doc-shot`/`figcaption` — монохромні рамки для 8 скріншотів (вперше на doc-сторінках, немає аналога в faq/terms/rules)
- Зображення: `img/how-to-add/1-login.png` … `7-submit-btn.png` (8 файлів, реальні статичні PNG, не base64) — звичайні `<img loading="lazy">`, на відміну від Artifact-версії цього ж гайду
- Новий route в Paskal.py: `GET /how-to-add.html` (поруч з `rules_page`/`terms_page`/`faq_page`, ~рядок 2217)
- Навігація: посилання додано в `.doc-footer__right` усіх 4 doc-сторінок, і в `#site-rules`/`#bb-popup` (index.html, desktop+mobile) — усього 6 місць
- i18n: 90+ нових ключів під префіксом `howto.*` + спільний `doc.howto_nav`, повна uk/en локалізація через `data-i18n`/`data-i18n-html`, той самий `#doc-lang-toggle` патерн що в faq.html
- Важливе бізнес-уточнення в тексті (`howto.s5.moderation_note`): запис публікується на карті лише після модерації, термін обробки — від 7 робочих днів до 30 днів
- Нова SQL-міграція: `migrations_i18n_how_to_add.sql`

### v3.4 (2026-07-15) — Фікс обрізаних підказок (hint) в шапці на мобільних/планшетах
- Проблема: підказки (`.zp-hint::after`, `data-hint`) в `#topbar` обрізались знизу на мобільних/планшетах — видно було лише верхню частину балона. **Це не проблема z-index** — `#topbar` є overflow-контейнером (`overflow-x:auto` для горизонтального скролу шапки), тому CSS створює clipping box, що ріже будь-якого `position:absolute` нащадка, який виходить за межі блоку по вертикалі, незалежно від z-index
- Перша спроба (JS `getBoundingClientRect()` + `position:fixed` через `mouseenter`/`touchstart`) виявилась ненадійною на touch/DevTools-емуляції — `mouseenter` не підтримує делегування через `capture`, а сама ідея "емулювати hover на touch" суперечить UX (на тач-пристроях немає наведення курсору)
- **Фінальне рішення**: на `pointer:coarse` (телефони/планшети) CSS-hover балон повністю вимикається (`@media (pointer:coarse) { .zp-hint::after, .zp-hint::before { display:none } }`, [Style.css](Style.css) ~рядок 144), замість нього — tap-toast: клік на `.zp-hint` в `#topbar` показує текст `data-hint` в `#hint-toast` (`position:fixed`, центр знизу екрана, JS в index.html ~рядок 5167) на 1.8с
- `#hint-toast` — новий елемент, стилізований під той самий золотий балон, але поза overflow-контейнерами (`position:fixed` відносно viewport)
- Desktop (`pointer:fine`) поведінка не змінена — hover-балон працює як раніше
- Стосується всіх `.zp-hint` елементів в шапці: лого, лічильник відвідувачів, дим, перемикач карти, пошук, вхід, мова, кава

### v3.3 (2026-07-15) — Google/Дія OAuth: редірект в /admin для адмінів
- Проблема: вхід через Google з `/admin` завжди редіректив на `/` (публічну головну), а не назад в адмін-панель — сесійна кука виставлялась коректно, але сторінка губилась
- Рішення: стандартний OAuth `state`-параметр несе намір `next=admin` через увесь flow (Google/Дія повертають `state` без змін)
- `/api/auth/google` та `/api/auth/diia` (Paskal.py) приймають `?next=admin` → передають `state=admin` до провайдера
- `/api/auth/google/callback` та `/api/auth/diia/callback` читають `state` і редіректять на `/admin?oauth=success` замість `/?oauth=success`, якщо `state=="admin"`
- Захист від open-redirect: білий список `_OAUTH_NEXT_TARGETS = {"admin": "/admin"}` (Paskal.py, перед Google OAuth блоком) — будь-яке інше/відсутнє значення `state` фолбечиться на `/`
- `admin.html`: кнопка Google (рядок ~582) тепер `onclick="window.location.href='/api/auth/google?next=admin'"`
- `admin.html`: новий `checkOAuthCallback()` (біля `DOMContentLoaded`, ~рядок 5876) — обробляє `?oauth=success`/`oauth_error`, чистить URL, показує помилку в `#lerr` якщо роль не admin/moder (через `/api/auth/me`, бо `/api/admin/me` кидає 403 для не-модераторів)
- Нові i18n ключі: `adm.login.no_rights`, `adm.login.oauth_failed` (секція `admin`, uk+en)
- `index.html` — поведінка без змін (без `next` → дефолтний редірект на `/`)

### v3.2 (2026-07-15) — Лічильник відвідувачів: київська доба замість rolling 24h
- `visitors_24h` тепер рахується від **00:00 за київським часом (Europe/Kyiv)**, а не як плаваюче вікно "останні 24 години"
- Новий хелпер `_kyiv_day_start_ts()` (Paskal.py, ~рядок 1259) — обчислює unix-timestamp початку поточної доби за Києвом через `zoneinfo.ZoneInfo("Europe/Kyiv")`
- Змінено 3 місця в Paskal.py: middleware `track_visits` (dedup `_unique_visitors` + періодичне очищення), `/api/stats`, дублюючий адмін-ендпоінт статистики (~рядок 6170)
- Додано залежність **`tzdata`** в `requirements.txt` — обов'язкова на Windows (systemd/Linux зазвичай має системну tzdata, але пакет не завадить)
- **ВАЖЛИВО для деплою**: після `git pull` на проді виконати `pip install -r requirements.txt`, інакше `zoneinfo.ZoneInfoNotFoundError` при старті

### v3.1 (2026-07-14) — i18n Фаза 1: Інфраструктура
- Нові таблиці БД: `languages` + `i18n_translations` + колонка `users.lang`
- Новий модуль `lang_engine.py`: `t()`, `get_all()`, `get_languages()`, `invalidate_cache()`
- Новий файл `js/i18n.js`: `window.LANG`, `applyI18n()`, `switchLang()`, `BroadcastChannel`
- Нові ендпоінти: `/api/langs`, `/api/i18n/{lang}`, `/api/admin/i18n/*` (6 ендпоінтів)
- Документація: `DATABASE.md` + `CLAUDE.md` секція 16

### v2.2 (2026-07-02)
- Додано модуль **"Вартість проекту"** (sec-projcost) в адмін-панелі
- Нові ключі в `colors`: `proj_cost_*`, `proj_usd_rate`, `proj_usd_rate_updated`, `proj_cost_per_user_usd`
- Нові endpoints: `GET /api/admin/project-cost`, `POST /api/admin/project-cost/refresh-rate`
- Daemon thread `_currency_rate_loop()` — авто-оновлення курсу НБУ кожні 23г
- `portfolio/index.html`: статистика оновлюється кожні 30 хв через `/api/stats`
- `faq.html`, `terms.html`, `rules.html`: прихований блок ціни проекту (`display:none`)
- Виправлено баг SQL `IN` з Python list у PyMySQL
- Виправлено: `credentials:'include'` обов'язковий у всіх admin fetch
- Зображення `img/bgda.png` вставлено в `.doc-sign__stamp` на faq/terms/rules
- Email виправлено на `treetex.g.ads@gmail.com` скрізь (не `admin@zoryana.ua`)
- Фото в `card.html` / `cphoto` — виправлено обрізання (object-fit: contain)
- Кнопка "Схвалити всі" у секції "На модерації" (пакетне схвалення)
