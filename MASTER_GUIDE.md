# MASTER GUIDE — Зоряна Пам'ять
> Версія: 1.0 | Дата: 16.04.2026 | Гілка: `drop_data`  
> Цей файл — головний довідник для Claude Code та розробника.  
> **НЕ видаляти**. Оновлювати при кожній зміні архітектури.

---

## ЗМІСТ
1. [Огляд проєкту](#1-огляд-проєкту)
2. [Файлова структура](#2-файлова-структура)
3. [Поточний стек технологій](#3-поточний-стек-технологій)
4. [База даних — поточний стан](#4-база-даних--поточний-стан)
5. [API-ендпоінти — повний список](#5-api-ендпоінти--повний-список)
6. [Frontend — архітектура](#6-frontend--архітектура)
7. [Backend — архітектура](#7-backend--архітектура)
8. [Алгоритм пошуку](#8-алгоритм-пошуку)
9. [CSS та дизайн-система](#9-css-та-дизайн-система)
10. [Адмін-панель](#10-адмін-панель)
11. [WebSocket — онлайн-лічильник](#11-websocket--онлайн-лічильник)
12. [Запуск проєкту](#12-запуск-проєкту)
13. [Цільова архітектура (ТЗ)](#13-цільова-архітектура-тз)
14. [Критичні вразливості безпеки](#14-критичні-вразливості-безпеки)
15. [Дорожня карта рефакторингу](#15-дорожня-карта-рефакторингу)
16. [Правила роботи з кодом](#16-правила-роботи-з-кодом)

---

## 1. ОГЛЯД ПРОЄКТУ

**Зоряна Пам'ять** — українська меморіальна веб-платформа у форматі інтерактивної карти України.  
Увічнює пам'ять загиблих (військових та цивільних) під час російського вторгнення.

### Що вміє система прямо зараз:
- Інтерактивна SVG-карта України з маркерами меморіалів
- Нечіткий пошук (транслітерація кирилиця ↔ латиниця, fuzzy scoring)
- Картки меморіалів з повною біографічною інформацією
- Лайки з cooldown 2 секунди (fingerprint-based)
- Реєстрація та авторизація користувачів
- Додавання меморіалів → модерація адміном
- WebSocket онлайн-лічильник у реальному часі
- Адмін-панель: повний CRUD, управління кольорами, підписами карти
- WebGL флюїдна симуляція фону (Pavel Dobryakov, MIT)
- Аналітика пошуку (таблиця `search_logs`)
- Динамічна тема: 21 CSS-змінна зберігається в SQLite

### Репозиторій
```
https://github.com/Paskal19853d/StartUkraine.git
```

### Два шляхи проєкту
| Папка | Призначення |
|-------|-------------|
| `treetex/` | Основна робоча версія (SQLite + FastAPI, порт 8000) |
| `treetex-local/` | Дзеркало / копія для локального розвитку |

---

## 2. ФАЙЛОВА СТРУКТУРА

```
treetex/
├── Paskal.py               ← ГОЛОВНИЙ BACKEND (692 рядки)
│                             FastAPI, всі маршрути, БД-логіка
├── index.html              ← ПУБЛІЧНИЙ ІНТЕРФЕЙС (920 КБ, ~2900 рядків)
│                             SPA: карта, пошук, авторизація, картки
├── admin.html              ← АДМІН-ПАНЕЛЬ (936 КБ, ~3000 рядків)
│                             CRUD меморіалів, тема, підписи карти
├── Style.css               ← СПІЛЬНІ СТИЛІ (23 КБ, ~913 рядків)
│                             CSS-змінні, topbar, картки, модалки
├── memorial.db             ← SQLITE БАЗА ДАНИХ (155 КБ)
│                             7 таблиць, 20+ меморіалів seed
├── ukraine-map.svg         ← КАРТА УКРАЇНИ (884 КБ)
│                             Детальна SVG з областями, містами, річками
├── proxy.php               ← ПРОКСІ (1.7 КБ)
│                             Для alerts.in.ua
├── js/
│   ├── script.js           ← WebGL флюїд-симуляція (1922 рядки)
│   └── dat.gui.min.js      ← GUI бібліотека для dat.GUI
├── img/
│   ├── LDR_LLL1_0.png      ← Зображення (карта/оверлей)
│   ├── foto_false.png      ← Заглушка фото відсутнього меморіалу
│   ├── icon-lively-300.png ← Іконка для Lively Wallpaper
│   └── icon-lively-300 — копия.png
├── overlays/               ← UI-оверлеї (порожня або з SVG-файлами)
├── Doc/                    ← Документація (SVG-схеми)
│   ├── user_data_flow.svg
│   ├── admin_change_flow.svg
│   └── project_launch_structure.svg
├── venv/                   ← Python virtual environment
├── iconfont.ttf            ← Кастомний іконковий шрифт
├── LivelyInfo.json         ← Конфіг Lively Wallpaper
├── LivelyProperties.json   ← Властивості Lively Wallpaper
├── PROJECT_RESEARCH.md     ← Дослідження проєкту (автоаналіз)
├── SECURITY_RULES.md       ← Правила безпеки (детальний чек-лист)
├── MASTER_GUIDE.md         ← ЦЕЙ ФАЙЛ — головний довідник
├── 000.html                ← Архівна / тестова версія index.html
├── admin.html_old          ← Стара версія адмінки
├── ReSS/                   ← Папка з ресурсами (копії файлів)
├── ReSS.rar                ← Архів ресурсів
└── prompt.txt              ← (порожній)
```

### ВАЖЛИВО для Claude Code
- Редагувати лише: `Paskal.py`, `index.html`, `admin.html`, `Style.css`
- НЕ торкатись: `ukraine-map.svg`, `js/script.js` (WebGL), `js/dat.gui.min.js`
- `memorial.db` — НЕ видаляти та НЕ перезаписувати вручну
- `000.html` і `admin.html_old` — архіви, не використовуються
- При будь-яких змінах SWG (карта, UI) має працювати як і раніше

---

## 3. ПОТОЧНИЙ СТЕК ТЕХНОЛОГІЙ

### Backend (Python)
```
FastAPI          — async web framework
Uvicorn          — ASGI сервер
pymysql          — MySQL/MariaDB драйвер (замінив sqlite3)
python-dotenv    — .env конфігурація
Pydantic         — валідація моделей
python-multipart — (для форм, якщо є)
```

### База даних
```
MySQL / MariaDB-10.3 (OpenServer, порт 3306)
База: zoryana_pamyat (auto-create при першому запуску)
Credentials: .env → DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
```

### Frontend (Vanilla JS, без фреймворків)
```
HTML5 + вбудований SVG (карта)
CSS3 з CSS-змінними
Vanilla JavaScript — без React/Vue/Angular
WebGL — флюїдна симуляція (js/script.js)
Google Fonts CDN — Unbounded (заголовки), Geologica (текст)
dat.GUI — бібліотека контролів (js/dat.gui.min.js)
WebSocket — нативний браузерний API
```

### Запуск
```bash
# УВАГА: Спочатку запустити MariaDB у OpenServer GUI!

# З папки treetex/
python -m uvicorn Paskal:app --reload --port 8000

# Або через venv
venv/Scripts/python -m uvicorn Paskal:app --reload --port 8000
```

### Доступні URL
```
http://localhost:8000/        → index.html (публічний інтерфейс)
http://localhost:8000/admin   → admin.html (адмін-панель)
http://localhost:8000/docs    → FastAPI Swagger UI (тільки dev)
```

---

## 4. БАЗА ДАНИХ — ПОТОЧНИЙ СТАН

**Файл:** `memorial.db` (SQLite)  
**Місце:** у корені проєкту (небезпечно в production — має бути поза web-root)

### Таблиця `memorials` — головна
```sql
CREATE TABLE memorials (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    last     TEXT NOT NULL,          -- Прізвище
    first    TEXT NOT NULL,          -- Ім'я
    mid      TEXT DEFAULT '',        -- По батькові
    birth    TEXT,                   -- Дата народження (рядок, формат вільний)
    death    TEXT,                   -- Дата загибелі
    loc      TEXT DEFAULT '',        -- Місце загибелі
    bury     TEXT DEFAULT '',        -- Місце поховання
    circ     TEXT DEFAULT '',        -- Обставини загибелі
    descr    TEXT DEFAULT '',        -- Опис / біографія
    photo    TEXT DEFAULT '',        -- URL фотографії
    color    TEXT DEFAULT '#4fc3f7', -- Колір маркера (hex)
    pos_x    REAL DEFAULT 0.5,       -- Позиція на карті X (0.0–1.0, нормалізована)
    pos_y    REAL DEFAULT 0.5,       -- Позиція на карті Y (0.0–1.0, нормалізована)
    likes    INTEGER DEFAULT 0,      -- Лічильник вподобань
    rating   REAL DEFAULT 0,         -- Рейтинг (зірки)
    approved INTEGER DEFAULT 0,      -- 0=модерація, 1=підтверджено
    grp      TEXT DEFAULT '',        -- Позивний / підрозділ
    added_by TEXT DEFAULT ''         -- Хто додав
);
```

### Таблиця `likes_log` — антиспам лайків
```sql
CREATE TABLE likes_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    memorial_id INTEGER,
    fingerprint TEXT,    -- браузерний fingerprint (рядок)
    ts          INTEGER  -- unix timestamp
);
-- Cooldown: 2 секунди між лайками з одного fingerprint
```

### Таблиця `users` — користувачі
```sql
CREATE TABLE users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,    -- SHA256 хеш (НЕБЕЗПЕЧНО! потрібен bcrypt)
    is_admin  INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    last_seen INTEGER DEFAULT 0, -- unix timestamp останнього входу
    created   INTEGER DEFAULT (strftime('%s','now'))
);
-- Дефолтний адмін: admin@admin.com / Admin (SHA256)
```

### Таблиця `colors` — тема кольорів
```sql
CREATE TABLE colors (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    label TEXT DEFAULT ''
);
```
**21 кольоровий ключ:**
| key | default | опис |
|-----|---------|------|
| bg | #03070e | Фон сторінки |
| surface | #070d1a | Поверхня карток |
| text_primary | #d0dce8 | Основний текст |
| text_secondary | #8a9cb0 | Другорядний текст |
| accent | #00c8ff | Акцент синій |
| yellow | #d4a800 | Жовтий (логотип) |
| yellow2 | #f0c030 | Жовтий яскравий |
| neon_blue | #00ccff | Неон синій (межа країни) |
| neon_yellow | #d4a800 | Неон жовтий (межа областей) |
| oblast_fill | #040f1e | Заливка областей |
| oblast_stroke | rgba(90,110,130,.3) | Межі міст/сіл |
| thread_color | rgba(0,200,255,1) | Нитки між дублікатами |
| map_bg | #03070e | Фон карти |
| bar_bg | rgba(3,7,14,.96) | Фон шапки |
| logo_star | #f0c030 | Зірка логотипу |
| logo_text | #f0c030 | Текст логотипу |
| logo_accent | #00c8ff | Акцент логотипу |
| btn_add_bg | #0e2860 | Кнопка Додати (фон) |
| btn_add_text | #a8e0f8 | Кнопка Додати (текст) |
| card_bg | rgba(4,9,18,.98) | Фон картки |
| label_opacity | 0.45 | Прозорість підписів областей |

### Таблиця `map_labels` — підписи областей
```sql
CREATE TABLE map_labels (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,             -- Назва (наприклад "Київська")
    x     REAL NOT NULL,             -- SVG-координата X
    y     REAL NOT NULL,             -- SVG-координата Y
    type  TEXT DEFAULT 'oblast',
    color TEXT DEFAULT 'rgba(160,195,220,0.45)',
    size  INTEGER DEFAULT 145
);
-- 24 записи (всі області України)
```

### Таблиця `search_logs` — аналітика пошуку
```sql
CREATE TABLE search_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    query         TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    created_at    INTEGER DEFAULT (strftime('%s','now'))
);
-- Кожен пошуковий запит записується сюди
```

---

## 5. API-ЕНДПОІНТИ — ПОВНИЙ СПИСОК

### Статичні сторінки
| Метод | URL | Відповідь |
|-------|-----|-----------|
| GET | `/` | `index.html` |
| GET | `/admin` | `admin.html` |
| GET | `/Style.css` | CSS файл |
| GET | `/ukraine-map.svg` | SVG карта |
| GET | `/img/*` | Зображення (StaticFiles) |

### Публічні API
| Метод | URL | Опис | Параметри |
|-------|-----|------|-----------|
| GET | `/api/people` | Всі затверджені меморіали | — |
| GET | `/api/search` | Нечіткий пошук | `?q=рядок` |
| POST | `/api/search/log` | Логування пошуку з клієнта | JSON: `{query, results_count}` |
| GET | `/api/search/stats` | Статистика пошуку | — |
| GET | `/api/stats` | Загальна статистика | — |
| GET | `/api/colors` | Тема кольорів | — |
| GET | `/api/labels` | Підписи регіонів | — |
| POST | `/api/people` | Додати меморіал (на модерацію) | JSON: PersonIn |
| POST | `/api/like/{id}` | Лайк меморіалу | `?fp=fingerprint` |
| POST | `/api/auth/register` | Реєстрація | JSON: `{name, email, password}` |
| POST | `/api/auth/login` | Вхід | JSON: `{email, password}` |

### Адмін API (захищені email+password у query params — НЕБЕЗПЕЧНО)
| Метод | URL | Опис |
|-------|-----|------|
| GET | `/api/admin/pending` | Меморіали на модерації |
| POST | `/api/admin/approve/{id}` | Затвердити меморіал |
| DELETE | `/api/admin/memorial/{id}` | Видалити меморіал |
| PUT | `/api/admin/memorial/{id}` | Редагувати меморіал |
| GET | `/api/admin/users` | Список користувачів |
| POST | `/api/admin/ban/{user_id}` | Заблокувати користувача |
| POST | `/api/admin/unban/{user_id}` | Розблокувати |
| PUT | `/api/admin/color` | Оновити один колір |
| PUT | `/api/admin/colors/batch` | Масове оновлення кольорів |
| PUT | `/api/admin/label/{id}` | Оновити підпис на карті |
| GET | `/api/admin/stats` | Повна статистика адмінки |

### WebSocket
```
WS /ws/online  — онлайн-лічильник в реальному часі
  Сервер → клієнт: {"online": N}
  Клієнт → сервер: "user:ім'я"  (опційно)
```

### Моделі даних (Pydantic)
```python
PersonIn:      last, first, mid, birth, death, loc, bury, circ, descr, 
               photo, color, pos_x, pos_y, grp, added_by
PersonUpdate:  всі поля PersonIn опціональні + approved
UserReg:       name, email, password
UserLogin:     email, password
ColorUpdate:   key, value
LabelUpdate:   id, x, y, color(opt), size(opt)
```

---

## 6. FRONTEND — АРХІТЕКТУРА

### index.html — публічний інтерфейс
```
#topbar                  — фіксована шапка (height: 54px, z-index: 700)
  #logo                  — "★ Зоряна Памʼять" (Unbounded font)
  .tstat × 3             — кількість людей, зірок, онлайн
  #sw                    — пошуковий рядок
    #search              — input[type=text]
    #search-clear        — кнопка ✕
    #sdrop               — dropdown результатів
  #un                    — ім'я поточного користувача
  #btn-logout            — кнопка Вийти
  #btn-auth              — кнопка Увійти
  #btn-add               — кнопка "+ ДОДАТИ"

#map-wrap                — контейнер карти
  #svg-layer             — SVG карта (ukraine-map.svg завантажується fetch)
    [marker-dots]        — .dot елементи (position: absolute)

#panel (rights sidebar)  — картка обраного меморіалу (360px)
  .panel-photo           — фото або заглушка
  .panel-name            — ФІО
  .panel-meta            — дати, місце, обставини
  .panel-descr           — опис
  .panel-likes           — кнопка лайку + лічильник
  .panel-rating          — зірки рейтингу

#modal-auth              — модальне вікно авторизації
  .tab-login             — вкладка входу
  .tab-reg               — вкладка реєстрації

#modal-add               — модальне вікно додавання меморіалу
  [форма з полями]       — всі поля PersonIn

#fluid (canvas)          — WebGL флюїдна симуляція (z-index: 900, pointer-events: none)
```

### Ключові JS-функції в index.html
```javascript
// Ініціалізація
loadColors()             — GET /api/colors → вставляє в <style id="dynamic-colors">
loadStats()              — GET /api/stats → оновлює #sttotal, #stlikes
loadMap()                — fetch ukraine-map.svg → вставляє в #svg-layer
loadPeople()             — GET /api/people → малює маркери на карті

// Пошук
initSearch()             — debounce 350ms на input#search
doSearch(q)              — GET /api/search?q=... → заповнює #sdrop
closeDrop()              — закриває dropdown
onSelectResult(r)        — клік по результату → центрує карту, відкриває панель

// Карта (SVG/пан/зум)
initMap()                — ініціалізація pan/zoom
centerOn(x, y, zoom)     — центрує карту на координатах
onDotClick(id)           — клік по маркеру → відкриває панель

// Панель
openPanel(person)        — показує деталі меморіалу
closePanel()             — ховає панель

// Авторизація
openAuth()               — показує #modal-auth
doLogin()                — POST /api/auth/login
doRegister()             — POST /api/auth/register
doLogout()               — очищує localStorage, оновлює UI

// Додавання
onAdd()                  — перевіряє авторизацію, показує #modal-add
submitAdd()              — POST /api/people

// Лайки
doLike(id)               — POST /api/like/{id}?fp=fingerprint

// WebSocket
initWS()                 — підключається до /ws/online, оновлює #stonline

// WebGL
initFluid()              — запускає js/script.js симуляцію
```

### Масштаб маркерів (формула з ТЗ)
```javascript
scale = Math.max(0.4, 1 - (count / 2000))
// При 0 меморіалів: scale = 1.0
// При 1000: scale = 0.5
// При 2000+: scale = 0.4 (мінімум)
```

### Маркери (дублікати)
- Меморіали з однаковим `grp` (підрозділ) з'єднуються ниткою (`thread_color`)
- При кліку на один — підсвічуються всі з тієї ж групи
- Маркери злегка зміщуються якщо pos_x/pos_y однакові

---

## 7. BACKEND — АРХІТЕКТУРА

### Paskal.py — структура файлу
```
рядки 1-10:    Імпорти
рядки 11-15:   Перша app = FastAPI() (потім перевизначається — баг дублювання!)
рядки 16-17:   DB = "memorial.db" константа
рядки 18-22:   get_db() — отримати підключення SQLite
рядки 23:      hash_pass() — SHA256 хеш (потрібен bcrypt!)
рядки 25-237:  init_db() — створення таблиць + seed даних
рядки 239-244: Друга app = FastAPI() + CORS middleware + @startup
рядки 246-257: Статичні маршрути (/, /admin, /Style.css, /ukraine-map.svg)
рядки 259-285: WebSocket /ws/online
рядки 287-316: Pydantic схеми (PersonIn, PersonUpdate, UserReg, UserLogin...)
рядки 318-329: AUTH хелпери (get_user, get_admin)
рядки 331-514: Публічні API ендпоінти
рядки 516-690: Адмін API ендпоінти
рядки 691-692: app.mount("/", StaticFiles(...)) — небезпечно! відкриває .db файл
```

### УВАГА: Баг дублювання `app`
У файлі `Paskal.py` є TWO визначення `app = FastAPI()`:
- рядок 11: `app = FastAPI()` — перше (без заголовку)
- рядок 240: `app = FastAPI(title="Зоряна Памʼять API", version="2.0")` — фактично використовується

Перше перекривається другим. Монтаж `/img` на рядку 14 прив'язується до першого `app` і **не працює** після перевизначення.

### НЕБЕЗПЕЧНИЙ рядок 692
```python
app.mount("/", StaticFiles(directory=".", html=True), name="static")
# Робить весь поточний каталог доступним через HTTP!
# Включно з memorial.db, Paskal.py, .env тощо
```

### Аутентифікація адміна (поточний небезпечний метод)
```python
def require_admin(email: str, password: str):
    u = get_admin(email, password)
    if not u: raise HTTPException(403, "Доступ заборонено")
    return u

# Використання (email/password у query params кожного запиту!):
@app.get("/api/admin/pending")
def pending(email: str, password: str):
    require_admin(email, password)
    ...
```

---

## 8. АЛГОРИТМ ПОШУКУ

**Файл:** `Paskal.py`, рядки 350–464

### Кроки

#### 1. Нормалізація (`_normalize`)
```python
s = s.lower().strip()
# Транслітерація кирилиця → латиниця:
# а→a, б→b, є→ye, ж→zh, х→kh, ц→ts, ч→ch, ш→sh, щ→shch, ю→yu, я→ya ...
```

#### 2. Fuzzy scoring (`_fuzzy_score`)
```
1.00 — точний збіг
0.92 — текст починається з запиту
0.80 — запит входить у текст
0.75 — слово починається з запиту
0.65 — запит входить у слово
0.xx — часткові символи (якщо >60% збігу)
0.00 — не знайдено
```

#### 3. Зважені поля (`_score_person`)
```
last  (прізвище)   × 2.0   — найважливіше
first (ім'я)       × 1.8
grp   (позивний)   × 1.5
loc   (місце загибелі) × 1.3
mid   (по батькові) × 1.2
bury  (поховання)  × 1.0
circ  (обставини)  × 0.8
descr (опис)       × 0.6
fullname           × 2.0   — повне ФІО разом
```

#### 4. Сортування та ліміт
```python
scored.sort(key=lambda x: (-x[0], -(x[1].get("rating") or 0)))
results = scored[:10]  # Максимум 10 результатів
```

#### 5. Результат (поля відповіді)
```json
{
  "id": 1,
  "name": "Шевченко Олег Миколайович",
  "last": "Шевченко",
  "first": "Олег",
  "mid": "Миколайович",
  "callsign": "Херсон-1",
  "location": "Херсон",
  "bury": "Херсон, Центральний цвинтар",
  "color": "#4fc3f7",
  "x": 0.630,
  "y": 0.720,
  "likes": 142,
  "score": 0.921
}
```

---

## 9. CSS ТА ДИЗАЙН-СИСТЕМА

### Файл: Style.css (23 КБ, ~913 рядків)

### CSS-змінні (`:root`)
```css
--bg:         #03070e      /* фон сторінки */
--surface:    #070d1a      /* поверхня карток */
--surface2:   #0a1220      /* другий рівень */
--border:     rgba(255,255,255,.07)
--border2:    rgba(255,255,255,.12)
--text:       #d0dce8      /* основний текст */
--text2:      #8a9cb0      /* другорядний */
--muted:      #3a5068
--accent:     #00c8ff      /* синій акцент */
--accent2:    #0088bb
--yellow:     #d4a800      /* жовтий */
--yellow2:    #f0c030      /* яскравий жовтий */
--star:       #c8a040
--neon-blue:  #00ccff
--neon-yel:   #d4a800
--panel:      360px        /* ширина правої панелі */
--bar:        54px         /* висота topbar */
--radius:     10px
--radius-lg:  14px
--ease:       cubic-bezier(.16,1,.3,1)
```

### Кольорова схема: темна (dark theme, космічна)
- Фон: темно-синій #03070e → чорний
- Акцент: ціан #00c8ff + жовтий #d4a800 (кольори прапора)
- Текст: світло-сірий #d0dce8
- Неонові ефекти: box-shadow, text-shadow
- Шрифти: Geologica (основний), Unbounded (заголовки/логотип)

### z-index шари
```
z-index: 900  — WebGL canvas #fluid
z-index: 700  — #topbar
z-index: 600  — #panel (бічна панель)
z-index: 500  — .dot (маркери на карті)
z-index: 9999 — модальні вікна (#modal-auth, #modal-add)
```

### Динамічна тема
```javascript
// При завантаженні сторінки:
// GET /api/colors → об'єкт {bg: {value: "#03070e"}, ...}
// Генерує і вставляє в <style id="dynamic-colors">:
// :root { --bg: #03070e; --surface: #070d1a; ... }
```

---

## 10. АДМІН-ПАНЕЛЬ

### Доступ
```
URL:      http://localhost:8000/admin
Логін:    admin@admin.com
Пароль:   Admin
```
⚠️ ЗМІНИТИ ПЕРЕД PRODUCTION!

### Розділи адмін-панелі (`admin.html`)
1. **Статистика** — загальна кількість записів, затверджених, на модерації, користувачів, лайків, онлайн
2. **Меморіали** — таблиця всіх записів, редагування inline, підтвердження/відхилення
3. **На модерації** — нові надходження (approved=0)
4. **Користувачі** — список з can_ban/unban, мітка online (якщо last_seen < 120с)
5. **Кольори теми** — 21 color picker у реальному часі → PUT /api/admin/colors/batch
6. **Редактор карти** — перетягування підписів областей, колір, розмір → PUT /api/admin/label/{id}
7. **Пошукова аналітика** — GET /api/search/stats → топ запитів, порожні результати

---

## 11. WEBSOCKET — ОНЛАЙН-ЛІЧИЛЬНИК

```python
connected: set[WebSocket] = set()
online_users: dict = {}  # id(ws) -> ім'я

@app.websocket("/ws/online")
async def ws_online(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    await broadcast({"online": len(connected)})  # сповіщає ВСІХ при підключенні
    try:
        while True:
            msg = await asyncio.wait_for(ws.receive_text(), timeout=60)
            if msg.startswith("user:"):
                online_users[id(ws)] = msg[5:]
    except:
        pass
    finally:
        connected.discard(ws)
        online_users.pop(id(ws), None)
        await broadcast({"online": len(connected)})  # при відключенні
```

**Важливо:** `connected` і `online_users` — in-memory, не персистентні. При перезапуску сервера скидаються до 0.  
При масштабуванні на кілька воркерів потрібен Redis для шерінгу стану.

---

## 12. ЗАПУСК ПРОЄКТУ

### Поточний спосіб (dev)
```bash
cd d:/OSPanel/OpenServer/domains/localhost/treetex
venv/Scripts/python -m uvicorn Paskal:app --reload --port 8000
```

### Через Srart.txt (вміст файлу)
```
uvicorn Paskal:app --reload
```

### Залежності Python
```
fastapi
uvicorn[standard]
python-multipart
pydantic
```

Встановлення:
```bash
venv/Scripts/pip install fastapi uvicorn[standard] python-multipart pydantic
```

### Venv активація (Windows)
```bash
venv/Scripts/activate
```

---

## 13. ЦІЛЬОВА АРХІТЕКТУРА (ТЗ)

> Це технічне завдання на рефакторинг. НЕ ламати поточний UI/UX.  
> Підтримка до 3000+ одночасних користувачів.

### Цільовий стек

```
Frontend (Vanilla JS, без змін UI)
         ↓
FastAPI (async) + Uvicorn + Gunicorn
         ↓
Service Layer (business logic)
         ↓
MySQL (InnoDB) — замість SQLite
         ↓
Redis — кеш, rate limit, антиспам, WebSocket broadcast
```

### Python бібліотеки (цільові)
```
fastapi[all]
uvicorn[standard]
gunicorn
pymysql                    ← ВСТАНОВЛЕНО (поточний MySQL драйвер)
python-dotenv              ← ВСТАНОВЛЕНО
sqlalchemy[asyncio]        — async ORM (наступна фаза)
aiomysql                   — async MySQL driver (наступна фаза)
redis[hiredis]             — async Redis
python-jose[cryptography]  — JWT токени
passlib[bcrypt]            — bcrypt хешування
slowapi                    — rate limiting
httpx                      — async HTTP клієнт (для ДІЯ OAuth)
```

### Цільова база даних (MySQL InnoDB)
```sql
-- Нові таблиці (додати до існуючих):
payments (id, user_id, amount, status, provider, created_at)
visits   (id, session_id, ip, user_agent, page, created_at)
donations (id, amount, provider, status, created_at)
settings  (key, value, updated_at)
login_attempts (id, ip, ts)

-- Індекси для memorials:
INDEX idx_name (last, first)
INDEX idx_search (last, first, grp, loc)
INDEX idx_approved (approved)
FULLTEXT INDEX idx_fulltext (last, first, descr)

-- Додати до users:
ALTER TABLE users ADD COLUMN diia_id TEXT UNIQUE;
ALTER TABLE users ADD COLUMN diia_verified INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN real_name TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN auth_method TEXT DEFAULT 'password';
```

### JWT авторизація (цільова)
```python
# Замість email/password у кожному запиті:
SECRET_KEY = os.environ.get("JWT_SECRET")  # 32+ символи, у .env
ALGORITHM = "HS256"
TOKEN_EXPIRE = 30  # хвилини

# Login повертає JWT токен
# Адмін-ендпоінти: Authorization: Bearer <token>
```

### Rate Limiting (цільовий)
```
login:      5/хвилину на IP
register:   3/годину на IP
search:     30/хвилину на IP
like:       1/2 секунди на fingerprint (вже є)
api:        100/хвилину загально
```

### Авторизація через ДІЯ (цільова)
```
Flow: Кнопка "Увійти через Дія" → OAuth 2.0 redirect → 
      id.gov.ua авторизація → callback → JWT token
Fallback: BankID (якщо ДІЯ недоступна)
Потребує: реєстрації на id.gov.ua, client_id + client_secret у .env
```

### Масштабування WebSocket
```python
# Поточно: in-memory set() — не масштабується
# Цільово: Redis Pub/Sub
import aioredis
redis = aioredis.from_url("redis://localhost")

async def broadcast_via_redis(data: dict):
    await redis.publish("online_channel", json.dumps(data))
```

---

## 14. КРИТИЧНІ ВРАЗЛИВОСТІ БЕЗПЕКИ

> Детально: SECURITY_RULES.md

### КРИТИЧНІ (виправити до production)

| # | Рядок | Проблема | Виправлення |
|---|-------|----------|-------------|
| 1 | `Paskal.py:23` | SHA256 замість bcrypt | `passlib[bcrypt]` |
| 2 | `Paskal.py:85-88` | Стандартний пароль admin | Змінити email+password, перенести в .env |
| 3 | `Paskal.py:241` | CORS `allow_origins=["*"]` | Обмежити конкретним доменом |
| 4 | Весь файл | Немає rate limiting | `slowapi` |
| 5 | Всі admin routes | email/password у query params | JWT токени в Authorization header |
| 6 | `Paskal.py:692` | StaticFiles монтує весь каталог | Прибрати або обмежити |
| 7 | `PersonIn.photo` | URL без перевірки | SSRF-захист, whitelist доменів |
| 8 | Всі /api/people | Немає пагінації | `page` + `limit` params |

### СЕРЙОЗНІ (виправити при рефакторингу)
- `memorial.db` лежить у web-root → переписати у `../data/`
- Немає обмеження розміру полів у Pydantic моделях
- Немає валідації email при реєстрації (формат)
- `search_logs` необмежено росте → лімітувати до 10000 записів
- Немає логування підозрілої активності
- FastAPI `/docs` і `/redoc` відкриті публічно

### Що вже захищено
- SQL Injection: всі запити параметризовані (`?` placeholder)
- Лайки: cooldown 2с через fingerprint + ts
- Бан користувачів: поле is_banned
- XSS: FastAPI автоматично екранує JSON-відповіді

---

## 15. ДОРОЖНЯ КАРТА РЕФАКТОРИНГУ

### Фаза 1 — Безпека (не ламаючи UI)
- [ ] SHA256 → bcrypt (потребує скиду паролів існуючих юзерів)
- [ ] JWT токени для адмін-ендпоінтів
- [ ] Rate limiting (slowapi)
- [ ] Пагінація `/api/people`
- [ ] CORS обмежити
- [ ] Перенести DB поза web-root
- [ ] .env для секретів
- [ ] Вимкнути /docs в production
- [ ] Security Headers middleware

### Фаза 2 — Продуктивність
- [ ] Пагінація `/api/people` (вже у фазі 1)
- [ ] Redis кеш для `/api/people` (TTL 60с)
- [ ] Redis кеш для `/api/colors` (TTL 300с)
- [ ] FTS5 індекси для SQLite (або перехід на MySQL FULLTEXT)
- [ ] WebSocket через Redis Pub/Sub

### Фаза 3 — MySQL міграція
- [ ] SQLAlchemy async моделі
- [ ] Alembic міграції
- [ ] Перенести дані з SQLite → MySQL
- [ ] Async ендпоінти (async def замість def)

### Фаза 4 — Нові функції
- [ ] Оплата (Monobank API / LiqPay)
- [ ] ДІЯ OAuth 2.0
- [ ] Система рейтингу (зірки) з таблицею `rating_log`
- [ ] Disclaimer вікно при першому вході
- [ ] Антибот: challenge зображеннями
- [ ] CDN для фотографій
- [ ] Аналітика відвідувань

### Фаза 5 — Deployment
- [ ] Gunicorn + Uvicorn воркери
- [ ] Nginx reverse proxy
- [ ] SSL/HTTPS (Let's Encrypt)
- [ ] Docker-compose (app + MySQL + Redis)
- [ ] Автобекапи БД
- [ ] Моніторинг (логи, алерти)

---

## 16. ПРАВИЛА РОБОТИ З КОДОМ

### Залізні правила
1. **UI/UX не змінювати** — зовнішній вигляд і логіка лишаються як є
2. **SVG карта не чіпати** — `ukraine-map.svg` (884 КБ), `js/script.js` (WebGL)
3. **SWG не ламати** — після будь-яких змін карта і пошук мають працювати
4. **Не видаляти seed-дані** — `init_db()` ініціалізує базу при першому запуску
5. **Мова інтерфейсу** — тільки українська
6. **Тільки додавати/правити** — нічого не видаляти без явної команди

### При редагуванні Paskal.py
- Зберігати всі існуючі ендпоінти та їх URL
- Не змінювати формат відповідей (JSON-структуру)
- Нові залежності — вказати user'у для pip install
- Перевіряти: баг подвійного `app =` на рядках 11 і 240

### При редагуванні index.html / admin.html
- Всі JS-функції мають залишатись з тими ж іменами
- id HTML-елементів не змінювати (topbar, panel, sdrop, etc.)
- CSS-змінні (`--accent`, `--bg` тощо) використовувати, не хардкодити кольори
- `<style id="dynamic-colors">` — не видаляти, через нього вантажиться тема

### При редагуванні Style.css
- CSS-змінні в `:root` — не видаляти (можна додавати)
- z-index шари дотримуватись (900=fluid, 700=topbar, 9999=modals)
- Не ламати responsive поведінку

### Тест після змін
```
1. Перезапустити Paskal.py
2. Відкрити http://localhost:8000/
3. Перевірити: карта завантажилась, маркери видно
4. Виконати пошук → результати показуються
5. Кліknути маркер → панель відкрилась
6. Відкрити http://localhost:8000/admin → адмін-панель завантажилась
```

---

*Файл створено: 16.04.2026 | Оновлювати при зміні архітектури*
