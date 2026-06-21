# MODERATOR_DOCUMENTATION.md — Технічна документація модератора «Зоряна Пам'ять»

> Версія: v2.1 · Оновлено: 2026-05-28  
> Аудиторія: модератори (role=`moder`)  
> URL панелі: `/admin` → `admin.html`

---

## Зміст

1. [Роль модератора](#1-роль-модератора)
2. [Авторизація](#2-авторизація)
3. [Повний список дозволів](#3-список-дозволів)
4. [Черга модерації](#4-черга-модерації)
5. [Управління меморіалами](#5-меморіали)
6. [Нагороди меморіалів](#6-нагороди)
7. [Власний профіль](#7-профіль)
8. [Статистика (read-only)](#8-статистика)
9. [SEO-інструменти](#9-seo)
10. [Щільність (read-only)](#10-щільність)
11. [Що заборонено модератору](#11-заборони)
12. [БД-операції модератора](#12-база-даних)
13. [Безпека](#13-безпека)

---

## 1. Роль модератора

### Визначення ролі

Модератор (`role='moder'`) — проміжна роль між звичайним користувачем (`user`) та адміністратором (`admin`). Основне завдання — перевірка та схвалення нових меморіалів, редагування існуючих записів, робота зі списком черги.

**У БД:** поле `role='moder'` в таблиці `users`.

### Middleware

```python
# Ендпоінти з require_moder пропускають обидві ролі:
def require_moder(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") not in ("admin", "moder"):
        raise HTTPException(403, "Недостатньо прав")
    return u

# Ендпоінти з require_admin — ТІЛЬКИ admin:
def require_admin(request: Request) -> dict:
    u = _get_session_user(request)
    if not u or u.get("role") != "admin":
        raise HTTPException(403, "Недостатньо прав")
    return u
```

### Ключові відмінності від адміна

| Можливість | admin | moder |
|------------|:-----:|:-----:|
| Схвалення записів | ✓ | ✓ |
| Редагування записів | ✓ | ✓ |
| Видалення записів | ✓ | **✗** |
| Управління користувачами | ✓ | **✗** |
| Зміна ролей | ✓ | **✗** |
| Кольори/теми | ✓ | **✗** |
| Міста на карті | ✓ | **✗** |
| Імпорт CSV (apply) | ✓ | **✗** |
| Блокування users | ✓ | **✗** |

### Як призначити роль moder

Тільки адмін може призначити роль:
- В панелі: `sec-users` → `openUserModal(uid)` → поле «Роль» → «Модератор» → Зберегти
- API: `PUT /api/admin/users/{uid}/role` з `{"role": "moder"}`
- SQL (вручну): `UPDATE users SET role='moder', is_admin=0 WHERE id=7`

---

## 2. Авторизація

### Форма входу

Модератор входить через ту ж саму форму, що й адміністратор.

**Поля:**
- `#login-email` — email адреса
- `#login-pass` — пароль

**Backend:** `POST /api/admin/login`

```python
@app.post("/api/admin/login")
def admin_login(request: Request):
    # Декодує Basic Auth header
    email, password = base64.b64decode(auth[6:]).decode().split(":",1)
    # Rate limit: 5 спроб / 15 хвилин
    if not _rl.check(f"admin_login:{ip}:{email}", 5, 900):
        raise HTTPException(429, "Забагато спроб")
    c.execute("SELECT * FROM users WHERE email=%s AND role IN ('admin','moder')", (email,))
    if not verify_pass(password, user["password"]):
        sec_log("ADMIN_LOGIN_FAIL", ip, email)
        raise HTTPException(401, "Невірні дані")
    # Сесія зберігається в _sessions (in-memory, TTL 7 днів)
    sec_log("ADMIN_LOGIN_OK", ip, email)
    return {"ok": True, "user": {id, name, email, role}}
```

**Захист:**
- 5 невдалих спроб → блокування 15 хвилин (per IP+email)
- bcrypt 12 rounds
- Cookie `admin_session` (httponly, max_age=604800)

**Авто-вхід:** при відкритті `/admin` перевіряється `GET /api/admin/me` — якщо cookie валідна, вхід без форми.

---

## 3. Список дозволів

### Дозволені ендпоінти (require_moder)

| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/api/admin/me` | Власний профіль |
| PUT | `/api/admin/profile` | Зміна власного профілю (ім'я, логін, email, пароль) |
| GET | `/api/admin/stats` | Загальна статистика |
| GET | `/api/admin/server-stats` | CPU, RAM, uptime |
| GET | `/api/admin/pending` | Черга записів на модерації |
| POST | `/api/admin/approve/{id}` | Схвалення запису |
| GET | `/api/admin/memorials` | Список всіх меморіалів (пагінація) |
| POST | `/api/admin/memorial` | Створення нового запису (approved=1 auto) |
| PUT | `/api/admin/memorial/{id}` | Редагування запису |
| GET | `/api/memorial/{id}/awards` | Нагороди конкретного меморіалу |
| GET | `/api/admin/memorial/{id}/awards` | Нагороди (адмін-версія) |
| POST | `/api/admin/memorial/{id}/awards` | Додати нагороду |
| DELETE | `/api/admin/awards/{id}` | Видалити нагороду (не меморіал!) |
| GET | `/api/admin/export/csv` | Експорт CSV |
| GET | `/api/admin/export/json` | Експорт JSON |
| GET | `/api/admin/seo-dashboard` | SEO дашборд |
| GET | `/api/admin/seo-stats` | Статистика пошуку |
| GET | `/api/admin/seo/scores` | SEO оцінки всіх карток |
| GET | `/api/admin/seo/analyze/{id}` | Аналіз конкретного меморіалу |
| POST | `/api/admin/seo/regenerate-slugs` | Регенерація пустих slug |
| POST | `/api/admin/seo/ping-google` | Відправка до Google Indexing API |
| POST | `/api/admin/seo/check-broken-links` | Запуск перевірки битих посилань |
| GET | `/api/admin/seo/broken-links` | Список битих посилань |
| GET | `/api/admin/seo/duplicates` | Дублікати ПІБ |
| POST | `/api/admin/seo/snapshot` | Збереження знімку SEO score |
| GET | `/api/admin/seo/score-history` | Історія SEO знімків |
| GET | `/api/admin/density-settings` | Налаштування щільності (читання) |
| GET | `/api/admin/density-heatmap` | Heatmap щільності |
| GET | `/api/admin/density-stats` | Статистика щільності |
| GET | `/api/admin/google/status` | Статус Google API |

---

## 4. Черга модерації

### 4.1 Перегляд черги

**Де:** секція `#sec-pend` в адмін-панелі, badge `#pend-nb` у навігації.

**JS-функція:** `loadPending()`

**Backend:** `GET /api/admin/pending`

```python
@app.get("/api/admin/pending")
def pending(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC")
        rows = c.fetchall()
    db.close()
    return rows
```

**SQL:**
```sql
SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC
```

**Рендеринг:** кожен запис відображається карткою з:
- id, ПІБ (last, first, mid), дата додавання
- `added_by` — хто подав запис
- Фото (якщо є URL у `photo`)
- Місце загибелі (`loc`), підрозділ (`unit`)
- Кнопка **[Схвалити]** — доступна модератору
- Кнопка **[Видалити]** — **тільки адмін** (модератор не бачить або кнопка неактивна)

**Лічильник:** `#pend-nb` — кількість записів у черзі, оновлюється після `loadPending()`.

### 4.2 Схвалення запису

**JS-функція:** `approveMem(id)`

```javascript
async function approveMem(id) {
  if (!confirm('Схвалити запис #' + id + '?')) return;
  const r = await fetch(API + '/api/admin/approve/' + id, { method: 'POST' });
  const d = await r.json();
  if (d.ok) {
    showToast('Схвалено');
    loadPending();  // оновити чергу
    loadStats();    // оновити лічильники
  } else {
    showToast(d.detail || 'Помилка', 'err');
  }
}
```

**Backend:** `POST /api/admin/approve/{mid}`

```python
@app.post("/api/admin/approve/{mid}")
def approve(mid: int, request: Request):
    require_moder(request)  # доступно moder і admin
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE memorials SET approved=1 WHERE id=%s", (mid,))
        # Генерація slug якщо відсутній:
        c.execute("SELECT id, first, last, slug FROM memorials WHERE id=%s", (mid,))
        row = c.fetchone()
        if row and not row.get('slug'):
            sl = make_slug(row['first'], row['last'], row['id'])
            try:
                c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, mid))
            except Exception:
                pass  # ігнорує дубль slug
    db.commit()
    db.close()
    cache_flush_memorials()  # скидає Redis кеш списку
    cache_delete("sitemap")  # оновлює sitemap.xml
    return {"ok": True}
```

**SQL:**
```sql
-- Схвалення:
UPDATE memorials SET approved=1 WHERE id=42;

-- Генерація slug (якщо порожній):
SELECT id, first, last, slug FROM memorials WHERE id=42;
UPDATE memorials SET slug='mykola-petrenko-42' WHERE id=42;
```

**Slug-генерація:** `seo_utils.make_slug(first, last, id)`
- Транслітерація KMU 2010 (кирилиця → латиниця)
- Формат: `{first_translit}-{last_translit}-{id}`
- Приклад: «Іван Шевченко» → `ivan-shevchenko-42`
- Унікальність: суфікс `id` гарантує відсутність конфліктів

**Наслідки схвалення:**
1. `approved=1` — запис з'являється на публічній карті
2. Slug генерується автоматично (SEO URL `/memorial/ivan-shevchenko-42`)
3. Redis кеш скидається → наступний GET `/api/people` отримає свіжі дані
4. `sitemap.xml` оновлюється (новий URL включається)

**Що бачить модератор:** toast «Схвалено» → картка зникає з черги → `#pend-nb` зменшується на 1.

### 4.3 Відхилення запису

Модератор **не може видалити** запис з черги. Кнопка [Видалити] доступна тільки адміну.

**Дія при неприйнятному записі:** повідомити адміна або залишити запис у черзі без схвалення.

### 4.4 Поля для перевірки при модерації

| Поле | Перевірка |
|------|-----------|
| `last`, `first` | Обов'язкові, реальне ПІБ |
| `photo` | Доступний URL (не 404); не приватна IP-адреса |
| `loc` | Відповідає географії України |
| `descr` | Не містить спаму або образливого контенту |
| `video_url` | Лише YouTube (validate при редагуванні) |
| `unit` | Реальний підрозділ |

---

## 5. Меморіали

### 5.1 Список всіх меморіалів

**Де:** секція `#sec-mem`

**JS-функції:** `loadMem()`, `memDoSearch()`, `memRender()`, `memSetPageSize(n)`, `memPage(delta)`

**Backend:** `GET /api/admin/memorials?page=1&limit=500`

```python
@app.get("/api/admin/memorials")
def admin_all_memorials(page: int=1, limit: int=100, request: Request=None):
    require_moder(request)
    page = max(1, page)
    limit = max(1, min(limit, 500))
    offset = (page-1) * limit
    c.execute("SELECT * FROM memorials ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
    c.execute("SELECT COUNT(*) AS cnt FROM memorials")
    return {"items": rows, "total": total, "page": page, "limit": limit, "pages": ...}
```

**SQL:**
```sql
SELECT * FROM memorials ORDER BY id DESC LIMIT 500 OFFSET 0
```

**Клієнтська пагінація:**
```javascript
let allPeople = [];       // всі завантажені записи
let filteredPeople = [];  // після пошуку
let memPage = 1;
let memPageSize = 25;     // Перемикач: 10/25/50/100/200/Всі
```

**Пошук:** `memDoSearch(q)` — локальний фільтр по `last`, `first`, `mid`, `loc` без додаткових запитів до сервера.

### 5.2 Редагування меморіалу

**JS-функції:** `openEditById(id)`, `saveEdit()`, `_buildEditModal(data)`

**Де:** модальне вікно `#edit-modal`

**Відкриття:**
```javascript
async function openEditById(id) {
  const r = await fetch(API + '/api/memorial/' + id);
  const d = await r.json();
  _buildEditModal(d);
  document.getElementById('edit-modal').style.display = 'flex';
}
```

**Поля форми для редагування:**

| Поле | id | Обов'язкове | Обмеження |
|------|----|-------------|-----------|
| Прізвище | `em-last` | Так | max 100 |
| Ім'я | `em-first` | Так | max 100 |
| Позивний | `em-mid` | Ні | max 100 |
| Дата народження | `em-birth` | Ні | рядок |
| Дата загибелі | `em-death` | Ні | рядок |
| Місце загибелі | `em-loc` | Ні | max 300 |
| Поховання | `em-bury` | Ні | max 300 |
| Обставини | `em-circ` | Ні | max 500 |
| Опис | `em-descr` | Ні | TEXT |
| Фото URL | `em-photo` | Ні | SSRF check |
| YouTube URL | `em-video` | Ні | YouTube only |
| Звання | `em-rank` | Ні | max 100 |
| Посада | `em-position` | Ні | max 100 |
| Підрозділ | `em-unit` | Ні | max 200 |
| Підрозділ/гр | `em-grp` | Ні | max 100 |
| Колір маркера | `em-color` | Ні | hex |
| Схвалено | `em-approved` | — | checkbox 0/1 |

**Збереження:**
```javascript
async function saveEdit() {
  const id = document.getElementById('em-id').value;
  const payload = {
    last:      document.getElementById('em-last').value.trim(),
    first:     document.getElementById('em-first').value.trim(),
    mid:       document.getElementById('em-mid').value.trim(),
    // ... інші поля
    approved:  document.getElementById('em-approved').checked ? 1 : 0,
  };
  const r = await fetch(API + '/api/admin/memorial/' + id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const d = await r.json();
  if (d.ok) {
    showToast('Збережено');
    closeModal('edit-modal');
    loadMem();
  } else {
    showToast(d.detail || 'Помилка', 'err');
  }
}
```

**Backend:** `PUT /api/admin/memorial/{mid}`

```python
@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid: int, p: PersonUpdate, request: Request):
    require_moder(request)  # доступно moder і admin
    # Санітизація вхідних даних:
    last  = _sanitize_text(p.last, 100)
    first = _sanitize_text(p.first, 100)
    descr = _sanitize_text(p.descr, 5000)
    # Валідація URL:
    photo = _validate_photo_url(p.photo or '')
    video = _validate_yt_url(p.video_url or '')
    # Auto-update slug при зміні ПІБ:
    if p.first or p.last:
        sl = make_slug(p.first or first_old, p.last or last_old, mid)
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, mid))
    c.execute("""UPDATE memorials
                 SET last=%s, first=%s, mid=%s, birth=%s, death=%s,
                     loc=%s, bury=%s, circ=%s, descr=%s, photo=%s,
                     video_url=%s, rank=%s, position=%s, unit=%s, grp=%s,
                     color=%s, approved=%s, pos_x=%s, pos_y=%s
                 WHERE id=%s""", (..., mid))
    db.commit()
    cache_flush_memorials()
    return {"ok": True}
```

**SQL:**
```sql
UPDATE memorials
SET last='Кравченко', first='Микола', mid='Сергійович',
    birth='1990-07-12', death='2022-03-15', loc='Маріуполь',
    approved=1, slug='mykola-kravchenko-15'
WHERE id=15
```

**Безпека:**
- `_sanitize_text()` — видаляє HTML з текстових полів
- `_validate_photo_url()` — SSRF захист для URL фото
- `_validate_yt_url()` — YouTube-only для video_url
- Параметризовані запити (без SQL injection)
- `cache_flush_memorials()` — скидає Redis кеш після змін

### 5.3 Створення нового меморіалу (адмін-форма)

**JS-функція:** `openAddMemModal()`, `saveNewMem()`

**Backend:** `POST /api/admin/memorial`

```python
@app.post("/api/admin/memorial")
def admin_add_person(p: PersonIn, request: Request):
    require_moder(request)
    c.execute("""INSERT INTO memorials
                 (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,
                  rank,position,unit,pos_x,pos_y,grp,added_by,approved)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)""",
              (..., 'admin'))  # approved=1 одразу!
    new_id = c.lastrowid
    sl = make_slug(p.first.strip(), p.last.strip(), new_id)
    c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, new_id))
    db.commit()
    cache_flush_memorials()
    return {"ok": True, "id": new_id}
```

**Примітка:** меморіали, створені через адмін-форму, одразу публікуються (`approved=1`), на відміну від записів через публічну форму (`approved=0`).

---

## 6. Нагороди

### 6.1 Перегляд нагород меморіалу

**Де:** вкладка «Нагороди» в `#edit-modal`

**JS-функція:** `loadAwards(memId)`

**Backend:** `GET /api/memorial/{id}/awards` (публічний) або `GET /api/admin/memorial/{id}/awards`

```python
@app.get("/api/memorial/{mid}/awards")
def get_memorial_awards(mid: int):
    c.execute("""SELECT id, memorial_id, name, img_file, award_date, descr, sort_order
                 FROM memorial_awards WHERE memorial_id=%s ORDER BY sort_order, id""", (mid,))
    return rows
```

**SQL:**
```sql
SELECT id, name, img_file, award_date, descr, sort_order
FROM memorial_awards
WHERE memorial_id=42
ORDER BY sort_order, id
```

**Відображення:** список нагород з іконками, назвами, датами, кнопкою [видалити].

**Зображення нагород:**
```javascript
function _wikiImg(file, w) {
  return `/img/awards/${encodeURIComponent(file)}`;  // локальні PNG!
}
```

### 6.2 Додавання нагороди

**JS-функція:** `addAward(memId)`

**Логіка:**
1. Відкриває picker з `AWARDS_DATA_ADM` (каталог нагород, завантажений при старті)
2. Модератор вибирає нагороду з каталогу (або вводить вручну)
3. Вказує дату нагородження, опис
4. Надсилає запит до API

**Backend:** `POST /api/admin/memorial/{mid}/awards`

```python
@app.post("/api/admin/memorial/{mid}/awards")
def add_award(mid: int, a: AwardIn, request: Request):
    require_moder(request)
    c.execute("""INSERT INTO memorial_awards
                 (memorial_id, name, img_file, award_date, descr, sort_order)
                 VALUES (%s, %s, %s, %s, %s, %s)""",
              (mid, a.name, a.img_file, a.award_date, a.descr, a.sort_order or 0))
    db.commit()
    return {"ok": True, "id": c.lastrowid}
```

**SQL:**
```sql
INSERT INTO memorial_awards (memorial_id, name, img_file, award_date, descr, sort_order)
VALUES (42, 'Орден «За мужність» III ступеня', 'order_courage_3.png', '2023-08-01', '', 10)
```

**Модель AwardIn (Pydantic):**
```python
class AwardIn(BaseModel):
    name:       str
    img_file:   str = ''
    award_date: str | None = None
    descr:      str = ''
    sort_order: int = 0
```

### 6.3 Видалення нагороди

**JS-функція:** `deleteAward(awardId)`

**Backend:** `DELETE /api/admin/awards/{id}`

```python
@app.delete("/api/admin/awards/{award_id}")
def delete_award(award_id: int, request: Request):
    require_moder(request)  # доступно moder і admin
    c.execute("DELETE FROM memorial_awards WHERE id=%s", (award_id,))
    db.commit()
    return {"ok": True}
```

**SQL:** `DELETE FROM memorial_awards WHERE id=17`

**⚠️ Важливо:** модератор може видаляти **нагороди** (рядки в `memorial_awards`), але не може видаляти **меморіали** (`DELETE /api/admin/memorial/{id}` — тільки admin).

### 6.4 Каталог нагород

**Завантаження при старті:**
```javascript
async function _loadAwardsCatalog() {
  const r = await fetch(API + '/api/awards/catalog');
  AWARDS_DATA_ADM = await r.json();
  // 31+ нагорода: name, img_file, category, description, sort_order
}
```

**Backend:** `GET /api/awards/catalog` (публічний, без auth)

```python
@app.get("/api/awards/catalog")
def get_awards_catalog():
    c.execute("""SELECT id, name, img_file, category, description, sort_order
                 FROM awards_catalog ORDER BY sort_order, name""")
    return rows
```

**Категорії:**
| category | Опис |
|----------|------|
| `hero` | Герой України |
| `order` | Ордени |
| `cross` | Хрести |
| `medal` | Медалі |
| `badge` | Нагрудні знаки |

**Зображення:** `/img/awards/{img_file}` — локальні PNG файли в `img/awards/`. **НЕ Wikimedia CDN!**

---

## 7. Профіль модератора

**Де:** модальне вікно `#admin-profile-modal`, відкривається кліком на ім'я у header.

### 7.1 Поля форми

| Поле | id | Опис |
|------|----|------|
| Поточний пароль | `ap-pass` | **Обов'язковий** для будь-яких змін |
| Повне ім'я | `ap-name` | Відображуване ім'я |
| Логін | `ap-login` | Тільки латиниця/цифри/_ - (3–50 символів) |
| Підтвердження логіну | `ap-login2` | Має збігатися з `ap-login` |
| Новий Email | `ap-email` | Опціонально |
| Підтвердження Email | `ap-email2` | Має збігатися |
| Новий пароль | `ap-newpass` | Опціонально |
| Підтвердження паролю | `ap-newpass2` | Має збігатися |

**Real-time перевірки доступності:**
- `#ap-login-avail` — статус логіну (зелений «✓ Вільний» / червоний «✗ Вже зайнятий»)
- `#ap-email-avail` — статус email

```javascript
// Використовує GET /api/auth/check-availability?type=login&value=...&exclude_uid={curAdminId}
// Debounce 600ms — не спамить сервер при кожному натисканні клавіші
async function _checkAvailAdmin(type, val, statusId, excludeUid) { ... }
```

### 7.2 Збереження

**JS-функція:** `saveAdminProfile()`

**Backend:** `PUT /api/admin/profile`

```python
@app.put("/api/admin/profile")
def update_admin_profile(body: AdminProfileUpdate, request: Request):
    me = require_moder(request)  # доступно moder і admin
    ip = _get_ip(request)
    # Rate limit: 5 спроб / 5 хвилин per IP
    if not _rl.check(f"admin_profile:{ip}", 5, 300):
        raise HTTPException(429, "Забагато спроб, зачекайте 5 хвилин")
    # Перевірка поточного пароля (bcrypt):
    if not verify_pass(body.current_password or "", cur["password"]):
        sec_log("ADMIN_PROFILE_WRONG_PASS", ip, f"uid={me['id']}")
        raise HTTPException(400, "Поточний пароль невірний")
    # Зміна логіну (re: r'^[a-zA-Z0-9_\-]{3,50}$'):
    if body.login:
        if not _LOGIN_RE.match(body.login):
            raise HTTPException(400, "Логін: 3–50 символів, лише латиниця, цифри, _ -")
        if body.login_confirm != body.login:
            raise HTTPException(400, "Логіни не збігаються")
        # Перевірка унікальності (виключаючи себе):
        c.execute("SELECT id FROM users WHERE nickname=%s AND id!=%s", (body.login, me["id"]))
        if c.fetchone():
            raise HTTPException(400, "Цей логін вже зайнятий")
    # Зміна email:
    if body.email:
        if body.email_confirm != body.email:
            raise HTTPException(400, "Email адреси не збігаються")
        c.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (body.email, me["id"]))
        if c.fetchone():
            raise HTTPException(400, "Цей email вже використовується")
    # Зміна пароля:
    if body.new_password:
        if body.new_password != body.new_password_confirm:
            raise HTTPException(400, "Паролі не збігаються")
        _validate_password(body.new_password)
    c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", vals)
    db.commit()
    sec_log("ADMIN_PROFILE_CHANGE", ip, f"uid={me['id']} changed={changed}")
    return {"ok": True, "changed": changed}
```

**SQL:**
```sql
UPDATE users SET name='Нове Ім''я', nickname='new_login', email='new@mail.com' WHERE id=5
```

**Модель AdminProfileUpdate (Pydantic):**
```python
class AdminProfileUpdate(BaseModel):
    current_password:    str | None = None
    name:                str | None = None
    login:               str | None = None
    login_confirm:       str | None = None
    email:               str | None = None
    email_confirm:       str | None = None
    new_password:        str | None = None
    new_password_confirm: str | None = None
```

**Перевірки:**
1. `current_password` — обов'язково (bcrypt verify)
2. Rate limit: 5 / 5 хвилин per IP
3. Логін regex: `r'^[a-zA-Z0-9_\-]{3,50}$'`
4. Логін підтвердження: `login_confirm == login`
5. Email regex: `r'^[^@\s]+@[^@\s]+\.[^@\s]+$'`
6. Email підтвердження: `email_confirm == email`
7. Новий пароль: `_validate_password()` — мінімальна довжина та складність
8. Пароль підтвердження: `new_password == new_password_confirm`
9. Унікальність нового логіну: `WHERE nickname=%s AND id!=%s`
10. Унікальність нового email: `WHERE email=%s AND id!=%s`

**Логування:** `sec_log("ADMIN_PROFILE_CHANGE", ip, f"uid={me['id']} changed=['login','email']")`

**Що бачить модератор:**
- Toast «Профіль оновлено» + оновлене ім'я у header при успіху
- Toast з текстом помилки при невдачі (напр. «Поточний пароль невірний»)

**⚠️ Обмеження:** модератор **не може** підвищити власну роль (немає доступу до `PUT /api/admin/users/{uid}/role`).

---

## 8. Статистика (read-only)

### 8.1 Загальна статистика

**Де:** секція `#sec-stats`

**JS-функція:** `loadStats()`

**Backend:** `GET /api/admin/stats`

```python
@app.get("/api/admin/stats")
def admin_stats(request: Request):
    require_moder(request)
    c.execute("SELECT COUNT(*) FROM memorials")             # total
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=1")   # approved
    c.execute("SELECT COUNT(*) FROM memorials WHERE approved=0")   # pending
    c.execute("SELECT COUNT(*) FROM users")                 # users
    c.execute("SELECT SUM(likes) FROM memorials")           # likes
    c.execute("SELECT COUNT(*) FROM users WHERE last_seen > %s AND is_banned=0", (time.time()-300,))
    return {"total", "approved", "pending", "users", "likes", "online"}
```

**Що бачить модератор:**
- `#stat-total` — всього записів у БД
- `#stat-approved` — опублікованих
- `#stat-pending` — на модерації
- `#stat-users` — зареєстрованих користувачів
- `#stat-likes` — сумарно лайків
- `#stat-online` — онлайн зараз (last_seen за останні 5 хвилин)

### 8.2 Серверна статистика

**Backend:** `GET /api/admin/server-stats`

```python
@app.get("/api/admin/server-stats")
def server_stats(request: Request):
    require_moder(request)
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    uptime = time.time() - _START_TIME
    return {cpu, ram_used, ram_total, ram_percent, uptime_seconds}
```

**Відображається:** `#stat-cpu` (%), `#stat-ram` (МБ / %), `#stat-uptime` (год:хв:сек).

---

## 9. SEO-інструменти

### 9.1 SEO Dashboard

**Де:** секція `#sec-seo`

**JS-функція:** `loadSeoDashboard()`

**Backend:** `GET /api/admin/seo-dashboard`

Показує:
- Загальний % покриття slug
- Кількість записів без slug
- Останні записи Google Indexing API log
- Розподіл оцінок A/B/C/D

### 9.2 SEO Scores — перегляд оцінок

**JS-функція:** `loadSeoScores(grade)`

**Backend:** `GET /api/admin/seo/scores?grade=A|B|C|D`

Повертає список меморіалів з їх SEO score, відсортованих від найгіршого.

**Оцінки (calc_seo_score):**

| Оцінка | Score | Критерії |
|--------|-------|---------|
| A | 85–100 | Фото + опис + дати + локація + підрозділ + відео + slug |
| B | 70–84 | Більшість полів заповнені |
| C | 50–69 | Базові поля (ПІБ + дати або фото) |
| D | < 50 | Мінімум даних |

**Алгоритм scoring:**
```python
def calc_seo_score(m: dict) -> int:
    score = 0
    if m.get('photo'):     score += 20
    if m.get('descr'):     score += 20
    if m.get('birth'):     score += 10
    if m.get('death'):     score += 10
    if m.get('loc'):       score += 10
    if m.get('unit'):      score += 10
    if m.get('video_url'): score += 10
    if m.get('slug'):      score += 10
    return min(score, 100)
```

### 9.3 Аналіз конкретного меморіалу

**JS-функція:** `analyzeSeoCard(id)`

**Backend:** `GET /api/admin/seo/analyze/{mid}`

```python
@app.get("/api/admin/seo/analyze/{mid}")
def seo_analyze(mid: int, request: Request):
    require_moder(request)
    c.execute("SELECT * FROM memorials WHERE id=%s", (mid,))
    m = c.fetchone()
    score = calc_seo_score(m)
    recommendations = []
    if not m.get('photo'):   recommendations.append("Додати фото")
    if not m.get('descr'):   recommendations.append("Додати опис")
    if not m.get('birth'):   recommendations.append("Вказати дату народження")
    if not m.get('unit'):    recommendations.append("Вказати підрозділ")
    if not m.get('slug'):    recommendations.append("Згенерувати slug")
    seo_title = gen_seo_title(m)
    seo_desc  = gen_seo_description(m)
    return {"id": mid, "score": score, "grade": grade, "recommendations": recommendations,
            "seo_title": seo_title, "seo_description": seo_desc}
```

**Що бачить модератор:** score (0–100), grade (A–D), список рекомендацій, готові title та description для Google.

### 9.4 Регенерація slug

**JS-функція:** `regenerateSlugs()`

**Backend:** `POST /api/admin/seo/regenerate-slugs`

```python
@app.post("/api/admin/seo/regenerate-slugs")
def regen_slugs(request: Request):
    require_moder(request)
    c.execute("SELECT id,first,last FROM memorials WHERE slug IS NULL AND approved=1")
    count = 0
    for row in c.fetchall():
        sl = make_slug(row['first'], row['last'], row['id'])
        c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, row['id']))
        count += 1
    db.commit()
    cache_delete("sitemap")
    return {"ok": True, "count": count}
```

**Використовується** коли є схвалені меморіали без slug (напр. після bulk import).

### 9.5 Google Ping

**JS-функція:** `pingGoogle()`

**Backend:** `POST /api/admin/seo/ping-google`

Відправляє URL нових/оновлених меморіалів до Google Indexing API для прискорення індексації.

**Умова:** активний `GOOGLE_INDEXING_KEY_FILE` у `.env`.

### 9.6 Биті посилання

**JS-функція:** `checkBrokenLinks()` (запуск), `loadBrokenLinks()` (результати)

**Backend:**
- `POST /api/admin/seo/check-broken-links` — запускає фонову перевірку
- `GET /api/admin/seo/broken-links` — результати з `seo_broken_links`

**SQL результати:**
```sql
SELECT m.id, m.last, m.first, b.url, b.status_code, b.is_broken, b.last_checked
FROM seo_broken_links b
JOIN memorials m ON m.id = b.memorial_id
WHERE b.is_broken = 1
ORDER BY b.last_checked DESC
```

### 9.7 Дублікати

**Backend:** `GET /api/admin/seo/duplicates`

```sql
SELECT last, first, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
FROM memorials WHERE approved=1
GROUP BY LOWER(last), LOWER(first)
HAVING cnt > 1
```

Показує групи меморіалів з однаковим ПІБ — можливі дублікати для перевірки.

### 9.8 Знімок SEO history

**Backend:** `POST /api/admin/seo/snapshot`, `GET /api/admin/seo/score-history`

Зберігає щоденний розподіл A/B/C/D оцінок для відстеження динаміки.

---

## 10. Щільність (read-only)

**Де:** секція `#sec-density`

Модератор може **тільки переглядати** налаштування щільності, але не змінювати.

### 10.1 Перегляд налаштувань

**Backend:** `GET /api/admin/density-settings`

Повертає поточні ваги алгоритму рейтингу (likes, views, activity, decay).

### 10.2 Heatmap

**Backend:** `GET /api/admin/density-heatmap`

Overlay на карті з тепловою картою розподілу меморіалів.

### 10.3 Статистика щільності

**Backend:** `GET /api/admin/density-stats`

Загальна статистика по розподілу рейтингів.

### 10.4 Тест-пісочниця

Модератор може вводити тестові параметри і бачити розрахований score без збереження — корисно для розуміння алгоритму.

---

## 11. Заборони

### Що модератор НЕ може робити

| Дія | Endpoint | Причина |
|-----|----------|---------|
| Видалити меморіал | `DELETE /api/admin/memorial/{id}` | `require_admin` |
| Переглянути список користувачів | `GET /api/admin/users` | `require_admin` |
| Редагувати будь-якого користувача | `PUT /api/admin/user/{uid}` | `require_admin` |
| Видалити користувача | `DELETE /api/admin/user/{uid}` | `require_admin` |
| Змінити роль | `PUT /api/admin/users/{uid}/role` | `require_admin` |
| Заблокувати user | `POST /api/admin/ban/{uid}` | `require_admin` |
| Змінити кольори/тему | `PUT /api/admin/color` | `require_admin` |
| Batch update кольорів | `POST /api/admin/colors/batch` | `require_admin` |
| Застосувати імпорт CSV | `POST /api/admin/import/apply` | `require_admin` |
| CRUD міст | `POST/PUT/DELETE /api/admin/city/*` | `require_admin` |
| Редагувати підписи карти | `PUT /api/admin/label/{id}` | `require_admin` |
| Завантажити SVG моря | `POST /api/admin/sea-svg` | `require_admin` |
| CRUD партнерів | `POST/PUT/DELETE /api/admin/partner/*` | `require_admin` |
| Налаштування хвилини мовчання | `POST /api/admin/minute-silence/*` | `require_admin` |
| Змінити власну роль | будь-який спосіб | Захист від ескалації |
| Скинути пароль user-ролі | `PUT /api/admin/user/{uid}` | Тільки для admin/moder |

### HTTP відповідь при спробі недозволеної дії

```python
raise HTTPException(403, "Недостатньо прав")
```

**Frontend:** toast з текстом «Недостатньо прав» або «403 Forbidden».

---

## 12. База даних

### Таблиці, з якими працює модератор

| Таблиця | Операції | Опис |
|---------|----------|------|
| `memorials` | SELECT, INSERT, UPDATE | Читання, редагування, схвалення, додавання |
| `memorial_awards` | SELECT, INSERT, DELETE | Нагороди меморіалів |
| `awards_catalog` | SELECT | Читання каталогу нагород |
| `users` | SELECT (власний) | Читання власного запису при /api/admin/me |
| `colors` | SELECT | Читання налаштувань через /api/colors |
| `search_logs` | SELECT | Читання через /api/admin/seo-stats |
| `seo_broken_links` | SELECT, INSERT/UPDATE | Результати перевірки посилань |
| `seo_score_history` | SELECT, INSERT | Знімки SEO оцінок |
| `seo_index_log` | SELECT, INSERT | Лог Google Indexing API |

### Ключові SQL-запити модератора

**Читання черги:**
```sql
SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC
```

**Схвалення:**
```sql
UPDATE memorials SET approved=1 WHERE id=%s;
UPDATE memorials SET slug='ivan-petrenko-42' WHERE id=%s;
```

**Редагування:**
```sql
UPDATE memorials
SET last=%s, first=%s, mid=%s, birth=%s, death=%s, loc=%s, bury=%s,
    circ=%s, descr=%s, photo=%s, video_url=%s, rank=%s, position=%s,
    unit=%s, grp=%s, color=%s, approved=%s
WHERE id=%s
```

**Додавання нагороди:**
```sql
INSERT INTO memorial_awards (memorial_id, name, img_file, award_date, descr, sort_order)
VALUES (%s, %s, %s, %s, %s, %s)
```

**Видалення нагороди:**
```sql
DELETE FROM memorial_awards WHERE id=%s
```

**Зміна профілю:**
```sql
UPDATE users SET name=%s, nickname=%s, email=%s, password=%s WHERE id=%s
```

**SEO регенерація:**
```sql
SELECT id, first, last FROM memorials WHERE slug IS NULL AND approved=1;
UPDATE memorials SET slug=%s WHERE id=%s;
```

---

## 13. Безпека

### 13.1 Rate limits для модератора

| Ключ | Ліміт | Вікно | Endpoint |
|------|-------|-------|----------|
| `admin_login:{ip}:{email}` | 5 | 900с | POST /api/admin/login |
| `admin_profile:{ip}` | 5 | 300с | PUT /api/admin/profile |
| `chk_avail:{ip}` | 30 | 60с | GET /api/auth/check-availability |

### 13.2 Хешування пароля

```python
# Хешування (при реєстрації або зміні):
bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))

# Верифікація (при вході):
bcrypt.checkpw(password.encode('utf-8'), hashed)
```

**12 rounds** — баланс між безпекою та швидкістю (~200мс на хеш).

### 13.3 Логування дій модератора

| Подія | Коли |
|-------|------|
| `ADMIN_LOGIN_OK` | Успішний вхід |
| `ADMIN_LOGIN_FAIL` | Невірний пароль |
| `ADMIN_PROFILE_CHANGE` | Зміна власного профілю |
| `ADMIN_PROFILE_WRONG_PASS` | Невірний поточний пароль |

**Файл:** `logs/security.log`

**Формат:**
```
2026-05-28 10:34:22 [INFO] [ADMIN_PROFILE_CHANGE] IP=192.168.1.10 uid=5 changed=['email']
```

### 13.4 Захист від ескалації привілеїв

- Модератор не має доступу до `PUT /api/admin/users/{uid}/role`
- Сервер завжди перевіряє роль з **БД**, не з cookie
- Session token: `secrets.token_hex(32)` — 256 bit entropy
- TTL сесії: 7 діб (604800 секунд)

### 13.5 Санітизація вхідних даних

Всі текстові поля, які модератор вводить при редагуванні меморіалу, проходять обробку:

```python
# Текст:
def _sanitize_text(text: str, max_len: int) -> str:
    text = re.sub(r'<[^>]+>', '', text)  # видаляє HTML теги
    text = html.escape(text)              # екранує спецсимволи
    return text[:max_len].strip()

# URL фото:
def _validate_photo_url(url: str) -> str:
    # Блокує: localhost, 127.x, 10.x, 192.168.x (SSRF)
    # Дозволяє: тільки http/https
    
# YouTube URL:
def _validate_yt_url(url: str) -> str:
    # Дозволяє: youtube.com/watch?v=, youtu.be/
    # Блокує: будь-який інший домен
```

---

*Технічна документація модератора «Зоряна Пам'ять» v2.1 · 2026-05-28*
