# CLAUDE.md — Зоряна Памʼять (Zoryana Memory)

> Цей файл читається Claude Code на початку кожної сесії. При зміні структури проекту — оновлювати цей файл.
>
> **Пов'язана документація:** [SKILL.md](SKILL.md) (постійні навички: безпека + адаптив, читати ЗАВЖДИ) · [DATABASE.md](DATABASE.md) (повна схема БД) · [MASTER_GUIDE.md](MASTER_GUIDE.md) (гайд розгортання) · [SECURITY_RULES.md](SECURITY_RULES.md) (політики безпеки) · [PRODUCTION.md](PRODUCTION.md) (чекліст продакшн) · [SESSION_CHANGES.md](SESSION_CHANGES.md) (швидкий чекліст деплою останньої сесії — файли + SQL по кожній зміні)

ТЗ модуля «Подарунки загиблому» — виконано повністю, етапи 1–11 (v3.45–v3.53); завантажується разом із цим файлом: @Gifts-for-fallen.md

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
├── pricing/index.html   # Публічна сторінка тарифів (Bronze/Silver/Gold/Platinum), demo-дані, mount /pricing
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
├── SESSION_CHANGES.md   # Швидкий чекліст деплою останньої сесії (файли + SQL, доповнює журнал змін)
├── DEPLOY_v3.44-v3.56.md # Зведена інструкція деплою v3.44–v3.56 (тарифні рамки, «Подарунки загиблому», адмінка, пошук на карті «Світ»): файли, SQL, перевірка, запасний SQL
└── Gifts-for-fallen.md  # ТЗ модуля «Подарунки загиблому» (card?slug=, ПриватБанк, 11 етапів — виконано, v3.45–v3.53) — читати разом із CLAUDE.md
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
descr TEXT                        -- опис (з адмінки — до 10000 символів, з публічної форми — до 5000)
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
tier VARCHAR(10) DEFAULT ''       -- тарифний план: bronze|silver|gold|platinum ('' — без плану); лише вигляд бокової панелі, виставляє адмін
published_at INT NULL               -- коли запис зʼявився на сайті (схвалено чи доданий адміном схваленим); NULL — давні записи й прибрані з «Нових надходжень» (v3.58)
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

#### `pricing_leads` — заявки на тарифи з `/pricing/`
```sql
id          INT PRIMARY KEY AUTO_INCREMENT
plan        VARCHAR(20)             -- bronze|silver|gold|platinum
price_label VARCHAR(40)             -- сирий текст ціни з фронтенду, напр. "799 ₴"
name        VARCHAR(150)
contact     VARCHAR(150)            -- email або телефон (одне поле "як звʼязатись")
memorial_id INT NULL                -- необов'язковий зв'язок з конкретним записом memorials
comment     TEXT
status      VARCHAR(20) DEFAULT 'new'  -- new|contacted|closed
ip          VARCHAR(64)
created_at  INT
INDEX idx_status (status, created_at)
```

#### Модуль «Подарунки загиблому» (Gifts-for-fallen.md) — 4 таблиці, створюються в `init_db()`
```sql
gift_categories (id, code VARCHAR(40) UNIQUE, sort_order, active)
gifts (id, category_id, price_kop INT,          -- ціна в копійках
       img_main, gif_place, img_final,          -- каталог / GIF покладання (етап 7) / біля свічки
       anim_ms, active, sort_order,             -- active=0: не продається, куплені лишаються
       place_scale DECIMAL(4,2), place_area, place_z, created_at, updated_at)
gift_i18n (entity 'gift'|'category', entity_id, lang, name, descr)   -- PK(entity,entity_id,lang), фолбек uk
memorial_gifts (id, memorial_id, gift_id, user_id,
       status,          -- created|pending|paid|cancelled|error|unknown|granted (granted — розміщено адміном без оплати; pending — перехід на оплату LiqPay; paid — підтверджено callback або запитом статусу; cancelled — скасовано або повернення коштів)
       price_kop, currency, order_id UNIQUE, payment_id UNIQUE NULL,
       slot,            -- місце біля свічки: 0–7 передній ряд, 8–15 задній; парні — ліворуч, непарні — праворуч; NULL — понад 16 місць
       anim_state,      -- pending|shown: pending — GIF покладання ще не показано власнику (покупцю чи адміну, що поклав); без GIF — одразу shown
       img_snap, gif_snap,  -- знімок зображень: куплене не зникає при зміні каталогу
       created_at, paid_at, updated_at, INDEX(memorial_id, status), INDEX idx_user_status(user_id, status))
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
| POST | `/api/pricing-lead` | Заявка на тариф з `/pricing/` (rate limit 3/год/IP), зберігає в `pricing_leads` + email-сповіщення `ADMIN_NOTIFY_EMAIL` |
| GET | `/api/recent-additions` | «Нові надходження» (v3.58): схвалені записи, що зʼявились на сайті за останні `recent_days` днів (`published_at`), найновіші першими, до 30 — `id, slug, last, first, ts`. Вимкнено (`recent_enabled=0`) → `{"enabled":false,"items":[]}`. Кеш 60 с (скидається при змінах меморіалів). Rate limit 60/хв/IP |
| GET | `/api/gifts/catalog?lang=uk` | «Подарунки загиблому»: активні подарунки (назва/опис мовою з фолбеком uk, ціна, категорія, зображення; без GIF). Модуль вимкнений → `{"enabled":false,"items":[]}`. Rate limit 60/хв |
| GET | `/api/memorial/{id}/gifts?lang=uk` | Розміщені біля свічки подарунки (`granted`/`paid`): слот, зображення зі знімка, назва, масштаб. Rate limit 60/хв. Власнику подарунка (покупцю чи адміну, що поклав) — ще `anim` `{gif, ms}`, поки покладання не показано; іншим адреса GIF не віддається. Етап 10: за замовчуванням — лише подарунки на місцях (≤16) і `total`; повний список (до 500) — `?full=1`, коли відкривають «ще N» |
| POST | `/api/memorial-gift/{id}/shown` | Етап 7: власник переглянув GIF покладання → `anim_state='shown'` (лише свій подарунок, лише раз; чужий — `changed: 0`). Rate limit 60/хв/IP |
| POST | `/api/gifts/orders` | «Подарунки загиблому»: оформити замовлення `{memorial_id, gift_id}` — лише авторизований (401), модуль і «Купівля доступна» увімкнені (403), ключі LiqPay задані (503). Ціна, користувач і меморіал — на сервері; статус `created`; повторний клік за 10 хв повертає те саме замовлення (`created`/`pending`); ≤5 незавершених на користувача (409); подарунок без ціни — 400. Rate limit 20/год/IP, 10/год/користувач |
| GET | `/api/gifts/orders?memorial_id=&lang=` | Власні замовлення поточного користувача (без тестових `granted`) |
| POST | `/api/gifts/orders/{order_id}/cancel` | Скасувати власне неоплачене замовлення: `created` — одразу; `pending`/`unknown` — після звірки з LiqPay (обробляється чи оплачено — 409, LiqPay не відповів — 503); чуже — 404 |
| POST | `/api/gifts/orders/{order_id}/pay` | Етап 6: перехід на оплату `{lang}`. Повертає `checkout` `{action: https://www.liqpay.ua/api/3/checkout, data, signature}` для форми POST — `data`/`signature` формує сервер із замовлення; статус → `pending`. Незавершену попередню спробу спершу звіряє з LiqPay (щоб не оплатити двічі). Без ключів — 503. Rate limit 30/год/IP, 20/год/користувач |
| POST | `/api/gifts/orders/{order_id}/sync` | Звірити своє замовлення з LiqPay (`action=status`) — після повернення з оплати (`?gift_order=`) або «Перевірити оплату». Повертає замовлення і `check`: `payment` / `none` (платежу немає: `pending` → `created`) / `fail` (LiqPay не відповів) / `skip`. Rate limit 60/год/IP |
| POST | `/api/gifts/liqpay/callback` | `server_url` LiqPay (form `data`, `signature`): підпис `base64(sha1(private+data+private))`, ключ магазину, сума й валюта зі знімка замовлення; оплачене зараховується один раз, місце біля свічки — під блокуванням меморіалу. Працює й під час техробіт. Rate limit 120/хв/IP |
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
| GET | `/api/admin/pricing-leads` | Список заявок на тарифи (`require_moder`) |
| PUT | `/api/admin/pricing-lead/{id}` | Змінити статус заявки (new/contacted/closed) |
| DELETE | `/api/admin/pricing-lead/{id}` | Видалити заявку |
| GET | `/api/admin/recent-additions` | «Нові надходження»: записи, що зараз у блоці, і налаштування (`enabled`, `days`) — `require_admin`, rate limit 60/хв |
| POST | `/api/admin/recent-additions/{id}/hide` | Прибрати запис із блоку (`published_at=NULL`; сам запис на сайті лишається) — `require_admin`, rate limit 60/хв |
| POST | `/api/memorial/{id}/gifts` | «Подарунки загиблому», етап 3 (без оплати): покласти подарунок `{gift_id}` — **лише `require_admin`**; статус `granted`, місце — найближче вільне з урахуванням боку `place_area` (`_gift_pick_slot`); подарунок із GIF — адмін один раз бачить покладання (так анімацію можна перевірити без оплати) |
| DELETE | `/api/admin/memorial-gift/{id}` | Прибрати тестове розміщення (лише `status='granted'`; оплачені так не видаляються) |
| POST | `/api/admin/memorial-gift/{id}/sync` | Звірити замовлення з LiqPay (callback не дійшов, повернення коштів); тестове розміщення адміна — 400, без ключів — 503 |
| GET | `/api/admin/gifts` | «Подарунки загиблому», етап 4: увесь каталог (з вимкненими), категорії, тексти всіма мовами (`i18n`), активні мови, лічильник розміщень `placed`; стан оплати `payment` `{ready, sandbox, callback_url}`; `notify` `{email, smtp_ready}` — куди піде лист про оплату |
| POST / PUT / DELETE | `/api/admin/gifts`, `/api/admin/gifts/{id}` | Створити / змінити / видалити подарунок. Ціна в ₴ (зберігається в копійках), зображення — лише `/img/gifts/…`. Видалення з розміщеннями → 409 (лише вимкнути) |
| POST / PUT / DELETE | `/api/admin/gift-categories`, `/api/admin/gift-categories/{id}` | Категорії: код `^[a-z0-9_-]{2,40}$` (дубль → 409), назва uk обов'язкова; видалення категорії з подарунками → 409 |
| POST | `/api/admin/gifts/upload` | Multipart `file` + `kind` = `main` (PNG/JPG/WEBP ≤2 МБ) / `final` (PNG/WEBP ≤2 МБ) / `gif` (GIF ≤6 МБ). Сигнатура файлу має відповідати розширенню; для GIF повертає `frames`, `duration_ms`, `w`, `h`. Rate limit 30/хв; для зображень — `w`, `h`, `size` (адмінка попереджає, якщо більше 600 px або 300 КБ) |
| GET | `/api/admin/memorial-gifts?status=&q=&page=` | Розміщення / покупки: фільтр за статусом, пошук (ID меморіалу, прізвище, email/нік), пагінація, лічильники за статусами; `paid_sum` — сума оплачених (₴) |

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
LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY   # оплата подарунків (LiqPay); без них оплата вимкнена
LIQPAY_SANDBOX=1                        # 1 — тестові платежі, 0 — бойові
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
- Привиди в диму — силуети-примари, що з'являються в диму (`ghost_*` налаштування, деталі нижче)
- Хвилі моря (`sea.js`, SVG overlay)
- Кнопка fullscreen (`#btn-fs`)
- Теми: `loadColors()` → CSS variables

### Модуль «Привиди в диму» (`js/ghost-faces.js`, Canvas2D + фізична інтеграція з WebGL-димом)
**Призначення**: меморіальний ефект — прозорі людські силуети (SVG, `img/ghosts/*.svg`)
періодично з'являються поверх карти в потоці диму, ніби постаті проступають і розчиняються
в димі. Візуально й фізично прив'язані до вже наявної WebGL fluid-симуляції (`js/script.js`),
але живуть в окремому Canvas2D-шарі (`#ghost-layer`, `mix-blend-mode:screen`) — не чіпають
WebGL-рендер напряму, окрім однієї спеціальної інтеграції (нижче).

**Архітектура (коротко, детальна історія фіксів — v3.29–v3.32 нижче в журналі змін)**:
- **Позиціонування**: привид з'являється у випадковій точці всередині поточного bbox
  видимої карти України (`getMapScreenBBox()`), не будь-де на екрані
- **Fade-анімація**: рівномірна (constant-rate) поява/зникнення — `currentOpacity` рухається
  до `targetOpacity` фіксованою швидкістю (`ghost_fade_in_speed`/`ghost_fade_out_speed` per
  секунду, не per кадр), а не експоненціальним згладжуванням (те давало суб'єктивний "ривок")
- **Видимість (`targetOpacity`)**: добуток близькості курсора до привида, щільності диму в
  цій точці (`sampleSmokeDensityAt`) і `ghost_max_opacity` — привид проступає сильніше, коли
  курсор і густий дим одночасно поруч
- **Тонування кольору силуету**: SVG розтеризується в offscreen canvas і перефарбовується
  (`source-in` composite) у колір `ghost_tint_color`/`ghost_tint_opacity` (адмінка) — сирий
  чорний SVG на `mix-blend-mode:screen` був би невидимий (чорний = прозорий у screen-режимі)
- **Підсвічена кромка** (`renderEdgeHighlight()`): тонка світла обводка вздовж реального
  альфа-контуру силуету (не bbox), видима лише локально біля курсора (~15-35px), кольору
  "як дим" — незалежний генератор кольору, не тягне справжній колір з `js/script.js`
- **Фізична перешкода для диму** (єдине місце, де модуль торкається `js/script.js`):
  альфа-маска силуету (той самий offscreen canvas) вивантажується в WebGL-текстуру
  (`window._fluidUpdateObstacleMask`) — `divergenceShader` трактує контур як тверду стінку
  (`OBSTACLE_PERMEABILITY=0` за дефолтом), плюс окремий `obstacleAttractShader` "примагнічує"
  дим вздовж контуру — дим візуально відштовхується/обтікає форму, а не проходить крізь неї
- **Налаштування**: усі `ghost_*` ключі в таблиці `colors`, керуються через адмінку (розділ
  "Привиди в диму") з live-preview через `BroadcastChannel`, той самий патерн що й `smoke_*`

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
- **Привиди в диму**: `ghost_enabled`, `ghost_dev_mode`, `ghost_max_opacity`, `ghost_fade_in_speed`, `ghost_fade_out_speed`, `ghost_reveal_threshold_px`, `ghost_mouse_recency_threshold_ms`, `ghost_tint_color`, `ghost_tint_opacity`, `ghost_obstacle_permeability`, `ghost_obstacle_attract_strength`, `ghost_edge_highlight_enabled`, `ghost_edge_highlight_radius_px`, `ghost_edge_highlight_width_px`, `ghost_edge_highlight_blur_px`, `ghost_edge_highlight_strength`
- **Sea**: `sea_enabled`, `sea_wave_color`, `sea_svg_content`, тощо
- **Іконки**: `icon_logo` (`★`), `icon_likes` (`⭐`), `icon_people` (`👥`)
- **Соцмережі**: `social_facebook`, `social_facebook_url`, `social_order`
- **Admin**: `admin_theme`, `admin_nav_order`, `admin_logo_url`
- **Фото на карті**: `map_photo_url`, `map_photo_opacity`, `map_photo_blend`
- **Пристрої**: `device_desktop_enabled`, `device_tablet_enabled`, `device_mobile_enabled` (1=так, 0=ні), `device_block_msg` (текст заглушки)
- **Вартість проекту**: `proj_cost_server_usd`, `proj_cost_domains_usd`, `proj_cost_ai_usd`, `proj_cost_other_usd`, `proj_cost_months`, `proj_usd_rate` (НБУ, авто), `proj_usd_rate_updated` (timestamp), `proj_cost_per_user_usd` (CPM, default 1.0)
- **Підказки сайту**: `tour_enabled` (1=так, 0=ні — вимикає онбординг-тур для нових відвідувачів), `tour_video_enabled` (1=так, 0=ні — окремо вимикає показ відео-вікна, не видаляючи URL), `tour_video_url` (посилання на відео-інструкцію, показується замість туру коли `tour_enabled=0` і `tour_video_enabled=1`; YouTube → вбудований iframe, інше → кнопка-посилання)
- **Подарунки загиблому**: `card_gifts_enabled` (1=так, 0=ні, дефолт 0) — кнопка й каталог подарунків біля свічки на `card?slug=`; перемикач в адмінці: розділ «Подарунки загиблому» → вкладка «Налаштування»; `card_gifts_buy_enabled` (1=так, 0=ні, дефолт 0) — «Купівля доступна»: авторизовані відвідувачі можуть оформити замовлення (там само, «Налаштування»); `card_gifts_pay_ready` — у БД не зберігається: `/api/card/settings` обчислює з `.env` (1 — ключі LiqPay задані); етап 9: `card_gifts_button` (1 — кнопка «Подарунки загиблому» й каталог; 0 — нового подарунка не обрати й не купити, покладені лишаються), `card_gifts_anim` (1 — GIF покладання покупцю), `card_gifts_anim_scale` (у скільки разів GIF ширший за подарунок, 1.5–5, дефолт 2.8), `card_gifts_size` (розмір подарунків біля свічки, 70–140 %, дефолт 100), `card_gifts_notify` (1 — лист адміну про оплачений подарунок на `ADMIN_NOTIFY_EMAIL` з `.env`). Усі — у розділі «Подарунки загиблому» → «Налаштування»
- **Нові надходження** (v3.58): `recent_enabled` (1=так, 0=ні, дефолт 1) — блок над статистикою в лівому нижньому куті index.html; `recent_days` (1–14, дефолт 3) — скільки днів запис тримається в блоці. Адмінка → «Нові надходження»; значення перевіряються в `PUT /api/admin/colors/batch`
- **Відео-попап (реклама)**: `ad_video_enabled` (1=так, 0=ні), `ad_video_url` (YouTube), `ad_video_title` (назва над плеєром), `ad_video_preview_url` (URL прев'ю-картинки), `ad_video_channel_url` (посилання на канал), `ad_video_channel_btn` (текст кнопки каналу), `ad_video_freq_days` (частота показу одному відвідувачу, днів)

---

## 11. ПРАВИЛА РОБОТИ ДЛЯ CLAUDE

### При старті нової задачі — ОБОВ'ЯЗКОВО
1. Прочитати **всі MD файли** проекту: `CLAUDE.md`, `SKILL.md`, `DATABASE.md`, `MASTER_GUIDE.md`, `SECURITY_RULES.md`, `PRODUCTION.md`, `SESSION_CHANGES.md`, `Gifts-for-fallen.md` (активне ТЗ модуля «Подарунки загиблому»; підключений до цього файлу через `@`-імпорт)
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
- Наявні іконки спрайту: `#ico-stats`, `#ico-doc`, `#ico-hourglass`, `#ico-users`, `#ico-auth`, `#ico-email`, `#ico-palette`, `#ico-share`, `#ico-smoke`, `#ico-waves`, `#ico-star`, `#ico-photo`, `#ico-city`, `#ico-candle`, `#ico-search`, `#ico-check`, `#ico-cross`, `#ico-edit`, `#ico-trash`, `#ico-plus`, `#ico-map`, `#ico-gift`
- **Іконки спрайту:** будь-який новий `href="#ico-…"` — лише якщо `<symbol>` справді є в спрайті admin.html. `#ico-plus` і `#ico-cross` раніше використовувались (15 місць), але не були визначені — кнопки «Додати» стояли без іконки. Додано у v3.46
- **Тексти каталогу «Подарунків загиблому»** зберігати через `_gift_text()`, не `_sanitize_text()`: останній робить `html.escape` і апостроф («пам'ять») показувався б як `&#x27;`. `_gift_text` прибирає `<`, `>` і керівні символи, а екранування — на виводі (`h()` / `textContent`)
- **Оплата LiqPay (v3.48)**: ключі мерчанта — лише в `.env` (`LIQPAY_PUBLIC_KEY`/`LIQPAY_PRIVATE_KEY`/`LIQPAY_SANDBOX`), ніколи в `colors` (`/api/colors` публічний) чи на фронтенді. Оплаченим замовлення робить лише `_gift_apply_payment()` — після підписаного callback або запиту статусу з сервера (сума й валюта — зі знімка замовлення). Параметр `?gift_order=` і кнопки на сторінці лише запускають звірку. Префікс `/api/gifts/liqpay/` у `_MAINTENANCE_ALLOW` не прибирати — інакше платежі під час техробіт не зарахуються
- **GIF покладання (v3.49)**: адресу GIF сервер віддає лише власнику подарунка й лише поки `anim_state='pending'`; іншим відвідувачам — тільки статичне зображення (GIF не вантажиться). Біля свічки GIF показується в 2.8 раза ширшим за подарунок і з тим самим низом, тож у файлі подарунок наприкінці має стояти внизу по центру й займати ≈⅓ ширини кадру (підказка є в адмінці). Нові оверлеї над свічкою — через `.gift-anim` / `_giftMaybeAnimate()`: анімація грає лише коли вікно подарунків закрите, вкладка видима, а свічка в полі зору
- **Місця біля свічки (v3.50)**: 16 місць — 2 ряди × 8 (`_GIFT_SLOTS`); місце призначає лише сервер через `_gift_pick_slot()` (бік `place_area`, спершу передній ряд, понад 16 — `slot=NULL` → «ще N» і список усіх подарунків). На сторінці: крок `--gs` не менший за найширший подарунок (масштаб біля свічки обмежено 0.6–1.25), тож сусіди в ряду не накладаються; `_giftRelayout()` разом зменшує ряди на вузькому екрані (`--gfit` до 0.6), а що не вміщується — ховає в «ще N» (горизонтального прокручування немає). `.gift-stage { z-index:1 }` не прибирати: без нього подарунок із від'ємним «шаром» ховається за фоном секції
- **Налаштування модуля (v3.51)**: ключі `card_gifts_*` перевіряються при збереженні в `PUT /api/admin/colors/batch` (`_GIFT_FLAG_KEYS` — лише 0/1, `_GIFT_NUM_KEYS` — числа в межах). Нове налаштування модуля — туди ж і в дефолти `/api/card/settings`. Адреси, ключі й інші секрети в `card_*` не класти: `/api/card/settings` і `/api/colors` публічні (адреса листів — лише `ADMIN_NOTIFY_EMAIL` у `.env`). Листи про оплату — у фоновому потоці (`_gift_notify_paid`), лише при переході в `paid`
- **Продуктивність модуля (v3.52)**: при відкритті картки — лише 2 легкі запити (тексти `gifts` і подарунки на місцях, паралельно); повний список — тільки за «ще N»; каталог, його зображення й GIF — тільки за дією користувача; зображення біля свічки — `loading="lazy"`. Не повертати повний список у запит за замовчуванням і не вантажити каталог заздалегідь. Налаштування модуля читати одним запитом (`_gift_settings()`). Звільнене місце (повернення коштів, прибране розміщення) займає найстаріший «понад місця» (`_gift_fill_free_slots`)
- **Тайли Leaflet-карт (v3.54)**: адресу тайлів брати лише з налаштування `worldmap_tile_url` (адмінка → «Карта світу», з ключем CARTO), в admin.html — через `_admTileLayer()`. Адресу CARTO в коді не хардкодити: з 2026 року без ключа вона віддає заглушку «API KEY REQUIRED». Через таку карту адмін поставив мітку наосліп, і зірка запису опинилась в Індії
- **Довжина опису (v3.55)**: «Опис» (`descr`) — до 10000 символів з адмінки (редагування, створення, імпорт CSV), до 5000 — з публічної форми (`add_person`). Межу міняти всюди разом: `maxlength` поля `#e-desc` і лічильник `/N` (admin.html), `PersonIn.descr`, обрізання в `update_memorial`, імпорт. `maxlength` текстового поля не може бути меншим за найдовший збережений текст: `_V.text` на кожному вводі обрізає значення до `maxlength` (так поле з `maxlength=200` обрізало опис до 200 при першому ж стертому символі)
- **Кнопки CSS**: базовий `.btn` — чорний фон `#111318`. `.btn-p` — чорний фон з синьою рамкою (`border-color:rgba(0,136,187,.6);color:#a8e0f8`). `.btn-r/g/b` — чорний фон зі своїм кольором рамки/тексту
- CSS через `var(--variable)` для підтримки тем
- `applySocialLinks()` викликати після `loadColors()` в index.html
- `BroadcastChannel('zoryana_colors')` для синхронізації між вкладками
- **КРИТИЧНО — успадковувані CSS-властивості на `#map-wrap`**: JS перемикає `cursor` на `#map-wrap` (наведення на точку, драг, вибір точки). Правило `#svg-layer, #city-overlay { cursor: default; }` у Style.css **не видаляти**. Без нього кожне перемикання перераховує стилі ~1560 елементів SVG-карти і перемальовує весь шар карти (до ~200 мс GPU-растеризації, дим підвисає; див. v3.39). Те саме стосується будь-якої іншої успадковуваної властивості (`color`, `font-*` тощо), яку JS змінюватиме на великому контейнері
- **Зум карти — гібридний рендер (v3.42)**: кожна зміна `viewBox` SVG-карти — це повна перерастеризація (~170–250 мс GPU на слабких машинах), тому щокадрово міняти його в анімаціях не можна.
  - нові анімації зуму робити через `_zoomBy(f, ax, ay)` (плавна ціль) або через `_applyTrVisual()` (CSS-transform `#svg-layer` від `_trC`) з комітом `_commitTr()` у спокої;
  - перетягування (миша, палець), щипок і `flyTo` — теж гібридні (v3.67): кожен рух — `scheduleGesture()` (раз на кадр) → `_gestureFrame()` (лише `_applyTrVisual`), кінець жесту — `_gestureEnd()` (один `_commitTr`): `mouseup`, `touchend`, кінець польоту, 400 мс без вводу. Проміжний коміт — лише зсув понад 1.5 екрана, віддалення нижче ×0.5 чи наближення понад ×2.5 від растру, не частіше ніж раз на 300 мс. `applyTr()` — тільки для разових змін (скидання, ресайз), не для анімацій і жестів;
  - підписи міст (`scaleCityLabels`, v3.67): приховані (нижче порогу меж міст) — не розставляються, розставляються при появі (`_applyZoomClasses`); під час жесту без зміни масштабу — одна CSS-трансформація шару `#city-overlay` (у Style.css `will-change: transform`, не прибирати), точне розставлення — після жесту. Новий код, що змінює `tr`, має йти через ці функції, а не писати `transform` кожному підпису;
  - `#svg-layer { will-change: transform }` у Style.css не прибирати;
  - мінімум зуму в коді — `min(zoom_min, 1)`: стартовий вигляд ×1 мусить бути досяжним без стрибків
- **Зум Leaflet-карт (v3.43)**: кожен `L.map(...)` створювати з `Object.assign({...}, _LF_ZOOM_OPTS)` і одразу підключати `_lfSmoothWheel(map)`. Штатний `scrollWheelZoom` не вмикати: він крокує цілими рівнями й губить оберти під час анімації. Перед програмним зумом (кнопки, `flyTo`) викликати `map._zpWheelStop()`
- **Цикл зірок України в режимі «Світ» (v3.67)**: `_startCanvasLoop()` зупиняється, коли `_mapMode==='world'` (канвас прихований), і запускається знову в `setMapMode('ukraine')`. Раніше `_canvasLoopRunning=false` нічого не зупиняв: прихований канвас малював далі, а кожне повернення на карту України запускало ще один цикл
- **Режим «Світ» і `#map-wrap` (v3.43)**: Leaflet-контейнер лежить усередині `#map-wrap`, і його події спливають до обробників основної карти. Кожен новий обробник жестів чи кліків основної карти (`#map-wrap`, `window`) має ігнорувати `_mapMode==='world'`. Інакше жести «Світу» рухатимуть приховану карту України або відкриватимуть картку іншої людини
- **Пошук і картка в режимі «Світ» (v3.56)**: вибір загиблого в режимі «Світ» — політ по Leaflet-карті (`_worldFlyTo`), а не `flyTo()`: та рухає приховану карту України. Зірку відкритої картки підсвічує `_worldPick(id)` (аналог `selId` на карті України): ставиться в `openCard()`, знімається в `closeCard()`, повертається після перемальовування маркерів. Новий шлях відкриття картки, що має показати точку на карті, — через ці функції «Зірка памʼяті» в режимі «Світ» (v3.62) — `_worldLikeBurst(p)` (⭐ у шарі маркерів Leaflet), а не `particles` канвасу України: той у режимі «Світ» зупинений, і зірочки накопичувались би
- **Кеш HTML-сторінок (v3.57)**: `security_headers` додає `Cache-Control: no-cache` до HTML без власного правила кешу (адмінка, картка, faq, профіль, `/update_v`, `/pricing`…) і відповідає `304` за ETag (з урахуванням слабкого `W/…`, який робить gzip у Nginx). Не прибирати: без цього після заливки браузери показують стару сторінку з кешу (так адмінка після деплою v3.54 ще показувала стару карту). Сторінці з особливим кешем — ставити `Cache-Control` у маршруті (як `/` — `no-store`, `/memorial/…` — `max-age=300`)
- **«Нові надходження» (v3.58)**: запис потрапляє в блок лише тоді, коли зʼявляється на сайті — `published_at` ставлять `POST /api/admin/approve/{id}`, створення адміном і правка «схвалено» 0 → 1 (присвоєння `published_at=IF(approved=1, published_at, now)` — перед `approved`, щоб бачити старе значення). Новий шлях публікації запису має ставити `published_at` так само; звичайне збереження вже схваленого запису його не змінює. Блок на сайті — над `#bottom-blocks`, а якщо чат увімкнено — над `#micro-chat` (`_rbPlace()`). На телефоні (v3.60) — розділ угорі попапу ★ (`#bbp-recent`) і значок кількості нових на кнопці ★ зі сяйвом, доки попап із цими записами не відкривали (`localStorage zp_recent_seen`; позначка — за класом `bb-open` попапу, а не обробником кнопки)
- **HTML у вбудованих обробниках (v3.59)**: розмітку в атрибут на кшталт `onerror="this.outerHTML='…'"` вставляти лише через `h()` (подвійні лапки → `&quot;`), без заміни лапок: сирі `"` закривають атрибут і ламають сторінку, а заміна `"` на `'` обриває JS-рядок `'…'`. Сама розмітка при цьому не повинна містити `'`
- **«Опис» у боковій панелі (v3.63)**: текст опису ставити лише через `_descSet()` + `_descLayout()` (як у `_renderCardDetails`), не через `_setText('cdesc', …)` — інакше не перерахується згорнута висота й не скинеться «розгорнуто». `#cdesc` — `display:block` (інакше `scrollHeight` = 0); стан — класи `desc-long` / `desc-expanded` на `#cdesc-row`, висота — inline `max-height` (ціле число рядків). Нова картка — `_descReset()` в `openCard()`. Поріг (10 рядків) і частка (0.4) — `_DESC_MIN_LINES`, `_DESC_SHOW` (index.html і mobile.html однаково)
- **Тарифний план погибшого (v3.44)**: `memorials.tier` (`bronze|silver|gold|platinum`, `''` — без плану) виставляє **лише адмін**:
  - адмінка: поле «Тарифний план» у модалці редагування/створення; для модератора поле заблоковане, а сервер відкидає план від модератора;
  - публічна форма «Додати запис» план не записує;
  - сайт: `openCard()` → `_applyCardTier()` → `#card[data-tier]` + шар `#ctier` (Style.css). Перелив кромки анімувати лише `transform`/`opacity`: панель має `backdrop-filter` і не повинна перемальовуватись щокадру;
  - кромка (v3.66): тонке кільце 2 px — маска `#ctier` із 2 шарів (`content-box` / `border-box`, `exclude`; повторює заокруглені кути листа). Відблиск — смуги `.ctg` (у `#ctier`, у межах кільця) і ореоли `.ctf` (у `#ctier-spark`, без маски) зі спільними keyframes `ctgTop/Left/Right/Bottom`: діагональ c = x + y (однакова швидкість на всіх сторонах), довжина шляху — `cqw`/`cqh`, тому обидва контейнери мають `padding: 2px` і `container-type: size`. Іскри — `#ctier-spark::before/::after`. Цикл 7 с спільний для відблиску, іскор і відблиску таблички — міняти разом. Лише `transform`/`opacity`; маску не анімувати. `#cclose` при плані — `z-index: 8`;
  - назва плану в лівому верхньому куті — `#ctier-badge` / `#ctier-name` (v3.64): текст ставить лише `_applyCardTier()`. Шрифт Cinzel підключено окремим посиланням Google Fonts з `text=` — у файлі шрифту лише літери чотирьох назв (B R O N Z E S I L V G D P A T U M). Нова назва плану з іншими літерами — дописати їх у `text=` (index.html і mobile.html), інакше вони намалюються запасним шрифтом;
  - цін і оплати поки немає — план означає тільки вигляд бокової панелі
- **Оверлеї поверх повноекранної картки (телефон)**: `#card` має z-index 800. Будь-який новий `position:fixed` віджет (реклама, годинник, кнопки тощо) з вищим z-index ляже поверх опису загиблого. Його селектор треба додати в правило `body.zp-panel-open …` у Style.css (див. v3.40). Ховати через `_partnersHide()`/`_partnersShow()` (визначені перед `openCard()` в index.html), а не inline-стилями

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
| Усі міста з адмінки (`cities_ua_enabled=1`) | ~460 підписів. Драг — 25–43 кадри/с (v3.67, раніше 3–6), але зум (колесо, щипок, політ) і далі переставляє й перемальовує кожен підпис щокадру — повільно, як і до v3.67. Кандидат: під час зміни масштабу оновлювати лише видимі підписи |
| Планшет: політ разом із відкриттям картки | ~30–35 кадрів/с (без картки — ~56): аркуш картки на ~90 % екрана з `backdrop-filter` щокадру розмиває карту, що рухається. Кандидат: без розмиття під час виїзду аркуша |
| Карта «Світ» — FPS | 1168 маркерів — DOM-елементи (`L.divIcon` зі SVG і CSS-пульсацією); на слабких GPU ~10 кадрів/с у спокої. Кандидат на canvas-рендер маркерів (див. v3.43) |
| `mobile.css` локально | Локальний uvicorn не має маршруту `/mobile.css` (є лише `/Style.css`, `/silence-module.css`) → 404, і mobile.html локально рендериться без нього. На проді файл роздає Nginx (`try_files`). Для локальної перевірки mobile.html підставляти файл через CDP `Fetch` |
| LiqPay локально | Callback LiqPay не дістане `127.0.0.1`: локально оплата підтверджується звіркою (`action=status`) при поверненні на `card?slug=…&gift_order=…` або кнопкою «Перевірити оплату». На проді `SITE_BASE_URL` — публічна адреса (кириличний домен — у punycode); від неї будуються `server_url` і `result_url` |
| `card.html` англійською | Сторінка меморіалу не локалізована: англійською перемикаються лише тексти модуля «Подарунки загиблому» (секція `gifts`), а свічка й решта картки — українською. Текст свічки за ТЗ модуля не змінюється; локалізація картки — окремим рішенням (помічено на етапі 11) |

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

### v3.67 (2026-10-05) — Плавне перетягування карти України (і щипок, і політ) + цикл зірок не працює в режимі «Світ»
- Скарга користувача: при перетягуванні карти в обох режимах (UA і «Світ») ривки й підвисання в будь-якому напрямку. Спершу — аналіз із замірами (headless Chrome зі справжньою відеокартою AMD Radeon 610M, 1920×1080, драг 2 с із подіями миші 60 Гц), потім за рішенням користувача — перший блок виправлень (W1 + UA1), «щоб звʼязки й керування з адмінки працювали»
- **Причини (заміри):**
  - карта України: кожен рух драгу міняв `viewBox` SVG (`applyTr` → `_commitTr`) — повна перерастеризація карти (~1400 фігур, свічення 3× `drop-shadow`, фото з маскою) ~180–230 мс на кадр: 4–5 кадрів/с, відеокарта зайнята 97 %. Свічення подвоює ціну перерисовки, фото — ×1.6; дим — другорядний;
  - «Світ»: 1168 маркерів — DOM-елементи з вічною CSS-анімацією всередині SVG (браузер не віддає її відеокарті): головний потік зайнятий 94 %, 5 кадрів/с. Окрема вада: прихований канвас зірок України малював і в «Світі», а кожне повернення на карту України запускало ще один цикл
- **Зроблено (index.html, mobile.html, Style.css):**
  - драг мишею й пальцем, щипок (`zoomAt`) і `flyTo` (клік по зірці, пошук, «Нові надходження») — як плавний зум v3.42: під час руху лише CSS-зсув шару карти, `viewBox` — один раз у кінці (`mouseup`, `touchend`, кінець польоту, 400 мс без руху). Браузер уже малює карту за межами екрана (SVG з `overflow: visible`): перевірено — зсув до 5200 px і віддалення до ×0.35 показують ту саму карту, що й після перерисовки, без порожніх країв. Проміжний коміт — лише як запас: зсув понад 1.5 екрана, віддалення нижче ×0.5, наближення понад ×2.5 (інакше розмито), не частіше ніж раз на 300 мс; «400 мс без руху» — від останнього вводу, не від кадру;
  - підписи міст: приховані — не переставляються; під час драгу — один CSS-зсув шару замість переписування кожного (з усіма ~460 містами з адмінки — ~460 атрибутів щокадру); точне розставлення після жесту; `#city-overlay { will-change: transform }`;
  - W1: цикл канвасу зірок України зупиняється в режимі «Світ» і запускається знову при поверненні (дублювання циклів прибрано)
- **Заміри ДО → ПІСЛЯ** (ПК 1920×1080; планшет — mobile.html 1180×820, дотики):

  | | ДО | ПІСЛЯ |
  |---|---|---|
  | драг мишею (UA) | 4–5 кадрів/с, кадр до ~1 с | 50–60 кадрів/с, медіана 16.7 мс |
  | драг пальцем (планшет) | — | 60 кадрів/с |
  | `viewBox` за драг | щокадру | 0 під час руху, 1 після |
  | політ до точки | коміт щокадру (~55) | 1 коміт, медіана кадру 16.7 мс |
  | драг з усіма ~460 містами | 3–6 кадрів/с | 25–43 кадри/с |
  | прихований цикл зірок у «Світі» | 190–390 мс роботи за драг | 0 |

  Після відпускання — один кадр перерисовки (на цій відеокарті 220–520 мс): та сама пауза, про яку попереджено, замість ривків протягом усього руху
- **Перевірено** (headless Chrome, :8000 лише читання; ПК 24/24, планшет — драг, щипок, «Світ»):
  - посеред драгу зірки (канвас) і точки карти (SVG) збігаються з точністю 0 px; лінії звʼязку малюються щокадру; підписи міст — ≤ 0.07 px; після жесту — закомічено, зсув знято;
  - клік по зірці → картка + політ; пошук / «Нові надходження» → політ; колесо — як і було; пороги зуму (клас `zoom-city`) застосовуються після жесту;
  - керування з адмінки наживо (BroadcastChannel, той самий формат, що шле admin.html): заливка областей, межа зуму (щипок упирається в ×5), поріг меж міст, прозорість фото, усі міста — застосовуються, жести працюють; налаштування повернуто;
  - «Світ»: канвас зірок України не малює; повернення — цикл один (виклики циклу / кадри = 0.98); 0 помилок JS
- **Помічено, не змінювалось:**
  - колір свічення країни з адмінки застосовується після перезавантаження сторінки (`initSVGBorders()` викликається лише при старті) — так було й до v3.67;
  - див. розділ 12: зум з усіма містами; планшет — політ разом із відкриттям картки (~30–35 кадрів/с через розмиття аркуша); карта «Світ» — FPS (маркери-DOM, наступний крок W2)
- Версія: `Style.css?v=20261005d` (index.html, mobile.html)
- Файли: `index.html`, `mobile.html`, `Style.css`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні
- **Далі (за рішенням користувача):** W2 — маркери «Світу» на одному канвасі (заміри: 5 → ~60 кадрів/с), UA2 — дешевша перерисовка карти (свічення, фото)

### v3.66 (2026-10-05) — Рамка тарифного плану: тонка 2 px із відблиском і блиском
- Пряма вимога користувача: переробити рамку — тонка 2 px, але з ефектом відблиску й блиску (мʼяке широке світіння v3.65 прибрано)
- **Як виглядає (Style.css, index.html, mobile.html):**
  - тонка металева лінія 2 px у кольорі плану (маска-кільце, як до v3.65, але 2 px замість 3);
  - **відблиск:** світло спалахує в лівому верхньому куті й біжить рамкою в обидва боки — верхом і правим боком та лівим боком і низом — до правого нижнього кута, де дві половини зустрічаються. Це як діагональна смуга світла, що проходить панеллю (c = x + y), тож швидкість на всіх сторонах однакова, а кути передаються без розривів. Кожна половина — яскрава біла смуга на самій лінії (130 px) і мʼякий ореол світла плану, що виходить у панель (70 px);
  - **блиск:** іскра-хрестик спалахує в лівому верхньому куті, коли виходить відблиск (~5 % циклу), і в правому нижньому — у мить зустрічі (~31 %);
  - цикл 7 с: пробіг ~2.5 с (з плавним розгоном і гальмуванням), далі пауза; відблиск таблички «GOLD» — у тому самому циклі, коли світло проходить над нею;
  - лише поки картка відкрита; при `prefers-reduced-motion` — тільки тонка лінія, без руху; у браузерах без `cqw` — без бігу світла (іскри лишаються)
- **Як зроблено:** 4 смуги `.ctg` у `#ctier` (маска кільця пропускає лише лінію) і 4 ореоли `.ctf` у `#ctier-spark` (без маски; зовнішню половину ореолу обрізає край панелі) зі спільними keyframes `ctgTop/Left/Right/Bottom`. Довжина шляху — з розміру рамки через `cqw`/`cqh` (`container-type: size` на обох контейнерах). Старий перелив (смуга згори вниз, `#ctier::after`) прибрано
- **Перевірено** (headless Chrome, :8000 лише читання; #1294 — gold з БД, інші плани — `_applyCardTier()` у сторінці; ПК 17/17, телефон 16/16, планшет — mobile.html 16/16):
  - у спокої — лінія рівно 2 px (122, 123 → одразу фон 17); бронза, срібло, платина — так само;
  - анімації лише при відкритій картці: 4 смуги, 4 ореоли, 2 іскри, відблиск таблички — усі 7 с;
  - в 9 моментах пробігу всі 4 смуги й 4 ореоли на одній діагоналі (розкид 0 px), ореоли — по центру лінії, рух лише вперед від −62 до 1267 px (W + H = 1205);
  - іскра старту — непрозора на 5 %, іскра зустрічі — на 31 % (світло саме в куті);
  - reduced-motion — без анімацій; панель не перемальовується (`paintCount` шару `#card` за 3 с — 1 → 1); закрили картку — анімацій немає; 0 помилок JS
- Версія: `Style.css?v=20261005c` (index.html, mobile.html)
- Файли: `Style.css`, `index.html`, `mobile.html`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.65 (2026-10-05) — Кромка тарифного плану: внутрішній бік мʼякий і товщий
- Пряма вимога користувача (скриншот з проду, Platinum): рамка бокової панелі з боку, що дивиться всередину, має бути розмита й товща — плавно зливатись із панеллю
- **Було:** маска `#ctier` — кільце 3 px: металева лінія різко обривалась у фон панелі
- **Стало (Style.css):**
  - по зовнішньому краю — та сама чітка лінія 3 px;
  - від неї всередину — мʼяке світіння металу плану, що плавно згасає до ~23 px: 4 лінійні згасання (по одному на кожен бік, профіль 3 px → 66 % на 6 px → 38 % на 10 px → 17 % на 15 px → 6 % на 19 px → 0 на 23 px) додано до кільця в масці (`mask-composite: add, add, add, add, exclude`);
  - кільце лишилось окремим шаром маски, тож лінія повторює заокруглені кути листа в mobile.html; світіння біля кутів трохи сильніше — природно;
  - перелив (світла смуга згори вниз) тепер теж пробігає мʼяким світінням;
  - кнопка закриття при плані — над світінням (`z-index: 8`); табличка назви плану й так вище; текст панелі починається на 18 px, де світіння вже майже згасло
- **Перевірено** (headless Chrome, :8000 лише читання; #1294 — gold з БД, інші плани — `_applyCardTier()` у сторінці; ПК 11/11, телефон 10/10, планшет 10/10):
  - профіль яскравості від краю панелі всередину (смуга в темній частині фото; дим і привиди, що лежать над панеллю, на час виміру сховано): ДО — після лінії одразу фон (123 → 17); ПІСЛЯ — плавно 117 → 105 → 93 → 76 → 56 → 38 → 25 → 17 (4…23 px), монотонно; ліворуч +76 / +45 / +21 / +6 на 6 / 10 / 15 / 20 px, праворуч +114 / +66 / +28 / +7; на 26 px і далі — як було; лінія по краю та сама;
  - бронза, срібло, платина — так само;
  - маска — 6 шарів; кнопка закриття — `z-index 8`;
  - перелив іде, а панель не перемальовується: `paintCount` шару `#card` за 3 с — 2 → 2;
  - 0 помилок JS (поза відомим: дим без WebGL у headless)
- Версія: `Style.css?v=20261005b` (index.html, mobile.html)
- Файли: `Style.css`, `index.html`, `mobile.html` (лише версія CSS), `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.64 (2026-10-05) — Назва тарифного плану («GOLD» тощо) в лівому верхньому куті бокової панелі
- Пряма вимога користувача (скриншот з проду): у кого виставлено бронзу, срібло, золото чи платину — у боковому вікні вгорі зліва гарним шрифтом написати назву плану, наприклад «GOLD»
- **Як виглядає (index.html, mobile.html, Style.css, mobile.css):**
  - темна табличка 28 px заввишки з металевою рамкою плану (`--tier-metal`), ромб-орнамент і назва великими літерами — шрифт Cinzel (класичні «римські» капітелі), текст залитий металом плану (новий `--tier-text`: золото, мідь, сріблясто-білий, біло-крижано-бузковий);
  - на рівні кнопки закриття: 13 px від країв (на листі mobile.html — по центру 44-піксельної кнопки);
  - відблиск пробігає табличкою одразу після переливу кромки (той самий цикл 6.5 с), лише `transform` і лише поки картка відкрита; при `prefers-reduced-motion` — без відблиску;
  - запис без плану — таблички немає
- Назви — латиницею, як на сторінці `/pricing/` і в прикладі користувача (BRONZE / SILVER / GOLD / PLATINUM), однаково українською й англійською — перекладів не потрібно
- **Шрифт:** окреме посилання Google Fonts `Cinzel:wght@700&text=…` — лише літери чотирьох назв, файл 4.8 КБ. Стиль підключено без блокування рендеру (`media="print"` → `all` після завантаження), сам шрифт — через 3 с після старту (`document.fonts.load`), тож при першому відкритті картки з планом запасний шрифт не мигає. CSP (`fonts.googleapis.com`, `fonts.gstatic.com`) уже дозволяє
- **JS:** `_applyCardTier()` ставить текст `#ctier-name` (Gold, Bronze…; великими робить CSS) і очищає його для запису без плану
- **Перевірено** (headless Chrome, :8000 лише читання; #1294 — gold у локальній БД, інші плани — підстановкою `_applyCardTier()` у сторінці; ПК 1440×900, телефон 390×844, планшет — mobile.html 1180×820 з mobile.css / mobile.js із диска; по 20/20):
  - новий CSS підхоплено; стиль Cinzel підключився без блокування; шрифт підвантажено до відкриття картки;
  - #1294 — «GOLD»; текст справді намальовано Cinzel (CDP `getPlatformFontsForNode`); 13 px від лівого краю й 13 px — кнопка закриття від правого, по центру з нею (на планшеті — 14 px); до кнопки закриття далеко; ширина — менше половини панелі (PLATINUM — 130 px з 360);
  - BRONZE / SILVER / PLATINUM — кожен у своєму металі; план знято — табличка зникла; запис без плану — таблички немає;
  - відблиск анімується лише поки картка відкрита; reduced-motion — без відблиску; 0 помилок JS (поза відомим: дим без WebGL у headless)
- Версії: `Style.css?v=20261005` (index.html, mobile.html), `mobile.css?v=20261005` (mobile.html)
- Файли: `index.html`, `mobile.html`, `Style.css`, `mobile.css`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.63 (2026-10-04) — «Опис» у боковій панелі: довгий текст згорнуто + «Розгорнути / Згорнути»
- Пряма вимога користувача (скриншот бокової панелі): коли тексту багато — скоротити основний текст на 60 % і вбудувати «розгорнути / згорнути». Лише поле «Опис»
- **Як працює (index.html, mobile.html, Style.css):**
  - опис від 10 рядків згорнуто до ~40 % висоти (ціле число рядків, не менше 4), останні рядки мʼяко згасають (`mask-image`); під текстом — золота кнопка «Розгорнути ⌄» / «Згорнути ⌃» (`aria-expanded`, на телефоні зона натискання 32 px);
  - висота змінюється плавно (0.35 с; кінець — `transitionend`, запасний таймер 700 мс); при `prefers-reduced-motion` — одразу;
  - «Згорнути» внизу довгого тексту: якщо початок «Опису» пішов за край, панель прокручується до нього;
  - висота перераховується при зміні ширини вікна (поворот екрана) і після завантаження шрифтів;
  - нова картка й повторне відкриття — згорнуто; фаза 2 тієї самої картки (повні дані) розгорнутий стан не скидає;
  - короткий опис (до 10 рядків) — повністю, без кнопки, як раніше; інші поля панелі не змінювались;
  - `_descSet()`, `_descLayout()`, `_descToggle()`, `_descReset()` — перед `_renderCardDetails()`; `Style.css?v=20261004f` (index.html, mobile.html)
- Усі схвалені описи на сайті — 670–5000 знаків (у середньому ≈1840), тож згорнуті майже всі. На ПК (панель 360 px): 670 знаків — 12 рядків, видно 5; 5000 знаків — 99 рядків, видно 40 (≈680 px)
- **Тексти:** `migrations_i18n_card_desc.sql` — `card.desc_more` / `card.desc_less` (uk «Розгорнути» / «Згорнути», en «Show more» / «Show less»); без неї — вбудовані українські. Словник кешується в памʼяті бекенду, тож SQL — до рестарту
- **Перевірено** (headless Chrome; :8000 лише читання, EN — свіжий процес :8001, після тесту зупинено):
  - ПК 1440×900 — 22/22, телефон 390×844 — 23/23, планшет (mobile.html, з mobile.css / mobile.js із диска, як роздає Nginx) 1180×820 — 23/23;
  - видно 40.4 % (ПК), 40.3 % (телефон), 38.6 % (планшет — округлення до цілого рядка); загасання є;
  - кнопку натискає справжній клік мишею (hit-test); розгорнуто — весь текст без обмеження й загасання, «Згорнути», стрілка догори; анімація — перехід max-height 350 мс в обидва боки;
  - «Згорнути» знизу — панель повернулась до початку «Опису»; якщо початок і так видно — без прокрутки;
  - фаза 2 не скидає «розгорнуто»; нове відкриття — згорнуто; інша картка — своя висота; короткий опис — повністю без кнопки; з короткого на довгий — кнопка повертається;
  - поворот телефона 390 → 844 px: 597 з 1483 px → 256 з 631 px; планшет 1180 px: найкоротший опис — 4 рядки, показано повністю;
  - EN — «Description» / «Show more» / «Show less», UA — «Опис» / «Розгорнути» / «Згорнути»; 0 помилок JS (поза відомим: дим без WebGL у headless)
- Файли: `index.html`, `mobile.html`, `Style.css`, `migrations_i18n_card_desc.sql` (новий), `CLAUDE.md`, `SESSION_CHANGES.md`

### v3.62 (2026-10-04) — «Зірка памʼяті» на карті «Світ»: зірочка над точкою загибелі, як на карті України
- Пряма вимога користувача: у режимі «Світ» натискання «Зірка памʼяті» має показувати над точкою загибелі ті самі зірочки, що на карті України
- **Причина:** `doLike()` додавав зірочку в `particles` — їх малює лише канвас карти України, а в режимі «Світ» він прихований і зупинений. Тому на карті світу ефекту не було, а зірочки накопичувались і вилетіли б разом при поверненні на карту України
- **Фікс (index.html, mobile.html, Style.css):** у режимі «Світ» — `_worldLikeBurst(p)`: ⭐ у шарі маркерів Leaflet над точкою загибелі (рухається разом із картою), з тими самими параметрами, що на канвасі України: здіймається на 55 px, зменшується з 19 до 13 px і згасає за 0.76 с, потім прибирається. На карті України — як і раніше (`particles`). `Style.css?v=20261004e`
- **Перевірено** (headless Chrome, :8000; запит `/api/like` підмінено в сторінці — лайки в БД не писались): «Світ» — ⭐ у шарі маркерів по центру точки, низом біля неї; `particles` порожній; лайк надіслано один раз; після анімації елемент прибрано; два натискання — дві зірочки; після повернення на карту України накопичених зірочок немає; на карті України — зірочка на канвасі, DOM-зірочок немає; анімація (пауза й `currentTime`): 0 мс — низ у точці, 380 мс — +27 px, масштаб 0.84, прозорість 0.5, 760 мс — +55 px, 0.68, 0; 0 помилок JS
- Файли: `index.html`, `mobile.html`, `Style.css`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.61 (2026-10-04) — Посилання «Тарифи» тимчасово приховано
- Пряма вимога користувача: тимчасово сховати посилання «Тарифи»
- Приховано (`display:none` + коментар «тимчасово приховано (v3.61)»): попап ★ на телефоні (`index.html`, `#bb-popup`), блок «Інформація» в `mobile.html`, верхня панель промо-сторінки (`promo/index.html`). У блоці «Інформація» на ПК (`index.html`, `#site-rules`) посилання вже було приховане. Сама сторінка `/pricing/` лишається доступною за прямою адресою
- Повернути — прибрати `display:none` у цих чотирьох посиланнях (шукати `href="/pricing/"`)
- Файли: `index.html`, `mobile.html`, `promo/index.html`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.60 (2026-10-04) — «Нові надходження» на телефоні: розділ у попапі ★ і значок на кнопці
- Скарга користувача (скриншот з проду, телефон 400 px): у мобільній версії «Нові надходження» не показуються. У v3.58 блок на тач-пристроях свідомо ховався — лівий нижній кут там займають кнопки, а статистика й «Інформація» відкриваються в попапі кнопки ★
- **Зроблено (index.html, Style.css):**
  - у попапі ★ (`#bb-popup`) угорі — розділ «Нові надходження» в тому самому золотому стилі: усі нові записи списком із прокруткою (до 150 px; у ландшафті — 64 px, щоб попап уміщався), «Прізвище Імʼя» + «додано»; торкання імені — попап закривається, політ до точки й картка (`_focusPerson`);
  - на кнопці ★ — золотий значок із кількістю нових і мʼяке сяйво (шар `::after`, лише `opacity`), доки відвідувач не відкрив попап із цими записами. Час найновішого побаченого — у `localStorage` (`zp_recent_seen`); зʼявився новий запис — значок знову. Позначка «побачено» — за класом `bb-open` попапу (MutationObserver), тож не залежить від порядку обробників кнопки ★;
  - спільна розмітка запису — `_rbItemHtml()`; дані ті самі, що для блоку на ПК (`/api/recent-additions`, оновлення кожні 5 хв);
  - `Style.css?v=20261004d` (index.html, mobile.html)
- **Перевірено** (iPhone 390×844, торкання; тестовий сервер :8001, тимчасові адмін і 4 записи — видалені; 13/13): на ★ значок «3» і сяйво; десктопного блоку немає; попап — розділ угорі з 3 записами, найновіший першим; після відкриття значок і сяйво зникли й не повертаються після перезавантаження; торкання імені — попап закрився, картка цього загиблого; новий запис — значок «1»; EN — «New additions» / «added»; ландшафт 844×390 — список 64 px, попап у межах екрана; горизонтального прокручування немає; ПК — блок над статистикою як і був, кнопки ★ немає; 0 помилок JS
- Не змінювалось: `mobile.html` (планшети) — там інша оболонка (нижня навігація, «Інформація» у шторці); блок на планшетах — окремим кроком, якщо потрібно
- Файли: `index.html`, `Style.css`, `mobile.html` (лише версія CSS), `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.59 (2026-10-04) — Нагороди на сторінці меморіалу: «'">» і літера замість картки
- Скарга користувача (скриншот з проду, `card?slug=…`, «Державні та відомчі нагороди»): у картці нагороди окрема літера «О», далі текст `'">`, а назва ордена — поза карткою
- **Причина:** заглушка нагороди (HTML з подвійними лапками `class="medal" style="…"`) вставлялась прямо в атрибут `onerror="this.outerHTML='…'"`. Перша ж `"` закривала атрибут, решта розмітки розсипалась: літера-заглушка — текстом, `</div>` закривав картку раніше, `'">` — на екрані, назва — поза карткою. Ламалась кожна нагорода з картинкою, навіть коли картинка завантажилась (`.replace(/'/g,'"')` лише погіршував). Та сама вада у зворотний бік — у `admin.html` (`_awardImg`) і `index.html` (нагороди у формі «Додати запис»): заміна `"` на `'` обривала JS-рядок, тож замість заглушки при незавантаженій картинці була помилка JavaScript
- **Фікс (card.html, index.html, admin.html):** заглушка в `onerror` — через `h()` (лапки → `&quot;`; браузер розкодовує їх перед виконанням), без заміни лапок
- **Перевірено** (headless Chrome, :8000, лише читання — нагороди підставлено у функції самих сторінок; 10/10): картка — 3 нагороди, тексту поза картками немає; з картинкою — картинка, назва, дата й «посмертно» всередині картки; картинка не завантажилась — заглушка «М»; без картинки — «В»; index.html і admin.html — заглушки «М» / «О» замість помилки JavaScript; 0 помилок JS
- Файли: `card.html`, `index.html`, `admin.html`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL і рестарт не потрібні

### v3.58 (2026-10-04) — «Нові надходження»: блок нових загиблих над статистикою (index.html) + розділ в адмінці
- Пряма вимога користувача: у лівому нижньому куті, над блоками статистики (на місці вимкненого чату), блок у тому самому стилі — нові загиблі, що зʼявились на сайті: прізвище, імʼя й «додано» (без місця загибелі), рамка світиться з плавним ефектом; запис тримається кілька днів (за замовчуванням 3), період і показ — в адмінці
- **БД:** нова колонка `memorials.published_at` (INT NULL) — створюється сама в `init_db()`. Ставиться, коли запис стає видимим на сайті: схвалення з модерації (`/api/admin/approve/{id}`), створення адміном (одразу схвалений), правка «схвалено» 0 → 1. Публічна форма й імпорт CSV додають записи на модерацію — у блок вони потрапляють лише після схвалення. Давні записи — без часу (у блоці їх немає), повторне збереження схваленого запису час не змінює
- **Paskal.py:** `GET /api/recent-additions` (публічний; `recent_enabled`, `recent_days`; до 30 записів; кеш 60 с, скидається в `cache_flush_memorials`/`cache_flush_all`), `GET /api/admin/recent-additions`, `POST /api/admin/recent-additions/{id}/hide`; перевірка `recent_enabled` (0/1) і `recent_days` (1–14) у `colors/batch`
- **index.html + Style.css:** `#recent-block` у стилі `#count`/`#site-rules` (фон, радіус, відступи, шрифти), золота рамка мʼяко світиться (шар `::before`, анімується лише `opacity`), записи зʼявляються по черзі; заголовок «Нові надходження» і кількість; до 5 записів на сторінці — більше гортаються самі кожні 6 с (пауза, поки курсор над блоком); клік — політ до точки й картка (спільна з пошуком `_focusPerson()`: карта України чи «Світ»); блок над статистикою, а якщо чат увімкнено — над чатом (`_rbPlace()`, стежить за розмірами й класом чату); оновлення кожні 5 хв; на тач-пристроях блоку немає (як і статистики — там FAB-кнопки); `#recent-block` додано до винятків обробників карти. `Style.css?v=20261004c` (index.html, mobile.html)
- **admin.html:** розділ «Нові надходження» (`sec-recent`, іконка `#ico-recent`): показувати блок, скільки днів (1–14), «Зберегти»/«Скасувати», список «Зараз у блоці» з часом появи й кнопкою «Прибрати» (запис на сайті лишається)
- **Тексти:** `migrations_i18n_recent.sql` — `recent.title`, `recent.added`, `nav.recent`, `adm.recent.title` (uk/en); без неї — вбудовані українські
- **Перевірено** (тестовий сервер :8001, тимчасові адмін і 9 записів — видалені; 40/40 функціональних перевірок):
  - сервер: записи адміна — одразу в блоці, найновіші першими; заявка на модерації — ні, після схвалення — так; повторне «схвалити» час не змінює; зняли схвалення — зник, повернули правкою — знову «новий»; збереження давнього запису (465) — не «новий»; 4 дні тому — поза 3 днями, у 7 днях; межі: днів 0→1, 99→14, «abc»→3, 2.6→2, `recent_enabled` «yes»→0; «Прибрати» — зник, запис схвалений; без входу — 403
  - сайт (1440×900): 5 записів, лічильник 7; «Прізвище Імʼя» + «додано»; той самий лівий край і ширина, що в статистики, проміжок ≈10 px; рамка світиться; під курсором сторінки не гортаються, без нього — за 6 с наступна; чат увімкнено → блок над чатом, вимкнено → знову над статистикою; клік — політ і картка на карті України (×3.5) і на «Світі» (зум ≥ 9, фокус на зірці); EN — «New additions» / «added»; телефон — блоку немає
  - адмінка: пункт меню, налаштування й список, «Прибрати», 20 днів → 14
  - консоль: помилки лише від диму (`js/script.js`): у тестовому Chrome цього прогону не було WebGL (`getContext('webgl')` → null — диск C: майже повний). Окремо помічено: без WebGL `script.js` падає з помилками замість тихого вимкнення диму (давнє, не змінювалось)
- **Помічено:** диск C: розробника заповнений на 99–100% (вільно 0.2–0.5 ГБ). Тимчасові профілі Chrome і старі трасування продуктивності з тестів (~1.7 ГБ) видалено
- Файли: `Paskal.py`, `index.html`, `mobile.html` (лише версія CSS), `Style.css`, `admin.html`, `migrations_i18n_recent.sql` (новий), `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`. Колонка — сама при рестарті бекенду; SQL — лише тексти (`migrations_i18n_recent.sql`)

### v3.57 (2026-10-04) — Після заливки адмінка показувала стару карту: кеш браузера для HTML
- Скарга користувача (скриншот з проду після заливки v3.44–v3.56): у вікні редагування запису знову «API KEY REQUIRED»
- **Діагностика:** прод віддає нову адмінку (`_admTileLayer`, `maxlength="10000"`, файл від 04.10 13:35 GMT), нові `index.html` (`Style.css?v=20261004b`) і бекенд — заливка правильна. На скриншоті ж лічильник опису «4691/200» — стара сторінка з кешу браузера. `/admin`, `/card`, faq та інші HTML віддавались без `Cache-Control` (лише `Last-Modified`/`ETag`), тож браузер сам вирішував, скільки вважати копію свіжою, і при відкритті із закладки міг навіть не питати сервер. Головну (`no-store`) і SSR `/memorial/…` (`max-age=300`) це не стосувалось
- **Фікс (Paskal.py, `security_headers`):** HTML без власного правила кешу отримує `Cache-Control: no-cache` — браузер перевіряє актуальність при кожному відкритті й після заливки одразу бачить нову версію. Незмінений файл — `304 Not Modified` за ETag: `FileResponse` сам 304 не вміє, а без цього адмінка (1.7 МБ) завантажувалась би щоразу повністю; враховано слабкий `W/` ETag, який робить gzip у Nginx. Головна й SSR — зі своїми правилами, без змін
- **Перевірено** (тестовий сервер :8001): `/admin`, `/card`, `/faq.html`, `/update_v/…`, `/pricing/` — `no-cache`; `If-None-Match` з тим самим ETag (і з `W/`) → 304, 0 байт; інший ETag → 200; `/` — `no-store`, `/memorial/…` — `max-age=300`, API й зображення — без змін. Chrome: перше відкриття адмінки — 200 (1.7 МБ), повторне — запит з `If-None-Match` і 304 (150 байт)
- **Помічено:** диск C: розробника заповнений на 100% — Chrome не міг писати кеш (перша перевірка показала повне завантаження без 304). Тимчасові профілі headless Chrome з тестів (~1.4 ГБ) видалено
- Файли: `Paskal.py`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL не потрібен; на проді — залити `Paskal.py` і перезапустити бекенд. Уже закешовану стару адмінку браузер ще раз покаже до Ctrl+F5 — далі нові версії підхоплюються самі

### v3.56 (2026-10-04) — Пошук у режимі «Світ»: карта летить до точки загибелі, зірка підсвічена
- Скарга користувача: у карті світу пошук відкриває бічну панель загиблого, але точка загибелі на карті не показується і зуму немає
- **Причина:** `pickRes()` (index.html, mobile.html) завжди викликав `flyTo()` — анімацію прихованої карти України. Карта «Світ» (Leaflet) лишалась на місці, а зірка серед сусідів нічим не виділялась (на карті України зірку відкритої картки виділяє `selId`)
- **Фікс (index.html, mobile.html, Style.css):**
  - у режимі «Світ» пошук летить по карті світу — `_worldFlyTo(p)`: `_worldMap.flyTo(точка, зум ≥ 9, 0.9 с)`; прихована карта України більше не рухається;
  - зірка відкритої картки — з тим самим фокусом, що на карті України (`drawDotFX`, гілка `isS`): золоте кільце 5.5r, м'яке золоте свічення до 18r і три кільця-маяки, що розходяться до 18r / 23r / 28r і гаснуть (r ≈ 3.7 px; ті самі кольори й періоди). `_worldPick(id)` додає маркеру `.wm-picked` і розмітку `.wm-beacon`, піднімає його над сусідами (`setZIndexOffset`). Як `selId`: ставиться в `openCard()` (пошук і клік по зірці), знімається в `closeCard()`, повертається після перемальовування маркерів (`_worldMarkerById`); підпис сам не відкривається; при `prefers-reduced-motion` — без маяків і мерехтіння. Фокус доопрацьовано за скриншотом користувача (спершу було біле кільце й підпис);
  - `Style.css?v=20261003b` → `?v=20261004b` (index.html, mobile.html): Nginx кешує CSS на 30 днів
- **Перевірено** (headless Chrome, тестовий сервер :8001; index.html — ПК, mobile.html — планшет; 26/26): пошук «Горяйнов» у «Світі» → зум ≥ 9, точка в центрі (< 300 м), карта України не рухалась, відкрилась картка, на зірці фокус (свічення, кільце, три маяки — маяки по черзі розходяться 30 → 134 / 170 / 208 px і гаснуть); закрили картку → фокус знято; клік по зірці → фокус; режим України — як раніше (×3.5); 0 помилок консолі. У першому прогоні раз не встиг зум режиму України — затримка кадрів headless-браузера; у повторних прогонах і окремій перевірці зі справжньою мишею — гаразд
- Файли: `index.html`, `mobile.html`, `Style.css`, `CLAUDE.md`, `SESSION_CHANGES.md`, `DEPLOY_v3.44-v3.56.md`. SQL не потрібен

### v3.55 (2026-10-04) — «Опис»: межа 200 → 10000 символів; поле в адмінці обрізало довгі описи
- Пряма вимога користувача: у вікні редагування запису поле «Опис» обмежене 200 символами — змінити на 10000 (на скриншоті з проду — «4691/200»)
- **Що було:**
  - admin.html: `<textarea id="e-desc" maxlength="200">` і лічильники `/200`;
  - **знайдено під час аналізу — втрата даних:** `_V.text()` на кожному вводі обрізає значення до `maxlength`. У довгому описі (у локальній копії всі 1168 записів мають опис понад 200 символів) досить було стерти один символ чи щось вставити — текст миттєво обрізався до 200, і «Зберегти» записувало обрізане;
  - сервер: правка (`PUT /api/admin/memorial/{id}`) мовчки обрізала опис до 5000; створення адміном (`POST /api/admin/memorial`, модель `PersonIn`) — 422 понад 5000; імпорт CSV — обрізання до 5000. У локальній копії 9 описів рівно по 5000 символів — імовірно, обрізані раніше
- **Стало:**
  - admin.html: `maxlength="10000"`, лічильник `N/10000` (редагування й створення);
  - Paskal.py: `PersonIn.descr` — до 10000; `update_memorial` — обрізання на 10000; імпорт CSV — 10000;
  - публічна форма «Додати запис» (`POST /api/people`) — без змін, 5000 (власна перевірка в `add_person`). Колонка `descr` — TEXT, 10000 символів уміщує — SQL не потрібен
- **Перевірено** (тестовий сервер :8001, тимчасовий адмін і тимчасовий запис — видалені; 13/13):
  - сервер: створення з 9500 символами — OK (раніше 422); правка на 10000 — зберігається повністю; 12000 — обрізається до 10000; створення з 10001 — 422;
  - адмінка: опис 4691 символ — «4691/10000»; стерли символ — 4690 (раніше ставало 200); дописали ~3300 — усе на місці; «Зберегти» з вікна — у БД увесь текст; новий запис — «0/10000»; 0 помилок консолі
- **На проді перевірити**, чи не обрізані вже описи: `SELECT id, `last`, `first`, CHAR_LENGTH(descr) AS len FROM memorials WHERE CHAR_LENGTH(descr) IN (200, 5000) ORDER BY len, id;` (у DEPLOY_v3.44-v3.56.md). Обрізаний текст сам не відновлюється — лише з джерела (наприклад, сторінки ukraine-memorial.org) чи повторним імпортом
- Файли: `Paskal.py`, `admin.html`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`, `DEPLOY_v3.44-v3.56.md` (було `DEPLOY_v3.44-v3.54.md`). SQL не потрібен

### v3.54 (2026-10-04) — Карти в адмінці показували «API KEY REQUIRED» замість карти
- Скарга користувача (скриншот з проду): у вікні редагування запису карта «Місце Зірки на карті» порожня, лише водяні знаки «API KEY REQUIRED · carto.com/basemaps/apikey»
- **Причина:** у admin.html дві Leaflet-карти — вибір місця зірки в редагуванні (`_initEmMap`) і превʼю на вкладці «На модерації» (`_initPendMap`) — мали захардкожену стару адресу CARTO `https://{s}.basemaps.cartocdn.com/dark_all/…` без ключа. З 2026 року CARTO без ключа віддає заглушку. У v3.20 це виправили для сайту (карта «Світ», форма «Додати запис» беруть `worldmap_tile_url` з ключем), а карти адмінки лишились на старій адресі. На проді ключ у «Карта світу» заданий — карти сайту працюють
- **Фікс (admin.html):** `_admTileLayer()` — той самий URL, що на сайті (`COLORS.worldmap_tile_url`); якщо його не задано чи в ньому незаповнений `{carto_key}` — OpenStreetMap (ключ не потрібен). Обидві карти адмінки використовують його
- **Наслідок на проді (дані, не код):** запис #669 (Канцір Андрій) збережено з міткою, поставленою наосліп по порожній карті: `world_lat 24.7069, world_lng 79.2773` (Індія), `pos_x 3.0258, pos_y 3.2854` (поза картою України, 0…1) — зірка зникла з карти України, а на карті «Світ» стоїть в Індії. Інших таких записів немає (світові координати на проді лише в нього). Попереднє положення з локальної копії — `pos_x 0.8475, pos_y 0.3513` (≈ 49.41, 38.15 — Сватове, збігається з місцем загибелі). SQL відновлення — у DEPLOY_v3.44-v3.56.md:
  ```sql
  UPDATE memorials SET pos_x = 0.8475, pos_y = 0.3513, world_lat = NULL, world_lng = NULL WHERE id = 669;
  SELECT id, pos_x, pos_y, world_lat, world_lng FROM memorials WHERE id = 669;   -- 0.8475, 0.3513, NULL, NULL
  ```
- **Перевірено** (тестовий сервер :8001, тимчасовий адмін, headless Chrome): редагування запису — карта CARTO з ключем із налаштування, мітка в збережених координатах; превʼю модерації — те саме; налаштування порожнє → OpenStreetMap; стара адреса без ключа більше не запитується; 0 помилок консолі. Скриншоти — справжня карта (Луганська обл., Сватове), без заглушки
- **Не змінювалось (можна окремо):** сервер приймає `pos_x`/`pos_y` поза 0…1, а карта адмінки — клік будь-де у світі; попередження «точка поза Україною» в адмінці й перевірка діапазону на сервері запобігли б таким записам
- Файли: `admin.html`, `CLAUDE.md`, `SESSION_CHANGES.md`, `DEPLOY_v3.44-v3.54.md` (було `DEPLOY_v3.44-v3.53.md`; поточна назва — у розділі 3). SQL-міграцій немає; разове виправлення запису #669 — за бажанням

### v3.53 (2026-10-04) — «Подарунки загиблому», етап 11: повне тестування сценарію
- Останній етап ТЗ `Gifts-for-fallen.md` («делай»). Код сайту не змінювався — лише перевірка. Усі проблеми, знайдені під час етапу, були в тестовому оточенні, не в коді
- **Як перевірено** (тестовий сервер :8001 з тестовими ключами LiqPay sandbox; headless Chrome; спільна локальна БД; тимчасові акаунти й дані прибрано):
  - вхід через Google — справжній код сайту (`/api/auth/google` → Google → callback → сесія → повернення на меморіал); підмінено лише сторінку Google і два серверні запити до Google (обмін коду на токен і профіль);
  - LiqPay — справжня форма, підпис і callback; сторінку оплати й відповіді банку імітує тест (ключів мерчанта ще немає)
- **Сценарій ТЗ — 117 перевірок, усі пройдено**, двічі:
  - ПК, українська, наявний акаунт, меморіал #465 — callback LiqPay прийшов раніше за повернення покупця;
  - телефон 390 px, English, перший вхід через Google (акаунт створено), меморіал #933 — покупець повернувся раніше за callback: «Оплата ще обробляється» → «Перевірити ще раз» → «Дякуємо!»;
  - кроки: порожній меморіал (0 подарунків, при відкритті лише 2 запити модуля) → свічка (лайк +1) → каталог (вантажиться лише після кліку) → вибір → «Увійти через Google» → повернення на меморіал з відкритим каталогом → «Купити за X ₴» → підтвердження (подарунок, меморіал, сума) → LiqPay (POST-форма, підпис, сума з каталогу, мова, `result_url`/`server_url`) → замовлення `pending` → підтвердження оплати (`paid`, ID платежу, місце 0, один лист адміну) → «Дякуємо!» → «Закрити» → прокрутка до свічки → GIF покладання (той самий низ і центр, що в подарунка, ширший у 2.8 раза, завантажений один раз) → статичний подарунок (`anim_state=shown`) → «Мої замовлення» — «Оплачено» → повторне відкриття (те саме місце, без GIF) → інший відвідувач (статичний подарунок, адреси GIF сервер не віддає);
  - адмінка: обидва замовлення «Оплачено» з ID платежу, підсумок «Оплачено: 2 на 170 ₴», LiqPay «Підключено · тестовий режим»
- **Захист оплати (ТЗ, розділ 6) — 44 перевірки, усі пройдено:**
  - зміна ціни: ціна, валюта й статус із запиту ігноруються; LiqPay підтвердив 1 ₴ замість 30 або USD замість UAH → `error`, біля свічки нічого, запис `GIFT_PAY_MISMATCH`;
  - підміна меморіалу: неіснуючий чи не схвалений → відмова; чужий `memorial_id` у даних LiqPay ігнорується;
  - підміна користувача: `user_id` з тіла запиту ігнорується; без входу — 401; чужі «оплатити / звірити / скасувати» — 404;
  - фіктивний платіж: повернення з `?gift_order=` без платежу → не оплачено; чужий ключ, дані змінені після підпису, чужий магазин, нечитабельні дані → 400; покласти без оплати може лише адмін;
  - повторне зарахування: повтори callback і пізня `failure` нічого не змінюють; той самий платіж для іншого замовлення не зараховано (`GIFT_PAY_DUP_PAYMENT`); 6 одночасних callback → одне зарахування, місця без дублів; лист — рівно один на замовлення;
  - чужа покупка: не скасувати (404); оплачену не скасувати й власнику (409); чужий показ покладання — `changed: 0`; оплачену не прибрати навіть адміну (`deleted: 0`); адмінські ендпоінти користувачу — 403
- **Регресія — 33 перевірки, усі пройдено:**
  - модуль вимкнений, ключів немає (як на проді одразу після заливки; окремий тестовий сервер :8003 приховував рядок `card_gifts_enabled` лише при читанні — налаштування користувача в БД не змінювалось): кнопки немає, біля свічки порожньо (хоча оплачені подарунки в БД є), жодного запиту модуля, API модуля закриті (каталог порожній, замовлення 403, callback 503), свічка працює, решта картки на місці, 0 помилок консолі;
  - головна (карта, `/?open=<slug>`), mobile.html (планшет), адмінка (9 розділів), публічні API (health, stats, people, map-points, search, by-slug, SSR `/memorial/<slug>`, sitemap, robots); секретів LiqPay у публічних налаштуваннях немає;
  - свічка не змінена: порівняння з комітом до модуля — CSS свічки, код запалювання й `card_show_candle` без змін; у розмітці блоку лише 2 рядки модуля (порожній якір `#gift-stage` і прихована кнопка)
- **Консоль:** лише відомі записи — CSP блокує Google Analytics (давнє, не модуль), 401 `/api/auth/me` в аноніма, 403 `/api/admin/me` до входу в адмінку
- **Помічено, не змінювалось:**
  - `card.html` не локалізована: англійською перемикаються лише тексти модуля, а свічка й решта картки — українською (текст свічки за ТЗ не змінюється) — розділ 12;
  - `DELETE /api/admin/memorial-gift/{id}` для оплаченого замовлення відповідає `200 {"deleted": 0}`: нічого не видаляє, а кнопки видалення для оплачених в адмінці немає
- **Не перевірено локально (потрібні ключі мерчанта):** справжня сторінка оплати LiqPay і чи дістає LiqPay `server_url` на проді. Чекліст першого запуску — MASTER_GUIDE.md, розділ 17
- Файли: `CLAUDE.md`, `SESSION_CHANGES.md`, `MASTER_GUIDE.md` (лише документація). Код і SQL не змінювались — деплой як для v3.52
- **ТЗ виконано повністю (етапи 1–11)**

### v3.52 (2026-10-04) — «Подарунки загиблому», етап 10: оптимізація
- Наступний етап ТЗ `Gifts-for-fallen.md` («по тз далее»; задачу «колір зірки за тарифом» користувач скасував). ТЗ, розділ 12: не погіршити `card?slug=`, контролювати завантаження GIF, зображень, каталогу й великої кількості подарунків, перевірити мобільні
- **Заміри до змін** (headless Chrome, холодний кеш, медіана з 3; ПК і телефон 390 px із CPU ×4 і мережею 4G):
  - модуль вимкнено → увімкнено (меморіал без подарунків): DCL / load / LCP однакові в межах похибки (ПК 493 → 452 мс load; телефон LCP 2740 → 2640 мс). Модуль додає 2 запити, 4.7 КБ (тексти `gifts` 4.4 КБ і список подарунків), і вони йдуть уже після завантаження сторінки; каталог і його зображення — лише після кліку
  - меморіал із 316 подарунками (16 на місцях + 300 понад): список — 38.1 КБ і 15.4 мс на сервері, хоча показується 16; на телефоні тексти й список ішли послідовно — подарунки з'являлись на 2.96 с
- **Зроблено:**
  - список подарунків за замовчуванням — лише на місцях (≤16) і `total`; повний (до 500) — `?full=1`, лише коли відкривають «ще N» (з індикатором завантаження);
  - тексти й подарунки вантажаться паралельно;
  - налаштування модуля — одним запитом (`_gift_settings()`), купівля й список роблять менше звертань до БД;
  - індекс `memorial_gifts (user_id, status)` — «мої замовлення» й ліміт незавершених (таблиця росте з усього сайту); створюється сам у `init_db()`;
  - звільнене місце (повернення коштів, адмін прибрав розміщення) займає найстаріший подарунок «понад місця» — раніше такі подарунки назавжди лишались лише в списку (знайдено під час етапу);
  - адмінка: після завантаження зображення сервер повертає `w`, `h`, `size` (PNG/JPEG/WEBP за заголовком, без Pillow) — якщо більше 600 px чи 300 КБ, під полем попередження «краще до 512×512 px і до 300 КБ» (біля свічки подарунок ≈60 px); для GIF — якщо більше 2 МБ;
  - телефон: зона натискання «ще N» — 34 px заввишки
- **Після змін** (той самий сценарій, 316 подарунків):

  | | ДО | ПІСЛЯ |
  |---|---|---|
  | трафік модуля при відкритті картки | 42.5 КБ | 6.6 КБ |
  | список подарунків | 38.1 КБ | 2.2 КБ |
  | час списку на сервері | 15.4 мс | 6.4 мс |
  | подарунки з'являються (телефон) | 2.96 с | 2.07 с |
  | уся сторінка | 128.5 КБ | 93.7 КБ |
  | load / LCP | без змін | без змін |

- **Перевірено** (тестовий сервер :8001, тимчасові акаунти й дані прибрано): індекс створено; адмін прибрав розміщення на місці 5 → його зайняв найстаріший «понад місця» (на місцях 16, понад 300 → 299); повернення коштів за подарунок на місці 0 → те саме (понад 5 → 4); розміри PNG / JPEG / WEBP 1200×800 визначено правильно; попередження про 1400×1400 у вікні подарунка; «ще 4» на телефоні 34 px, повний список вантажиться лише після кліку (20 подарунків); покладання (етап 7) працює; помилок консолі модуля немає (єдиний 403 — штатна перевірка `/api/admin/me` до входу в адмінку)
- **Не змінювалось:** Nginx/кешування статики (на проді `/img` роздає Nginx), стиснення зображень (без Pillow — лише попередження адміну; Pillow можна додати окремим рішенням)
- Файли: `Paskal.py`, `card.html`, `admin.html`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`. SQL не потрібен (індекс — у `init_db()`)
- **Далі — етап 11** (повне тестування сценарію)

### v3.51 (2026-10-04) — «Подарунки загиблому», етап 9: налаштування модуля
- Наступний етап ТЗ `Gifts-for-fallen.md` («++»). ТЗ, розділ 10: кнопка, каталог, покупка, анімація, розміщення, обмеження, тексти, сповіщення, поведінка після оплати — «лише справді потрібні, не заради кількості»
- **Адмінка → «Подарунки загиблому» → «Налаштування»** (тепер усе модуля в одному місці):
  - модуль (було) · **кнопка й каталог** (нове: вимкнено — нового подарунка не обрати й не купити, а покладені лишаються біля свічки; раніше для паузи доводилось вимикати весь модуль, і подарунки зникали) · купівля (було) · стан LiqPay (було);
  - **анімація покладання** (вимкнено — одразу статичний подарунок) і **розмір GIF відносно подарунка** (1.5–5, дефолт 2.8 — справжні GIF можуть бути скомпоновані інакше, ніж демо);
  - **розмір подарунків біля свічки** (70–140 %; на вузьких екранах далі ще зменшуються самі);
  - **лист про оплачений подарунок** — на `ADMIN_NOTIFY_EMAIL` з `.env` (адресу показано; у публічні налаштування вона не потрапляє), з попередженням, якщо SMTP не налаштовано;
  - **тексти модуля** → кнопка «Редагувати» відкриває «Локалізацію» одразу на секції `gifts` (у фільтр секцій додано `gifts`)
- **Свідомо не додано** (було б «заради кількості»): ліміти (5 незавершених замовлень, rate limit — захисні константи в коді), окрема «поведінка після оплати» (екран «Дякуємо!» → покладання вже визначені етапами 6–7), налаштування рядів і кількості місць
- **«Замовлення»:** підсумок «Оплачено: N на X ₴»
- **Paskal.py:** дефолти нових ключів у `/api/card/settings`; перевірка значень у `PUT /api/admin/colors/batch` (`_GIFT_FLAG_KEYS`, `_GIFT_NUM_KEYS`); `_gifts_buy_enabled()` враховує кнопку; `anim` лише при ввімкненій анімації; `_gift_notify_paid()` — лист у фоновому потоці після переходу в `paid` (callback і звірка), повтори листів не дублюють; `GET /api/admin/memorial-gifts` → `paid_sum`; `GET /api/admin/gifts` → `notify`
- **card.html:** кнопка за налаштуванням; без каталогу «до каталогу» стає «Закрити»; розмір подарунків і GIF із налаштувань; місце над свічкою для GIF рахується з розміру
- **`migrations_i18n_gifts.sql`:** +12 ключів адмінки (uk/en)
- **Перевірено** (тестовий сервер :8001; листи підмінено записом у файл — справжніх листів не надсилалось; тимчасові акаунти й налаштування прибрано, на сайті — дефолти):
  - API: межі значень (9 → 5, 10 % → 70 %, «yes» → 0, нечислове → дефолт); лист після оплати — один, на `ADMIN_NOTIFY_EMAIL`, з посиланням на меморіал і номером замовлення; повторний callback — без другого листа; оплата через звірку — лист є; вимкнено — листа немає; анімація вимкнена → без `anim`; кнопка вимкнена → купити не можна (403), подарунки біля свічки лишаються; підсумок «оплачено 3 на 200 ₴»
  - браузер: без каталогу кнопки немає, список «усіх подарунків» закривається «Закрити»; розмір 140 % → ×1.4; GIF ×4 → ×4; адмінка завантажує й зберігає значення (у межах), «Редагувати» відкриває «Локалізацію» на `gifts` (53 ключі); 0 помилок консолі
- Файли: `Paskal.py`, `card.html`, `admin.html`, `migrations_i18n_gifts.sql`, `CLAUDE.md`, `SESSION_CHANGES.md`
- **Далі — етап 10** (оптимізація: завантаження ресурсів, продуктивність `card?slug=`, мобільна версія)

### v3.50 (2026-10-04) — «Подарунки загиблому», етап 8: кілька подарунків на меморіалі
- Наступний етап ТЗ `Gifts-for-fallen.md` («далее»): кожен подарунок — на своєму місці, без неконтрольованого накладання; враховуються позиція, розмір, порядок відображення й бік від свічки
- **Що було не так (аналіз етапу):**
  - лише 8 місць; крок 50 px, а подарунок з масштабом до 1.4 займав до 64 px — сусіди накладались;
  - «Бік від свічки» з каталогу (`place_area`) не враховувався взагалі;
  - «шар» −10 ховав подарунок за фоном секції (від'ємний `z-index` без власного контексту накладання);
  - на вузькому телефоні великі подарунки могли вийти за край екрана;
  - подарунки понад 8 не можна було переглянути ніде («ще N» був просто текстом)
- **Місця:** 16 = 2 ряди × 8, по 4 з кожного боку. Передній ряд — на лінії основи свічки; задній — на 24 px вище, у 0.78 розміру, між передніми й трохи притемнений. Менший номер — ближче до свічки; парні — ліворуч, непарні — праворуч
- **Призначення місця — лише сервер** (`_gift_pick_slot`): найближче вільне з урахуванням `place_area` (якщо на цьому боці все зайнято — будь-яке вільне), спершу передній ряд; понад 16 — `slot=NULL`. Однаково для оплати й розміщення адміном; розміщення адміном тепер теж під блокуванням меморіалу
- **Розкладка на сторінці:**
  - крок між місцями не менший за найширший подарунок (масштаб біля свічки обмежено 0.6–1.25) — сусіди в ряду не накладаються;
  - задній ряд завжди позаду переднього, «шар» з каталогу — порядок у межах ряду; `.gift-stage` має власний `z-index`, тож від'ємний шар більше не ховає подарунок;
  - на вузькому екрані всі подарунки й кроки зменшуються разом (`--gfit`, до 0.6); що не вміщується й тоді — у «ще N»; перерахунок при зміні ширини вікна;
  - «ще N» — кнопка: список «Подарунки біля свічки · N» з усіма подарунками (зображення й назва), зокрема тими, яким не вистачило місця;
  - GIF покладання (етап 7) працює й на задньому ряду — на його висоті й у його розмірі
- **Paskal.py:** `_GIFT_SLOTS = 16`, `_gift_pick_slot()`; у розміщенні адміном і при оплаті — бік із каталогу
- **card.html:** розкладка в 2 ряди, `_giftRelayout()`, `showAllGifts()`, кнопка «ще N»; номер місця в `data-slot`
- **admin.html:** «Масштаб біля свічки (0.6–1.25)», підказки до «Бік від свічки» й «Шар»
- **`migrations_i18n_gifts.sql`:** +1 ключ `gifts.all_title` (uk/en)
- **Перевірено** (тестовий сервер :8001, тимчасові акаунти й подарунки, дані тестів прибрано):
  - модульно `_gift_pick_slot`: ліворуч — парні, праворуч — непарні, бік заповнено → інший бік, передній ряд заповнено → задній, 16 зайнято → `None`, невідомий бік → «авто»;
  - 18 розміщень на одному меморіалі отримали місця 0–15 і двічі «понад місця» точно за очікуванням; оплачений подарунок «праворуч» на меморіалі з двома розміщеннями адміна (0 і 1) → місце 3;
  - браузер, ПК / 390 px / 320 px: видно всі 16, накладань у ряду 0, нічого не виходить за межі секції, горизонтального прокручування немає (`--gfit` 1.0 / 0.81 / 0.64), «ще 2»; задній ряд позаду переднього; подарунок із «шаром» −10 видно; «ще 2» → список із 18; після зміни ширини розкладка перерахувалась; покладання на задньому ряду — на його висоті; 0 помилок консолі
- Файли: `Paskal.py`, `card.html`, `admin.html`, `migrations_i18n_gifts.sql`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`
- **Далі — етап 9** (налаштування модуля й адміністративне керування)

### v3.49 (2026-10-04) — «Подарунки загиблому», етап 7: GIF покладання → статичний подарунок
- Наступний етап ТЗ `Gifts-for-fallen.md` («продолжай по плану»). Рішення користувача з етапу 2: GIF бачить лише покупець після оплати, решта — одразу статичний подарунок
- **Як працює:**
  - після оплати замовлення отримує `anim_state='pending'`, якщо в подарунка є GIF (без GIF — одразу `shown`);
  - `GET /api/memorial/{id}/gifts` віддає власнику `anim` `{gif, ms}`; іншим — лише статичне зображення;
  - сторінка ховає статичний подарунок і грає GIF на його місці (у 2.8 раза ширший, той самий низ). Через `ms` (тривалість GIF із каталогу; невідома — 3 с, межі 0.8–15 с) — плавна заміна на статичний подарунок і `POST /api/memorial-gift/{id}/shown`; удруге анімація не запускається;
  - GIF вантажиться лише в момент показу, з окремою адресою (`?play=…`), щоб завжди починатись із першого кадру
- **Коли грає:** вікно подарунків закрите, вкладка видима, свічка в полі зору (з місцем над нею). Після оплати «Закрити» на екрані «Дякуємо!» прокручує сторінку до свічки. Якщо посеред покладання відкрили вікно чи сховали вкладку — анімацію перервано, після повернення вона починається з початку. Свічка поза екраном — чекає (IntersectionObserver). `prefers-reduced-motion` — без GIF, одразу статичний, показ позначено. GIF не завантажився за 10 с — статичний подарунок, покладання лишається до наступного візиту
- **Адмін-розміщення «без оплати (тест)»** подарунка з GIF — адмін один раз сам бачить покладання; так анімацію можна перевірити без ключів LiqPay
- **Paskal.py:** `anim` у списку подарунків меморіалу (лише власнику), `POST /api/memorial-gift/{id}/shown`, `_gift_anim_ms()`; оплата й адмін-розміщення ставлять `anim_state` залежно від наявності GIF
- **card.html:** шар `.gift-anim`, черга покладань, `_giftMaybeAnimate()`; оновлення списку подарунків перериває поточне покладання (черга збирається заново)
- **admin.html:** підказка до поля «GIF покладання» — як має бути скомпонований кадр
- **Демо (лише локально, не заливати):** `img/gifts/demo/{roses,lampadka,teddy}_place.gif` — «руки опускають подарунок і відпускають» (27 кадрів, 2.78 с, ≈60 КБ), згенеровані без Pillow (декодер PNG, палітра, LZW); у локальній БД підключені до 3 демо-подарунків
- **Перевірено** (тестові ключі LiqPay на :8001, тимчасові акаунти, дані тестів прибрано):
  - API: власник бачить `anim` (`roses_place.gif`, 2780 мс), інший користувач і анонім — ні; `shown`: анонім 401, чужий `changed: 0`, свій 1, повторно 0, після цього `anim` немає; подарунок без GIF після оплати — без `anim`; адмін-розміщення з GIF — `anim` лише адміну
  - браузер:
    - оплата → «Дякуємо!» (під вікном анімації немає) → «Закрити» → прокрутка до свічки → GIF покладання → статичний подарунок на тому самому місці й того ж розміру; 1 завантаження GIF; на сервері показ позначено;
    - повторний візит покупця й візит іншого користувача — без анімації й без жодного завантаження GIF;
    - свічка поза екраном — анімація чекає; відкрили вікно посеред покладання — перервано, після закриття — з першого кадру;
    - `prefers-reduced-motion` — без GIF; телефон 390 px — покладання в крайнє місце, без горизонтального скролу;
    - адмін «Покласти без оплати (тест)» — сам бачить покладання; 0 помилок консолі
- Файли: `Paskal.py`, `card.html`, `admin.html`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`. SQL не потрібен
- **Далі — етап 8** (кілька подарунків: розміщення без накладань, більше 8 — «ще N»)

### v3.48 (2026-10-03) — «Подарунки загиблому», етап 6: оплата через LiqPay (ПриватБанк)
- Наступний етап ТЗ `Gifts-for-fallen.md` («продолжай»). Ключів мерчанта поки немає: інтеграція повна, але вмикається лише після додавання ключів у `.env`. Перевірено на тестових ключах із підробленим LiqPay (нижче)
- **Шлях покупця:** «Купити за X ₴» → підтвердження («Оплата через LiqPay… ви повернетеся на цю сторінку») → «Перейти до оплати» → сервер створює замовлення й формує `data`/`signature` → сторінка відправляє форму POST на `https://www.liqpay.ua/api/3/checkout` → LiqPay повертає на `card?slug=…&gift_order=…` → сторінка звіряє статус через сервер і показує результат:
  - «Дякуємо! Подарунок покладено біля свічки» — подарунок одразу з'являється біля свічки;
  - «Оплата ще обробляється» + «Перевірити ще раз»;
  - «Оплату не завершено» + «Оплатити» / «Скасувати»;
  - «Оплата не пройшла» / «Замовлення скасовано»
- «Мої замовлення»: «Оплатити» (створене), «Перевірити оплату» (обробляється), «Скасувати»; на телефоні кнопки стоять під текстом в один ряд
- **Підтвердження оплати — лише на сервері:**
  - callback `POST /api/gifts/liqpay/callback` (`server_url`): підпис `base64(sha1(private+data+private))` (порівняння сталого часу), ключ магазину, формат `order_id`; сума й валюта мають точно збігатися зі знімком замовлення, інакше `error` і запис `GIFT_PAY_MISMATCH`;
  - звірка `action=status` з сервера — при поверненні з оплати, «Перевірити оплату», повторній оплаті й скасуванні вже розпочатої оплати;
  - один платіж зараховується один раз (`payment_id` UNIQUE): повторний callback нічого не змінює, той самий платіж для іншого замовлення не зараховується (`GIFT_PAY_DUP_PAYMENT`);
  - місце біля свічки призначається під блокуванням меморіалу (`SELECT … FOR UPDATE`), тож одночасні оплати не займають одне місце;
  - гроші перемагають: успішна оплата зараховується й для скасованого замовлення; пізніша помилка чи повтор оплачене не відкочують; повернення коштів (`reversed`) прибирає подарунок і звільняє місце
- **Статуси LiqPay → замовлення:** `success` (і `sandbox` — лише в тестовому режимі) → `paid`; `failure`/`error` → `error`; `reversed` → `cancelled`; `processing`, `wait_*` (зокрема `wait_accept` — магазин ще не пройшов перевірку LiqPay) і `*_verify` → `pending`; решта → `unknown`
- **Paskal.py:**
  - конфігурація `LIQPAY_PUBLIC_KEY`, `LIQPAY_PRIVATE_KEY`, `LIQPAY_SANDBOX` — лише `.env`; без ключів оплата вимкнена: замовлення не створюються (503), на сторінці «Оплата незабаром»;
  - ендпоінти `pay`, `sync`, `liqpay/callback` і адмінський `memorial-gift/{id}/sync`;
  - `/api/card/settings` віддає обчислений `card_gifts_pay_ready`; `GET /api/admin/gifts` — стан оплати (`payment`);
  - скасування розпочатої оплати — лише після звірки з LiqPay; повторний клік «Купити» повертає й замовлення, що вже на оплаті;
  - подарунок без ціни купити не можна (400);
  - callback працює й під час техробіт (`/api/gifts/liqpay/` у `_MAINTENANCE_ALLOW`)
- **admin.html:** у «Замовленнях» — ID платежу LiqPay під статусом і кнопка «Перевірити оплату в LiqPay» (звірка, зокрема виявлення повернення коштів); у «Налаштуваннях» — стан LiqPay («Підключено · тестовий режим», адреса callback або підказка про `.env`); оновлено описи перемикачів
- **`migrations_i18n_gifts.sql`:** +19 ключів uk/en (оплата, результати, звірка) і оновлені описи двох перемикачів. **`.env.example`:** блок LiqPay
- **Перевірено** (тестові ключі; сервер :8001 + підроблений API статусів LiqPay :8002; тимчасові акаунти; дані тестів прибрано):
  - API:
    - перехід на оплату: сума, валюта, `order_id`, `result_url`/`server_url`, мова uk/en, `sandbox`; підпис збігся з незалежним обчисленням у Node; чуже 404, анонім 401;
    - callback: підроблений підпис, чужий ключ і нечитабельні дані → 400; невідоме замовлення ігнорується; сума 29.99 замість 30 і валюта USD → `error`;
    - успіх → `paid`, місце 0, подарунок біля свічки; повтор і пізня `failure` нічого не змінюють; той самий `payment_id` для іншого замовлення не зараховано;
    - дві одночасні оплати → місця 1 і 2; на меморіалі з розміщеннями адміна на місцях 0 і 1 → місце 2;
    - повернення коштів → подарунок зник, місце звільнилось; оплата скасованого замовлення → `paid`;
    - звірка: платіж є → `paid`, немає → `created`, LiqPay не відповів → без змін; скасування під час обробки → 409, при недоступному LiqPay → 503; адмінська звірка виявила повернення коштів;
    - техроботи: сайт віддає 503, а callback зараховано; купівля вимкнена → 403; ціна 0 → 400
  - браузер:
    - повний шлях із перехопленням форми на checkout (POST, підпис вірний) → «Дякуємо!», параметр прибрано з адреси, подарунок біля свічки;
    - «Оплату не завершено» → «Скасувати»; «обробляється» → «Перевірити ще раз» → «Дякуємо!»;
    - «Мої замовлення» з кнопками за статусом, «Оплатити» з переліку веде на checkout; EN; телефон 390 px без горизонтального скролу;
    - адмінка: ID платежу, звірка («LiqPay: без змін · Оплачено»), стан LiqPay; 0 помилок консолі
  - без ключів: `card_gifts_pay_ready=0`, кнопки купівлі немає («Оплата незабаром»), замовлення й callback → 503, адмінка «Не підключено»; у бойовому режимі статус `sandbox` не зараховується
- **Знайдено й виправлено під час перевірки:**
  - після повернення з LiqPay вікно відкривалось одразу на результаті без каталогу, і «← До каталогу» показувала порожню сітку — тепер каталог підвантажується при будь-якому показі сітки;
  - подарунок із ціною 0 ₴ пропонувався до купівлі («Купити за 0 ₴»), а сервер відмовляв загальною помилкою — тепер кнопки немає;
  - на телефоні в «Моїх замовленнях» дві кнопки стискали текст у вузьку колонку («Замовлення» залазило під кнопку) — кнопки перенесено під текст
- Не перевірено (потрібні ключі мерчанта): справжня сторінка оплати LiqPay і реальний callback. Перший крок після отримання ключів — тест у режимі sandbox (`LIQPAY_SANDBOX=1`), див. MASTER_GUIDE.md, розділ 17
- Файли: `Paskal.py`, `card.html`, `admin.html`, `migrations_i18n_gifts.sql`, `.env.example`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`, `MASTER_GUIDE.md`, `SECURITY_RULES.md`
- **Далі — етап 7** (GIF покладання → статичний подарунок; GIF бачить лише покупець після оплати)

### v3.47 (2026-10-03) — «Подарунки загиблому», етап 5: оформлення покупки (без підтвердження оплати)
- Наступний етап ТЗ `Gifts-for-fallen.md` («далее»). Покупець проходить шлях до оплати: обрати → «Купити за X ₴» → підтвердження (подарунок, меморіал, сума) → замовлення створене, статус `created` «Створено, очікує оплати». Біля свічки замовлення не з'являється, поки не оплачене (етап 6 — LiqPay); місце (slot) призначається лише після оплати
- **Захист (ТЗ, розділ 6):**
  - клієнт передає тільки `memorial_id` і `gift_id`; ціна береться з каталогу (знімок `price_kop`), користувач — із сесії, меморіал перевіряється (схвалений);
  - підставлені `price`/`user_id`/`status` ігноруються (перевірено);
  - чуже замовлення не видно й не скасувати (404);
  - оплачене не скасувати (409);
  - повторний клік за 10 хв повертає те саме замовлення, а не дубль;
  - не більше 5 незавершених на користувача;
  - rate limit на створення, перегляд і скасування
- **Paskal.py:**
  - `POST /api/gifts/orders`, `GET /api/gifts/orders`, `POST /api/gifts/orders/{order_id}/cancel` (номер — `zp-` + 24 hex, перевіряється форматом);
  - нове налаштування `card_gifts_buy_enabled` (дефолт 0) — окремо від модуля, щоб на проді не з'являлись замовлення, які ще нема чим оплатити
- **card.html:**
  - у деталях подарунка для авторизованого — «Купити за X ₴» (або «Оплата незабаром», якщо купівля вимкнена);
  - в адміна додатково «Покласти без оплати (тест)»;
  - екран підтвердження → «Замовлення створено, № XXXXXXXX»;
  - «Мої замовлення» для цього меморіалу зі статусами й «Скасувати» для неоплачених;
  - після повернення з Google-входу (`?oauth=success`) каталог відкривається сам, параметр прибирається з адреси
- **admin.html:**
  - вкладка «Розміщення» перейменована на «Замовлення» (там і покупки, і тестові розміщення);
  - у «Налаштуваннях» — другий перемикач «Купівля доступна»
- **`migrations_i18n_gifts.sql`:** +22 ключі (покупка, статуси замовлень, перемикач) uk/en; повторний запуск безпечний
- **Перевірено** (на окремому сервері :8001, щоб не скидати сесію користувача на :8000; тимчасові акаунти, дані тестів прибрано):
  - API:
    - анонім 401; купівля вимкнена 403;
    - замовлення створюється з ціною каталогу (50 ₴), а не з підставленими 1 ₴;
    - дубль-клік → те саме замовлення; 6-те незавершене → 409;
    - «мої замовлення» — лише свої; скасування чужого 404, повторне й оплаченого 409;
    - біля свічки неоплачене не з'являється; адмінка бачить статуси з лічильниками
  - UI:
    - повернення з входу відкриває каталог; «Купити за 50 ₴» → підтвердження з іменем загиблого → «Замовлення створено» → «Мої замовлення» → «Скасувати»;
    - EN; при вимкненій купівлі — «Оплата незабаром»; в адміна обидві кнопки; 0 помилок
  - знайдено й виправлено: у підтвердженні прізвище й ім'я злипались («НауменкоРоман») — `#hero-name` розділяє їх `<br>`, тепер береться `innerText` з нормалізацією пробілів
- **Знайдено й виправлено (баг етапу 4):** демо-подарунки з `img/gifts/demo/` не можна було зберегти чи вимкнути в адмінці — `_GIFT_IMG_RE` не допускав підпапку, форма отримувала 400 «Недопустимий шлях зображення». Тепер дозволена лише фіксована підпапка `demo/` (завантаження з адмінки, як і раніше, лягають у корінь `img/gifts/`); `..`, інші папки, SVG і зовнішні URL відхиляються (перевірено до/після на :8000)
- Файли: `Paskal.py`, `card.html`, `admin.html`, `migrations_i18n_gifts.sql`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`
- **Далі — етап 6** (ПриватБанк / LiqPay: перехід на оплату, callback з підписом, перевірка суми, `paid` → подарунок біля свічки). Потрібні ключі мерчанта LiqPay

### v3.46 (2026-10-03) — «Подарунки загиблому», етап 4: адмінка каталогу
- Наступний етап ТЗ `Gifts-for-fallen.md` («далее по списку задач»). Новий розділ адмінки «Подарунки загиблому» (`sec-gifts`, іконка `#ico-gift`, пункт меню після «Картка»), 4 вкладки:
  - **Каталог:** таблиця з мініатюрою, категорією, ціною, позначкою GIF, лічильником розміщень, порядком; клік по «Так/Ні» вмикає/вимикає подарунок. Вікно додавання/редагування:
    - назва й короткий опис кожною активною мовою (`languages`);
    - категорія, ціна в ₴;
    - 3 зображення із завантаженням і попереднім переглядом: у каталозі, біля свічки, GIF покладання;
    - тривалість GIF (заповнюється сама), масштаб, бік від свічки, шар (z), порядок, активність
  - **Категорії:** код латиницею, назви мовами, порядок, активність
  - **Розміщення:** усі покладені подарунки (покупки) — фільтр за статусом із лічильниками, пошук (ID/прізвище/email), пагінація, посилання на меморіал; тестове розміщення адміна можна прибрати
  - **Налаштування:** перемикач модуля (`card_gifts_enabled`) — перенесений сюди з розділу «Картка» (там прибраний, щоб не було двох місць)
- **Paskal.py:**
  - `GET /api/admin/gifts`; `POST`/`PUT`/`DELETE /api/admin/gifts…`; `POST`/`PUT`/`DELETE /api/admin/gift-categories…`; `POST /api/admin/gifts/upload`; `GET /api/admin/memorial-gifts` — усі `require_admin`
  - видалити подарунок із розміщеннями чи категорію з подарунками не можна (409) — лише вимкнути
  - зображення — лише шляхи `/img/gifts/…`; файл зберігається з випадковим іменем; сигнатура має відповідати розширенню (SVG не приймається)
  - тривалість і кадри GIF читаються без нових залежностей (`_gif_meta`: Graphic Control Extension), бо Pillow немає в `requirements.txt`
  - тексти каталогу — `_gift_text()` замість `_sanitize_text()`, щоб апостроф не перетворювався на `&#x27;` (див. розділ 11)
- **admin.html:** розділ, вкладки, вікна подарунка й категорії. До спрайту додано відсутні `#ico-plus` і `#ico-cross` — раніше 15 кнопок адмінки (зокрема «Додати» в «Друзях») показувались без іконки
- **`migrations_i18n_gifts.sql`:** доповнено 23 ключами адмінки (`nav.gifts`, `adm.gifts.*`) uk/en; файл ідемпотентний, можна виконувати повторно
- **Перевірено** (локально; тимчасовий адмін через справжній вхід; файли й записи тестів прибрано):
  - API:
    - анонім 403 на всіх адмін-ендпоінтах;
    - завантаження PNG/GIF — OK, GIF: 3 кадри, 2.0 с, 120×120;
    - відхиляються: GIF під виглядом `.png`, SVG, 3.6 МБ, неправильний формат для типу, невідомий `kind`;
    - категорія: дубль 409, поганий код 400; подарунок: без назви uk / без зображення / чужий шлях `../` / зовнішній URL / неіснуюча категорія 400, від'ємна ціна 422;
    - апостроф у «Пам'ятний вінок» зберігся, `<b>` знешкоджено;
    - новий подарунок з'являється в публічному каталозі (uk/en), вимкнений зникає;
    - видалення розміщеного подарунка 409, після прибирання розміщення — видаляється
  - UI (headless Chrome):
    - розділ і пункт меню є; таблиця, вкладки, лічильники статусів працюють;
    - вікно подарунка: реальне завантаження файлів через поля форми, попередній перегляд, автотривалість GIF, збереження;
    - вимкнення/увімкнення кліком; видалення кнопками з підтвердженням;
    - перемикач модуля в «Налаштуваннях», у «Картці» його вже немає; 0 помилок консолі
- Під час тестів користувач паралельно перевіряв модуль локально (поклав 2 подарунки на меморіал #1045) — його дані не чіпались; перезапуск сервера скинув його сесію (сесії в пам'яті)
- Файли: `Paskal.py`, `admin.html`, `migrations_i18n_gifts.sql`, `CLAUDE.md`, `SESSION_CHANGES.md`
- **Далі — етап 5** (оформлення покупки без підтвердження оплати) — за командою користувача

### v3.45 (2026-10-03) — «Подарунки загиблому» (Gifts-for-fallen.md): етапи 1–3 — аналіз, план, базовий функціонал без оплати
- ТЗ користувача `Gifts-for-fallen.md` (підключене до цього файлу через `@`-імпорт): подарунки біля свічки на `card?slug=`, оплата ПриватБанком, GIF покладання → статичний подарунок. Виконується **строго поетапно** (11 етапів)
- **Етап 1 (аналіз, без змін коду):**
  - `card.html` — самодостатня сторінка без локалізації й без входу;
  - свічка — `POST /api/like/{id}` + `localStorage`;
  - Google-вхід повертав лише на `/admin`;
  - платіжної інтеграції немає (лише посилання на банку Monobank і ручні суми в «Спадщині»), тож LiqPay буде новою і єдиною;
  - CSP дозволяє перехід на сторінку LiqPay, але не його iframe;
  - ризики — у плані сесії: ключі LiqPay, callback не дістане localhost, ціна й статус лише на сервері, свічку не чіпати, продуктивність
- **Етап 2 (план):** 4 таблиці (див. розділ 4); налаштування `card_gifts_*` через наявний `/api/card/settings`; UI-тексти — секція `gifts` в `i18n_translations`; LiqPay — перехід на checkout + callback з підписом і перевіркою суми + `action: status`; GIF — лише покупцю (`anim_state`)
- **Рішення користувача:** до оплати подарунок ставить лише адмін, модуль за замовчуванням вимкнений; GIF — покупцю після оплати; оплата — LiqPay; зображень поки немає — локальні заглушки
- **Етап 3 (реалізовано):**
  - Paskal.py:
    - таблиці `gift_categories`, `gifts`, `gift_i18n`, `memorial_gifts` в `init_db()`; дефолт `card_gifts_enabled: "0"`;
    - `GET /api/gifts/catalog`, `GET /api/memorial/{id}/gifts`, `POST /api/memorial/{id}/gifts` (`require_admin`), `DELETE /api/admin/memorial-gift/{id}` (лише `granted`);
    - Google-вхід: `next=card:<slug>` (slug `^[a-z0-9-]{3,220}$`) → `/card?slug=…&oauth=success` (`_oauth_url` ставить `&`, якщо в адресі вже є `?`)
  - card.html:
    - перед `.candle` — якір нульового розміру `#gift-stage`; подарунки стоять на лінії основи свічки в 8 слотах ліворуч/праворуч (телефон — менший крок); розмітка, текст і логіка свічки не змінені;
    - кнопка «Подарунки загиблому» під кнопкою свічки;
    - вікно каталогу (вантажиться лише після кліку): сітка → деталі → анонім «Увійти через Google», не адмін «Оплата незабаром», адмін «Покласти подарунок»;
    - тексти через `_gt()` зі словника `/api/i18n/{lang}?sections=gifts` (мова — cookie `lang`, інакше браузер)
  - admin.html: перемикач «Модуль "Подарунки загиблому"» у `sec-card` (той самий список збереження, що `card_show_*`)
  - `migrations_i18n_gifts.sql`: 16 ключів `gifts.*` + 2 адмінські, uk/en (без міграції — вбудовані українські тексти)
  - `img/gifts/demo/` (троянди, лампадка, ведмедик) і 3 демо-подарунки — **лише в локальній БД**, на прод не заливати
- **Перевірено** (локально, headless Chrome, тимчасові акаунти admin/user — видалені після тесту):
  - модуль вимкнений: кнопки немає, додаткових запитів 0, розмітка й тексти свічки ідентичні, клік по свічці працює;
  - модуль увімкнений:
    - під час завантаження лише 2 легкі запити (секція `gifts`, подарунки меморіалу), каталог — тільки після кліку;
    - анонім → «Увійти через Google» з поверненням на цей меморіал; користувач → «Оплата незабаром»;
    - адмін поклав 3 подарунки — з'являються одразу, після перезавантаження на місці, без накладань, не перекривають свічку;
    - EN-тексти; телефон 390px без горизонтального скролу; 0 нових помилок консолі (лише давня CSP-блокировка Google Analytics);
  - бекенд:
    - анонім 403; неіснуючий меморіал 404; неактивний подарунок 400 (у каталозі прихований, але розміщений лишається); модуль вимкнений 403;
    - видалення оплаченого заблоковане; мова `zz'--` → uk; каталог не віддає GIF-адрес
- Файли: `Paskal.py`, `card.html`, `admin.html`, `migrations_i18n_gifts.sql` (новий), `img/gifts/demo/*` (лише локально), `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`
- **Далі — етап 4** (адмінка каталогу: подарунки, категорії, зображення/GIF, ціни, порядок, розміщення) — за командою користувача

### v3.44 (2026-10-03) — Тарифний план погибшого (Бронза / Срібло / Золото / Платина): металева кромка бокової панелі, виставляє лише адмін
- Пряма вимога користувача: в адмінці при редагуванні чи додаванні погибшого адміністратор обирає тарифний план — бронза, срібло, золото або платина. Бокова панель з інформацією про погибшого на головній сторінці набуває вигляду обраного плану: кромки кольору металу з переливом, щоб план було видно одразу. Поки лише зовнішній вигляд, без цін і оплати. Усе зберігається в БД
- **БД:** нова колонка `memorials.tier` VARCHAR(10) NOT NULL DEFAULT `''` (`bronze|silver|gold|platinum`, `''` — без плану). Додається автоматично в `init_db()` при старті бекенду, тим самим патерном, що `video_url`/`rank`/`unit`. Усі наявні записи — без плану, їхній вигляд не змінився
- **Backend (Paskal.py):**
  - `_TIERS` + `_validate_tier()` — allowlist; регістр і пробіли нормалізуються, невідоме значення → `''`
  - `PUT /api/admin/memorial/{id}`: план приймається лише від `role='admin'`; від модератора поле мовчки відкидається, решта його правок зберігається
  - `POST /api/admin/memorial`: план записується лише від адміна
  - публічний `POST /api/people`: план не записується (INSERT без цієї колонки) — відвідувач не може виставити собі план
  - `tier` додано в SELECT `/api/map-points`, `/api/people`, `/api/memorial/by-slug/{slug}`; `/api/memorial/{id}` і адмінський список — `SELECT *`
- **Адмінка (admin.html):** поле «Тарифний план» (без плану / Бронза / Срібло / Золото / Платина) у спільній модалці редагування й створення, у вільній клітинці поруч із «Показувати автора публічно». `_setEditTier()` заповнює поле; для модератора воно заблоковане з позначкою «лише адмін», і `saveEdit()` план не надсилає
- **Сайт (index.html, mobile.html, Style.css, mobile.css):**
  - `openCard()` → `_applyCardTier()` ставить `#card[data-tier]` у фазі 1 (з легкого списку) і у фазі 2 (з повного запису); запис без плану знімає атрибут
  - новий шар `<div id="ctier">` усередині `#card`: маска-рамка 3px (`mask-composite: exclude`) зі статичним металевим градієнтом плану
  - `#ctier::after` — світла смуга переливу: пробігає кромкою згори вниз (~2.3 с, далі пауза; цикл 6.5 с), лише поки картка відкрита; при `prefers-reduced-motion` анімації немає
  - світіння назовні від лівого краю й м'який відсвіт усередині вздовж кромки; рамка `#card` і розділювачі `hr` — у тон плану
  - кольори: бронза — мідна, срібло — холодна сіро-біла, золото — жовто-золота, платина — біла з крижано-бузковим переливом (як на `/pricing/`, щоб не плутати зі сріблом)
  - mobile.html (лист знизу): рамка повторює заокруглені кути, світіння йде вгору (правило в mobile.css)
- **Продуктивність:** смуга переливу — окремий композитний шар, анімується лише `transform`. Trace за 3.5 с: Paint-подій 294 (перелив іде) проти 295 (зупинений), RasterTask 170 проти 172; жодної перемальовки `#card` чи `#ctier`
- **Перевірено** локально (headless Chrome і прямі виклики ендпоінтів):
  - бекенд: адмін ставить усі 4 плани; `diamond` → `''`; ` GOLD ` → `gold`; модератор план не змінює, а інші його поля зберігаються; створення адміном — з планом, модератором — без; публічна форма (режим «вільно») план не записує. Тестові записи видалено, плани повернуто
  - сайт: 4 плани і запис без плану (десктоп); посилання поста `/memorial/{slug}` відкривається одразу з кромкою плану; телефон (index.html, картка на весь екран); планшет (mobile.html, лист знизу); `prefers-reduced-motion`; 0 помилок консолі
  - адмінка: поле заповнюється; для модератора заблоковане; збереження й створення надсилають план лише від адміна
- Помічено, не змінювалось: локальний uvicorn не роздає `/mobile.css` (див. розділ 12). Для перевірки mobile.html файл підставлено з диска через CDP `Fetch`; прод (`/mobile.css?v=20261003b`) віддає 200 `text/css`
- Версіонування: `Style.css?v=20261003` → `?v=20261003b` (index.html, mobile.html); `mobile.css` → `mobile.css?v=20261003b` (mobile.html, раніше без версії)
- Файли: `Paskal.py`, `admin.html`, `index.html`, `mobile.html`, `Style.css`, `mobile.css`, `CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`. Ручного SQL не потрібно: колонка створиться при рестарті бекенду (запасний SQL — у SESSION_CHANGES.md)

### v3.43 (2026-10-03) — Дробовий плавний зум у Leaflet-картах («Світ», вибір точки у формі) + жести «Світу» більше не рухають приховану карту України
- ТЗ користувача «Оптимизация управления масштабом (Zoom) карты»: зум має змінюватись плавно, через проміжні дробові значення (5.00 → 5.05 → … → 6.00), без стрибків на цілі рівні. Використовувати штатні механізми бібліотеки карти (fractional zoom, zoomSnap, анімація); зум відносно курсора; маркери й решта логіки не мають зламатись. Рішення користувача: «Обидві» карти; для Leaflet — «Штатні опції + плавне колесо»
- Основна карта України вже мала плавний дробовий зум з v3.42 — без змін (регресійно перевірено)
- **Діагностика** (код Leaflet 1.9.4 + CDP-замір локально):
  - усі три Leaflet-карти (`_worldMap` в index.html і mobile.html, `_maddMap` у формі «Додати запис») працювали з дефолтними `zoomSnap: 1`, `zoomDelta: 1`
  - `ScrollWheelZoom._performZoom` округлює кожну порцію колеса вгору до `zoomSnap` (`Math.ceil`), тож будь-який рух колеса — щонайменше цілий рівень. `_tryAnimatedZoom` ігнорує нові запити, поки йде анімація (250 мс), тому частина обертів губиться
  - pinch (TouchZoom) безперервний, але наприкінці жесту «доскакує» до цілого рівня (`_animateZoom(..., zoomSnap)`)
  - замір ДО (10 «кліків» колеса з інтервалом 60 мс): зум 5 → 14 (+9 рівнів, тобто ×512), лише цілі значення 5, 6, 7 … 14, кожна сходинка — цілий рівень за кадр
- **Рішення А — штатні опції Leaflet** (`_LF_ZOOM_OPTS`, додаються в кожен `L.map`):
  - `zoomSnap: 0` — дробовий зум без округлення (pinch, подвійний клік, клавіатура)
  - `zoomDelta: 0.5` — кнопки +/− на пів-рівня зі штатною анімацією Leaflet
  - `scrollWheelZoom: false` — штатне порційне колесо замінене на `_lfSmoothWheel`
- **Рішення Б — плавне колесо `_lfSmoothWheel(map)`** на тому самому безперервному механізмі, що й штатний pinch Leaflet: `_moveStart` → щокадру `_move(center, zoom, {pinch:true, round:false})` → `_moveEnd` (тайли довантажуються після зупинки):
  - миша ~0.25 рівня за «клік» (`−dy·0.0025`), тачпад — пропорційно, pinch тачпада (`ctrlKey`) — `−dy·0.01`; кроки накопичуються в ціль у межах min/max зуму
  - зум наздоганяє ціль експоненційно (`τ = 80 мс`, як в основної карти); центр рахується так, щоб точка під курсором лишалась на місці
  - захист: карту змінили ззовні (кнопки, `flyTo`, драг) — завершення; `mousedown`/`touchstart` — завершення одразу; під час штатної анімації Leaflet подія пропускається; `map._zpWheelStop()` — для наших кнопок
  - dt кадру обмежено 250 мс: на повільних кадрах зум іде в реальному часі, а не «тягнеться»
- Кнопки режиму «Світ» (index.html; тепер і mobile.html): `#zin/#zout` → `zoomIn()/zoomOut()` (±0.5 рівня, анімація Leaflet), `#zrst` → `flyTo([49,32], 5, {duration: 0.8})` замість миттєвого `setView`
- Style.css: поки йде будь-який зум «Світу» (клас `.zp-zooming` на `zoomstart`/`zoomend`), пульсація SVG-зірок призупиняється — менше роботи щокадру
- **Знайдено під час перевірки й виправлено — жести «Світу» потрапляли в приховану карту України.** Давня вада, не пов'язана з v3.42. Контейнер Leaflet лежить усередині `#map-wrap`, Leaflet не зупиняє спливання `mousedown`/`touch*`, а обробники основної карти на `#map-wrap` не перевіряли режим:
  - драг «Світу» панорамував приховану карту України (0,0 → −120,−64), pinch її зумив (×1 → ×2.35). Після повернення в режим України вигляд був «випадковим» (×3.5 у випадковому місці)
  - у mobile.html наведення на порожнє місце «Світу» показувало тултіп прихованої точки, а тап **відкривав картку іншої людини** — точки прихованої карти під пальцем
  - кнопки `#zin/#zout/#zrst` у mobile.html в режимі «Світ» зумили приховану карту України: видимі поверх карти, але без видимого ефекту
  - фікс:
    - `mousedown` основної карти ігнорує режим «Світ»
    - у `touchmove` pinch і панорамування основної карти в режимі «Світ» пропускаються; дим від пальця лишається
    - у mobile.html `mousemove`/`mouseup` отримали ту саму перевірку, що вже була в index.html
    - кнопки mobile.html працюють з картою «Світ» так само, як в index.html
- **ДО → ПІСЛЯ** (карта «Світ», десктоп, 10 «кліків» колеса з інтервалом 60 мс):

  | Метрика | ДО | ПІСЛЯ |
  |---|---|---|
  | зум | 5 → 14 (+9 рівнів) | 5 → 7.5 (+0.25 за «клік») |
  | різних значень зуму | 10 (лише цілі) | 33 (дробові) |
  | найбільший крок за кадр | 1 рівень (×2) | 0.24 рівня |
  | зсув точки під курсором | — | ≤1 px |
  | тайли після зупинки | довантажені | довантажені (69, порожніх 0) |
  | маркерів | 1168 | 1168 |

- Функціонально перевірено (index.html — десктоп, mobile.html — UA планшета):
  - кнопки +/− (наші й контрол Leaflet) дають ±0.5 рівня; ⌂ плавно летить на рівень 5 (6–8 проміжних значень)
  - колесо над «Світом» не зумить приховану карту України
  - перетягування після колеса, тултіп і клік/тап по маркеру (картка) працюють
  - pinch закінчується на дробовому рівні (5 → 6.233), без «доскоку»
  - форма «Додати запис»: колесо плавне (5 → 5.75 за 3 «кліки»), клік ставить точку
  - витоки жестів:
    - ДО: драг, pinch і тап «Світу» змінювали приховану карту, тап відкривав картку іншої людини
    - ПІСЛЯ: карта України лишається в тому самому вигляді (×1, 0, 0), тап по порожньому місцю картку не відкриває
  - регресія карти України: колесо ×1.1 за «клік», драг мишею й пальцем, pinch, тултіп, клік/тап по зірці відкриває правильну картку
  - 0 помилок консолі
- **Відоме обмеження (не змінювалось)**: на тестовій машині (AMD Radeon 610M) режим «Світ» сам по собі має низький FPS. Причина — 1168 маркерів-DOM-елементів (`L.divIcon` зі SVG-зіркою і CSS-пульсацією):
  - FPS у спокої: ~10 кадрів/с; із прихованими маркерами — ~38; з призупиненою пульсацією — ~19
  - тому плавний зум «Світу» тут іде з ~5–7 кадрами/с (паузи rAF p95 ~270 мс; ДО — 317 мс)
  - повноцінне рішення — малювати маркери «Світу» на canvas. Опція `renderer: L.canvas()` вже є, але `L.marker` + `divIcon` її не використовують. Це окремий крок, потребує підтвердження
- Версіонування: `Style.css?v=20261002e` → `?v=20261003` (index.html, mobile.html)
- Файли: `index.html`, `mobile.html`, `Style.css`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL не потрібен

### v3.42 (2026-10-03) — Плавний зум карти, як у Google Maps (колесо, кнопки +/−, ⌂), index.html + mobile.html
- Скарга користувача: прокрутка колесом і кнопки +/− зумують «великим різким» стрибком. Вимога — плавне й гнучке керування, як у Google Maps, з більшою кількістю дрібних кроків; без нових налаштувань в адмінці; обидві сторінки
- **Діагностика** (CDP-заміри локально, Chrome 154, AMD Radeon 610M):
  - на проді й локально `zoom_min = 2`, а стартовий вигляд — ×1, тобто нижче мінімуму. Тому перший «клік» колеса чи «+» миттєво стрибав ×1→×2, ще ~6 кліків «відпрацьовували борг» віртуального зуму `_vZoom` без жодної реакції, а на «мінімумі» (×2) прокрутка чи «−» стрибали назад на ×1 через `resetView()`
  - зміни масштабу застосовувались миттєво, без анімації, а кожна зміна `viewBox` SVG-карти — це повна перерастеризація шару, ~170–250 мс GPU на цій машині. Тому кілька «кліків» злипались, і масштаб у одному кадрі змінювався до **×2**
  - тротлінг 8 мс у wheel-обробнику губив частину подій
- **Рішення 1 — гібридний рендер:**
  - під час руху карта (`#svg-layer`) масштабується CSS-трансформацією від закоміченого стану `_trC` до `tr` (GPU, без перерастеризації); Style.css: `#svg-layer { will-change: transform; transform-origin: 0 0; }`
  - чіткий `viewBox` комітиться через ~120 мс після зупинки (`_commitTr`)
  - класи порогів `zoom-city`/`zoom-deep` перемикаються лише при коміті, щоб не було рестайлу SVG посеред анімації
  - щоб при віддаленні не було порожніх країв, працює правило покриття (`_coveredByCommit`): коміт робиться з запасом відносно цілі (×0.6), але растр збільшується не більше ніж у 2.5 раза (`_ZOOM_MAX_BLUR`). При більшому збільшенні Chrome перерастеризовує шар щокадру — так виявилось на першій версії ⌂
- **Рішення 2 — анімований зум за ціллю (`_zoomBy`/`_zoomFrame`):**
  - кроки накопичуються в ціль, масштаб наздоганяє її експоненційно в log-просторі (`τ=80 мс`, крок осідає за ~250 мс); точка під курсором лишається на місці
  - колесо: ×1.1 за «клік»; тачпад — пропорційно (`exp(−dy·0.0022)`); pinch тачпада (`ctrlKey`) — `exp(−dy·0.01)`
  - кнопки: ×1.2 (дрібніше за попередні ×1.28)
  - ⌂: зум навколо нерухомої точки перетворення `(s,x,y)→(1,0,0)` тим самим рушієм, рівно в стартовий вигляд
  - межі: `_zoomLimits()` — мінімум `min(zoom_min, 1)`, тож стартовий вигляд ×1 завжди досяжний плавно, без стрибків; максимум — `zoom_max`
  - прибрано `_vZoom`, тротлінг 8 мс і стрибки `resetView()` на мінімумі
- Перетягування, pinch на тачскріні і `flyTo` лишились на старому шляху (`applyTr` → коміт щокадру). `applyTr()` зупиняє анімацію зуму, а `mousedown`/`touchstart` фіксують її поточний стан
- **ДО → ПІСЛЯ** (десктоп, той самий сценарій):

  | Сценарій | Метрика | ДО | ПІСЛЯ |
  |---|---|---|---|
  | 10 кліків колеса, наближення | найбільша зміна масштабу за кадр | ×2.0 | ×1.05 |
  | | кадрів з плавною зміною | 5 | 74 |
  | | паузи rAF, p95 | 200 мс | 33 мс |
  | | перемальовок | 5 | 2 |
  | 10 кліків колеса, віддалення | найбільша зміна за кадр | ×2.0 | ×1.065 |
  | | паузи rAF, p95 | 150 мс | 67 мс |
  | | перемальовок | 5 | 2 |
  | 5×«+» і 5×«−» | перемальовок | 10 | 1 |
  | | паузи rAF, p95 | 117 мс | 17 мс |
  | | GPU-растеризація | 2673 мс | 600 мс |
  | ⌂ | вигляд | миттєвий стрибок | плавна анімація |
  | на «мінімумі» | вигляд | стрибок ×2→×1 | плавно |
- Функціонально перевірено на `index.html` (десктоп) і `mobile.html` (UA планшета):
  - точка під курсором стабільна; межа ×8 тримається;
  - після зупинки карта чітка (transform порожній, viewBox закомічено), підписи міст з'являються на ≥4;
  - посеред віддалення немає порожніх країв (скріншот);
  - перетягування, тултіп, клік по зірці (картка + `flyTo`), кнопки ×1.2 і pinch працюють;
  - ⌂ точно повертає (×1, 0, 0); 0 помилок консолі
- Відоме обмеження: кожен коміт — це повна растеризація SVG-карти з drop-shadow-світінням. На слабкому GPU після зупинки зуму й при віддаленні можлива коротка пауза диму. ⌂ з глибокого зуму на тестовій машині займає ~1.8 с (2 коміти). Здешевити растеризацію можна окремо, спростивши зовнішнє світіння країни
- Версіонування: `Style.css?v=20261002d` → `?v=20261002e` (index.html, mobile.html)
- Файли: `index.html`, `mobile.html`, `Style.css`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL не потрібен

### v3.41 (2026-10-02) — Кнопка закриття картки в червоному стилі
- Пряма вимога користувача (у два кроки): спершу червона рамка кнопки «×» бічної панелі меморіалу (`#cclose`), потім уся кнопка «в червоному стилі»
- Style.css, `#cclose` — стиль узгоджено з кнопкою «НАГОРОДИ» (`#awards-btn`, inline-стиль в index.html) на тій самій панелі:
  - фон `rgba(139,15,15,.82)`, колір «×» `#f5d0d0`, тінь `0 2px 8px rgba(139,0,0,.4)`
  - рамка яскравіша, ніж у «НАГОРОДИ»: `1px solid #e53935` (той самий червоний, що в помилках форм `.f-err`)
  - наведення: фон `rgba(30,0,0,1)` (як у «НАГОРОДИ»), рамка `#ff5252`, «×» білий, тінь `0 3px 14px rgba(139,0,0,.6)`; поворот/масштаб збережено
- `mobile.css` перевизначає лише розмір/позицію `#cclose`, тож червоний стиль діє і в mobile.html
- Перевірено в headless Chrome (1920×937): обчислені фон, рамка, колір і тінь відповідають заданим у звичайному стані й при наведенні; клік закриває картку; 0 помилок консолі
- Версіонування: `Style.css?v=20261002b` → `?v=20261002d` (index.html, mobile.html)
- Файли: `Style.css`, `index.html`, `mobile.html` (лише версія CSS)

### v3.40 (2026-10-02) — Фікс: реклама партнерів, соцпанель і годинник лягали поверх опису загиблого на телефоні
- Скарга користувача (скриншот з iPhone, index.html): над відкритою карткою видно блок «Українська Діаспора», а соцпанель закриває рядок опису. Годинник `#kyiv-clock` теж був поверх картки
- **Причина 1 — z-index:** на телефоні `#card` займає весь екран, але має z-index 800. Партнери мають 1580 (inline при `pointer:coarse`), соцпанель — 1000, годинник — 890
- **Причина 2 — порядок init:** ховати ці оверлеї мали `_partnersHide()`/`_partnersShow()`, але вони визначались наприкінці init (після прелоадера). Посилання поста `/memorial/{slug}` (зокрема з Facebook) перенаправляє на `/?open={slug}`, і картка відкривається вже на `DOMContentLoaded`, раніше за init. Тому `_partnersHide()` ще не існувала й мовчки пропускалась. Потім init виконував `window._cardOpen = false`, хоча картка була відкрита, і будь-який тап знову показував партнерів. При відкритті тапом на зірку все працювало, тому ваду не помічали
- **Причина 3:** годинника в списку прихованих не було взагалі. Ховати його inline-стилем не можна: `_updateClock()` (silence-module.js) щосекунди переписує його `display` і створює елемент із запізненням
- **Фікс:**
  - `_partnersHide`/`_partnersShow` перенесено в IIFE перед `openCard()` (index.html), тож будь-який шлях відкриття картки їх викликає. Скидання `_cardOpen=false` в init прибрано
  - Ховаємо тепер класом `body.zp-panel-open` замість inline-стилів. Клас ставлять картка, чат і інфо-попап, як і раніше
  - CSS-правило в Style.css ховає `#partners-layer`, `#social-bar` і `#kyiv-clock` (`visibility:hidden !important`) лише за тих умов, де картка на весь екран: `(pointer: coarse) and (max-width: 700px), (orientation: landscape) and (max-height: 400px)`. Поворот екрана обробляється автоматично. На десктопі (бічна панель) нічого не ховається — як і раніше
- `mobile.html` не зачеплено: там партнери й плаваюча соцпанель приховані через mobile.css, а картка-аркуш має z-index 1100, вищий за годинник
- Перевірено в headless Chrome (iPhone UA, 390×844, touch):
  - вхід за посиланням `/memorial/andrii-abolmasov-127`: партнер, соцпанель і годинник `hidden`, у їхніх точках зверху сама картка (`elementFromPoint`); після тапу всередині картки нічого не повертається; після закриття все знову видно; повторне відкриття тапом на зірку знову ховає
  - на десктопі (1440×900) усе видно, поведінка без змін
  - скриншоти телефона: опис читається повністю, 0 помилок консолі
  - сценарій повороту (скарга користувача про «логотип повертається після альбома»): портрет (картка тапом на зірку) → альбом → перезавантаження сторінки в альбомі (iOS так робить із важкими WebGL-сторінками при нестачі пам'яті; адреса `/memorial/…` веде через `/?open=`) → назад у портрет + тап — на всіх кроках приховано. На момент скарги на проді ще працював старий код: `Style.css?v=20261002` без цього правила, в `index.html` — inline-ховання і скидання `_cardOpen`
- Версіонування: `Style.css?v=20261002` → `?v=20261002b` (index.html, mobile.html)
- Файли: `index.html`, `Style.css`, `mobile.html` (лише версія CSS), `CLAUDE.md`, `SESSION_CHANGES.md`. SQL не потрібен

### v3.39 (2026-10-02) — Фікс: дим підвисав при наведенні курсора на точку загиблого (cursor на `#map-wrap`)
- Скарга користувача: у вільному просторі дим плавний, а в момент наведення на точку (і виходу з неї) коротко підвисає. Фікс v3.33 цієї причини не зачепив
- **Діагностика** — без змін у коді, за трейсом користувача `Temo_rec/Trace-20260918T025447.json` (прод) і живими CDP-замірами локально (Chrome 154, AMD Radeon 610M, D3D11):
  - Ланцюжок: `window mousemove` → rAF → `hit()` знаходить точку → `mw.style.cursor='pointer'` (index.html, обробник mousemove; при виході — `'grab'`)
  - `cursor` — успадковувана CSS-властивість. Тому Chrome перераховує стилі всіх нащадків `#map-wrap`: 1558/1561 елементів (717 `<path>` карти в `#svg-layer`, підписи міст у `#city-overlay`, UI). У трейсі користувача — рівно 22 таких перерахунки по 7.8–14.4 мс, решта 843 мали менше 10 елементів. Стек `ScheduleStyleRecalculation` вказує саме на рядки з `mw.style.cursor=`
  - Головна ціна — на GPU: після перерахунку Chrome **перемальовує весь композитний шар `#map-wrap` (1698×1104)**. Підтверджено через `LayerTree.paintCount`: 10 перемикань курсора дають 10 перемальовок, без перемикань — 0. GPU-растеризація тайлів (`RendererRasterWorker`) зросла з 181 до 3401 мс за 6 с, окремі задачі тривали до 200 мс. GPU і так зайнятий ~78% (дим + зірки), тож кадри не встигають: rAF стоїть 160–285 мс, FPS падає з ~46 до ~19
  - Чому у вільному просторі плавно: там JS записує те саме значення (`cursor='grab'`), а такий запис Chrome ігнорує
  - Ізоляцією виключено: тултіп (його поява/зникнення окремо — 0 впливу), `hit()`, `people.filter`, forced layout, дим (`script.js` і `ghost-faces.js` у mousemove лише зберігають координати)
- **Фікс** (лише CSS, Style.css поруч із `#map-wrap`): `#svg-layer, #city-overlay { cursor: default; }`. Ці шари мають `pointer-events:none` і ніколи не є ціллю hit-test: у трейсі всі 448 hit-test повернули `DIV#map-wrap`, тож видимий курсор завжди береться з самого `#map-wrap`. Фіксоване значення лише обриває успадкування: їхні обчислені стилі не змінюються, піддерева не перераховуються і не перемальовуються. JS, події, тултіп, дим і SVG не змінювались. Фікс автоматично покриває також `.grabbing` (драг) і `.picking`
- **ДО → ПІСЛЯ** (той самий сценарій: 10 циклів вхід/вихід на точку id=140 + контрольний рух по вільному простору):
  - перерахунок стилів при вході/виході: 1558–1561 ел. / 7.0–12.9 мс → 26–29 ел. / 0.5–0.95 мс
  - кадри зі зміною курсора: медіана 22.7 мс, максимум 35.9 мс → медіана 18.7 мс, максимум 24.0 мс (решта — фоновий цикл зірок, як і в контрольній фазі)
  - паузи rAF (дим) у фазі наведення: p95 183 мс, максимум 250 мс → p95 50 мс, максимум 83 мс (= контрольна фаза)
  - GPU у фазі наведення: 89%, найдовша задача 163 мс, 12 задач понад 90 мс → 79%, 85 мс, 0 (= контрольна фаза 80% / 81 мс)
- Функціонально перевірено: курсор `pointer` на точці, `grab` поза нею, `grabbing` під час драгу; ціль hit-test — `#map-wrap`; тултіп з правильним іменем; клік відкриває картку; скріншот до/після ідентичний; `mobile.html` (UA планшета) підхоплює правило; 0 нових помилок консолі
- Версіонування: `Style.css?v=20260920c` → `?v=20261002` (index.html, mobile.html)
- Помічено, не змінювалось (поза обсягом):
  - фоновий цикл зірок `_startCanvasLoop` — медіана 13.8 мс на кадр малювання, ~10 разів/с
  - `_glowCache` у `drawDotFX` не враховує alpha в ключі, тому посилене світіння наведеної зірки майже не видно
  - `#bottom-blocks` перемальовується щокадру через CSS-анімацію `.sr-link--highlight`
- Публічний журнал оновлень `update_v/uddate_history.html` (маршрут `/update_v/uddate_history.html`): на запит користувача фікс опубліковано як **v3.33.1**. Публічна нумерація — окрема від внутрішньої, номер обирає користувач. Новий запис стоїть першим у масиві `entries`, отже автоматично отримує позначку «поточна версія». Вручну оновлено картки «Поточна версія» (`v3.33.1`), «Останнє оновлення» і дату у футері (`02.10.2026`). Внутрішні v3.34–v3.38 у публічний журнал не вносились
- Обмеження макета журналу: картки верхнього ряду ростуть угору, і над лінією є лише ~360 px. Задовгий текст у розгорнутому стані обрізає теги згори, тому текст запису скорочено. Перевірено в headless Chrome: усі розгорнуті картки верхнього ряду вміщуються (верх ≥ 30 px від краю), 0 помилок консолі
- Файли: `Style.css`, `index.html`, `mobile.html` (лише версія CSS), `update_v/uddate_history.html`, `CLAUDE.md`, `SESSION_CHANGES.md`. SQL не потрібен

### v3.38 (2026-09-24) — Воронка замовлення тарифу: demo-модалка → реальна форма заявки (лід)
- Продовження v3.37: користувач попросив довести воронку до реального ліда — форма заявки замість demo-модалки "оплата ще в розробці", без платіжної інтеграції (свідомо відкладена)
- Нова таблиця `pricing_leads` (Paskal.py, `init_db()`, той самий `CREATE TABLE IF NOT EXISTS` патерн, що `partners`) — plan/price_label/name/contact/memorial_id/comment/status(new|contacted|closed)/ip/created_at
- Новий публічний `POST /api/pricing-lead`: rate limit `_rl.check(f"pricinglead:{ip}", 3, 3600)` (той самий шаблон, що `/api/like`), валідація плану проти allowlist, `_sanitize_text()` на name/comment, INSERT в БД — лід зберігається незалежно від того, чи вдасться надіслати email-сповіщення (обгорнуто в окремий `try/except`, не блокує успішну відповідь)
- Email-сповіщення адміну — перевикористано вже готову `_send_email()` (Paskal.py, не нова функція), нова адреса-константа `ADMIN_NOTIFY_EMAIL` (env-змінна з фолбеком на `treetex.g.ads@gmail.com`, додано в `.env.example`)
- Нові адмінські ендпоінти: `GET /api/admin/pricing-leads` (`require_moder`), `PUT /api/admin/pricing-lead/{id}` (зміна статусу), `DELETE /api/admin/pricing-lead/{id}` — той самий CRUD-патерн, що партнери
- **`pricing/index.html`**: demo-модалка замінена на реальну форму (імʼя, email/телефон, коментар) всередині того самого overlay — client-side валідація (email regex + телефон pattern) перед `fetch POST`, успіх показує окремий екран підтвердження, помилка (включно з rate-limit 429) виводиться прямо у формі без закриття модалки. Заголовок модалки забарвлюється кольором обраного тарифу (`--tier` custom property, той самий механізм, що вже застосований до карток)
- **admin.html**: нова секція `sec-pricing` ("Заявки на тарифи") за точним зразком `sec-friends` — таблиця з фільтрами за статусом (Всі/Нові/У роботі/Закриті), бейдж-кольори статусу (`badge by/bb/bg`, ті самі класи що вже є в проєкті), select для зміни статусу, лічильник нових заявок у nav-item (`.nb` бейдж, той самий патерн, що вже є для чату). Live-оновлення списку — **не BroadcastChannel** (заявка й адмінка зазвичай на різних пристроях/сесіях різних людей, той канал не спрацював би) — простий `setInterval` polling кожні 30с, поки секція відкрита (`_plPollStart()`/`_plPollStop()`)
- Перевірено живим тестом: `POST /api/pricing-lead` через curl (успішний INSERT, підтверджено прямим SELECT з БД, коректна кирилиця/UTF-8), rate limit підтверджено (3 заявки пройшли, 4-та отримала 429 з тим самим повідомленням, показаним користувачу у формі), живий CDP-тест на `/pricing/` (форма відкривається з кольором тарифу, невдалий сабміт через rate-limit показує помилку у формі без закриття, успішний сабміт показує екран підтвердження), адмінська таблиця перевірена мокнутими даними (обхід реального логіну — та сама безпечна техніка, що вже застосовувалась раніше в проєкті): 3 рядки, лічильники статусів коректні, бейдж-класи точно відповідають статусам. 0 помилок консолі на всіх етапах. Тестові записи прибрані з БД після перевірки
- Файли: `Paskal.py`, `pricing/index.html`, `admin.html`, `.env.example`
- **Дія користувача**: на проді таблиця `pricing_leads` створиться автоматично при рестарті backend (`init_db()`); опційно — задати `ADMIN_NOTIFY_EMAIL` в `.env` на проді, якщо потрібна інша адреса ніж дефолтна
- **Продовження в тому ж заході**: пряма вимога користувача — змінити загальний фон сторінки на світліший, "приємніший замовнику" (уточнено через AskUserQuestion: м'який теплий кремово-білий, не синьо-блакитний)
- Повна інверсія теми `pricing/index.html` з темної (navy/gold/cyan) на світлу — перероблені всі кольорові токени `:root` (`--navy-0/1/2` → кремово-білі відтінки `#faf7f2/#f3ede2/#ffffff`, `--ink` → темний текст `#2a2620`, `--muted`/`--muted-dim` → теплі сірі, `--gold`/`--cyan` → трохи приглушені для кращого контрасту на світлому фоні), нові допоміжні `--card-bg`/`--card-border` для карток/форм. Кольори тарифів (bronze/silver/gold/platinum) підкориговані на насиченіші відтінки — на світлому фоні початкові пастельні тони (особливо silver) були б малопомітні
- Зоряний фоновий ефект (`.stars`) — білі цятки на темному фоні замінені на теплі золотисті (колір `--gold`, менша базова опасність) — білі на світлому фоні були б невидимі
- Пройдено кожен блок сторінки послідовно: topbar/`.eyebrow`, картки тарифів (фон/рамка/тінь — раніше напівпрозорі білі шари на темному, тепер напівпрозорі кольорові на `--card-bg`), `.plan-features`, FAQ-акордеон, footer, модалка підтвердження і форма заявки (фон, рамки полів, колір помилки з яскраво-рожевого на приглушений червоний, доречніший для світлого тла)
- Перевірено живим CDP-тестом: `getComputedStyle(body).backgroundColor` = `rgb(250,247,242)` (підтверджує теплий кремовий фон), скріншоти desktop/footer/модалка підтверджують контрастність тексту, читабельність карток і форми на новому фоні. 0 помилок консолі
- Файли (додатково): `pricing/index.html`
- **Ще один раунд у тому ж заході**: користувач попросив повернути темну зоряну тему назад ("нет верни темный звездный фон") і додати живіший космічний ефект — падаючі зірки та рухомий Чумацький Шлях
- Повна інверсія назад: `:root` повернутий до оригінальної темної палітри (navy/gold/cyan), усі точкові світлі override (`--cyan-deep`, `--gold-soft`, `rgba(226,161,0,...)`, `rgba(40,32,16,...)`, кремові фони форми/модалки) відкочені на темні відповідники — пройдено кожен блок сторінки (topbar/eyebrow/картки/FAQ/footer/модалка/форма) точково
- Новий `.milky-way` — діагональна смуга з 8 розсіяних `radial-gradient`-точок + м'який лінійний light-band, `background-size` кожного шару 260×260px (велика площа тайлу — ключова деталь: перша спроба з 3-5px тайлом дала небажаний щільний муаровий/сітчастий артефакт замість розсіяного зоряного пилу), повільний `animation: milkyDrift 140s linear infinite` — усі 8 шарів рухаються синхронно, зберігаючи єдиний патерн
- Нові `.shooting-star` (метеори) — 6 штук, `js` генерує випадкову стартову позицію (верхня половина екрана), кут падіння (25-45°), довжину шляху, тривалість (2.5-5с) і затримку (0-14с) для кожного, щоб не з'являлись синхронно. Технічна деталь: 3-рівнева вкладена структура (`.shooting-star` — позиція → `.spin` — статичний `rotate()` під кут польоту → `.trail` — сама анімована точка з хвостом на `::before`) — необхідна, бо `rotate()` і `translate()`-анімація в keyframes конфліктують, якщо обидва пишуть в один `transform` на тому самому елементі
- Перевірено живим CDP-тестом: `getComputedStyle(body).backgroundColor` = `rgb(4,6,15)` (точний оригінальний `#04060f`), `.milky-way` `background-position` підтверджено змінюється з часом (рух), 6 `.shooting-star`/`.trail` елементів з коректною анімацією `shoot`, скріншоти до і після виправлення щільності тайлу підтверджують перехід від муарового артефакту до чистого розсіяного зоряного поля. 0 помилок консолі
- **Знайдений і виправлений баг у тому ж заході**: користувач повідомив, що метеори летять вгору замість вниз. Причина — неправильна формула кута повороту `rot = 180 - angle` (розрахунок не врахував, що в CSS вісь Y росте вниз, а `rotate()` обертає за годинниковою стрілкою для позитивних значень; ця комбінація давала протилежний до задуманого підсумковий вектор руху). Виправлено на `rot = -angle` — перевірено прямим розрахунком вектора (обертання базового напрямку руху `(-1,0)` на `-angle` дає `(-cos(angle), sin(angle))`, тобто вниз-вліво в CSS-координатах) і підтверджено живим CDP-тестом через реальні `getBoundingClientRect()` координати до/після (не просто читання `transform`-матриці) — `deltaY:+250px` (рух вниз), `deltaX:-274px` (рух вліво)
- **Ще один раунд у тому ж заході**: користувач повідомив про другий баг — хвіст комети опинявся ПОПЕРЕДУ напрямку руху замість позаду, і нагадав про пропущену раніше вимогу — декоративна планета типу Сатурн на фоні
- **Фікс хвоста**: `.trail::before` (сам хвіст) малювався через `right:0` — тобто в тому самому напрямку, куди рухається голова (вона рухається по від'ємному X, тобто вліво; хвіст, намальований "справа від точки", насправді опинявся спереду). Виправлено на `left:0` (хвіст тепер тягнеться праворуч від голови — назустріч напрямку руху, тобто позаду) + градієнт кольору розвернутий (від суцільного біля голови до прозорого на кінчику, замість навпаки)
- **Нова декоративна планета «Сатурн»**: SVG (куля з радіальним градієнтом `#ffe9b0→#ffc01e→#b3780a` + два еліптичних півкільця — заднє блакитне через `clip-path` позаду кулі, переднє тепле поверх неї, для реалістичного ефекту кільця навколо планети), розміщена у правому верхньому куті `.stage`, повільна плаваюча анімація `saturnFloat` (22с, легкий вертикальний дрейф + нахил), `opacity:.5` щоб не відволікати від контенту, зменшена на мобільних (`max-width:760px`)
- Перевірено живим CDP-тестом: Сатурн існує в DOM, видимий (`opacity:0.5`), анімація активна; хвіст комети перевірений через `getComputedStyle(::before)` (`left:0px, right:-88px` — підтверджує напрямок тягнення) і через реальні координати руху голови (`travelingDownLeft:true`); скріншот (повний і кадрований) підтверджує коректний вигляд планети з кільцем, що проходить і позаду, і попереду кулі. 0 помилок консолі
- **Ще один раунд у тому ж заході**: користувач надіслав HTML/CSS готового компонента з Uiverse.io (`ElSombrero2/tricky-robin-67`) — 3D flip-картка рецепта з обертовою неоновою рамкою на зворотній стороні — з проханням застосувати цей стиль до картки Platinum
- Оригінал (`.card`/`.content`/`.front`/`.back` — повне перевертання картки з фото-заглушкою спереду і "Hover Me" ззаду) прямо не підходив — тарифна картка Platinum має список переваг/ціну/кнопку, які б зникли при flip. Уточнено через AskUserQuestion: зворотна сторона отримує власну кнопку "Обрати Platinum", щоб CTA лишався доступним з обох сторін
- Нова `.plan-flip` — обгортка з `perspective`, застосована ЛИШЕ до картки Platinum (Bronze/Silver/Gold не зачеплені — підтверджено `otherCardsCount:3` в тесті). На `hover` картка обертається `rotateY(180deg)` (`transition .6s`), зворотна сторона (`.plan-back`) — новий блок з короною (SVG), фразою "Найвища турбота про памʼять", коротким описом і власною кнопкою "Обрати Platinum". Обертова неонова смуга з оригіналу (`.back::before`, `animation:rotation_481`) перенесена як `.plan-back::before`/`platinumSpin` з кольором переведеним на платиновий (`var(--platinum)` замість оригінального `#ff9966`)
- На тач-пристроях (`@media (pointer:coarse)`) hover недоступний — `.plan-back` приховано повністю, flip не спрацьовує, показується лише звичайний front-вигляд (той самий підхід, що вже застосований для `.zp-hint` в основному сайті — CLAUDE.md v3.4)
- JS-обробник кліку на `.plan-cta` не змінювався — вже глобальний `querySelectorAll('.plan-cta')` і `btn.closest('.plan')` автоматично підхопили другу кнопку на back-стороні (вона теж вкладена в `.plan[data-tier="platinum"]`)
- Перевірено живим CDP-тестом: структура підтверджена (`flipExists`/`planExists`/`backExists`/`frontCtaExists`/`backCtaExists` — усі `true`), обчислена `transform`-матриця після симульованого hover підтверджує реальний поворот на 180° (`matrix3d(-1,0,0,...,-1,...)`), клік на кнопку зворотної сторони відкрив модалку з правильними даними ("Platinum — 1999 ₴"), скріншоти до/після hover підтверджують коректний вигляд і відсутність регресій на інших картках. 0 помилок консолі
- **Знайдений і виправлений баг у тому ж заході**: користувач показав скріншот — картка Platinum виявилась нижчою за сусідні (Bronze/Silver/Gold мають однакову висоту завдяки `align-items:stretch` на grid-контейнері `.plans`, Platinum виглядала обрізаною). Причина — новий проміжний контейнер `.plan-flip` (доданий для 3D-перспективи) сам не мав `display:flex`/розмірних властивостей, тому grid розтягував лише його, а вкладена `.plan` всередині лишалась природної висоти, не успадковуючи розтягнуту висоту батька
- **Фікс**: `.plan-flip{display:flex}` + `.plan-flip .plan{width:100%}` — тепер розтягування grid передається крізь обгортку до самої картки. Перевірено живим CDP-тестом через реальні `getBoundingClientRect()` усіх 4 карток: Bronze/Silver/Platinum тепер мають ідентичну `height:525.625px` і однаковий `top`; Gold трохи більша через навмисний ефект виділення (`.featured{transform:scale(1.035)}`), що не є регресією. 0 помилок консолі
- **Ще один раунд у тому ж заході**: користувач повідомив, що кнопка "Обрати" на лицевій стороні Platinum стоїть не на одному рівні з кнопками інших карток. Причина — `.plan-desc` Platinum мав довший текст ("Максимальна турбота про памʼять — з особистою підтримкою"), що займав 3 рядки (`58.5px` висоти) замість 2 (`~39px`) як в решти карток — `min-height:34px` на `.plan-desc` розрахований під короткі описи, не покривав цей випадок
- **Фікс**: скорочено текст на "Максимальна турбота — з особистою підтримкою" (без втрати сенсу) — тепер вкладається у 2 рядки як і всі інші описи. Перевірено живим CDP-тестом через реальні координати кнопок: `ctaTop` Bronze/Silver/Platinum тепер ідентичний (`691.53px`), Gold трохи вищий через той самий навмисний `scale`-ефект виділення
- **Ще один раунд у тому ж заході**: користувач попросив повністю прибрати декоративну планету «Сатурн» — видалено CSS (`.saturn`/`.saturn svg`/`@keyframes saturnFloat`/мобільний override) і HTML (SVG-розмітка кулі+кілець у `.stage`) повністю. Зоряний фон (`.milky-way`/`.stars`/`.shooting-stars`) не чіпався
- Перевірено живим CDP-тестом: `document.querySelector('.saturn')` = `null` (елемент відсутній у DOM), скріншот підтверджує чистий правий верхній кут без планети, решта фону (зорі/Чумацький Шлях/метеори) і картки не зачеплені. 0 помилок консолі
- **Ще один раунд у тому ж заході**: користувач попросив вирівняти заголовок "Оберіть, як вшанувати памʼять" "як у книзі" — блок `.hero` має лишитись по центру сторінки, змінюється лише вирівнювання тексту всередині заголовка (уточнено через AskUserQuestion: по лівому краю)
- **Фікс**: `h1.head` отримав власний `text-align:left` (перебиває успадкований `text-align:center` з `.hero`, який лишається без змін — бейдж і підзаголовок і далі по центру), `text-wrap:balance` замінено на `text-wrap:pretty` (balance симетрично балансує ширину рядків під центроване вирівнювання — при лівому вирівнюванні це вже не мало сенсу)
- Перевірено живим CDP-тестом: `getComputedStyle(h1).textAlign` = `"left"`, `.hero` як контейнер лишився по центру viewport (перевірено координатами), скріншот підтверджує книжковий вигляд заголовка з блоком на тому самому місці. 0 помилок консолі
- **Ще один раунд у тому ж заході — критичний баг**: користувач повідомив, що кнопка "Обрати Platinum" на ЗВОРОТНІЙ стороні картки (після 3D-перевертання) не клікабельна — курсор наведений на неї, але клік не спрацьовує
- **Глибока діагностика живим CDP-тестом** виявила справжню причину, відмінну від очікуваної: `document.elementFromPoint()` на реальних екранних координатах кнопки стабільно повертав або `null`, або сам контейнер `.plan-flip` — НІКОЛИ саму кнопку чи `.plan-back`, попри те що вона видима й `.click()` напряму на елементі спрацьовував без проблем. Це вказало на розрив саме в геометричному hit-testing, не в JS/CSS видимості
- **Корінна причина**: попередня структура мала ПОДВІЙНЕ вкладення 3D-трансформацій — `.plan` (сама картка) мала `transform-style:preserve-3d` І оберталась через `rotateY(180deg)` на hover, а `.plan-back` була НАЩАДКОМ цієї ж `.plan` з власним статичним `rotateY(180deg)` усередині вже поверненого 3D-простору батька. Вкладений 3D-контекст у вже трансформованому 3D-контексті — нестандартна конструкція, яку Chromium (принаймні в цій версії/GPU-конфігурації) рендерить візуально коректно, але неправильно роутить реальні вказівникові події для нащадків такого подвійного стеку
- **Фікс — плоска ієрархія (стандартний flip-card патерн)**: новий проміжний `.flip-inner` (замість `.plan` як контейнера обох сторін) — `.plan` (front) і `.plan-back` (back) стали СЕСТРАМИ всередині `.flip-inner`, а не батько-нащадок. Сам `.flip-inner` отримав `transform-style:preserve-3d` і `rotateY(180deg)` на hover; і `.plan`, і `.plan-back` — прості `backface-visibility:hidden` елементи без власного вкладеного 3D-простору. HTML-розмітка Platinum-картки перебудована відповідно (`.plan-flip > .flip-inner > (.plan, .plan-back)`)
- **Побічний фікс JS**: `btn.closest('.plan')` для визначення `data-tier` при кліку на `.plan-cta` більше не спрацьовував для back-кнопки (вона вже не нащадок `.plan`) — виправлено на `btn.closest('.plan')||btn.closest('.plan-flip')?.querySelector('.plan')` (пошук сестринського `.plan` через спільного батька `.plan-flip`, коли кнопка не всередині `.plan` напряму)
- Мобільний override (`@media (pointer:coarse)`) оновлено на новий селектор `.flip-inner` замість застарілого `.plan`
- Перевірено живим CDP-тестом (реалістичний сценарій — сторінка проскролена так, щоб картка була в центрі viewport, як у реального користувача, через `scrollIntoView({block:'center'})`, а не з самого верху сторінки): `document.elementFromPoint()` на координатах кнопки тепер коректно повертає `BUTTON.plan-cta` (`isBackBtn:true`), реальний CDP-клік (mousePressed/mouseReleased, не `.click()`) відкрив модалку з правильними даними (`"Platinum — 1999 ₴"`). Bronze/Silver/Gold не зачеплені. 0 помилок консолі
- Файли: `pricing/index.html`

### v3.37 (2026-09-24) — Нова публічна сторінка «Тарифи» (Bronze/Silver/Gold/Platinum), demo-дані
- Пряма вимога користувача: сторінка, де відвідувач одразу бачить 4 тарифні плани, порівнює переваги й розуміє, що обрати, з переходом до кроку "оплата" — поки що demo, без реальної платіжної інтеграції
- Новий каталог `pricing/index.html` — самодостатній HTML/CSS/JS (без залежності від Style.css), за тим самим патерном, що `promo/index.html` і `portfolio/index.html`: та сама navy/gold/cyan палітра, шрифти Unbounded+Manrope, зоряний фон, ідентичний topbar/footer (копірайт `© 2026 ТМ «ЗОРЯНА ПАМ'ЯТЬ»` з посиланням на `/portfolio/`) — обрано користувачем як "окрема маркетингова тема"
- `Paskal.py`: новий `StaticFiles` mount `/pricing` (той самий патерн, що `/promo`, `/portfolio`, `/update_v`)
- **Контент 4 тарифів** (demo, але спираються на реальні можливості платформи — не вигадані абстрактні фічі): Bronze (безкоштовно — базова картка, 1 фото, стандартна модерація 7-30 днів), Silver (299₴ одноразово — до 5 фото, відео, нагороди, розширений опис), Gold (799₴, позначено «Рекомендовано» — необмежена галерея, пріоритетне відображення на карті, вкладка «Спадщина памʼяті», бейдж підтвердженої сторінки), Platinum (1999₴ — персональний менеджер, друковані матеріали, індивідуальне оформлення картки). Прогресивне нарощення — кожен наступний план явно каже "Усе з {попередній}"
- **Дія кнопки "Обрати {план}"** — за рішенням користувача: demo-модалка підтвердження (не окрема checkout-сторінка), чесний текст "Оплата ще у розробці... дякуємо за інтерес" + кнопка "Написати нам" (`mailto:treetex.g.ads@gmail.com`). Жодного payment provider, форм чи запису вибору в БД — суто демонстрація потоку
- Посилання на нову сторінку додано в 3 місця: `promo/index.html` (topbar, поруч з копірайтом), `index.html` (`#site-rules` і `#bb-popup`, той самий патерн що вже є для `/how-to-add.html`), `mobile.html` (`#site-rules`)
- Новий i18n-ключ `pricing_nav` (секція `ui`, uk="Тарифи"/en="Pricing") — `migrations_i18n_pricing_nav.sql`; фолбек безпечний навіть без виконання міграції (`applyI18n()` не перезаписує `textContent`, якщо ключа немає в словнику — залишається статичний українською текст прямо в HTML)
- Перевірено живим CDP-тестом (headless Chrome, реальний GPU): 4 картки/4 кнопки знайдено, клік на Gold і Bronze відкриває модалку з правильним текстом («Gold — 799 ₴», «Bronze — Безкоштовно»), закриття коректне, мобільна сітка (375px) коректно одноколонкова, `/pricing/` віддає 200 через реальний сервер (не просто відкриття файлу напряму), 0 помилок консолі. Скріншоти desktop/модалка/mobile підтверджують візуальну відповідність стилю `promo/index.html`
- Файли: `pricing/index.html` (новий), `Paskal.py`, `promo/index.html`, `index.html`, `mobile.html`, нова `migrations_i18n_pricing_nav.sql`
- **Дія користувача**: виконати `migrations_i18n_pricing_nav.sql` в PhpMyAdmin (опційно — сторінка й посилання вже працюють без неї завдяки безпечному i18n-фолбеку)
- **Продовження в тому ж заході**: користувач попросив, щоб кожна картка виглядала кольором свого тарифу, а не лише мала маленький кольоровий індикатор біля назви
- **Фікс**: кожна `.plan` отримала CSS custom property `--tier` (bronze/silver/gold/platinum кольори з `:root`, вже існували для swatch-індикаторів), застосовану через `color-mix(in srgb, var(--tier) N%, ...)` до рамки картки, фонового градієнта, кольору ціни, кнопки (фон+рамка), галочок списку переваг і назви тарифу — не лише до маленького кружечка. Прибрано окремий `.plan-free` клас із захардкодженим зеленим кольором для Bronze (суперечило вимозі — Bronze тепер послідовно бронзовий скрізь, як і решта тарифів)
- Перевірено живим CDP-тестом: `getComputedStyle()` підтвердив різні обчислені кольори рамки/ціни/кнопки/галочок для кожного з 4 tier (bronze `rgb(200,138,74)`, silver `rgb(199,208,224)`, gold `rgb(255,192,30)`, platinum `rgb(201,168,255)`), скріншот підтверджує чітко відмінний вигляд кожної картки. 0 помилок консолі
- Файли (додатково): `pricing/index.html`

### v3.36 (2026-09-24) — Дим: рівний 30fps-лімітер + зменшений canvas (лише js/script.js)
- Продовження діагностики подвисань диму: живі виміри цієї сесії (headless Chrome з реальним апаратним GPU — AMD Radeon 610M, ANGLE/D3D11, не SwiftShader) підтвердили гіпотезу користувача — `script.js` не має жодного коду, залежного від hover/точок загиблих; базове GPU-навантаження ~83% (GPUTask ~2500ms/3000ms) присутнє завжди, з наведенням чи без
- Користувач запропонував 2 конкретні точкові фікси, обмежені лише `js/script.js` (адмінка/`window._fluidConfig`/`colors` не чіпались — жодних нових параметрів не додано)
- **Фікс 1 — рівний (drift-free) 30fps-лімітер**: `update()` раніше писав `_lastFrameTime = now` при кожному виконаному кроці — при реальному vsync-джиттері поріг `< TARGET_FRAME_MS` спрацьовував нерівно (то на другому rAF-тіку ~33ms, то на третьому ~50ms). Замінено на акумулятивний розклад — `_lastFrameTime += TARGET_FRAME_MS` (з запобіжником від "втечі в минуле" при лагах/фоновій вкладці: `if (now - _lastFrameTime > TARGET_FRAME_MS) _lastFrameTime = now`). `calcDeltaTime()`/фізика не чіпались — dt і далі рахується з реального `Date.now()`-інтервалу
- **Фікс 2 — зменшений розмір canvas**: новий множник `SMOKE_CANVAS_SCALE = 0.7` в `scaleByPixelRatio()` — `canvas.width/height` (drawingBuffer) тепер ×0.7 від попереднього розміру (площа ×0.49), CSS-розмір (`width:100%;height:100%`) не змінюється, буфер розтягується автоматично. Дим візуально розмитий by design (bloom+blur) — зменшення непомітне на око, підтверджено скріншотом до/після
- **Знайдено і виправлено реальний баг під час верифікації**: перша версія `SMOKE_CANVAS_SCALE` була оголошена як `const` поруч зі `scaleByPixelRatio()` (~рядок 2286, нижче за файлом) — але `resizeCanvas()` викликається СИНХРОННО на рядку 55 (задовго до цього), одразу під час першого виконання скрипта. `const`, оголошений нижче точки виконання, падав у Temporal Dead Zone → `ReferenceError: Cannot access 'SMOKE_CANVAS_SCALE' before initialization` при кожному завантаженні сторінки, fluid-цикл взагалі не стартував (canvas лишався default 300×150, весь дим був невидимий). Виправлено — константа перенесена перед рядком `resizeCanvas()` (до першого виклику)
- Версіонування піднято: `js/script.js?v=20260919` → `?v=20260924` (index.html, mobile.html)
- **Перевірено живими CDP-тестами** (headless Chrome з апаратним GPU, той самий метод що й у діагностиці): (1) canvas ratio підтверджено `0.699` (очікувано `0.700`) — Фікс 2 технічно працює точно; (2) Фікс 1 логічно коректний (підтверджено прямим читанням `_lastFrameTime` — зафіксовано послідовність з 5 ідеальних `33.3ms` кроків підряд, коли rAF-доставка браузера була регулярною), але на цій конкретній тестовій машині (вбудований GPU, вже перевантажений сумарним рендером усіх шарів — fluid+ghost-layer+canvas-layer) сама частота rAF-callback'ів іноді падає нижче 30fps під навантаженням (підтверджено незалежним виміром — навіть з fluid примусово поставленим на паузу, rAF rate ~34.5fps замість чистих 60fps на порожній сторінці) — throttle коректно обмежує максимум, але не може підняти частоту вище того, що браузер фізично доставляє; (3) пряме порівняння GPUTask до/після (canvas forced back to старого розміру в runtime vs новий 0.7×) дало статистично невиразну різницю (~2440ms vs ~2450ms на 3с вікні) — очікувано: `SIM_RESOLUTION`/`DYE_RESOLUTION`/`BLOOM_RESOLUTION`/`SUNRAYS_RESOLUTION` фіксовані константи, не залежать від `canvas.width/height` (підтверджено читанням `getResolution()`), тому Фікс 2 економить лише найбільший ОКРЕМИЙ прохід (`drawDisplay()`, fullscreen quad), а не симуляційні проходи, які й домінують у сумарному GPUTask-бюджеті на цій машині. 0 помилок консолі на всіх етапах, скріншот підтверджує відсутність візуальної втрати якості диму
- **Чесно зафіксовано для користувача**: обидва фікси технічно коректні й реалізовані як заплановано, але сумарний вимірюваний виграш на цій конкретній тестовій машині малий і в межах шуму — корінь залишкового навантаження сидить саме в `SIM_RESOLUTION`/`PRESSURE_ITERATIONS`/`BLOOM`/`SUNRAYS`, які користувач явно попросив поки не чіпати ("якщо цього не хватить — по замеру решим")
- Файли: `js/script.js`, `index.html`, `mobile.html` (версіонування)

### v3.35 (2026-09-20) — Preloader: зважений розрахунок прогресу замість фіксованих контрольних точок
- Пряма вимога користувача: візуал екрана завантаження (`#preloader`, spinner, progress bar, кольори, переходи) лишити 1:1 як є, але переробити розрахунок самих чисел прогресу — "детальніше, як і має бути"
- **Було**: `_setPL(0/15/20/75/88/94/97/100, ...)` — довільні контрольні точки, розкидані вручну між `await`-кроками init-послідовності, незалежно від реального обсягу/тривалості кожного кроку (наприклад, `/api/map-points` міг повертати і 100, і 10000+ записів — прогрес завжди стрибав на ту саму фіксовану величину)
- **Стало**: новий `_PL_WEIGHTS` (index.html: `{colors:8, device:4, statscities:10, mappoints:58, labels:15, render:5}`; mobile.html — той самий принцип, лише `mappoints`→`people`, бо mobile.html вантажить людей через пагінований `/api/people`, не `/api/map-points`) + `_plStep(key, label)` (додає вагу кроку до накопиченого `_plDone`, викликає `_setPL`) + `_plSub(key, frac, label)` (проміжний прогрес всередині ще не завершеного кроку, не мутує `_plDone`) — прогрес тепер рухається пропорційно вазі реально виконаної роботи, найважчий крок (список людей) отримує найбільшу частку (58%)
- **index.html**: `loadData()` — `/api/map-points` тепер має 2 точки виміру всередині одного кроку (`_plSub('mappoints', 0.5)` одразу як HTTP-заголовки прийшли, до `.json()`; `_plStep('mappoints', ...)` після парсингу відповіді) — раніше був один стрибок 20%→75% одразу після завершення запиту
- **mobile.html**: тут вже існувала окрема, точніша логіка — пагіноване завантаження `/api/people?page=N&limit=100` в циклі з розрахунком `page/totalPages` (не чіпалась структурно, лише перебазована на нову вагову шкалу через `_plSub('people', page/totalPages)` на кожній ітерації циклу, і `_plStep('people')` після завершення) — це вже сама по собі більш детальна метрика, ніж у index.html (реальна кількість завантажених сторінок, а не половина запиту)
- Рендер-хвіст (`renderCityLabels`+`initSVGBorders`) свідомо лишився одним фінальним кроком без внутрішнього поділу — синхронний, дешевий, підтверджено користувачем не розбивати
- `_setPL()` сама не змінювалась (сигнатура, clamp, оновлення DOM) — нова логіка лише інакше обчислює, яке число їй передати
- Перевірено живим CDP-тестом (headless Chrome, `MutationObserver` на `#preloader-bar`/`#preloader-pct` — перехоплення реальних змін DOM, не polling): **desktop** — послідовність `0→8→12→22→51→80→95→100`, монотонно зростає, найдовша пауза видима саме на найважчому кроці (22→51→80, map-points); **mobile** — плавна послідовність `8→12→22→27→32→…→80→100` (по 5% на кожну із ~12 сторінок `/api/people`) — суттєво детальніше і точніше, ніж старий стрибок 20%→75% одним кроком. 0 помилок консолі на обох файлах
- Побічно виявлено (НЕ виправлено, поза межами цього запиту): `LANG.applyI18n()` викликається вдруге в кінці init-послідовності index.html (рядок з коментарем "Повторний прохід — на випадок текстів, відрендерених компонентами вище") **після** того як preloader вже прихований і показує "Готово" — цей повторний прохід відкочує `#preloader-text` назад на `data-i18n="preload.loading"` через атрибут у розмітці. Невидимо для користувача (елемент вже `display:hidden`/opacity:0 на той момент), тому не займався без окремого підтвердження — обсяг цього запиту стосувався лише розрахунку прогресу, не i18n-логіки
- Файли: `index.html`, `mobile.html`

### v3.34 (2026-09-20) — «Друзі та партнери»: індивідуальна рамка блоку (увімкнення + колір) для кожного партнера окремо
- Пряма вимога користувача: можливість вмикати/вимикати рамку навколо блоку партнера і обирати її колір — окремо для кожного запису в списку партнерів, не глобальним налаштуванням
- Нові колонки `partners`: `border_enabled` TINYINT default `0`, `border_color` VARCHAR(20) default `'#ffffff'` — міграція через `ALTER TABLE` в `init_db()` (як і всі попередні міграції цієї таблиці — `caption_url` тощо), застосована напряму на dev-БД через pymysql під час розробки
- `Paskal.py`: `PartnerCreate`/`PartnerUpdate` розширені `border_enabled`/`border_color`; `POST/PUT /api/admin/partner` валідують колір через вже наявний `_HEX_COLOR_RE` (фолбек на `#ffffff` при некоректному форматі — той самий патерн, що вже застосований для `ghost_tint_color`)
- `admin.html`, модалка "Редагувати партнера": новий блок під основними полями — тумблер "Рамка блоку (індивідуально для цього партнера)" + `<input type="color">`, що з'являється лише коли тумблер увімкнено; `savePartner()` надсилає обидва нові поля
- `index.html`, `renderPartners()`: `border` блоку партнера тепер умовний — `1px solid {border_color}` коли `border_enabled`, інакше стара напівпрозора рамка за замовчуванням (`rgba(255,255,255,.1)`) — без регресії для вже існуючих партнерів
- `mobile.html`, `renderPartners()`: той самий принцип — раніше рамки не було взагалі (`border` не задавався), тепер умовний `border`+`padding`, коли `border_enabled` вимкнено — вигляд без змін (padding:0, border:none)
- Перевірено живим CDP-тестом (headless Chrome, raw WebSocket): увімкнена рамка кольору `#ff3355` на тестовому партнері дала коректний inline та computed `border` на реальній сторінці, скріншот підтверджує видиму кольорову обвідку навколо блоку "Українська Діаспора"; після перевірки тестове значення повернуто на дефолт (`border_enabled=0`) — вигляд прод-сайту не змінився без явної дії адміна. mobile.html свідомо не показує `#partners-layer` взагалі (`mobile.css: display:none !important` — вже задокументована в CLAUDE.md поведінка, не регресія цієї зміни)
- **Продовження в тому ж заході — світіння рамки з регульованою силою**: пряма вимога користувача додати свічення навколо рамки і окремий регулятор його сили
- Нова колонка `partners.border_glow` (INT, default `40`, діапазон 0-100) — та сама `ALTER TABLE` міграція в `init_db()`, серверний clamp `max(0,min(100,...))` в обох ендпоінтах (`POST`/`PUT /api/admin/partner`)
- Реалізація світіння — через `box-shadow` (colored glow), додається ДРУГИМ шаром до вже наявної тіні блоку (`0 4px 18px rgba(0,0,0,.45)`), а не замінює її: `blur = glow*0.3px`, `spread = glow*0.08px`, `alpha = 0.15 + glow*0.0075` (0%→ледь помітно, 100%→насичене світіння). Колір світіння — той самий `border_color`, конвертований з hex в rgb через новий `_hexToRgb()` helper (index.html, mobile.html) — світіння завжди узгоджене з кольором рамки, не окремий пікер. Активне лише коли `border_enabled=1` і `border_glow>0`; на hover світіння підсилюється (×1.3 blur/spread, ×1.25 alpha) за тим самим патерном, що вже мав місце для звичайної тіні при наведенні
- `admin.html`: слайдер "Сила світіння" (0-100%, крок 5) доданий в той самий блок під тумблером рамки, під color-picker'ом — з'являється/ховається разом з рештою border-полів
- Перевірено живим CDP-тестом: `getComputedStyle(box).boxShadow` на тестовому партнері з `border_glow=85`, `border_color=#00e5ff` дав точний очікуваний другий шар `rgba(0,229,255,0.79) 0px 0px 26px 7px` — кадрований скріншот навколо блоку підтверджує чітко видиме бірюзове світіння навколо рамки. Тестові дані повернуто на дефолт після перевірки
- Файли: `Paskal.py`, `admin.html`, `index.html`, `mobile.html`
- **Дія користувача**: на проді обидві міграції (`border_enabled`/`border_color`/`border_glow`) виконаються автоматично при наступному рестарті backend-процесу (`init_db()`, try/except) — окремого SQL вручну не потрібно

### v3.33 (2026-09-18) — Фікс: дим підвисав при наведенні курсора на маркер (forced layout reflow)
- Користувач повідомив про підвисання диму саме при hover на точку загиблого на карті, надав Chrome DevTools Performance trace (67MB, 26.6с запису) для аналізу
- **Діагностика через CPU-профіль з трейсу** (парсинг `ProfileChunk`-подій, побудова self-time рейтингу по 79306 семплах): `get clientWidth` — 3.82% self-time, стек `resizeCanvas() (js/script.js:1666) ← update() (js/script.js:1635)`. `update()` — головний rAF-цикл WebGL fluid-симуляції диму, викликається щокадру (60 раз/сек)
- **Корінна причина**: `resizeCanvas()` читала `canvas.clientWidth`/`clientHeight` напряму щокадру — це forced synchronous layout read. Паралельно, в тому самому кадрі, обробник `mousemove` карти (index.html/mobile.html) при наведенні на маркер писав у DOM: `tip.style.left/top` (layout-тригерні властивості) + `tip.innerHTML` (зміна DOM-дерева). Ці записи "бруднили" layout — і наступне читання `clientWidth` змушувало браузер синхронно перерахувати layout прямо в гарячому rAF-циклі диму (layout thrashing). При нерухомому курсорі DOM не мінявся → `clientWidth` читався майже безкоштовно (звідси відсутність підвисань без hover)
- **Фікс 1** (`js/script.js`): нові module-scope `_cachedClientWidth`/`_cachedClientHeight`, ініціалізовані один раз при завантаженні й далі оновлювані ПОДІЄВО через `ResizeObserver` на `canvas` + `window resize`-listener — не читанням щокадру. `resizeCanvas()` тепер читає ці кешовані змінні замість `canvas.clientWidth`/`clientHeight` напряму
- **Фікс 2** (Style.css, index.html, mobile.html): позиціонування `#tip` (тултіп маркера) переведено з `style.left`/`style.top` (layout-тригерні) на `style.transform: translate()` (compositor-only, GPU, не викликає layout recalculation). `#tip` в Style.css отримав базові `left:0;top:0` (потрібно як точка відліку для transform)
- Обидва фікси **не змінюють видиму поведінку** — той самий результат (розмір canvas, позиція тултіпа), лише без зайвого forced reflow
- Перевірено живим CDP-тестом (headless Chrome, raw WebSocket без puppeteer — puppeteer не встановлений у проєкті): тултіп з'являється точно в очікуваній позиції (`translate(816px,286px)` = `sx+16,sy-10` з точністю ~1-2px), `display:block/none` перемикається коректно, `#fluid` canvas коректно розмірюється при завантаженні (1384×805, відповідає viewport), скріншот підтверджує відсутність візуальних регресій, 0 помилок консолі
- Версіонування піднято: `js/script.js?v=20260914` → `?v=20260918` (index.html, mobile.html) — форсує оновлення кешу браузера
- Файли: `js/script.js`, `Style.css`, `index.html`, `mobile.html`
- **Дія користувача**: після заливки на прод — оцінити суб'єктивну плавність диму при наведенні на маркери у щільних зонах (найбільш показовий сценарій з першоджерела проблеми)
- **Продовження в тому ж заході**: користувач повідомив про регресію від фіксу вище — при наведенні на маркер тултіп на мить (мікросекунди) з'являвся в лівому верхньому куті екрана, потім стрибав на правильне місце
- **Причина**: `#tip` мав спільну `animation: fadeIn .15s var(--ease)` (Style.css), а `@keyframes fadeIn` анімує `transform: scale(.95)→scale(1)`. CSS keyframes-анімація на короткий час перебивала inline `style.transform: translate(...)`, який JS щойно встановив для позиції тултіпа (сама зміна з фіксу вище) — ефективний transform на перших кадрах анімації відкочувався до `scale()` без `translate`, тобто до базових `left:0;top:0` — звідси видимий стрибок з кута
- **Фікс**: нова окрема `@keyframes tipFadeIn { from{opacity:0} to{opacity:1} }` (лише opacity, без transform) — `#tip` тепер використовує `animation: tipFadeIn` замість спільної `fadeIn`. Спільна `fadeIn` (з transform:scale) не чіпалась — лишається для інших елементів (модалки, картки), де transform-анімація не конфліктує з positioning
- Перевірено живим CDP-тестом (rAF-семплер `getBoundingClientRect()` на кожному кадрі перші ~500мс після `display:none→block`): 0 кадрів з позицією в лівому верхньому куті, включно з найпершим відрендереним кадром; `getComputedStyle(tip).animationName==='tipFadeIn'` підтверджено; плавна поява (opacity fade) збережена; inline `transform:translate()` не перебивається
- Файли (додатково): `Style.css`

### v3.32 (2026-09-16) — «Привиди в диму»: рівномірна (constant-rate) fade-анімація замість експоненціального згладжування
- **Пряма вимога користувача**: "должно работать плавное появление и затухание при смене"
- **Причина**: попередня логіка `currentOpacity += (target-current)*speed` — експоненціальне
  згладжування, суб'єктивно нерівномірне: швидко на старті (великий залишок × speed), потім
  прогресивно сповільнюється й "зависає" біля цілі (малий залишок × speed теж малий) —
  саме той "ривок" ефект, на який скаржився користувач
- **Реалізація** (`js/ghost-faces.js`, `tick()`): замінено на РІВНОМІРНУ (constant-rate)
  анімацію — `currentOpacity` рухається до `targetOpacity` з фіксованою швидкістю (частка
  opacity за секунду, не за кадр — новий `dt` рахується з `performance.now()`, незалежно
  від частоти кадрів). `cfg.fade_in_speed`/`cfg.fade_out_speed` (вже регульовані через
  адмінку) лишились тими самими одиницями й дефолтами — просто застосовані як стала
  швидкість, а не коефіцієнт спадної кривої
- **Знайдено і виправлено 2 реальних баги під час розробки** (обидва спіймані ізольованим
  Node.js unit-тестом самої математики, до живого браузерного тестування):
  1. `ghost._lastTickTs: 0` як маркер "ще не було тика" — класична JS pitfall, `0` є falsy,
     тому перевірка `if (ghost._lastTickTs)` хибно трактувала легітимний timestamp `0` як
     "ще не ініціалізовано" на кожному наступному тику, весь час скидаючи `dt` в 0. Виправлено
     на явний sentinel `-1` + порівняння `>= 0`
  2. Умова `if (Math.abs(diff) <= maxStep || maxStep <= 0)` — коли `maxStep=0` (перший кадр
     після старту/паузи, `dt` ще не визначено), помилково трактувалось як "ціль вже
     досягнута" й миттєво телепортувало `currentOpacity` до `targetOpacity` за один кадр
     замість плавного руху. Виправлено: `maxStep=0` тепер означає "не рухаємось у цьому
     кадрі", не "готово"
- Перевірено: (1) ізольований Node.js unit-тест тієї самої формули — підтвердив ідеально
  рівний крок (`min=max=0.011952` на кожному проміжному кадрі) при дефолтному
  `fade_in_speed=0.06`, досягнення цілі за ~800мс; (2) живий CDP-тест на реальному сайті
  (форсований стабільно високий target через тимчасове збільшення `reveal_threshold_px`/
  `mouse_recency_threshold_ms`, щоб ізолювати саме fade-математику від природної
  мінливості курсора/диму) — підтвердив константний крок `0.01200` між послідовними
  замірами, коли ціль реально залишалась вище поточного значення. 0 помилок консолі
- Файли: `js/ghost-faces.js`, `index.html`, `mobile.html` (версіонування `?v=`)

### v3.31 (2026-09-16) — «Привиди в диму»: колір і прозорість тонування силуету — регульовані через адмінку
- Продовження v3.30: тонування силуету (`#e8f4ff`, захардкожене в v3.30 для вирішення
  проблеми "чорний SVG невидимий на mix-blend-mode:screen") тепер повністю налаштовується
  — за прямим запитом користувача ("добавь выбор цвета и его прозрачность")
- **Реалізація** (`js/ghost-faces.js`):
  - Переюзано вже наявне (але не задіяне з моменту первинного ТЗ) поле `cfg.tint_color` —
    дефолт змінено з `""` на `"#e8f4ff"`. Новий `cfg.tint_opacity` (0-1, дефолт `1`)
  - `readCfgFromColors()`: `ghost_tint_color` валідується проти `/^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/`
    (fallback на `#e8f4ff` при некоректному форматі — значення йде напряму в
    `ctx.fillStyle`, невалідний рядок там не є діркою в безпеці, але захист від "порожнього"
    рендеру). `ghost_tint_opacity` — parseFloat з явною перевіркою `isNaN` (не `||`, бо `0`
    — валідне значення "тонування вимкнено", яке `||` помилково замінило б на дефолт)
  - `rasterizeSvg()`: тонування тепер умовне (`if (cfg.tint_opacity > 0)`), сила регулюється
    через `ctx.globalAlpha` НА ЕТАПІ ЗАЛИВКИ (не через альфа-канал самого `fillStyle`) —
    при `source-in` це коректно змішує новий колір із уже намальованим під ним (тобто з
    оригінальним кольором SVG), а не просто применшує підсумкову альфу форми
  - Новий `reRasterizeCurrentGhost()` — перемальовує вже завантажений SVG з новими
    tint-налаштуваннями, НЕ обираючи нову картинку й не переміщуючи привида (на відміну
    від `relocateAndMaybeChangeImage(true)`). `applyGhostConfig()` порівнює
    `tint_color`/`tint_opacity` до і після `readCfgFromColors()` — якщо реально змінились,
    викликає перерисовку негайно, щоб live-preview в адмінці був миттєвим, а не чекав
    наступної природної зміни картинки (яка може статись через хвилини)
  - `admin.html`: новий блок "Тонування силуету" в розділі "Зовнішній вигляд" —
    `<input type="color">` (той самий патерн, що вже використовує `smoke_color_from/to`)
    + слайдер сили тонування. Обидва ключі додані в `applyGhostSettings()`
- Перевірено живим CDP-тестом (3 етапи, пряма перевірка через `getImageData` на реальному
  привиді, не лише читання cfg): (1) дефолт `#e8f4ff`/opacity=1 дав середній колір пікселів
  силуету `rgb(233,245,255)` — відповідає; (2) зміна на `#ff0000`/opacity=1 дала
  `rgb(255,13,0)` — миттєво, без зміни картинки/позиції, підтверджено на скріншоті (яскраво
  червоний силует); (3) той самий колір з `opacity=0` дав `rgb(15,13,0)` (майже чорний —
  оригінальний колір SVG без тонування) — підтверджує що `tint_opacity=0` коректно
  деградує до "кольору SVG як є". 0 помилок консолі
- Файли: `js/ghost-faces.js`, `admin.html`, `index.html`, `mobile.html` (версіонування `?v=`)

### v3.30 (2026-09-14) — «Привиди в диму»: підсвічена кромка силуету, курсор-залежна, кольору "як у диму"
- Новий чисто візуальний шар (Canvas2D, `js/ghost-faces.js`) поверх уже стабільно працюючої
  фізики зіткнення/примагнічування з v3.29 — **не чіпає `js/script.js`/WebGL взагалі**
- **Пряма вимога користувача**: розмита кромка привида кольору "як у диму", видима ЛИШЕ
  коли курсор над нею або поруч (~15px), і ЛИШЕ з того боку контуру, де курсор зараз (не
  по всьому контуру одразу) — "ніби дим облизує край"
- **Явні рішення користувача** (через AskUserQuestion): (1) точний контур по альфа-каналу
  SVG, не приближений bbox/овал; (2) незалежний генератор кольору в ghost-faces.js, не
  тягнути реальний колір диму з js/script.js (розвідка підтвердила що цей колір взагалі
  ніде не експортований — `pointers[i].color` лишається локальною змінною в js/script.js)
- **Реалізація** (усе в `js/ghost-faces.js`):
  - `extractContourPoints()` — одноразовий (при зміні SVG, не щокадру) прохід по
    альфа-каналу вже наявного `ghost.offscreen.canvas` (той самий, що дає GL-маску для
    фізики) через `getImageData`, з прорідженням (крок 3px). Для кожної межової точки
    рахує нормаль назовні (градієнт альфи по сусідах — той самий прийом, що вже
    застосований в `obstacleAttractShader`, js/script.js). Координати збережені
    нормалізованими (0..1) — не залежать від поточної позиції/розміру відмальовки.
    try/catch навколо `getImageData` (SecurityError на tainted canvas) — деградує до
    порожнього контуру, решта модуля продовжує працювати
  - `smokeLikeColor(now)` — плавний циклічний дрейф відтінку в синьо-блакитному спектрі
    (lerp між випадковими hue раз на ~3.2с, без різких стрибків), незалежний від
    справжнього кольору диму
  - `renderEdgeHighlight()` — для кожної точки контуру в межах `edge_highlight_radius_px`
    від курсора рахує силу підсвітки через степеневе згасання (`(1-dist/radius)^1.6`),
    малює короткий blur-fill `arc()` цим кольором. Швидкий bbox-based early exit, коли
    курсор далеко — не гнати прохід по контуру щокадру без потреби
  - **Критичний фікс під час верифікації**: підсвітка кромки спочатку була вкладена
    всередину того самого `if (effectiveOpacity > 0.003)` блоку, що й сам силует —
    суперечило задуму ("кромка видна незалежно від того, чи проступив привид на очах").
    `render()` переписано: обчислення `dx/dy/dw/dh` винесено перед умовою, виклик
    `renderEdgeHighlight()` тепер безумовний (лише за `ghost.offscreen`), силует і
    dev-підпис лишились умовними як і раніше
  - Нові `cfg`-поля: `edge_highlight_enabled` (default true), `edge_highlight_radius_px`
    (15), `edge_highlight_width_px` (5), `edge_highlight_blur_px` (7),
    `edge_highlight_strength` (0.75) — читаються з `colors` (`ghost_edge_highlight_*`)
  - `admin.html`: нова секція слайдерів "Підсвічена кромка (курсор-залежна)" в блоці
    налаштувань привида, ключі додані в `applyGhostSettings()` для live-preview
- Перевірено живим CDP-тестом на реальному сайті — **пряма пиксельна перевірка**, не лише
  скріншоти (скріншоти виявились малоінформативними: колір кромки візуально зливається з
  фоновим димом схожого відтінку): monkey-patch `CanvasRenderingContext2D.prototype.arc`,
  відфільтрований саме по контексту `#ghost-layer`, підтвердив реальні виклики `arc()` з
  `fillStyle` у форматі `#хxxxxx` (не білий, не жовтий dev-колір) і `filter:"blur(7px)"`
  саме під час наведення курсора поруч з контуром — підсвітка технічно спрацьовує,
  прив'язана до курсора, з правильним кольором/розмиттям. 0 помилок консолі на всіх етапах
- Файли: `js/ghost-faces.js`, `admin.html`, `index.html`, `mobile.html` (версіонування `?v=`)
- **Продовження в тому ж заході**: користувач повідомив "нет контура" зі скріншотом, де
  ефект не було видно (курсор у той момент не був поруч з привидом, але подальша перевірка
  підтвердила реальну проблему). Живий CDP-тест підтвердив корінну причину: реальний
  альфа-контур конкретного тестового SVG відстоїть від краю його bounding box на **19px**
  (виміряно напряму — окремий скрипт розтеризував той самий SVG і знайшов
  `leftmostSolidX`/`rightmostSolidX` відносно країв канваса). Курсор, наведений туди, де
  силует видно "на око" (glow/blur розширюють видиму межу за межі жорсткого альфа-порога),
  опинявся ЗА межами дефолтного 15px-радіуса активації — тому підсвітка ніколи не
  спрацьовувала в найбільш інтуїтивній точці наведення
- **Фікс**: дефолт `edge_highlight_radius_px` збільшено з `15` до **`35`** (3 місця:
  `js/ghost-faces.js` cfg default + fallback у `readCfgFromColors()`, `admin.html` fallback
  слайдера) — компенсує типовий розрив між bbox і реальним контуром для більшості SVG-форм.
  Регульованість через адмінку лишилась незмінною (slider range 3-60px)
- Перевірено живим CDP-тестом: monkey-patch `CanvasRenderingContext2D.prototype.arc`,
  відфільтрований по контексту `#ghost-layer` і кольору (`fillStyle` у форматі `#xxxxxx`,
  не білий/жовтий), підтвердив **24 реальних виклики** відмальовки підсвітки саме в точці,
  куди природно навів би курсор користувач (візуальний лівий край bbox) — на відміну від 0
  викликів до фіксу. 0 помилок консолі
- Файли (додатково): `js/ghost-faces.js`, `admin.html`, `index.html`, `mobile.html`
  (версіонування)
- **Ще один раунд у тому ж заході**: користувач повідомив "свечения нет", уточнивши явно
  запитати чи в тому розділі адмінки правки — підтверджено (`sec-ghosts`/`nav.ghosts`,
  "Привиди в диму", жодної плутанини з іншим модулем). Глибока живі CDP-діагностика
  (перехоплення `getImageData` через `Page.addScriptToEvaluateOnNewDocument` — доведено, що
  `extractContourPoints` реально викликається одразу при завантаженні; незалежна симуляція
  того самого алгоритму на тому ж SVG дала 472 контурні точки; наведення курсора точно на
  незалежно обчислену реальну точку контуру дало **111 реальних викликів** відмальовки
  підсвітки) підтвердила: **фіча технічно повністю справна**. Проблема — суто у виразності:
  альфа підсвітки навіть у найкращій точці була лише ~0.06-0.13 з максимальних 0.75 (крута
  крива згасання `t^1.6` різко гасила силу вже за кілька px від центру радіуса), і колір
  (`hsl(*, 85%, 62%)`) був занадто близький до відтінку фонового диму — глазом практично
  нерозрізнювані на однаковому `mix-blend-mode:screen` шарі
- **Користувач обрав усі 4 запропоновані посилення одразу**:
  1. `smokeLikeColor()` — яскравість/насиченість HSL піднято з `62%/85%` до **`85%/95%`** —
     тепер майже біло-блакитне світіння, явно контрастніше до тьмяно-синього фонового диму
  2. Крива згасання альфи пом'якшена з `t^1.6` до **`t^0.7`** — сила підсвітки тепер значно
     швидше досягає максимуму (`edge_highlight_strength`) вже за помірної відстані від
     курсора до контуру, не лише у вузькому кільці впритул до самої лінії
  3. Дефолт `edge_highlight_strength` піднято з `0.75` до **`0.9`**
  4. Дефолт `edge_highlight_width_px` піднято з `5` до **`9`** (товщина мазка),
     `edge_highlight_blur_px` знижено з `7` до **`6`** (менше розмиття "з'їдає" товщину)
  5. Всі 5 значень вже були регульовані через адмінку з попереднього раунду — лише fallback
     у слайдерах `admin.html` синхронізовано з новими дефолтами коду
- Перевірено живим CDP-тестом (той самий метод — наведення на незалежно обчислену реальну
  точку контуру): **37 викликів**, `maxAlpha: 0.88` (майже впритул до нового `strength:0.9`
  — підтверджує що м'якша крива дійсно швидше виходить на максимум), реальний намальований
  колір `#b4e2fd` (яскравий біло-блакитний, не тьмяний відтінок) — на скріншоті чітко видно
  яскравий білястий спалах, помітно контрастніший за фоновий дим. 0 помилок консолі, рендер
  стабільний
- Файли (додатково): `js/ghost-faces.js`, `admin.html`, `index.html`, `mobile.html`
  (версіонування)
- **Ще один раунд у тому ж заході**: користувач надіслав скріншот — біле пляма
  дійсно з'явилась саме коли курсор був поруч з привидом (підтверджує що прив'язка до
  курсора працює), але виглядала як велика розмита клякса, а не тонка обвідка вздовж краю.
  Корінна причина — побічний ефект попереднього посилення: при радіусі активації 35px і
  кроці сканування контуру 3px одночасно активні десятки сусідніх точок контуру, кожна
  малює коло `width:9px` з `blur:6px` — при м'якій кривій згасання (`t^0.7`, майже плоска
  по всьому радіусу) усі ці кола перекриваються майже однаковою яскравістю і зливаються в
  суцільну пляму замість тонкої лінії
- **Фікс — звуження самого мазка, без втрати яскравості**: `edge_highlight_width_px`
  зменшено з `9` до **`3`**, `edge_highlight_blur_px` з `6` до **`3`** (3 місця кожен:
  cfg default, fallback у `readCfgFromColors()`, fallback слайдера в `admin.html`). Крива
  згасання відкоригована з `t^0.7` (занадто плоска — і спричиняла зливання) на **`t^1.1`**
  — компроміс між попередньою `1.6` (ефект майже не видно) і `0.7` (суцільна клякса):
  яскраво точно біля курсора, помітно тьмяніше вже за третину радіуса. Радіус активації
  (35px) і колір/strength з попереднього фіксу не чіпались — вони вирішували іншу, вже
  підтверджену проблему (розрив bbox/альфа-контур)
- Перевірено живим CDP-тестом (наведення на незалежно обчислену реальну точку контуру):
  **66 викликів**, `maxAlpha: 0.876` (яскравість збережена), на скріншоті тепер видно
  тонкий яскравий біло-блакитний штрих вздовж краю силуету, а не розмиту пляму. 0 помилок
  консолі, рендер стабільний
- Файли (додатково): `js/ghost-faces.js`, `admin.html`, `index.html`, `mobile.html`
  (версіонування)
- **Ще один раунд у тому ж заході**: користувач попросив "добавь в адмінку включи
  видимість svg". Уточнено через AskUserQuestion: мова не про вже наявний перемикач
  «Режим розробки» (форсує повну видимість силуету), а про окремий toggle саме для
  увімкнення/вимкнення підсвіченої кромки (обводки) — раніше `ghost_edge_highlight_enabled`
  керувався незручним numeric-слайдером 0/1 у загальному ряду параметрів кромки, без
  власного явного перемикача з написом Увімкнено/Вимкнено
- **Фікс**: новий `adminToggleGhostEdgeHighlight()` (admin.html) — точна копія патерна вже
  існуючих `adminToggleGhosts()`/`adminToggleGhostDevMode()` (миттєве збереження через
  `PUT /api/admin/colors/batch`, оновлення локального кеша `COLORS`, виклик
  `applyGhostSettings()` для live-preview). Новий візуальний toggle-блок вставлено в HTML
  між «Привиди в диму» (головний) і «Режим розробки» — той самий дизайн (анімований
  повзунок, кольоровий акцент — тут блакитний `#b4e2fd`, під колір самої кромки). Старий
  numeric-слайдер `gh-edgeen-v` (0/1) видалено з загального ряду параметрів кромки —
  замінений цим окремим перемикачем, решта 4 числових параметри кромки (радіус/товщина/
  розмиття/яскравість) лишились слайдерами як і раніше
- Перевірено живим CDP-тестом (з мокнутими `COLORS`/`fetch`, щоб обійти форму логіну —
  безпечний спосіб перевірити саме UI-логіку, не реальні креденшли адміна): toggle-елемент
  реально рендериться (`ghost-edgehl-tog`/`ghost-edgehl-lbl` знайдені в DOM), клік викликає
  `adminToggleGhostEdgeHighlight()`, напис коректно перемикається
  Увімкнено↔Вимкнено. 0 помилок консолі
- Файли: `admin.html`
- **КОРІННИЙ ФІКС у тому ж заході** (після ще одного повідомлення користувача — "кромку не
  видно, навіть приблизно не повторюється силует"): замість чергового точкового
  налаштування (радіус/колір/товщина — усе це вже перевірялось і технічно працювало)
  проведено чесний живий тест — реалістичний sweep курсором + прямий піксельний дамп
  canvas `#ghost-layer` саме в області bbox привида. **Знайдено справжню корінну причину,
  яка пояснює ВСІ невдачі попередніх 6+ раундів**: сам силует малювався **суцільно чорним
  кольором** (`RGB(0,0,0)`, підтверджено прямим `getImageData()` дампом — `avgColorOfNonZero:
  {r:0,g:0,b:0}` при цьому `maxAlpha:233`, тобто піксель реально малювався, просто чорним).
  `#ghost-layer` (як і `#fluid`) має CSS `mix-blend-mode:screen` — **у цьому режимі чорний
  колір (0,0,0) завжди повністю прозорий візуально, незалежно від alpha-каналу**. Тому сам
  силует не був видимий НІКОЛИ — навіть у `dev_mode` з форсованою повною яскравістю
  (`effectiveOpacity` бралась з `Math.max(...,0.9)`, але множилась на чорний колір = нуль
  видимого ефекту). Підсвічена кромка технічно завжди малювалась правильним кольором
  (підтверджено в попередніх раундах через `arc()` monkey-patch), але користувач не міг
  візуально співвіднести її з формою силуету, бо самого силуету не було видно взагалі —
  на екрані був лише фоновий дим + рідкісні спалахи кромки без видимого контексту форми
- **Фікс**: `rasterizeSvg()` — після `octx.drawImage(img,...)` додано тонування через
  `globalCompositeOperation:"source-in"` + `fillRect` кольором `#e8f4ff` (світлий
  блакитно-білий) — замінює RGB усіх непрозорих пікселів на світлий відтінок, зберігаючи
  точну форму/альфа-канал (потрібні і для GL-маски фізики, і для контуру кромки — обидва
  читають лише альфа-канал, тонування їх не зачіпає). Працює з БУДЬ-яким кольором
  вихідного SVG, не тільки чорним — уніфікує вигляд усіх завантажених силуетів
- Перевірено живим CDP-тестом: прямий піксельний дамп після фіксу дав `avgColorOfNonZero:
  {r:232,g:245,b:255}` (≈`#e8f5ff`, відповідає тонуючому кольору) — і, найголовніше,
  **скріншот вперше за всю сесію реально показує видимий світлий силует людини з маскою**
  над картою, а не порожнє місце. Наступний sweep-тест підтвердив: кромка тепер видима
  БІЛЯ реального контуру видимого силуету (не в порожньому просторі) — саме той ефект
  "дим облизує форму", який користувач просив із самого початку цього ланцюжка фіксів.
  0 помилок консолі, рендер стабільний
- Файли (додатково): `js/ghost-faces.js`, `index.html`, `mobile.html` (версіонування)

### v3.29 (2026-09-13) — «Привиди в диму»: фізична перешкода тепер безумовна (як стінки canvas), а не прив'язана до видимості
- Продовження роботи над модулем «Привиди в диму» з попередньої сесії — permeability-фізика
  (`divergenceShader`, `js/script.js`) вже технічно працювала, але користувач продовжував бачити,
  що дим візуально не «вдаряється» об SVG-привида
- **Діагностика на реальному сайті** (headless Chrome + CDP, `window._ghostDebugState()` +
  `window._fluidConfig` в консолі, не синтетичний ізольований тест): підтверджено, що вся
  фізична ланка технічно справна (`config.OBSTACLE_*` → `divergenceShader` → `step()` —
  усі зв'язки на місці, гонки немає), і гейт «мінімум 2 SVG» не є причиною (в БД рівно 2
  enabled-записи). Справжня причина: `computeVisibilityTarget()` — добуток
  `proximityFactor × smokeDensity × max_opacity`, де `smokeDensity` читає яскравість лише
  5×5px саме в точці привида (`sampleSmokeDensityAt`, js/ghost-faces.js). Дим рухливий і
  розсіюється, привид стоїть на фіксованій позиції — вікно «курсор поруч І дим фізично
  щільний саме тут» було вузьким і рідкісним, тому ефект був майже непомітний
- **Пряма вимога користувача**: «Дим повинен просто відштовхуватися так само, як і від
  країв браузера» — тобто перешкода має бути безумовною межею (як стінки canvas у
  `divergenceShader`, `if (vL.x < 0.0) { L = -C.x; }` і т.д. — завжди активні), а не
  ймовірнісним ефектом, залежним від курсора/яскравості
- **Фікс** (`js/ghost-faces.js`, `syncObstacleWithFluid()`): `OBSTACLE_ENABLED` тепер
  `true` завжди, коли модуль увімкнено і в привида є розмальована позиція
  (`ghost.offscreen` готовий) — незалежно від `ghost.currentOpacity` (візуальної
  прозорості силуету). `OBSTACLE_PERMEABILITY` більше не масштабується через
  `opacityFactor` — використовується стала `cfg.obstacle_permeability` напряму.
  Візуальне проявлення силуету (Canvas2D рендер, alpha/blur/glow) — окремий естетичний
  шар, ця зміна його не чіпає
- Перевірено живим CDP-тестом на реальному сайті (`127.0.0.1:8000`, не ізольований HTML):
  `OBSTACLE_ENABLED:true` стабільно тримається навіть при `currentOpacity:0` (привид
  невидимий на очах), рендер стабільний на скріншотах (жодного хаосу/артефактів, як у
  двох попередніх непрацюючих спробах цієї фічі), 0 помилок у консолі
- Додатково прибрано технічний борг попередньої сесії: видалено тестовий admin-акаунт
  `ghost_test_tmp@localhost.test` (id=11) з таблиці `users`
- Файли: `js/ghost-faces.js`
- Не чіпались: `js/script.js` (сам шейдер/`step()` — вже підтверджені робочими з
  попередньої сесії, зміна лише в тому, ЯКІ умови вмикають `OBSTACLE_ENABLED`)
- **Продовження в тому ж заході** (той самий день): користувач показав скріншот, де
  обструкція технічно активна (жовта dev-рамка), але видимого зіткнення з димом
  все одно не видно. Живий CDP-тест зі стійкою інʼєкцією диму прямо через
  прямокутник привида підтвердив другу, окрему причину: `pickRandomPosition()`
  (js/ghost-faces.js) обирала позицію будь-де у viewport, незалежно від того, де
  реально є фоновий дим — привид часто опинявся в майже порожніх від диму зонах
  (за межами контуру мапи), де фізично нема чого відштовхувати
- **Пряма вимога користувача**: «Ставить привида всегда над картой Украины»
- **Фікс**: новий `getMapScreenBBox()` (js/ghost-faces.js) — рахує реальний
  bbox намальованого контуру `#ukraine-svg` на екрані зараз (вибіркове
  сканування `<path>`, враховує поточний pan/zoom; викликається лише в момент
  relocate — раз на кілька секунд, не щокадру). `pickRandomPosition()`
  переписана: замість `window.innerWidth/innerHeight` з `%`-відступом тепер
  семплить координати всередині цього bbox (з невеликим внутрішнім inset).
  Фолбек на стару поведінку (весь viewport), якщо мапа з якоїсь причини
  недоступна — привид не зникає повністю
- Перевірено живим CDP-тестом: 2 послідовні relocate дали позиції строго
  всередині bbox мапи; стійка інʼєкція диму прямо в нову позицію дала чітко
  видимий вихор/деформацію потоку на краю прямокутника привида (не розмита
  фонова хмара, а окрема відштовхнута завихрена маса) — саме той ефект
  зіткнення, який просив користувач. 0 помилок консолі
- Файли (додатково): `js/ghost-faces.js`
- **Третій раунд у тому ж заході**: користувач повідомив, що після Ctrl+F5
  (примусове скидання кешу браузера) ефект все одно не видно взагалі. Причина
  виявилась подвійна:
  1. **Кеш браузера** — `<script src="js/ghost-faces.js?v=1">` (index.html,
     mobile.html) не оновлював версію жодного разу за 3 попередні заходи в
     цій сесії, попри переписування самого файлу — браузер користувача міг
     виконувати найпершу, ще непрацюючу версію коду. Версія піднята до `?v=4`
     (обидва файли); `js/script.js?v=20260419` теж піднято до `?v=20260913`
     (той самий шаблон, що вже задокументований у v3.24 для `chat-admin.js`)
  2. **Сама фізика занадто м'яка для сприйняття на око**: попередній підхід
     (лише множення `div *= permeability` всередині прямокутника) — це
     непряма, слабка дія на розподіл тиску, майже непомітна на фоні щільного
     фонового диму. Справжні стінки canvas (той самий шейдер, рядки 1061-1064)
     працюють інакше — підміняють сусідній тексель на `-C` (інвертована
     швидкість центру), що дає справжній zero-normal-flow (потік реально не
     проходить крізь межу)
- **Фікс** (`js/script.js`, `divergenceShader`): новий `insideRect(uv)` хелпер
  + логіка на межі прямокутника привида — там, де сусід (`vL`/`vR`/`vT`/`vB`)
  і сам центральний тексель лежать по РІЗНІ боки контуру, швидкість сусіда
  підмінюється на `-C` (той самий прийом, що й зовнішні стіни canvas), змішана
  через `mix(...,wall)` де `wall = 1 - permeability` — 0=як було раніше
  (м'яко), 1=повноцінна тверда стіна з відбиттям потоку. Стеснення
  дивергенції всередині прямокутника (стара логіка) лишилось як додаткове
  прибирання залишкового проникнення. Той самий безпечний патерн, що й
  раніше в цій сесії (правка ДО розрахунку pressure, узгоджено в одному
  кадрі) — просто розширений на внутрішній контур, а не тільки зовнішній
- Перевірено живим CDP-тестом (3 етапи — стабільність без взаємодії, стійка
  інʼєкція диму прямо в прямокутник, кадр після осідання): 0 помилок консолі
  на кожному етапі, рендер стабільний (жодного хаосу/кислотних плям — на
  відміну від двох давніших зламаних спроб цієї ж категорії фізики), і
  вперше чітко видно окремий завихрений клубок диму, який зупиняється саме
  на нижній межі прямокутника, а не розмито проходить крізь неї
- Файли (додатково): `js/script.js`, `index.html`, `mobile.html`
  (версіонування `?v=`)
- **Четвертий раунд у тому ж заході**: користувач підтвердив, що кеш дійсно
  скинуто (свіжа перезагрузка), але навіть з новою "стінковою" логікою ефект
  все одно здавався слабким — показав скріншот з реальним відбиттям диму від
  краю ЕКРАНА (100% тверда стіна) як референс і попросив ту саму силу для
  привида. Дефолт `obstacle_permeability` був **0.4** (лише 60% від сили
  справжньої стіни, `wall=0.6` у формулі `mix()`) — саме тому власне стінкова
  логіка з попереднього кроку вже працювала правильно, але давала помітно
  слабший за очікування ефект
- **Фікс**: дефолт `obstacle_permeability` змінено з `0.4` на **`0`** (100%
  тверда стіна, та сама сила що в справжніх меж canvas) в трьох місцях:
  `js/ghost-faces.js` (`cfg.obstacle_permeability` initial value + fallback у
  `readCfgFromColors()`), `admin.html` (fallback слайдера `permeab`).
  Регульованість через адмінку (`ghost_obstacle_permeability` в `colors`)
  лишилась — хто захоче м'якшу перешкоду, зможе виставити вище 0
- Версія `js/ghost-faces.js` піднята до `?v=5` (index.html, mobile.html) —
  дефолтне значення в конфіг-об'єкті змінилось, потрібен новий кеш-бастинг
- Перевірено живим CDP-тестом (permeability=0 підтверджено в
  `window._fluidConfig.OBSTACLE_PERMEABILITY`): 0 помилок на всіх 3 етапах,
  рендер стабільний, і вперше чітко видно яскравий клубок диму, який реально
  впирається в межу прямокутника й роздувається/закручується вздовж неї, не
  проникаючи всередину — версія ефекту, візуально відповідна тому, що
  користувач показав як референс (відбиття від краю екрана)
- Файли (додатково): `js/ghost-faces.js`, `admin.html`, `index.html`,
  `mobile.html` (версіонування)
- **П'ятий раунд у тому ж заході**: користувач попросив прибрати жовту
  dev-рамку, пояснивши суть — дим "чіплявся" саме за прямокутну рамку
  (bounding box SVG), а не за реальний контур силуету. До цього моменту
  фізична перешкода дійсно працювала на прямокутнику (`OBSTACLE_RECT`), тому
  в прозорих кутах SVG (де самого силуету вже немає) дим все одно
  відбивався — невідповідність між тим, що видно (силует), і тим, що реально
  блокує потік (прямокутник навколо нього)
- **Пряма вимога користувача**: фізика має впиратись саме у форму SVG, не в
  прямокутник (підтверджено явним вибором складнішого підходу через
  AskUserQuestion, а не просто прибрати рамку косметично)
- **Фікс — альфа-маска форми замість bounding box**:
  - `js/script.js`: нова `ensureObstacleMaskTexture()`/
    `window._fluidUpdateObstacleMask(canvas)` — створює/оновлює WebGL-текстуру
    (RGBA, `CLAMP_TO_EDGE`, `UNPACK_FLIP_Y_WEBGL` для коректної орієнтації)
    напряму з offscreen canvas, який `ghost-faces.js` вже використовує для
    Canvas2D-рендера силуету — жодного дублювання растеризації SVG. Новий
    `config.OBSTACLE_MASK_READY` прапорець (safe default `false` — доки маска
    не завантажена, шейдер фолбечиться на старий прямокутник)
  - `divergenceShader`: `insideRect(uv)` тепер спершу перевіряє bounding box
    (як раніше, дешевий early-exit), а якщо маска готова (`uObstacleUseMask`)
    — додатково читає альфа-канал `uObstacleMask` за локальними UV всередині
    прямокутника (`localUv = (uv - rect.xy) / rect.zw`); перешкодою вважається
    лише точка з альфою > 0.15, не будь-яка точка всередині прямокутника.
    Вся інша логіка (стінка на межі контуру через `mix(...,-C,wall)`, м'яке
    стиснення дивергенції) лишилась — просто `insideRect()` тепер точніша
  - `js/ghost-faces.js`, `relocateAndMaybeChangeImage()`: після кожної
    растеризації нового SVG викликає
    `window._fluidUpdateObstacleMask(raster.canvas)` — маска синхронізується
    з кожною зміною привида автоматично
  - `renderDevOverlay()`: жовта заливка + пунктирна рамка прибрані повністю
    (залишився лише текстовий підпис `GHOST DEV · id=X`) — щоб візуально не
    вводити в оману щодо форми реальної перешкоди
- Перевірено живим CDP-тестом (3 етапи): `OBSTACLE_MASK_READY: true`
  підтверджено в рантаймі (текстура реально завантажилась і шейдер
  скомпілювався без помилок WebGL), 0 помилок консолі на кожному етапі,
  рендер стабільний на всіх скріншотах (жодного хаосу — найризикованіша
  зміна з усіх дотепер, новий uniform+текстура у вже складному шейдері,
  але пройшла чисто), жовта рамка видимо відсутня, підпис лишився
- Файли (додатково): `js/script.js`, `js/ghost-faces.js`, `index.html`,
  `mobile.html` (версіонування `?v=`)
- **Шостий раунд у тому ж заході (наступна сесія, 2026-09-14)**: користувач
  повідомив, що дим все одно погано помітно "вдаряється"/повторює траєкторію
  привида, і запропонував додати "примагнічування" диму — новий підхід, не
  розглянутий раніше в цій серії фіксів
- **Пряма вимога користувача** (підтверджено через AskUserQuestion): дим
  повинен ОДНОЧАСНО (а) притягуватись вздовж контуру привида (щоб явно
  обрисовувати форму своїм рухом) І (б) відштовхуватись зсередини (стінка з
  попереднього кроку лишається) — гібридна модель, а не заміна одного на інше
- **Реалізація — новий фізичний прохід `obstacleAttractShader`** (`js/script.js`),
  за тим самим архітектурним патерном, що вже використовує `vorticityShader`
  (окремий fragment-shader прохід, що ДОДАЄ силу до існуючого velocity, а не
  постфактум модифікує вже готовий результат):
  - Новий `obstacleAttractProgram` (Program), викликається в `step()` одразу
    після vorticity-проходу, до divergence — лише коли
    `OBSTACLE_ENABLED && OBSTACLE_MASK_READY && OBSTACLE_ATTRACT_STRENGTH > 0`
  - Шейдер читає градієнт альфа-маски форми (той самий `uObstacleMask`, що
    вже використовує `divergenceShader`) — `∇alpha` вказує впоперек контуру,
    поворот на 90° (`tangent = vec2(-normal.y, normal.x)`) дає напрямок
    ВЗДОВЖ краю силуету. Сила максимальна саме на різкому переході альфа
    (сама межа контуру) і зникає поза вузькою прикордонною смугою
    (`gradMag < 0.02` → сили немає). Напрямок вздовж контуру (за/проти
    годинникової стрілки) визначається знаком `dot(vel, tangent)` — дим
    "підхоплюється" в той бік, куди вже рухався, а не завжди в один
  - Новий `config.OBSTACLE_ATTRACT_STRENGTH` (дефолт `0` в самому
    `js/script.js` — фіча вимкнена, доки зовнішній модуль явно не задасть
    ненульове значення; safe default)
  - `js/ghost-faces.js`: новий `cfg.obstacle_attract_strength` (дефолт
    `6000`, читається з `ghost_obstacle_attract_strength` в `colors`),
    передається в `window._fluidConfig.OBSTACLE_ATTRACT_STRENGTH` через
    `syncObstacleWithFluid()` (той самий pull-патерн, що й permeability/rect)
  - `admin.html`: новий слайдер "Примагнічування диму вздовж контуру"
    (0-20000, крок 500) в тому самому блоці налаштувань привида; ключ
    доданий в `applyGhostSettings()` для live-preview через BroadcastChannel
- Перевірено живим CDP-тестом (3 етапи, найризикованіша зміна з усіх — новий
  повноцінний fragment-shader прохід у гарячому rAF-циклі щокадру): шейдер
  скомпілювався без помилок WebGL (`ATTRACT: 6000` підтверджено в рантаймі),
  0 помилок консолі на кожному етапі, рендер стабільний на всіх скріншотах
  (жодного хаосу/кислотних плям), і на фінальному скріншоті чітко видно
  яскраву спіраль/вихор диму саме в районі привида — дим явно закручується
  по замкнутій траєкторії вздовж контуру, а не просто лінійно тече, саме той
  ефект "обрисовування форми", який просив користувач
- Файли (додатково): `js/script.js`, `js/ghost-faces.js`, `admin.html`,
  `index.html`, `mobile.html` (версіонування `?v=`)

### v3.28 (2026-09-12) — `.env` переналаштовано під локальну розробку (не код-фікс)
- Користувач повідомив, що робоча папка була оновлена копією з прод-сервера, через що локальний запуск на `127.0.0.1:8000` не працює ("помилки через адреси")
- Дослідження (Explore agent, 28 tool calls) підтвердило: прод-домен НЕ зашитий в коді (`Paskal.py`/`.html`/`.js`) — всі URL будуються з `.env`, дефолти в коді вже правильно вказують на `127.0.0.1:8000`. Проблема повністю в **вмісті** поточного `.env` (прод-конфігурація замість дев)
- Виправлено в `.env` (лише локальний файл, не в git, не впливає на прод — прод-значення збережені закоментованими поруч для легкого повернення при наступному деплої):
  - `DB_USER`/`DB_PASS`: `zoryana_user`/прод-пароль → `root`/`root` (локальний MySQL OSPanel)
  - `SITE_BASE_URL`, `OAUTH_REDIRECT_BASE`: прод-домен → `http://127.0.0.1:8000`
  - `ALLOWED_ORIGINS`: прод-домени → `http://127.0.0.1:8000,http://localhost:8000`
  - `ENVIRONMENT=production` — закоментовано. **Найкритичніша знахідка**: цей прапорець вмикав `_IS_PROD=True` → всі `set_cookie()` виклики (сесії/логін/чат) отримували `secure=True` — браузер не зберігає такі cookie на `http://` (не HTTPS), тобто логін/сесії були б зламані на localhost навіть після виправлення домену
  - Окремо (не .env): **MySQL/OSPanel сервіс на машині розробника був взагалі не запущений** — Claude НЕ намагався запускати системні сервіси самостійно (може зачепити інші проєкти на тій самій машині), користувач запустив сам
- Перевірено наживо на локальному сервері (`uvicorn Paskal:app --port 8000`): `/health` → `db:"connected"`, CORS-заголовок `access-control-allow-origin: http://127.0.0.1:8000` (раніше віддавав би прод-домен)
- Файли: `.env` (лише конфігурація, коду не торкались)
- Не потребує SQL-міграцій чи змін у `Paskal.py`/HTML/JS

### v3.27 (2026-09-12) — Плавність карти (pan/zoom/маркери): viewport culling через grid-індекс + кешування градієнтів + прибрано зайвий CSS re-match
- Запит користувача: карта повинна працювати плавно, "як Google Maps" — без ривків при pan/zoom і в щільних зонах маркерів. Уточнено й підтверджено: дизайн/технологія рендерингу (inline SVG карта + Canvas2D зірки + WebGL дим) НЕ змінюється, лише продуктивність
- Повне дослідження pipeline (Explore agent, 49 tool calls) виявило конкретні вузькі місця в `_startCanvasLoop()` (рендер зірок-маркерів) і `applyTr()` (застосування pan/zoom) — нижче фікси для найбільш безпечних/вигідних з них
- **Фікс 1**: `applyTr()` — `classList.toggle('zoom-city'/'zoom-deep')` і `style.opacity` на `#city-overlay` тепер виконуються лише коли поріг zoom РЕАЛЬНО перетнуто (нові `_lastZoomCity`/`_lastZoomDeep` порівняння), а не безумовно на кожен pan/zoom тік — раніше це форсувало CSS re-match по всіх 727 `<path>` нащадках SVG-карти щокадру, навіть коли зум не наближався до жодного порогу
- **Фікс 2**: `drawDotFX()` — градієнти "хрест-променів" (2 `createLinearGradient` на кожен видимий маркер у стані спокою) тепер будуються в локальних координатах через `ctx.translate` (за тим самим патерном, що вже використовувався для glow-градієнта) і кешуються в тому самому `_glowCache` Map за ключем `color+радіус+alpha` — раніше будувались напряму у світових координатах кожного маркера, тому кеш був неможливий і градієнт перестворювався щокадру на кожну видиму зірку
- **Фікс 3**: `_densityScore()` — заміна O(m) `.find()` по `cfg.boosts` на попередньо побудований `Map` (`_DENSITY_BOOSTS_MAP`, будується разом з `_DENSITY_CFG_CACHE`) — O(n×m)→O(n) на кожен кадр рендер-циклу (та сама оптимізація, що вже виконувалась раніше в цій сесії, але була втрачена при поверненні коду до стану GitHub)
- **Фікс 4 (найбільший виграш)**: `_startCanvasLoop()` — головний цикл побудови `_vis[]` (видимі зірки для відмальовки) тепер використовує вже наявний просторовий grid-індекс (`window._geoGrid`, побудований у `loadData()` для `hit()`) для viewport culling: обчислюється видима world-space область екрана (через `s2w()` на кутах +запас 60px), і перебираються лише точки з відповідних ячейок грід замість ПОВНОГО перебору `people` щокадру. Фолбек на старий повний перебір лишається, якщо grid ще не побудований (до першого `loadData()`). Density-фільтр і AABB-культінг всередині циклу — без змін, лише джерело ітерації
- **Фікс 5**: `#sea-svg` (рухається через CSS `transform`, не через viewBox) — додано `will-change:transform` inline-стилем, форсує окремий compositor layer для GPU-дешевого pan/zoom моря
- Свідомо НЕ виконано (архітектурна зміна, потребує окремого підтвердження користувача): заміна способу руху головної SVG-карти (`viewBox`-атрибут на 727 `<path>`) — це найдорожче місце pipeline, але свідомо обране розробником раніше заради чіткості контурів при zoom×12 (CSS transform розтягував би вже раструйований SVG); альтернативи (гібридний viewBox/transform залежно від zoom-рівня, растеризація SVG у bitmap для низьких zoom) зафіксовані як відомий залишковий вузол, не змінювались
- Файли: `index.html`
- Синтаксис перевірено (`node -c`) — помилок нема
- Логічно: жодна з 5 змін не міняє видимий результат (набір видимих маркерів, їх позиції/кольори/анімація) — лише швидкість обчислення того самого результату
- **Не перевірено функціонально/скріншотами** — рекомендовано користувачу після деплою порівняти суб'єктивну плавність pan/zoom до/після, особливо у щільних зонах маркерів і на глибокому zoom

### v3.26 (2026-09-12) — Прибрано паузу диму на zoom/drag: хибні спрацювання від деяких пристроїв введення
- Продовження v3.25: після того як пауза диму на zoom/drag нарешті запрацювала (фікс `window._fluidConfig`), користувач повідомив що дим все одно "заморожується" при простому наведенні курсора на карту, без жодних кліків/скролу
- **Діагностика проведена в реальному браузері користувача** (через `Object.defineProperty` на `PAUSED` + `console.trace()`, підтверджено `console.log` пасткою на `window.addEventListener('wheel',...)`): дим ставився на паузу через **реальні wheel-події**, які браузер отримував від пристрою користувача (значення `deltaY=-100`), хоча користувач стверджував що не торкався колеса/трекпада — типова апаратна особливість чутливих/нахильних коліс миші та трекпадів, що генерують wheel-події від легкого випадкового дотику
- Замість смягшення порогу чутливості — за прямим запитом користувача пауза диму на zoom і на drag **прибрана повністю**:
  - `index.html`, `wheel`-обробник (zoom) — блок `if(window._fluidConfig...){PAUSED=true; setTimeout(...PAUSED=false...)}` видалено, разом з мертвою змінною `_zoomPauseTimer`. Сам zoom (`wheelZoom(...)`) не змінювався
  - `index.html`, `mousedown`-обробник (початок drag) — видалено `window._fluidConfig.PAUSED=true`
  - `index.html`, `mouseup`-обробник (кінець drag) — видалено відповідний блок зняття паузи (став мертвим кодом після видалення mousedown-частини)
- Не чіпались: пауза при вимкненні диму адміном (`_applySmokeState()`, toggle-кнопка) і touch-свайп одним пальцем на мобільних (`touchmove`, окрема логіка з `_touchSplat`) — користувач просив прибрати лише zoom/drag-паузу
- Побічно виявлено (НЕ виправлено цього разу, за межами запиту користувача): WebSocket `/ws/online` постійно не з'єднується і перепідключається (видно в консольному лозі діагностики), CSP блокує запит Google Analytics до `stats.g.doubleclick.net` — обидва потребують окремого дослідження
- Файли: `index.html`
- Синтаксис перевірено (`node -c`) — помилок нема
- **Перевірено в реальному браузері користувача** (на відміну від попередніх версій цієї сесії) — сама діагностика (wheel-подія від пристрою) підтверджена живими логами консолі, не лише статичним аналізом коду

### v3.25 (2026-09-03) — КРИТИЧНИЙ фікс: пауза диму на zoom/drag/hover НІКОЛИ фактично не працювала + grid-індекс для hit()
- Користувач попросив дослідити структуру диму (`js/script.js`) і карти (`index.html`) з нуля та знайти головну причину підвисань при hover на маркер і при zoom
- **Корінна причина**: `window._fluidConfig` ніде в проєкті фактично не присвоювався. У `js/script.js:30` об'єкт налаштувань дима `let config = {...}` — top-level `let` у класичному скрипті НЕ створює властивість `window` (на відміну від `var`/`function`). `index.html` у 7 місцях звертається саме до `window._fluidConfig.PAUSED` — властивість завжди була `undefined`, тому **усі** перевірки `if(window._fluidConfig){...}` (zoom-пауза, drag-пауза, admin toggle, `applySmokeConfig()`) ніколи не виконували своє тіло. Це мертвий код
- Наслідок: WebGL fluid-цикл (`update()`, script.js) молотив на повній потужності (20 pressure-ітерацій + 8 bloom-ітерацій + sunrays, 20+ fullscreen draw calls на кадр) **завжди**, включно з моментами zoom/drag/hover — одночасно з SVG `viewBox` reflow під час zoom (`updateMapSvgViewBox()`) та O(n) hit-test `hit()` (повний перебір усіх маркерів, "10k+ записів", на кожен rAF-тік руху миші) — звідси конкуренція за GPU/main thread і відчутні підвисання
- **Фікс 1 (критичний)**: `js/script.js` — додано `window._fluidConfig = config;` одразу після оголошення об'єкта. JS-об'єкти передаються за посиланням — зовнішній `window._fluidConfig.PAUSED = true` тепер напряму впливає на той самий `config`, який реально перевіряє `update()`. Це одразу "оживляє" всю раніше написану, але мертву логіку паузи (zoom wheel-обробник з `_zoomPauseTimer`, drag mousedown/mouseup, `_applySmokeState()` admin toggle)
- **Фікс 2 (просторовий grid-індекс)**: `index.html`, `loadData()` — новий блок побудови grid-індексу в world-space (координати `p.x`/`p.y`, нормалізовані 0..1, незмінні при pan/zoom): `Map("cx,cy" → [people...])`, розмір комірки `0.05`. Будується один раз при завантаженні даних. `hit(sx,sy)` переписано з лінійного O(n) перебору `people` на grid-based пошук — переводить координати кліку в world-простір (`s2w()`), визначає потрібні сусідні комірки (з урахуванням hit-радіуса в поточному zoom), перевіряє точним screen-space тестом (той самий `w2s()`+`Math.hypot()`+`dotR()`, без зміни логіки/точності) лише кандидатів з цих комірок — прибирає основне навантаження саме при hover
- Не виконано (другорядне, не першочергове): оптимізація `_densityScore()`/`_startCanvasLoop()` (O(n×m) через `.find()` по boost-правилах) — залишена на майбутнє, якщо Фікси 1-2 не приберуть підвисання повністю
- Файли: `js/script.js`, `index.html`
- Синтаксис перевірено (`node -c`) — помилок нема
- **Не перевірено функціонально/скріншотами** — рекомендовано користувачу після деплою: покрутити колесо миші над картою (zoom) — дим має видимо "заморожуватись" на короткий момент активного скролу; навести курсор на маркер у щільній зоні — підвисань має бути суттєво менше

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
