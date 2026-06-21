# ADMIN_DOCUMENTATION.md — Технічна документація адмін-панелі «Зоряна Пам'ять»

> Версія: v2.1 · Оновлено: 2026-05-28  
> Аудиторія: адміністратори (role=`admin`)  
> URL панелі: `/admin` → `admin.html`

---

## Зміст

1. [Архітектура адмін-панелі](#1-архітектура)
2. [Авторизація](#2-авторизація)
3. [Навігація та розділи](#3-навігація)
4. [Дашборд (sec-stats)](#4-дашборд)
5. [Управління меморіалами (sec-mem)](#5-меморіали)
6. [Черга модерації (sec-pend)](#6-модерація)
7. [Користувачі (sec-users)](#7-користувачі)
8. [Налаштування реєстрації (sec-authreg)](#8-реєстрація)
9. [Email / SMTP (sec-emailcfg)](#9-email)
10. [Редактор карти (sec-mapeditor)](#10-редактор-карти)
11. [Соціальні мережі (sec-social)](#11-соціальні-мережі)
12. [Кольори та тема (sec-colors)](#12-кольори)
13. [Smoke / Sea / Photo ефекти](#13-ефекти)
14. [Міста (sec-cities)](#14-міста)
15. [Партнери (sec-friends)](#15-партнери)
16. [SEO-інструменти (sec-seo)](#16-seo)
17. [Щільність і видимість (sec-density)](#17-щільність)
18. [Імпорт / Експорт](#18-імпорт-експорт)
19. [Картки меморіалу (sec-card)](#19-картки)
20. [Google та аналітика](#20-google)
21. [Хвилина мовчання (sec-silence)](#21-хвилина-мовчання)
22. [Профіль адміністратора](#22-профіль)
23. [Повна схема БД](#23-база-даних)
24. [Права доступу admin vs moder](#24-права-доступу)
25. [Безпека](#25-безпека)
26. [Моніторинг та логи](#26-моніторинг)
27. [BroadcastChannel (live синхронізація)](#27-broadcastchannel)

---

## 1. Архітектура

### Стек адмін-панелі

| Компонент | Деталь |
|-----------|--------|
| Frontend | `admin.html` (~1.3MB) — Vanilla JS, без фреймворків |
| Backend | `Paskal.py` — FastAPI (Python), async |
| Auth | Cookie `admin_session` (7 діб) або Basic Auth header |
| БД | MySQL `zoryana_pamyat`, connection pool 50 |
| Кеш | Redis (опціонально, TTL 60с) |
| Іконки | SVG inline sprite (`#ico-*`) — 21 іконка |
| Теми | `admin_theme: dark|light`, перемикач у header |
| Sync | BroadcastChannel API між вкладками/сторінками |

### Файлова структура admin.html

```
admin.html
  ├─ <style>           — вбудовані стилі панелі
  ├─ SVG sprite        — #ico-stats, #ico-doc, #ico-users, …
  ├─ #sidebar          — nav list (drag-to-reorder)
  ├─ #main-content     — 28 секцій (div.sec)
  └─ <script>
       ├─ CONSTANTS     — API base URL, AWARDS_DATA_ADM, RANK_POGON_IMG
       ├─ Auth layer    — login(), autoLogin(), logout()
       ├─ Section mgmt  — showSec(), #nav-item click handlers
       ├─ 200+ функцій  — по секціях
       └─ BroadcastChannel — 'zoryana_colors', 'zoryana_sea', etc.
```

### Middleware та захист

```python
# require_admin — тільки role='admin'
def require_admin(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") != "admin":
        raise HTTPException(403, "Forbidden")
    return u

# require_moder — role='admin' або role='moder'
def require_moder(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") not in ("admin","moder"):
        raise HTTPException(403, "Forbidden")
    return u
```

---

## 2. Авторизація

### 2.1 Форма входу

**Де:** `#login-screen` — overlay поверх всього контенту

**Поля:**
- `#login-email` — email адреса (type=email)
- `#login-pass` — пароль (type=password)
- `#btn-login` — кнопка «Увійти»

**JS-функція:** `doLogin()`

**Frontend-логіка:**
```javascript
async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const pass  = document.getElementById('login-pass').value;
  // Формує Basic Auth header
  const creds = btoa(email + ':' + pass);
  const r = await fetch(API + '/api/admin/login', {
    method: 'POST',
    headers: { 'Authorization': 'Basic ' + creds }
  });
  const d = await r.json();
  if (d.ok) {
    AE = email; AP = pass;
    curAdminRole = d.user.role || 'user';
    curAdminName = d.user.name || email;
    curAdminId   = d.user.id   || 0;
    document.getElementById('login-screen').style.display = 'none';
    init();  // завантаження всіх даних
  } else {
    showToast(d.detail || 'Помилка входу', 'err');
  }
}
```

**Backend:** `POST /api/admin/login`

```python
@app.post("/api/admin/login")
def admin_login(request: Request):
    auth = request.headers.get("Authorization","")
    # Декодує Basic Auth
    email, password = base64.b64decode(auth[6:]).decode().split(":",1)
    # Перевірка brute-force: 5 спроб / 15 хв
    if not _rl.check(f"admin_login:{ip}:{email}", 5, 900):
        raise HTTPException(429, "Забагато спроб")
    # Пошук у БД
    c.execute("SELECT * FROM users WHERE email=%s AND role IN ('admin','moder')", (email,))
    # Перевірка bcrypt
    if not verify_pass(password, user["password"]):
        sec_log("ADMIN_LOGIN_FAIL", ip, email)
        raise HTTPException(401, "Невірні дані")
    # Створення сесії
    token = secrets.token_hex(32)
    _sessions[token] = {...}
    response.set_cookie("admin_session", token, max_age=604800, httponly=True)
    sec_log("ADMIN_LOGIN_OK", ip, email)
    return {"ok": True, "user": {...}}
```

**БД:** `SELECT * FROM users WHERE email=%s AND role IN ('admin','moder')`

**Захист:**
- Rate limit: 5 спроб / 15 хвилин per IP+email → HTTP 429
- bcrypt 12 rounds verification
- Security log: `ADMIN_LOGIN_FAIL` / `ADMIN_LOGIN_OK`
- Cookie: `httponly=True`, `max_age=604800` (7 днів)

**Що бачить адмін:** при успіху — overlay зникає, завантажується панель; при помилці — toast «Невірні дані».

---

### 2.2 Авто-вхід

**JS-функція:** `autoLogin()`

```javascript
async function autoLogin() {
  const r = await fetch(API + '/api/admin/me');
  if (r.ok) {
    const u = await r.json();
    AE = u.email || ''; AP = '';
    curAdminRole = u.role || 'user';
    curAdminName = u.name || 'Admin';
    curAdminId   = u.id   || 0;
    document.getElementById('login-screen').style.display = 'none';
    init();
  }
}
```

**Backend:** `GET /api/admin/me`

```python
@app.get("/api/admin/me")
def admin_me(request: Request):
    u = require_moder(request)
    return u
```

**Логіка:** при завантаженні сторінки перевіряє cookie `admin_session` → якщо валідна і не протермінована (7 діб) → auto-login без форми.

---

### 2.3 Вихід

**JS-функція:** `doLogout()`

**Backend:** `POST /api/admin/logout` — видаляє `_sessions[token]`, очищує cookie.

---

## 3. Навігація

### 3.1 Sidebar (nav list)

**Структура:** `#sidebar` → `ul#nav-list` → `li.nav-item[data-sec="..."]`

**28 розділів (секцій):**

| data-sec | Назва | Іконка | Доступ |
|----------|-------|--------|--------|
| `stats` | Статистика | `#ico-stats` | moder+ |
| `mem` | Всі записи | `#ico-doc` | moder+ |
| `pend` | На модерації | `#ico-hourglass` | moder+ |
| `users` | Користувачі | `#ico-users` | admin |
| `authreg` | Реєстрація | `#ico-auth` | admin |
| `emailcfg` | Email/SMTP | `#ico-email` | admin |
| `mapeditor` | Редактор карти | `#ico-map` | admin |
| `social` | Соціальні мережі | `#ico-share` | admin |
| `colors` | Кольори | `#ico-palette` | admin |
| `smoke` | Дим | `#ico-smoke` | admin |
| `sea` | Море | `#ico-waves` | admin |
| `photo` | Фото карти | `#ico-photo` | admin |
| `icons` | Іконки | `#ico-star` | admin |
| `cities` | Міста | `#ico-city` | admin |
| `friends` | Партнери | `#ico-candle` | admin |
| `silence` | Хвилина мовчання | `#ico-candle` | admin |
| `seo` | SEO | `#ico-search` | moder+ |
| `card` | Картки | `#ico-doc` | admin |
| `version` | Версія | `#ico-stats` | admin |
| `density` | Щільність | `#ico-map` | moder+ |
| `google` | Google | `#ico-search` | admin |

### 3.2 Drag-to-reorder nav

**JS-функції:** `_initNavDrag()`, `_saveNavOrder()`

**Логіка:** `dragstart` / `dragover` / `drop` на `li.nav-item` → сортує масив → PUT `/api/admin/color` з ключем `admin_nav_order` (comma-separated list).

**БД:** `UPDATE colors SET value=%s WHERE key='admin_nav_order'`

### 3.3 Перемикач теми

**Функція:** `toggleAdminTheme()`

**Логіка:** читає `admin_theme` з colors → перемикає між `dark`/`light` → PUT `/api/admin/color` → застосовує CSS-клас `body.theme-light`.

---

## 4. Дашборд (sec-stats)

### 4.1 Загальна статистика

**JS-функція:** `loadStats()`

**Backend:** `GET /api/admin/stats`

```python
@app.get("/api/admin/stats")
def admin_stats(request: Request):
    require_moder(request)
    # COUNT всіх, approved, pending, users, likes, online
    c.execute("SELECT COUNT(*) FROM memorials")
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=1")
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=0")
    c.execute("SELECT COUNT(*) FROM users")
    c.execute("SELECT SUM(likes) FROM memorials")
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen > %s AND is_banned=0", (time.time()-300,))
    return {total, approved, pending, users, likes, online}
```

**Що відображається:**
- `#stat-total` — всього записів
- `#stat-approved` — опублікованих
- `#stat-pending` — очікують модерації
- `#stat-users` — зареєстрованих користувачів
- `#stat-likes` — сумарно лайків
- `#stat-online` — онлайн зараз

### 4.2 Серверна статистика

**JS-функція:** `loadServerStats()`

**Backend:** `GET /api/admin/server-stats`

```python
@app.get("/api/admin/server-stats")
def server_stats(request: Request):
    require_moder(request)
    # psutil — CPU%, RAM%, uptime
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    uptime = time.time() - _START_TIME
    return {cpu, ram_used, ram_total, ram_percent, uptime_seconds}
```

**Що відображається:** `#stat-cpu`, `#stat-ram`, `#stat-uptime` — у реальному часі.

### 4.3 Графік запитів (Chart.js)

**JS-функція:** `loadRequestChart()`

**Backend:** `GET /api/admin/request-log` (або аналог) — 24-годинна статистика запитів.

**Рендеринг:** `new Chart(ctx, {type: 'line', ...})` — лінійний графік за останні 24 год.

---

## 5. Меморіали (sec-mem)

### 5.1 Завантаження списку

**JS-функції:** `loadMem()`, `memDoSearch()`, `memRender()`

**Стан:**
```javascript
let allPeople = [];      // всі записи (завантажені з API)
let filteredPeople = []; // після пошуку/фільтру
let memPage = 1;
let memPageSize = 25;    // 10/25/50/100/200/Всі
```

**Backend:** `GET /api/admin/memorials?page=1&limit=500`

```python
@app.get("/api/admin/memorials")
def admin_all_memorials(page: int=1, limit: int=100, request: Request=None):
    require_moder(request)
    limit = max(1, min(limit, 500))
    offset = (page-1) * limit
    c.execute("SELECT * FROM memorials ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
    c.execute("SELECT COUNT(*) FROM memorials")
    return {"items": rows, "total": total, "page": page, "limit": limit}
```

**БД:** `SELECT * FROM memorials ORDER BY id DESC LIMIT %s OFFSET %s`

**Рендеринг таблиці:** `memRender()` — генерує рядки `<tr>` з:
- id, ПІБ, локація, статус (approved badge), лайки, кнопки [редагувати / видалити]

**Пошук:** `memDoSearch(q)` — локальний фільтр `filteredPeople` по полям `last`, `first`, `mid`, `loc`

**Пагінація:** `memSetPageSize(n)` — перемикач кількості рядків на сторінку; `memPage()` — кнопки Вперед/Назад.

### 5.2 Редагування меморіалу

**JS-функції:** `openEditById(id)`, `saveEdit()`, `_buildEditModal(data)`

**Де:** модальне вікно `#edit-modal`

**Відкриття:**
```javascript
async function openEditById(id) {
  const r = await fetch(API + '/api/memorial/' + id);
  const d = await r.json();
  _buildEditModal(d);  // заповнює поля форми
  document.getElementById('edit-modal').style.display = 'flex';
}
```

**Поля форми EditModal:**

| Поле | Тип | Валідація |
|------|-----|-----------|
| `em-last` | text | required, max 100 |
| `em-first` | text | required, max 100 |
| `em-mid` | text | max 100 (позивний) |
| `em-birth` | text | формат дати |
| `em-death` | text | формат дати |
| `em-loc` | text | max 300 |
| `em-bury` | text | max 300 |
| `em-circ` | text | max 500 |
| `em-descr` | textarea | TEXT |
| `em-photo` | url | SSRF check |
| `em-video` | url | YouTube only |
| `em-rank` | text | max 100 |
| `em-position` | text | max 100 |
| `em-unit` | text | max 200 |
| `em-grp` | text | max 100 |
| `em-color` | color | hex |
| `em-approved` | checkbox | 0/1 |

**Збереження:**
```javascript
async function saveEdit() {
  const id = document.getElementById('em-id').value;
  const payload = { last, first, mid, birth, death, loc, bury, circ,
                    descr, photo, video_url, rank, position, unit, grp,
                    color, approved, pos_x, pos_y };
  const r = await fetch(API + '/api/admin/memorial/' + id, {
    method: 'PUT', headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if (r.ok) { loadMem(); showToast('Збережено'); closeModal('edit-modal'); }
}
```

**Backend:** `PUT /api/admin/memorial/{mid}`

```python
@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid: int, p: PersonUpdate, request: Request):
    require_moder(request)
    # _sanitize_text() для всіх текстових полів
    # _validate_photo_url() — SSRF check
    # _validate_yt_url() — YouTube validation
    # auto-update slug при зміні ПІБ:
    if p.first or p.last:
        sl = make_slug(first, last, mid)
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, mid))
    c.execute("UPDATE memorials SET last=%s, first=%s, ... WHERE id=%s", (..., mid))
    db.commit()
    cache_flush_memorials()
    return {"ok": True}
```

**БД:** `UPDATE memorials SET ... WHERE id=%s`

**SQL приклад:**
```sql
UPDATE memorials
SET last='Шевченко', first='Іван', mid='Олексійович',
    birth='1995-03-15', death='2023-08-22', loc='Бахмут',
    photo='https://...', approved=1, slug='ivan-shevchenko-42'
WHERE id=42
```

**Безпека:**
- `_sanitize_text()` — видаляє HTML-теги з текстових полів
- `_validate_photo_url()` — блокує приватні IP (SSRF)
- `_validate_yt_url()` — перевіряє YouTube домен
- Параметризовані запити — захист від SQL injection

**Що бачить адмін:** toast «Збережено» / «Помилка» + оновлена таблиця.

---

### 5.3 Видалення меморіалу

**JS-функція:** `deleteMemorial(id)`

**Backend:** `DELETE /api/admin/memorial/{mid}` — **тільки admin**

```python
@app.delete("/api/admin/memorial/{mid}")
def delete_memorial(mid: int, request: Request):
    me = require_admin(request)  # ТІЛЬКИ ADMIN!
    ip = _get_ip(request)
    c.execute("SELECT last, first FROM memorials WHERE id=%s", (mid,))
    c.execute("DELETE FROM memorials WHERE id=%s", (mid,))
    db.commit()
    sec_log("DELETE_MEMORIAL", ip, f"id={mid} name={name} by={me['email']}")
    cache_flush_memorials()
    return {"ok": True}
```

**SQL:** `DELETE FROM memorials WHERE id=%s`

**Логування:** `sec_log("DELETE_MEMORIAL", ip, "id=... name=... by=...")` → `logs/security.log`

**Що бачить адмін:** підтвердження `confirm()` → toast «Видалено» → рядок зникає з таблиці.

---

### 5.4 Нагороди меморіалу

**JS-функції:** `loadAwards(id)`, `addAward(id)`, `deleteAward(awardId)`

**Де:** вкладка «Нагороди» всередині `#edit-modal`

**Завантаження списку нагород меморіалу:**
```javascript
async function loadAwards(memId) {
  const r = await fetch(API + '/api/memorial/' + memId + '/awards');
  // рендерить список з кнопками видалення
}
```

**Backend:** `GET /api/memorial/{id}/awards`

```python
@app.get("/api/memorial/{mid}/awards")
def get_memorial_awards(mid: int):
    c.execute("SELECT * FROM memorial_awards WHERE memorial_id=%s ORDER BY sort_order", (mid,))
    return rows
```

**Додавання нагороди:**
```javascript
async function addAward(memId) {
  // Відкриває вибірку з AWARDS_DATA_ADM (каталог)
  // AWARDS_DATA_ADM завантажується при старті: GET /api/awards/catalog
  const award = selectedFromCatalog;
  await fetch(API + '/api/admin/memorial/' + memId + '/awards', {
    method: 'POST',
    body: JSON.stringify({ name, img_file, award_date, descr, sort_order })
  });
}
```

**Backend:** `POST /api/admin/memorial/{mid}/awards`

```python
@app.post("/api/admin/memorial/{mid}/awards")
def add_award(mid: int, a: AwardIn, request: Request):
    require_moder(request)
    c.execute("""INSERT INTO memorial_awards
                (memorial_id, name, img_file, award_date, descr, sort_order)
                VALUES (%s,%s,%s,%s,%s,%s)""",
              (mid, a.name, a.img_file, a.award_date, a.descr, a.sort_order))
    db.commit()
    return {"ok": True, "id": c.lastrowid}
```

**Видалення нагороди:**

`DELETE /api/admin/awards/{id}` — доступно moder+

**БД:** таблиця `memorial_awards`

**Каталог нагород:**
```javascript
// Завантажується один раз при старті панелі:
async function _loadAwardsCatalog() {
  const r = await fetch(API + '/api/awards/catalog');
  AWARDS_DATA_ADM = await r.json();
  // 31+ нагорода: name, img_file, category, description
}
```

**Зображення нагород:** `_wikiImg(file)` → `/img/awards/${encodeURIComponent(file)}` (локальні PNG, НЕ Wikimedia CDN!)

---

## 6. Модерація (sec-pend)

### 6.1 Черга модерації

**JS-функція:** `loadPending()`

**Backend:** `GET /api/admin/pending`

```python
@app.get("/api/admin/pending")
def pending(request: Request):
    require_moder(request)
    c.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC")
    return rows
```

**БД:** `SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC`

**Рендеринг:** кожен запис відображається карткою з:
- ПІБ, дата додавання, автор (`added_by`), фото (якщо є)
- Кнопки: [Схвалити] [Видалити]

**Лічильник у badge:** `#pend-nb` — оновлюється після `loadPending()`.

### 6.2 Схвалення запису

**JS-функція:** `approveMem(id)`

**Backend:** `POST /api/admin/approve/{mid}`

```python
@app.post("/api/admin/approve/{mid}")
def approve(mid: int, request: Request):
    require_moder(request)
    c.execute("UPDATE memorials SET approved=1 WHERE id=%s", (mid,))
    # Якщо slug відсутній — генерується автоматично:
    c.execute("SELECT id, first, last, slug FROM memorials WHERE id=%s", (mid,))
    row = c.fetchone()
    if row and not row.get('slug'):
        sl = make_slug(row['first'], row['last'], row['id'])
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, mid))
    db.commit()
    cache_flush_memorials()
    cache_delete("sitemap")
    return {"ok": True}
```

**SQL:**
```sql
UPDATE memorials SET approved=1 WHERE id=42;
UPDATE memorials SET slug='ivan-petrenko-42' WHERE id=42;
```

**Slug-генерація:** `seo_utils.make_slug(first, last, id)` — транслітерація KMU 2010, формат `{first}-{last}-{id}`.

**Кеш:** після схвалення — `cache_flush_memorials()` + `cache_delete("sitemap")` (Redis).

**Що бачить moder:** картка зникає з черги, з'являється toast «Схвалено».

### 6.3 Відхилення запису

**JS-функція:** `delMem(id)`

**Backend:** `DELETE /api/admin/memorial/{mid}` — **тільки admin**

**Що бачить moder:** кнопка [Видалити] недоступна, лише [Схвалити].

---

## 7. Користувачі (sec-users)

### 7.1 Список користувачів

**JS-функції:** `loadUsers()`, `usersRender()`, `usersDoSearch(q)`

**Стан:**
```javascript
let _usersData = [];      // всі користувачі
let _filteredUsers = [];  // після фільтру/пошуку
let _usersPage = 1;
let _usersPageSize = 25;  // 10/25/50/100/Всі
```

**Backend:** `GET /api/admin/users` — **тільки admin**

```python
@app.get("/api/admin/users")
def get_users(request: Request):
    require_admin(request)
    c.execute("""SELECT id,name,first_name,last_name,nickname,email,phone,
                        role,is_banned,ban_until,last_seen,created,notes
                 FROM users ORDER BY id DESC""")
    return rows
```

**Рендеринг:** таблиця з колонками: id, ім'я, email, нік, роль (badge), статус (banned?), остання активність, кнопки.

**Пошук:** `usersDoSearch(q)` — локально по `email`, `name`, `nickname`.

**Фільтри:** за роллю (`all|admin|moder|user`) та статусом (`all|active|banned`).

**Пагінація:** `usersPage(delta)`, `usersSetPageSize(n)`.

### 7.2 Модал редагування користувача

**JS-функція:** `openUserModal(uid)`

**Де:** `#user-modal`

**Поля:**
- `#um-uid` (hidden) — id
- `#um-name` — повне ім'я
- `#um-email` — email + `#um-email-avail` (real-time перевірка)
- `#um-role` — select: admin/moder/user
- `#um-notes` — textarea нотатки
- `#um-banned` — checkbox заблокований
- `#um-ban-until` — datetime закінчення бану

**Збереження:**
```javascript
async function saveUser() {
  const uid = document.getElementById('um-uid').value;
  // Паралельно: PUT user + PUT role (якщо змінилась)
  await Promise.all([
    fetch(API + '/api/admin/user/' + uid, {
      method: 'PUT',
      body: JSON.stringify({ name, email, notes })
    }),
    fetch(API + '/api/admin/users/' + uid + '/role', {
      method: 'PUT',
      body: JSON.stringify({ role })
    })
  ]);
}
```

**Backend:**
- `PUT /api/admin/user/{uid}` — оновлення name/email/notes/password
- `PUT /api/admin/users/{uid}/role` — зміна ролі (тільки admin, не власної)

**SQL (зміна ролі):**
```sql
UPDATE users SET role='moder', is_admin=0 WHERE id=5
```

**Логування:**
```python
sec_log("ROLE_CHANGE", ip, f"uid={uid} email={email} admin->moder by={me['email']}")
```

**Обмеження:**
- Адмін не може змінити власну роль
- Адмін не може видалити власний акаунт
- Скидання пароля: тільки для admin/moder (не user); rate limit 10/год

### 7.3 Видалення користувача

**JS-функція:** `deleteUser(uid)`

**Backend:** `DELETE /api/admin/user/{uid}` — **тільки admin**

```python
@app.delete("/api/admin/user/{uid}")
def delete_user(uid: int, request: Request):
    me = require_admin(request)
    if uid == me["id"]:
        raise HTTPException(400, "Не можна видалити власний акаунт")
    # Захист: видаляє лише якщо is_admin=0 (звичайні user)
    c.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid,))
    db.commit()
    return {"ok": True}
```

**SQL:** `DELETE FROM users WHERE id=%s AND is_admin=0`

### 7.4 Блокування користувача

**JS-функція:** `banUser(uid, duration, reason)`

**Backend:** `POST /api/admin/ban/{uid}` — **тільки admin**

```python
@app.post("/api/admin/ban/{uid}")
def ban_user(uid: int, body: BanBody, request: Request):
    require_admin(request)
    ban_until = int(time.time()) + body.duration_hours * 3600
    c.execute("UPDATE users SET is_banned=1, ban_until=%s WHERE id=%s", (ban_until, uid))
    sec_log("USER_BAN", ip, f"uid={uid} hours={body.duration_hours}")
    return {"ok": True}
```

**SQL:**
```sql
UPDATE users SET is_banned=1, ban_until=1748563200 WHERE id=7
```

**Розблокування:** `POST /api/admin/unban/{uid}`

```sql
UPDATE users SET is_banned=0, ban_until=0 WHERE id=7
```

### 7.5 Скидання пароля

**JS-функція:** `resetUserPassword(uid)`

**Backend:** `PUT /api/admin/user/{uid}` з полем `new_password`

```python
if body.new_password is not None:
    if uid == me["id"]:
        raise HTTPException(400, "Використовуйте 'Мій профіль'")
    if not _rl.check(f"admin_pwreset:{ip}", 10, 3600):
        raise HTTPException(429, "Забагато спроб")
    _validate_password(body.new_password)
    # Тільки для admin/moder:
    c.execute("SELECT role FROM users WHERE id=%s", (uid,))
    if target["role"] not in ("admin","moder"):
        raise HTTPException(403, "Тільки для адмінів/модераторів")
    c.execute("UPDATE users SET password=%s WHERE id=%s", (hash_pass(new_pass), uid))
    sec_log("PASSWORD_RESET_BY_ADMIN", ip, f"target={uid} by={me['email']}")
```

**Rate limit:** 10 спроб / 1 година per IP.

### 7.6 Перемикач реєстрації

**Де:** `#sec-users` — кнопка «Відкрити/Закрити реєстрацію»

**JS-функція:** `toggleRegistration()`

**Backend:** `PUT /api/admin/color` → `key=reg_enabled`, `value=0|1`

---

## 8. Налаштування реєстрації (sec-authreg)

**Де:** секція `#sec-authreg`

### Ключі таблиці `colors` для реєстрації

| Ключ | Тип | Значення | Опис |
|------|-----|---------|------|
| `reg_enabled` | bool | `1` / `0` | Відкрита/закрита реєстрація |
| `reg_allow_google` | bool | `1` / `0` | Дозволити вхід через Google |
| `reg_field_mid` | bool | `1` / `0` | Показувати поле «по батькові» |
| `reg_field_phone` | bool | `1` / `0` | Показувати поле «телефон» |
| `reg_require_email_verify` | bool | `1` / `0` | Обов'язкова верифікація email |
| `reg_min_pass_len` | int | `8` | Мінімальна довжина пароля |
| `reg_welcome_msg` | text | `''` | Вітальне повідомлення після реєстрації |

**JS-функція:** `saveAuthRegSettings()`

**Backend:** `PUT /api/admin/color` для кожного ключа

```javascript
async function saveAuthRegSettings() {
  const keys = ['reg_enabled','reg_allow_google','reg_field_mid',
                 'reg_field_phone','reg_require_email_verify','reg_min_pass_len'];
  for (const key of keys) {
    await fetch(API + '/api/admin/color', {
      method: 'PUT',
      body: JSON.stringify({ key, value: getFieldValue(key) })
    });
  }
  showToast('Збережено');
}
```

**SQL:**
```sql
UPDATE colors SET value='0' WHERE `key`='reg_enabled'
```

---

## 9. Email / SMTP (sec-emailcfg)

**Де:** секція `#sec-emailcfg`

### Конфігурація SMTP

**Ключі в `colors`:**

| Ключ | Опис |
|------|------|
| `smtp_host` | Хост (напр. `smtp.gmail.com`) |
| `smtp_port` | Порт (465/587/25) |
| `smtp_user` | Логін |
| `smtp_pass` | Пароль (зберігається в БД!) |
| `smtp_from` | Адреса відправника |
| `smtp_secure` | `ssl` / `tls` / `none` |
| `smtp_enabled` | `1` / `0` |

### Presets

**JS-функція:** `applyEmailPreset(name)`

Доступні presets: `gmail`, `ukrnet`, `outlook`, `yahoo`, `meta` — автозаповнюють `smtp_host` та `smtp_port`.

### Тест-відправлення

**JS-функція:** `testEmail()`

**Backend:** `POST /api/admin/email/test`

```python
@app.post("/api/admin/email/test")
def test_email(body: EmailTestBody, request: Request):
    require_admin(request)
    # Завантажує SMTP налаштування з colors
    # smtplib.SMTP / SMTP_SSL → надсилає тестовий лист
    # Повертає {ok: True} або {error: "..."}
```

**Що бачить адмін:** toast «Лист надіслано» або деталь помилки SMTP.

---

## 10. Редактор карти (sec-mapeditor)

**Де:** секція `#sec-mapeditor` — iframe-подібний SVG-редактор

### 10.1 Режими редактора

| Режим | Кнопка | Призначення |
|-------|--------|-------------|
| `labels` | «Підписи» | Переміщення підписів областей |
| `dots` | «Маркери» | Переміщення маркерів меморіалів |
| `cities` | «Міста» | Переміщення точок міст |

**JS-функція:** `setMapMode(mode)`

### 10.2 Pan / Zoom редактора

**JS-функції:** `mapEditorWheel()`, `mapEditorDrag()`, `applyEditorTr()`

Трансформація SVG: `scale(zoom) translate(tx, ty)` — аналогічно до публічної карти.

### 10.3 Редагування підписів областей

**JS-функція:** `startDragLabel(lid)`, `saveLabelPos(lid, x, y)`

**Backend:** `PUT /api/admin/label/{lid}`

```python
@app.put("/api/admin/label/{lid}")
def update_label(lid: int, body: LabelUpdate, request: Request):
    require_admin(request)
    c.execute("UPDATE map_labels SET x=%s, y=%s, name=%s, color=%s, size=%s WHERE id=%s",
              (body.x, body.y, body.name, body.color, body.size, lid))
    db.commit()
    return {"ok": True}
```

**SQL:**
```sql
UPDATE map_labels SET x=5420.5, y=3100.2, color='rgba(160,195,220,0.45)' WHERE id=12
```

**Примітка:** `x/y` — координати у просторі SVG (великі числа ~1000–12000), НЕ нормалізовані!

### 10.4 Переміщення маркерів меморіалів

**JS-функція:** `startDragDot(id)`, `saveDotPos(id, px, py)`

**Backend:** `PUT /api/admin/memorial/{id}` з полями `pos_x`, `pos_y`

**Нормалізація:** `pos_x = clientX / editorWidth` (0.0–1.0)

**SQL:**
```sql
UPDATE memorials SET pos_x=0.4512, pos_y=0.3201 WHERE id=42
```

### 10.5 Переміщення міст

**JS-функція:** `startDragCity(id)`, `saveCityPos(id, px, py)`

**Backend:** `PUT /api/admin/city/{id}`

```python
@app.put("/api/admin/city/{cid}")
def update_city(cid: int, body: CityUpdate, request: Request):
    require_admin(request)
    c.execute("UPDATE cities SET pos_x=%s, pos_y=%s WHERE id=%s", (body.pos_x, body.pos_y, cid))
    db.commit()
    return {"ok": True}
```

---

## 11. Соціальні мережі (sec-social)

**Де:** секція `#sec-social`

### Структура

**8 соціальних мереж:** Facebook, Twitter/X, Instagram, YouTube, Telegram, TikTok, LinkedIn, Viber

**Ключі в `colors`:**
- `social_{id}` — `1`/`0` (показувати/приховати)
- `social_{id}_url` — URL профілю
- `social_order` — порядок (comma-separated: `facebook,twitter,...`)

### Drag-to-reorder

**JS-функція:** `_initSocialDrag()`, `_saveSocialOrder()`

Логіка аналогічна drag nav: перетягування карток → оновлення `social_order`.

### Toggle видимості

**JS-функція:** `toggleSocial(id, val)`

**Backend:** `PUT /api/admin/color` → `key=social_telegram`, `value=1`

### Зміна URL

**JS-функція:** `saveSocialUrl(id)`

**Backend:** `PUT /api/admin/color` → `key=social_telegram_url`, `value=https://t.me/...`

### Batch збереження

**Backend:** `POST /api/admin/colors/batch` — **тільки admin**

```python
@app.post("/api/admin/colors/batch")
def colors_batch(body: ColorsBatch, request: Request):
    require_admin(request)
    for item in body.items:
        c.execute("INSERT INTO colors (`key`,value,label) VALUES (%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE value=VALUES(value)", (item.key, item.value, item.label))
    db.commit()
    return {"ok": True}
```

**SQL:**
```sql
INSERT INTO colors (`key`,value,label) VALUES ('social_telegram','1','Telegram')
ON DUPLICATE KEY UPDATE value=VALUES(value)
```

**Live синхронізація:** після збереження надсилається BroadcastChannel повідомлення → index.html оновлює соцмережі без перезавантаження.

---

## 12. Кольори та тема (sec-colors)

**Де:** секція `#sec-colors`

### Підгрупи налаштувань кольорів

| Підгрупа | Ключі | Опис |
|----------|-------|------|
| `glow` | `glow_color`, `glow_spread`, `glow_outer_color`, `glow_outer_spread` | Свічення кордону |
| `zoom` | `zoom_min`, `zoom_max`, `city_border_zoom` | Рівні зуму |
| `dot` | `dot_pulse_speed`, `dot_glow_intensity`, `dot_twinkle`, ... | Маркери-зірки |
| `map` | `oblast_fill`, `oblast_stroke`, `neon_blue`, `neon_yellow`, ... | Карта |
| `bg` | `bg`, `surface`, `map_bg` | Фони |
| `text` | `text_primary`, `text_secondary` | Текст |
| `logo` | `logo_star`, `logo_text`, `logo_accent` | Логотип |
| `admin` | `admin_theme`, `admin_nav_order` | Адмін-панель |
| `card` | `card_bg`, `card_*` | Публічні картки |

### Редагування кольорів

**JS-функція:** `onClrChange(key, value)`

**Логіка:**
```javascript
const _pendingColors = {};  // накопичувач змін

function onClrChange(key, val) {
  _pendingColors[key] = val;
  // Preview: оновлює CSS variable без збереження в БД
  document.documentElement.style.setProperty('--' + key, val);
  // Auto-save після debounce 800ms:
  clearTimeout(_colorSaveTimer);
  _colorSaveTimer = setTimeout(_autoSaveToDb, 800);
}
```

**Збереження:**
```javascript
async function saveAllColors() {
  // POST /api/admin/colors/batch з _pendingColors
  const items = Object.entries(_pendingColors).map(([key,value]) => ({key,value}));
  await fetch(API + '/api/admin/colors/batch', {
    method: 'POST',
    body: JSON.stringify({ items })
  });
  // BroadcastChannel → live update main site
  new BroadcastChannel('zoryana_colors').postMessage({ type: 'update', colors: _pendingColors });
}
```

**Backend:** `POST /api/admin/colors/batch` — **тільки admin**

**БД:**
```sql
INSERT INTO colors (`key`,value) VALUES ('neon_yellow','#f0c030')
ON DUPLICATE KEY UPDATE value=VALUES(value)
```

**Live preview:** зміни кольорів відображаються в реальному часі через CSS variables без збереження — зручно для підбору.

---

## 13. Ефекти (sec-smoke / sec-sea / sec-photo)

### 13.1 Дим (sec-smoke)

**Ключі в `colors`:** `smoke_enabled`, `smoke_density`, `smoke_velocity`, `smoke_splat_radius`, `smoke_splat_force`, `smoke_curl`, `smoke_opacity`, `smoke_color_from`, `smoke_color_to`

**JS-функція:** `saveSmoke()`

**Backend:** `POST /api/admin/colors/batch`

**BroadcastChannel:** `'zoryana_colors'` → index.html перезапускає WebGL симуляцію диму.

### 13.2 Море (sec-sea)

**Ключі в `colors`:** `sea_enabled`, `sea_wave_color`, `sea_wave_count`, `sea_wave_intensity`, `sea_wave_speed`, `sea_wave_dir`, `sea_shore_impact`, `sea_blur`, `sea_glow_on`, `sea_glow_color`, `sea_glow_spread`, `sea_svg_tx`, `sea_svg_ty`, `sea_svg_scale`, `sea_svg_content`

**Завантаження SVG:** `uploadSeaSvg()`

**Backend:** `POST /api/admin/sea-svg`

```python
@app.post("/api/admin/sea-svg")
async def upload_sea_svg(request: Request, file: UploadFile = File(...)):
    require_admin(request)
    content = await file.read()
    # _sanitize_svg() — видаляє script, on*, foreignObject, use
    safe_svg = _sanitize_svg(content.decode())
    c.execute("UPDATE colors SET value=%s WHERE key='sea_svg_content'", (safe_svg,))
    db.commit()
    return {"ok": True}
```

**SVG sanitization:**
```python
def _sanitize_svg(svg: str) -> str:
    # Видаляє <script>, on* атрибути, <foreignObject>, <use>
    # Блокує href/xlink:href на зовнішні ресурси
    return cleaned_svg
```

**BroadcastChannel:** `'zoryana_sea'` → index.html оновлює SVG overlay моря.

### 13.3 Фото карти (sec-photo)

**Ключі:** `map_photo_url`, `map_photo_opacity`, `map_photo_blend`, `map_photo_feather`, `map_photo_scale`

**JS-функція:** `saveMapPhoto()`

**Перевірка URL:** SSRF check через `_validate_photo_url()` — блокує `localhost`, `127.x`, `10.x`, `192.168.x`.

**Backend:** `PUT /api/admin/color` для кожного ключа.

---

## 14. Міста (sec-cities)

**Де:** секція `#sec-cities`

### 14.1 Список міст

**JS-функція:** `loadCities()`

**Backend:** `GET /api/admin/cities`

```python
@app.get("/api/admin/cities")
def get_cities(request: Request):
    require_admin(request)
    c.execute("SELECT * FROM cities ORDER BY tier DESC, name")
    return rows
```

**Рендеринг:** таблиця з колонками: id, назва, tier, pos_x/pos_y, колір, кнопки [редагувати / видалити].

**Пошук/фільтр:** `citiesDoSearch(q)`, фільтр за `tier` (0–3) та placement (показані/всі).

### 14.2 Tier рівні

| tier | Кількість | Призначення |
|------|-----------|-------------|
| `0` | 435 | Звичайні міста/смт — не показуються на малих зумах |
| `1` | 21 | Обласні центри |
| `2` | 5 | Великі міста (Харків, Одеса, ...) |
| `3` | 2 | Столиця (Київ) |

### 14.3 Додавання міста

**JS-функція:** `addCity()`

**Backend:** `POST /api/admin/city`

```python
@app.post("/api/admin/city")
def create_city(body: CityCreate, request: Request):
    require_admin(request)
    c.execute("INSERT INTO cities (name, pos_x, pos_y, tier, color) VALUES (%s,%s,%s,%s,%s)",
              (body.name, body.pos_x, body.pos_y, body.tier, body.color or '#a0d7ff'))
    db.commit()
    return {"ok": True, "id": c.lastrowid}
```

### 14.4 Редагування міста (inline)

**JS-функція:** `saveCity(id)`

**Backend:** `PUT /api/admin/city/{id}`

**SQL:**
```sql
UPDATE cities SET name='Запоріжжя', pos_x=0.612, pos_y=0.581, tier=1, color='#a0d7ff' WHERE id=15
```

### 14.5 Видалення міста

**Backend:** `DELETE /api/admin/city/{id}` — тільки admin

### 14.6 Перехід до міста на карті

**JS-функція:** `goToCityOnMap(id)` — показує місто в редакторі карти.

---

## 15. Партнери (sec-friends)

**Де:** секція `#sec-friends`

### 15.1 Список партнерів

**JS-функція:** `loadPartners()`

**Backend:** `GET /api/admin/partners`

```python
@app.get("/api/admin/partners")
def get_partners(request: Request):
    require_admin(request)
    c.execute("SELECT * FROM partners ORDER BY id")
    return rows
```

### Поля партнера

| Поле | Тип | Опис |
|------|-----|------|
| `name` | VARCHAR | Назва організації |
| `image_url` | VARCHAR | URL логотипу |
| `link_url` | VARCHAR | URL сайту партнера |
| `caption` | VARCHAR | Підпис |
| `width` | INT | Ширина відображення (px) |
| `opacity` | FLOAT | Прозорість (0.0–1.0) |
| `pos_x` | FLOAT | X-позиція (для розміщення на карті) |
| `pos_y` | FLOAT | Y-позиція |
| `is_visible` | TINYINT | 1=видимий, 0=прихований |

### 15.2 CRUD партнерів

**Backend:**
- `POST /api/admin/partner` — додати
- `PUT /api/admin/partner/{id}` — оновити
- `DELETE /api/admin/partner/{id}` — видалити

**BroadcastChannel:** `'zoryana_partners'` → index.html оновлює overlay партнерів.

---

## 16. SEO (sec-seo)

**Де:** секція `#sec-seo`

### 16.1 SEO Dashboard

**JS-функція:** `loadSeoDashboard()`

**Backend:** `GET /api/admin/seo-dashboard`

```python
@app.get("/api/admin/seo-dashboard")
def seo_dashboard(request: Request):
    require_moder(request)
    # Статистика slug: total, with_slug, without_slug, percent
    # Статистика Google Indexing API: сents, errors
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=1")
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=1 AND slug IS NOT NULL")
    c.execute("SELECT * FROM seo_index_log ORDER BY created_at DESC LIMIT 20")
    return {...}
```

**Що відображається:** прогрес-бар покриття slug, остання активність Google Indexing API.

### 16.2 SEO Scores

**JS-функція:** `loadSeoScores(grade)`

**Backend:** `GET /api/admin/seo/scores?grade=A|B|C|D|F`

**Логіка оцінки (calc_seo_score):**
```python
def calc_seo_score(m: dict) -> int:
    score = 0
    if m.get('photo'):     score += 20   # фото є
    if m.get('descr'):     score += 20   # опис є
    if m.get('birth'):     score += 10   # дата народження
    if m.get('death'):     score += 10   # дата загибелі
    if m.get('loc'):       score += 10   # місце загибелі
    if m.get('unit'):      score += 10   # підрозділ
    if m.get('video_url'): score += 10   # відео
    if m.get('slug'):      score += 10   # slug
    return min(score, 100)
```

**Оцінки:** A (85–100), B (70–84), C (50–69), D (<50)

### 16.3 Аналіз окремого меморіалу

**JS-функція:** `analyzeSeoCard(id)`

**Backend:** `GET /api/admin/seo/analyze/{mid}`

```python
@app.get("/api/admin/seo/analyze/{mid}")
def seo_analyze(mid: int, request: Request):
    require_moder(request)
    c.execute("SELECT * FROM memorials WHERE id=%s", (mid,))
    m = c.fetchone()
    score = calc_seo_score(m)
    recs = []
    if not m.get('photo'):   recs.append("Додати фото")
    if not m.get('descr'):   recs.append("Додати опис")
    # ...
    return {"score": score, "grade": grade, "recommendations": recs, "title": gen_seo_title(m), ...}
```

### 16.4 Регенерація slug

**JS-функція:** `regenerateSlugs()`

**Backend:** `POST /api/admin/seo/regenerate-slugs`

```python
@app.post("/api/admin/seo/regenerate-slugs")
def regen_slugs(request: Request):
    require_moder(request)
    c.execute("SELECT id,first,last FROM memorials WHERE slug IS NULL AND approved=1")
    for row in c.fetchall():
        sl = make_slug(row['first'], row['last'], row['id'])
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, row['id']))
    db.commit()
    cache_delete("sitemap")
    return {"ok": True, "count": updated}
```

**SQL:**
```sql
UPDATE memorials SET slug='petro-kovalenko-17' WHERE id=17 AND slug IS NULL
```

### 16.5 Google Indexing API Ping

**JS-функція:** `pingGoogle()`

**Backend:** `POST /api/admin/seo/ping-google`

```python
# Відправляє approved memorials до Google Indexing API
# Вимагає google-service-account.json в .env
# Записує результат в seo_index_log
```

**Умова:** `GOOGLE_INDEXING_KEY_FILE` налаштований у `.env`, `SITE_BASE_URL` задано.

### 16.6 Перевірка битих посилань

**JS-функція:** `checkBrokenLinks()`

**Backend:** `POST /api/admin/seo/check-broken-links` — запускає background thread

```python
@app.post("/api/admin/seo/check-broken-links")
def check_broken_links(request: Request):
    require_moder(request)
    # Запускає threading.Thread
    def _worker():
        c.execute("SELECT id, photo FROM memorials WHERE approved=1 AND photo!=''")
        for row in rows:
            status = _check_url_status(row['photo'])  # HEAD request, timeout=10
            c.execute("""INSERT INTO seo_broken_links (memorial_id, url, link_type, status_code, last_checked, is_broken)
                         VALUES (%s,%s,'photo',%s,%s,%s)
                         ON DUPLICATE KEY UPDATE status_code=VALUES(status_code), ...""",
                      (row['id'], row['photo'], status, now, status==0 or status>=400))
    threading.Thread(target=_worker, daemon=True).start()
    return {"ok": True, "message": "Перевірку запущено у фоні"}
```

**Результати:** `GET /api/admin/seo/broken-links` → дані з `seo_broken_links`

**SQL:**
```sql
SELECT m.id, m.last, m.first, b.url, b.status_code, b.is_broken
FROM seo_broken_links b JOIN memorials m ON m.id=b.memorial_id
WHERE b.is_broken=1 ORDER BY b.last_checked DESC
```

### 16.7 Дублікати

**JS-функція:** `loadSeoduplicates()`

**Backend:** `GET /api/admin/seo/duplicates`

```python
c.execute("""SELECT last, first, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
             FROM memorials WHERE approved=1
             GROUP BY LOWER(last), LOWER(first)
             HAVING cnt > 1""")
```

### 16.8 Знімок SEO history

**Backend:** `POST /api/admin/seo/snapshot`

```sql
INSERT INTO seo_score_history (snapshot_date, total_count, avg_score, count_a, count_b, count_c, count_d)
VALUES ('2026-05-28', 123, 67.5, 12, 35, 48, 28)
ON DUPLICATE KEY UPDATE avg_score=VALUES(avg_score), ...
```

**Графік:** `GET /api/admin/seo/score-history` → Chart.js лінійний графік.

### 16.9 Статистика пошуку

**Backend:** `GET /api/admin/seo-stats`

```python
c.execute("""SELECT query, COUNT(*) as cnt, AVG(results_count) as avg_res
             FROM search_logs GROUP BY query ORDER BY cnt DESC LIMIT 50""")
```

---

## 17. Щільність (sec-density)

**Де:** секція `#sec-density`

### 17.1 Алгоритм рейтингу

**Параметри (ключі в colors або окрема таблиця):**

| Параметр | Опис |
|----------|------|
| `weight_likes` | Вага лайків у рейтингу |
| `weight_rating` | Вага базового рейтингу |
| `weight_views` | Вага переглядів |
| `weight_activity` | Вага нещодавньої активності |
| `decay_days` | Днів для decay функції |
| `boost_approved` | Бонус за схвалення |

**Backend:** `GET /api/admin/density-settings`, `POST /api/admin/density-settings`

### 17.2 Heatmap

**JS-функція:** `loadDensityHeatmap()`

**Backend:** `GET /api/admin/density-heatmap`

Повертає координати та щільність для overlay на карті.

### 17.3 Статистика щільності

**Backend:** `GET /api/admin/density-stats`

### 17.4 Тест-пісочниця

**JS-функція:** `testDensityScore()`

Дозволяє ввести параметри (likes, views, ...) і побачити розрахований score без збереження.

### 17.5 Zoom thresholds

Порогові значення зуму для відображення маркерів різних категорій.

---

## 18. Імпорт / Експорт

### 18.1 Експорт CSV

**JS-функція:** `exportCsv()`

**Backend:** `GET /api/admin/export/csv`

```python
@app.get("/api/admin/export/csv")
def export_csv(request: Request):
    require_moder(request)
    c.execute("SELECT id,last,first,mid,birth,death,loc,bury,circ,descr,photo,color,"
              "pos_x,pos_y,grp,rank,position,unit,video_url,added_by,approved,likes,rating "
              "FROM memorials ORDER BY id")
    # Генерує CSV з BOM для Excel
    buf.write('﻿')  # UTF-8 BOM
    return StreamingResponse(buf, media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="memorials_YYYY-MM-DD.csv"'})
```

**Колонки CSV:** id, last, first, mid, birth, death, loc, bury, circ, descr, photo, color, pos_x, pos_y, grp, rank, position, unit, video_url, added_by, approved, likes, rating

### 18.2 Експорт JSON → XLSX (client-side)

**JS-функція:** `exportXlsx()`

**Backend:** `GET /api/admin/export/json` — повертає масив об'єктів

**Frontend:** перетворює JSON → XLSX на клієнті через SheetJS або аналог.

### 18.3 Імпорт CSV

**Workflow:**

1. **Upload:** `importCsvUpload()` → `POST /api/admin/import/preview`
2. **Preview:** сервер повертає масив рядків для перевірки
3. **Edit:** редагування окремих записів у preview
4. **Pick coords:** вибір координат на карті для записів без pos_x/pos_y
5. **Add awards:** додавання нагород до нових записів
6. **Apply:** `importApply()` → `POST /api/admin/import/apply` — **тільки admin**

**Backend preview:**
```python
@app.post("/api/admin/import/preview")
async def import_preview(request: Request, file: UploadFile = File(...)):
    require_admin(request)
    raw = await file.read()
    text = raw.decode('utf-8-sig')  # підтримка UTF-8 BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    # Валідація: last, first обов'язкові; довжина полів; типи
    return {"ok": True, "preview": validated_rows, "errors": error_list}
```

**Backend apply:**
```python
@app.post("/api/admin/import/apply")
async def import_apply(request: Request, body: ImportApplyBody):
    require_admin(request)  # ТІЛЬКИ ADMIN!
    inserted, skipped = 0, 0
    for row in body.rows:
        c.execute("""INSERT INTO memorials (last,first,mid,...,approved)
                     VALUES (%s,%s,%s,...,1)""", (...))
        new_id = c.lastrowid
        sl = make_slug(row['first'], row['last'], new_id)
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, new_id))
    db.commit()
    cache_flush_memorials()
    return {"ok": True, "inserted": inserted, "skipped": skipped}
```

**SQL (import):**
```sql
INSERT INTO memorials (last,first,mid,birth,death,loc,photo,pos_x,pos_y,approved)
VALUES ('Коваленко','Петро','',1995-03-15,'2023-08-22','Бахмут','',0.45,0.32,1)
```

**Права:** `POST /api/admin/import/apply` — **тільки admin** (не moder).

---

## 19. Картки меморіалу (sec-card)

**Де:** секція `#sec-card`

**Ключі в `colors`:** `card_bg`, `card_text`, `card_accent`, `card_border`, `card_photo_size`, `card_font`, та інші стилі публічних карток.

**JS-функція:** `saveCardSettings()`

**Backend:** `POST /api/admin/colors/batch`

**Preview:** live-preview публічної картки в iframe.

**Картка `card.html`** — окрема публічна сторінка `/card?id=N` з темою dark gold.

---

## 20. Google та аналітика (sec-google)

**Де:** секція `#sec-google`

### Google Analytics

**Ключ:** `ga_id` в таблиці `colors` — ID рахунку GA4.

**JS-функція:** `saveGaId()`

**Backend:** `PUT /api/admin/color` → `key=ga_id`

### Google Search Console

**JS-функція:** `loadGoogleStatus()`

**Backend:** `GET /api/admin/google/status`

```python
@app.get("/api/admin/google/status")
def google_status(request: Request):
    require_admin(request)
    # Перевіряє наявність google-service-account.json
    # Повертає статус підключення до Google Indexing API
    has_key = os.path.exists(GOOGLE_KEY_FILE)
    return {"connected": has_key, "key_file": GOOGLE_KEY_FILE, "site_url": SITE_BASE_URL}
```

---

## 21. Хвилина мовчання (sec-silence)

**Де:** секція `#sec-silence`

### Налаштування

**Backend:** `GET /api/admin/minute-silence/settings`, `POST /api/admin/minute-silence/settings`

**Ключі в `colors`:**

| Ключ | Значення | Опис |
|------|---------|------|
| `minute_enabled` | `1`/`0` | Увімкнено |
| `minute_timezone` | `Europe/Kyiv` | Часовий пояс для таймера |
| `minute_color_overlay` | `#000000` | Колір накладки |
| `minute_color_clock` | `#ffffff` | Колір годинника |
| `minute_blur_amount` | `5` | Розмиття основного контенту (px) |
| `minute_font` | `digital` | Стиль шрифта годинника |
| `minute_font_size` | `24` | Розмір (px) |
| `minute_show_seconds` | `1` | Показувати секунди |
| `minute_sound_enabled` | `1` | Звук тиканья годинника |

### Завантаження аудіо

**JS-функція:** `uploadSilenceAudio()`

**Backend:** `POST /api/admin/minute-silence/audio`

```python
@app.post("/api/admin/minute-silence/audio")
async def upload_silence_audio(request: Request, file: UploadFile = File(...)):
    require_admin(request)
    # Зберігає у static/silence.mp3 або аналог
    # Перевіряє MIME type (audio/mpeg, audio/ogg)
    return {"ok": True, "url": "/static/silence.mp3"}
```

**BroadcastChannel:** `'zoryana_silence'` → index.html оновлює налаштування хвилини мовчання.

---

## 22. Профіль адміністратора

**Де:** модальне вікно `#admin-profile-modal`, кнопка у header «[ім'я адміна]»

**JS-функція:** `openAdminProfile()`, `saveAdminProfile()`

### Поля форми

| Поле | id | Тип | Опис |
|------|----|-----|------|
| Повне ім'я | `ap-name` | text | Відображуване ім'я |
| Поточний пароль | `ap-pass` | password | **Обов'язковий** для будь-яких змін |
| Логін | `ap-login` | text | Латиниця 3–50 + `#ap-login-avail` |
| Підтвердження логіну | `ap-login2` | text | Має збігатися з `ap-login` |
| Новий Email | `ap-email` | email | + `#ap-email-avail` (real-time) |
| Підтвердження Email | `ap-email2` | email | Має збігатися |
| Новий пароль | `ap-newpass` | password | Опціонально |
| Підтвердження паролю | `ap-newpass2` | password | Має збігатися |

### Відкриття модалу

```javascript
function openAdminProfile() {
  document.getElementById('ap-name').value = curAdminName;
  document.getElementById('ap-login').value = curAdminLogin || AE;
  // Очищення статусів перевірки доступності:
  ['ap-email-avail','ap-login-avail'].forEach(id => {
    const e = document.getElementById(id);
    if (e) { e.textContent = ''; e.style.color = ''; }
  });
  document.getElementById('admin-profile-modal').style.display = 'flex';
}
```

### Збереження

```javascript
async function saveAdminProfile() {
  const payload = {
    current_password: document.getElementById('ap-pass').value,
    name: document.getElementById('ap-name').value || null,
    login: document.getElementById('ap-login').value || null,
    login_confirm: document.getElementById('ap-login2').value || null,
    email: document.getElementById('ap-email').value || null,
    email_confirm: document.getElementById('ap-email2').value || null,
    new_password: document.getElementById('ap-newpass').value || null,
    new_password_confirm: document.getElementById('ap-newpass2').value || null,
  };
  const r = await fetch(API + '/api/admin/profile', { method:'PUT', body:JSON.stringify(payload) });
  const d = await r.json();
  if (d.ok) { showToast('Профіль оновлено'); curAdminName = payload.name || curAdminName; }
  else showToast(d.detail || 'Помилка', 'err');
}
```

### Backend

**Endpoint:** `PUT /api/admin/profile`

```python
@app.put("/api/admin/profile")
def update_admin_profile(body: AdminProfileUpdate, request: Request):
    me = require_moder(request)
    ip = _get_ip(request)
    # Rate limit: 5 спроб / 5 хвилин
    if not _rl.check(f"admin_profile:{ip}", 5, 300):
        raise HTTPException(429, "Забагато спроб, зачекайте 5 хвилин")
    # Перевірка поточного пароля (bcrypt):
    if not verify_pass(body.current_password, cur["password"]):
        sec_log("ADMIN_PROFILE_WRONG_PASS", ip, f"uid={me['id']}")
        raise HTTPException(400, "Поточний пароль невірний")
    # Логін: _LOGIN_RE = r'^[a-zA-Z0-9_\-]{3,50}$'
    # Унікальність: SELECT FROM users WHERE nickname=%s AND id!=%s
    # Email: re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', em)
    # Пароль: _validate_password()
    c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", vals)
    sec_log("ADMIN_PROFILE_CHANGE", ip, f"uid={me['id']} changed={changed}")
    return {"ok": True, "changed": changed}
```

**SQL:**
```sql
UPDATE users SET name='Іван Адміненко', nickname='ivan_admin', email='new@mail.com' WHERE id=1
```

**Перевірки:**
- `current_password` — обов'язково, bcrypt verify
- Login: `_LOGIN_RE = r'^[a-zA-Z0-9_\-]{3,50}$'` — тільки латиниця
- Login підтвердження: `login_confirm == login`
- Email підтвердження: `email_confirm == email`
- Пароль: `_validate_password()` — мінімальна довжина, складність
- Rate limit: 5 спроб / 5 хвилин per IP

**Логування:** `sec_log("ADMIN_PROFILE_CHANGE", ip, f"uid={me['id']} changed={changed}")`

**Що бачить адмін:** toast «Профіль оновлено» + оновлене ім'я у header.

---

## 23. База даних

### 23.1 Таблиця `memorials`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT AUTO_INCREMENT PK | — |
| `last` | VARCHAR(100) | Прізвище |
| `first` | VARCHAR(100) | Ім'я |
| `mid` | VARCHAR(100) | Позивний / по батькові |
| `birth` | VARCHAR(20) | Дата народження |
| `death` | VARCHAR(20) | Дата загибелі |
| `loc` | VARCHAR(300) | Місце загибелі |
| `bury` | VARCHAR(300) | Місце поховання |
| `circ` | VARCHAR(500) | Обставини загибелі |
| `descr` | TEXT | Опис |
| `photo` | VARCHAR(500) | URL фото |
| `color` | VARCHAR(20) | Колір маркера (hex) |
| `pos_x` | DOUBLE | X позиція 0.0–1.0 |
| `pos_y` | DOUBLE | Y позиція 0.0–1.0 |
| `likes` | INT | Кількість лайків |
| `rating` | DOUBLE | Рейтинг (алгоритм) |
| `approved` | TINYINT | 0=pending, 1=published |
| `grp` | VARCHAR(100) | Позивний/підрозділ |
| `added_by` | VARCHAR(100) | Хто додав |
| `video_url` | VARCHAR(500) | YouTube URL |
| `rank` | VARCHAR(100) | Військове звання |
| `position` | VARCHAR(100) | Посада |
| `unit` | VARCHAR(200) | Військовий підрозділ |
| `slug` | VARCHAR(220) UNIQUE | SEO slug |

**Критичні індекси:**
```sql
FULLTEXT idx_fulltext_search (last,first,mid,grp,loc,descr)  -- пошук
INDEX idx_approved_rating (approved, rating DESC, likes DESC) -- /api/people
INDEX idx_slug (slug) UNIQUE                                  -- SEO
```

### 23.2 Таблиця `users`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT AUTO_INCREMENT PK | — |
| `name` | VARCHAR(100) | ПІБ |
| `first_name` | VARCHAR(100) | Ім'я (незмінне) |
| `last_name` | VARCHAR(100) | Прізвище (незмінне) |
| `middle_name` | VARCHAR(100) | По батькові (незмінне) |
| `nickname` | VARCHAR(100) UNIQUE | Нік / логін |
| `email` | VARCHAR(120) UNIQUE | Email |
| `phone` | VARCHAR(20) | Телефон |
| `password` | VARCHAR(255) | bcrypt hash |
| `role` | VARCHAR(20) | admin/moder/user |
| `is_banned` | TINYINT | Заблокований |
| `ban_until` | INT | Unix timestamp кінця бану |
| `last_seen` | INT | Unix timestamp активності |
| `created` | INT | Unix timestamp реєстрації |
| `notes` | TEXT | Нотатки адміна |

### 23.3 Таблиця `colors`

**Schema:** `key VARCHAR(50) PK`, `value TEXT`, `label VARCHAR(100)`

**88+ ключів** — конфігурація всього сайту (кольори, ефекти, соцмережі, адмін, SEO, реєстрація).

### 23.4 Таблиця `cities`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT PK | — |
| `name` | VARCHAR(100) | Назва міста |
| `pos_x` | DOUBLE | Нормалізована позиція 0.0–1.0 |
| `pos_y` | DOUBLE | Нормалізована позиція 0.0–1.0 |
| `tier` | INT | 0–3 (важливість) |
| `color` | VARCHAR(20) | Колір крапки |

**463 міста** (435 tier-0 + 21 обласні + 5 великі + 2 столиця).

### 23.5 Таблиця `map_labels`

**⚠️ Важливо:** `x/y` — координати у просторі SVG (1000–12000), НЕ нормалізовані!

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT PK | — |
| `name` | VARCHAR(100) | Назва (напр. «Запорізька») |
| `x` | DOUBLE | SVG pixels X |
| `y` | DOUBLE | SVG pixels Y |
| `type` | VARCHAR(20) | `oblast` |
| `color` | VARCHAR(50) | RGBA колір |
| `size` | INT | Розмір шрифта (SVG units) |

**24 підписи** — 24 областей України.

### 23.6 Таблиця `memorial_awards`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT PK | — |
| `memorial_id` | INT FK→memorials.id | — |
| `name` | VARCHAR(200) | Назва нагороди |
| `img_file` | VARCHAR(300) | Локальне ім'я файлу PNG |
| `award_date` | DATE | Дата нагородження |
| `descr` | TEXT | Опис |
| `sort_order` | INT | Порядок |

### 23.7 Таблиця `awards_catalog`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT PK | — |
| `name` | VARCHAR(200) | Назва |
| `img_file` | VARCHAR(200) UNIQUE | Файл в `img/awards/` |
| `category` | VARCHAR(30) | hero/order/cross/medal/badge |
| `description` | TEXT | Офіційний опис |
| `sort_order` | INT | Порядок у списку |

**31 нагорода** (локальні PNG в `img/awards/`).

### 23.8 Таблиця `likes_log`

| Колонка | Тип | Опис |
|---------|-----|------|
| `memorial_id` | INT | FK |
| `fingerprint` | VARCHAR(128) | Браузерний fingerprint |
| `ts` | INT | Unix timestamp |

### 23.9 Таблиця `search_logs`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT PK | — |
| `query` | VARCHAR(200) | Текст пошуку |
| `results_count` | INT | К-сть результатів |
| `created_at` | INT | Unix timestamp |

### 23.10 SEO таблиці

**`seo_index_log`** — лог Google Indexing API (url, notification_type, status, response, created_at)

**`seo_broken_links`** — результати перевірки фото (memorial_id, url, status_code, is_broken, last_checked)

**`seo_score_history`** — знімки SEO балів (snapshot_date UNIQUE, total_count, avg_score, count_a/b/c/d)

---

## 24. Права доступу admin vs moder

### Таблиця порівняння

| Дія | admin | moder |
|-----|:-----:|:-----:|
| Вхід в панель | ✓ | ✓ |
| `GET /api/admin/me` | ✓ | ✓ |
| `GET /api/admin/stats` | ✓ | ✓ |
| `GET /api/admin/server-stats` | ✓ | ✓ |
| `GET /api/admin/pending` | ✓ | ✓ |
| `POST /api/admin/approve/{id}` | ✓ | ✓ |
| `GET /api/admin/memorials` | ✓ | ✓ |
| `POST /api/admin/memorial` | ✓ | ✓ |
| `PUT /api/admin/memorial/{id}` | ✓ | ✓ |
| `GET /api/admin/memorial/{id}/awards` | ✓ | ✓ |
| `POST /api/admin/memorial/{id}/awards` | ✓ | ✓ |
| `DELETE /api/admin/awards/{id}` | ✓ | ✓ |
| `PUT /api/admin/profile` | ✓ | ✓ |
| `GET /api/admin/export/csv` | ✓ | ✓ |
| `GET /api/admin/export/json` | ✓ | ✓ |
| `GET /api/admin/seo/*` | ✓ | ✓ |
| `POST /api/admin/seo/regenerate-slugs` | ✓ | ✓ |
| `POST /api/admin/seo/ping-google` | ✓ | ✓ |
| `GET /api/admin/density-*` | ✓ | ✓ |
| `GET /api/admin/google/status` | ✓ | ✓ |
| **`DELETE /api/admin/memorial/{id}`** | **✓** | **✗** |
| **`GET /api/admin/users`** | **✓** | **✗** |
| **`PUT /api/admin/user/{uid}`** | **✓** | **✗** |
| **`DELETE /api/admin/user/{uid}`** | **✓** | **✗** |
| **`PUT /api/admin/users/{uid}/role`** | **✓** | **✗** |
| **`POST /api/admin/ban/{uid}`** | **✓** | **✗** |
| **`POST /api/admin/import/apply`** | **✓** | **✗** |
| **`PUT /api/admin/color`** | **✓** | **✗** |
| **`POST /api/admin/colors/batch`** | **✓** | **✗** |
| **`POST/PUT/DELETE /api/admin/city/*`** | **✓** | **✗** |
| **`PUT /api/admin/label/*`** | **✓** | **✗** |
| **`POST /api/admin/sea-svg`** | **✓** | **✗** |
| **`POST /api/admin/import/preview`** | **✓** | **✗** |

### Middleware реалізація

```python
def require_admin(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") != "admin":
        raise HTTPException(403, "Недостатньо прав")
    return u

def require_moder(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") not in ("admin", "moder"):
        raise HTTPException(403, "Недостатньо прав")
    return u
```

### Сесія

```python
def _get_session_user(request: Request) -> dict | None:
    token = request.cookies.get("admin_session")
    if not token:
        # Fallback: Basic Auth header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            # Перевіряє email+password
    session = _sessions.get(token)
    if not session:
        return None
    if time.time() - session["created"] > 604800:  # 7 днів
        del _sessions[token]
        return None
    return session["user"]
```

---

## 25. Безпека

### 25.1 Механізми захисту

| Механізм | Реалізація |
|----------|-----------|
| Rate Limiting | `_RateLimiter._rl.check(key, limit, window)` — token bucket |
| Brute-force login | 5 спроб / 15 хвилин per IP+email |
| SQL Injection | Виключно параметризовані запити `cursor.execute(sql, (params,))` |
| XSS | `_sanitize_text()`, `html.escape()` на всіх текстових входах |
| SSRF | `_validate_photo_url()` блокує `localhost`, `127.x`, `10.x`, `192.168.x` |
| SVG Injection | `_sanitize_svg()` видаляє `<script>`, `on*`, `<foreignObject>`, `<use>` |
| Password hashing | bcrypt 12 rounds (`bcrypt.hashpw(pwd, bcrypt.gensalt(12))`) |
| Session security | `secrets.token_hex(32)`, max 50,000, `httponly=True` cookie |
| Admin isolation | Сесії in-memory `_sessions: dict` з `threading.Lock()` |

### 25.2 Rate limit ключі (адмін)

| Ключ | Ліміт | Вікно | Endpoint |
|------|-------|-------|----------|
| `admin_login:{ip}:{email}` | 5 | 900с (15хв) | POST /api/admin/login |
| `admin_profile:{ip}` | 5 | 300с (5хв) | PUT /api/admin/profile |
| `admin_pwreset:{ip}` | 10 | 3600с (1год) | PUT /api/admin/user/{uid} (new_password) |
| `chk_avail:{ip}` | 30 | 60с | GET /api/auth/check-availability |

### 25.3 Security Log Events

| Подія | Trigger |
|-------|---------|
| `ADMIN_LOGIN_OK` | Успішний вхід адміна |
| `ADMIN_LOGIN_FAIL` | Невірний пароль адміна |
| `ADMIN_PROFILE_CHANGE` | Зміна власного профілю |
| `ADMIN_PROFILE_WRONG_PASS` | Невірний поточний пароль при зміні профілю |
| `ROLE_CHANGE` | Зміна ролі користувача |
| `PASSWORD_RESET_BY_ADMIN` | Скидання пароля адміном |
| `DELETE_MEMORIAL` | Видалення меморіалу |
| `USER_BAN` | Блокування користувача |
| `USER_UNBAN` | Розблокування |
| `REGISTER_OK` | Реєстрація нового user |
| `REGISTER_FAIL` | Помилка реєстрації |
| `LOGIN_OK` | Вхід user |
| `LOGIN_FAIL` | Невірні дані user |
| `RATE_LIMIT` | Перевищення ліміту запитів |

**Файл:** `logs/security.log`

**Формат:** `2026-05-28 10:34:22 [INFO] [ROLE_CHANGE] IP=192.168.1.1 uid=5 email=moder@site.ua admin->moder by=admin@admin.com`

### 25.4 _sanitize_text()

```python
def _sanitize_text(text: str, max_len: int = 500) -> str:
    if not text:
        return ''
    # Видаляє HTML-теги
    text = re.sub(r'<[^>]+>', '', text)
    # html.escape для залишкових символів
    text = html.escape(text)
    return text[:max_len].strip()
```

### 25.5 _validate_photo_url()

```python
_SSRF_BLOCKED_HOSTS = re.compile(
    r'^(localhost|127\.|10\.|192\.168\.|0\.|169\.254\.)', re.I
)

def _validate_photo_url(url: str) -> str:
    if not url:
        return ''
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(400, "Невірний протокол URL")
    if _SSRF_BLOCKED_HOSTS.match(parsed.hostname or ''):
        raise HTTPException(400, "Заборонена адреса (SSRF захист)")
    return url
```

### 25.6 Сесії (in-memory)

```python
_sessions: dict = {}   # token -> {user, created}
_sessions_lock = threading.Lock()

# Lazy purge: кожні ~1000 запитів
def _purge_sessions():
    now = time.time()
    expired = [t for t,s in _sessions.items() if now - s["created"] > 604800]
    for t in expired:
        del _sessions[t]

# Ліміт 50,000 — evict старі при перевищенні
if len(_sessions) > 50000:
    oldest = sorted(_sessions.items(), key=lambda x: x[1]["created"])[:1000]
    for t,_ in oldest:
        del _sessions[t]
```

---

## 26. Моніторинг та логи

### 26.1 Health check

**Endpoint:** `GET /health`

```python
@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime": time.time() - _START_TIME,
        "db": _check_db(),      # True/False
        "redis": _check_redis(), # True/False
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent
    }
```

**Відповідь:**
```json
{
  "status": "ok",
  "uptime": 86400.5,
  "db": true,
  "redis": true,
  "cpu": 12.3,
  "memory": 45.6
}
```

### 26.2 Prometheus metrics

**Endpoint:** `GET /metrics` (захищений `METRICS_TOKEN`)

**Формат:** Prometheus text format — лічильники запитів, latency, active sessions.

### 26.3 Security log

**Файл:** `logs/security.log`

**Ротація:** вручну або через logrotate.

**Перегляд:**
```bash
tail -f logs/security.log
grep "ADMIN_LOGIN_FAIL" logs/security.log
```

### 26.4 Redis cache

**Ключі:**
- `people:p{page}:l{limit}` — публічний список меморіалів, TTL 60с
- `sitemap` — XML sitemap, TTL 600с
- `memorial:{id}` — деталі меморіалу, TTL 300с

**Flush при змінах:** `cache_flush_memorials()` — при approve, import, edit.

---

## 27. BroadcastChannel (live синхронізація)

**Механізм:** Web API `BroadcastChannel` — синхронізація між вкладками браузера.

### Канали

| Канал | Надсилає | Слухає | Що оновлює |
|-------|----------|--------|-----------|
| `zoryana_colors` | admin.html | index.html | CSS variables, теми, ефекти |
| `zoryana_sea` | admin.html | index.html | SVG море, хвилі |
| `zoryana_silence` | admin.html | index.html | Хвилина мовчання |
| `zoryana_partners` | admin.html | index.html | Партнери на карті |

### Приклад (відправник в admin.html)

```javascript
function broadcastColors(colors) {
  const bc = new BroadcastChannel('zoryana_colors');
  bc.postMessage({ type: 'update', colors: colors });
  bc.close();
}
```

### Приклад (приймач в index.html)

```javascript
const _colorsBc = new BroadcastChannel('zoryana_colors');
_colorsBc.onmessage = (e) => {
  if (e.data.type === 'update') {
    applyColors(e.data.colors);  // оновлює CSS variables
  }
};
```

**Обмеження:** BroadcastChannel працює в межах одного браузера (не між пристроями). Для production — після збереження в БД, при перезавантаженні index.html також підхоплює нові кольори з `/api/colors`.

---

*Технічна документація адмін-панелі «Зоряна Пам'ять» v2.1 · 2026-05-28*
