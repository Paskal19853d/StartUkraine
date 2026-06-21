# USER_DOCUMENTATION.md — Зоряна Пам'ять
# Технічна документація для користувачів (роль: user)

> Версія: v2.1 · Оновлено: 2026-05-28  
> Backend: FastAPI (Paskal.py) · Frontend: Vanilla JS (index.html) · DB: MySQL zoryana_pamyat

---

## 1. АРХІТЕКТУРА ТА СТЕК

| Компонент | Технологія |
|-----------|-----------|
| Backend | FastAPI (Python), Uvicorn/Gunicorn |
| База даних | MySQL/MariaDB, схема `zoryana_pamyat` |
| Кеш | Redis (TTL 60с), автодеградація без Redis |
| Auth | bcrypt 12 rounds + cookie `admin_session` (7 днів) |
| Frontend | Vanilla JS, Canvas API, SVG overlay |
| Файли | `index.html` (~1MB), `Style.css` (36KB), `script.js` (53KB) |

### Ролі користувачів

| Роль | Опис | Middleware |
|------|------|-----------|
| `user` | Зареєстрований публічний користувач | — (cookie сесія) |
| `moder` | Модератор контенту | `require_moder(request)` |
| `admin` | Повний доступ | `require_admin(request)` |

---

## 2. ГОЛОВНА СТОРІНКА `/`

**Файл:** `index.html`  
**Endpoint:** `GET /` → відповідь: `index.html`

### Що відображається

- Інтерактивна карта України (Canvas + SVG overlay, файл `ukraine-map.svg`, 883KB)
- Маркери-зірки на місцях загибелі (WebGL анімація)
- Панель пошуку (верхня частина сторінки)
- Соціальний бар (8 мереж, фіксований знизу)
- Кнопки: Увійти / Додати / Fullscreen
- Лічильник онлайн-користувачів
- Анімація диму (WebGL fluid simulation)
- Анімація хвиль моря (sea.js, SVG overlay)

### Ініціалізація (порядок завантаження)

```
1. DOMContentLoaded → loadColors() → applyColors() + applySocialLinks() + _applyRegSettings()
2. loadData() → GET /api/stats, GET /api/cities, GET /api/people (пагіновано по 100)
3. initSVGBorders() → малювання кордонів України
4. loadLabels() → GET /api/labels → renderCityLabels()
5. _startCanvasLoop() → requestAnimationFrame → drawDotFX() + drawNeonThreads()
6. connectWS() → POST /api/online/ping (кожні 30с)
```

---

## 3. КАРТА УКРАЇНИ

### 3.1 Ініціалізація SVG-кордонів

**Функція:** `initSVGBorders()` (`index.html`)

**Що робить:**
1. Знаходить `#ukraine-svg g[data-rid]` — групи населених пунктів кожної області (27 груп × ~20 шляхів)
2. Знаходить `#contours` — зовнішні межі областей (15 шляхів)
3. Налаштовує `vector-effect: non-scaling-stroke` для всіх шляхів
4. Стилі кордонів контролюються через CSS (`:id="dynamic-colors"` тег) — оновлюються при зміні кольорів в адмін-панелі

**Кольори кордонів (з таблиці `colors`):**

| Ключ | За замовч. | Призначення |
|------|-----------|------------|
| `oblast_fill` | `#0d2240` | Заливка областей |
| `oblast_stroke` | `#ededed` | Межа країни |
| `rayon_border` | `rgba(50,130,210,0.55)` | Межі районів + glow |
| `settlement_stroke` | `transparent` | Межі населених пунктів |

### 3.2 Навігація по карті

| Дія | Функція | Опис |
|-----|---------|------|
| Скрол колеса | `wheelZoom(cx, cy, f)` | Zoom ±25% за раз |
| Drag | `applyTr()` | Переміщення (pan) |
| Подвійний клік | `zoomAt(cx, cy, 1.5)` | Zoom ×1.5 до точки |
| Pinch (mobile) | — | Touch-zoom |
| Кнопка fullscreen | `toggleFullscreen()` | Повноекранний режим |
| Клавіша Escape | `closeCard()` | Закрити відкриту картку |

**Обмеження зуму:** керуються ключами `zoom_min` / `zoom_max` у таблиці `colors` (за замовч.: 0.4× – 8×)

**Функція `flyTo(xr, yr, ts)`:** анімований переліт до координат (xr, yr у відносних 0–1). Використовується при виборі результату пошуку.

### 3.3 Маркери-зірки

**Функція рендерингу:** `drawDotFX(p, pos, pulse)` — малює Canvas-маркер для кожного меморіалу

**Параметри вигляду (з `colors`):**

| Ключ | Опис |
|------|------|
| `dot_pulse_speed` | Швидкість мерехтіння (0.2–4.0) |
| `dot_pulse_amp` | Амплітуда пульсації (0.0–1.0) |
| `dot_glow_intensity` | Інтенсивність свічення |
| `dot_glow_size` | Розмір свічення (0.0–3.0) |
| `dot_twinkle` | Сила спалахів |

**Hit-test:** `hit(sx, sy)` — знаходить меморіал за координатами кліку мишки. Повертає найближчий ID, якщо відстань < radius.

**Радіус маркера:** `dotR(p)` — розраховує розмір на основі рейтингу та поточного зуму.

**Нитки між дублікатами:** `drawNeonThreads(visIds)` — малює лінії між записами з однаковим ПІБ.

### 3.4 Підписи областей і міст

**Функція:** `loadLabels()` → `GET /api/labels` → кешовано 60с у Redis

**Функція:** `renderCityLabels()` — малює назви міст на Canvas з урахуванням тиру (tier):
- Tier 3 (Київ): завжди видний
- Tier 2 (великі міста): від зуму 1.5
- Tier 1 (обласні центри): від зуму 2
- Tier 0 (інші): від зуму 4+

**Оновлення при зумі:** `scaleCityLabels()` — масштабує розмір тексту і показує/ховає залежно від поточного зуму.

---

## 4. ЗАВАНТАЖЕННЯ ДАНИХ

### 4.1 loadColors()

**Функція:** `loadColors()` (`index.html`)  
**Endpoint:** `GET /api/colors`  
**Кеш:** Redis TTL 60с

**Що робить:**
1. Отримує всі ключі з таблиці `colors`
2. Зберігає в `window.COLORS = {...}`
3. Викликає `applyColors()` → встановлює CSS Variables (`--bg`, `--surface`, `--accent`, ...)
4. Викликає `applySocialLinks()` → показує/ховає соцмережі, встановлює URLs і порядок
5. Викликає `_applyRegSettings()` → конфігурує форму реєстрації
6. Вставляє Google Analytics 4 script (якщо `ga_id` налаштовано)
7. Вставляє Google Site Verification meta (якщо `google_site_verification` налаштовано)

**CSS Variables що встановлюються:**
```css
--bg, --surface, --text, --text2, --accent, --yellow, --yellow2,
--neon-blue, --neon-yel (+ десятки інших кольорів)
```

### 4.2 loadData()

**Функція:** `loadData()`  
**Endpoints:** `GET /api/stats`, `GET /api/cities`, `GET /api/people?page=N&limit=100`

**Алгоритм:**
```
1. GET /api/stats → оновити лічильник записів у топбарі
2. GET /api/cities → завантажити список міст для карти
3. цикл GET /api/people?page=1&limit=100 → GET /api/people?page=2...
   поки не всі завантажені → малювати маркери порціями
```

**Кешування:** відповіді `/api/people` і `/api/cities` кешуються в Redis на 60с.

---

## 5. АВТОРИЗАЦІЯ

### 5.1 Відкриття вікна авторизації

**Елемент:** кнопка "Увійти" (або будь-яка дія що потребує авторизації)  
**Функція:** `openAuth()`  
**Модал:** `#mauth`

**Що відбувається:**
1. `document.getElementById('mauth').classList.add('open')`
2. Показується вкладка за замовч. (логін або реєстрація — залежно від контексту)
3. Якщо `reg_enabled=0` у `colors` → вкладка реєстрації прихована

**Закрити:** `closeAuth()` → `mauth.classList.remove('open')`  
**Перемикання вкладок:** `switchTab('login' | 'register')`

### 5.2 Вхід (Login)

**Де:** Модал `#mauth`, вкладка "Увійти"  
**Поля:** `#lemail` (email), `#lpass` (пароль)  
**Кнопка:** `onclick="doLogin()"`

#### 5.2.1 Frontend-логіка

**Функція:** `doLogin()` (`index.html`)

```javascript
async function doLogin() {
  const email = document.getElementById('lemail').value.trim();
  const pass  = document.getElementById('lpass').value;
  // POST /api/auth/login
  const r = await fetch(API + '/api/auth/login', {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email, password: pass})
  });
  const d = await r.json();
  if (d.ok) {
    curUser = {...d.user};
    localStorage.setItem('mu', JSON.stringify(curUser));
    updateAuthUI(); closeAuth();
    showN('Ласкаво просимо, @' + (d.user.nickname || d.user.name));
  }
}
```

#### 5.2.2 Backend

**Endpoint:** `POST /api/auth/login`  
**Файл:** `Paskal.py` (~рядок 3126)  
**Модель:** `UserLogin { email: str, password: str }`

**Логіка:**
1. Rate limit: `_rl.check(f"login_ip:{ip}", 10, 300)` → 10 спроб / 5 хв per IP. При перевищенні: 429 + `sec_log("LOGIN_RATE_LIMIT",...)`
2. Brute-force: `_is_locked(ip, email)` → якщо 5+ невдалих → 429 + `sec_log("LOGIN_LOCKOUT",...)`
3. `SELECT id,name,email,is_admin,is_banned,ban_until,password,role FROM users WHERE email=%s`
4. `verify_pass(password, row["password"])` — bcrypt (або legacy SHA256 + автоміграція)
5. Якщо `is_banned=1` і `ban_until=0` → 403 "Акаунт заблокований"
6. Якщо `is_banned=1` і `ban_until > now` → 403 "Заблокований до {дата}"
7. `_session_create(user_id)` → запис в `_sessions` dict (TTL 7 днів), повертає token
8. `resp.set_cookie("admin_session", token, httponly=True, max_age=604800)`
9. Повертає `{"ok": true, "user": {...}}`

#### 5.2.3 БД

**Таблиця:** `users`  
**Операція:** SELECT  
```sql
SELECT id, name, email, is_admin, is_banned, ban_until, password, role
FROM users WHERE email = %s
```

#### 5.2.4 Перевірки

| Перевірка | Помилка |
|-----------|---------|
| Rate limit (10/5хв per IP) | 429 "Забагато спроб входу. Зачекайте 5 хвилин." |
| Brute-force (5 спроб/15хв) | 429 "Акаунт тимчасово заблоковано. Зачекайте 15 хвилин." |
| Email не існує | 401 "Невірний email або пароль" |
| Невірний пароль | 401 "Невірний email або пароль" + `_record_fail(ip, email)` |
| Бан назавжди | 403 "Акаунт заблокований адміністратором" |
| Тимчасовий бан | 403 "Заблокований до {datetime}" |

#### 5.2.5 Права доступу

Публічний endpoint. Будь-хто може спробувати увійти.

#### 5.2.6 Що бачить користувач

- Успіх: toast "Ласкаво просимо, @nickname", модал закривається
- Помилка: toast з текстом помилки (червоний), лічильник спроб
- Rate limit: toast "Забагато спроб входу..."

---

### 5.3 Реєстрація (крок 1 — відправка коду)

**Де:** Модал `#mauth`, вкладка "Зареєструватись"  
**Модал-контейнер:** `#preg` (step 1), `#preg2` (step 2 — код)  
**Кнопка:** `#btn-send-code` → `onclick="doSendCode()"`

#### Поля форми (крок 1)

| ID елементу | Назва поля | Обов'язковість | Валідація |
|-------------|-----------|---------------|-----------|
| `#r-last` | Прізвище | Так | 2+ кирилиця, макс. 50 |
| `#r-first` | Ім'я | Так | 2+ кирилиця, макс. 50 |
| `#r-mid` | По батькові | Конфігуровано | 2+ кирилиця, макс. 50 |
| `#r-nick` | Нік | Так | 2-50 символів, букви/цифри/_ . - |
| `#r-email` | Email | Так | Формат + перевірка зайнятості |
| `#r-phone` | Телефон | Конфігуровано | 0XXXXXXXXX або +380XXXXXXXXX |
| `#r-pass` | Пароль | Так | Мін. 10 символів (конфігуровано), UPPER+lower+digit |
| `#r-pass2` | Підтвердити пароль | Так | Збігається з паролем |
| `#r-terms` | Погодитись з умовами | Так | Checkbox |

**Видимість полів по-батькові і телефон:** керується ключами `reg_field_mid` / `reg_field_phone` у `colors`:
- `required` → поле показано, обов'язкове
- `optional` → поле показано, необов'язкове
- `hidden` → поле приховано

#### Real-time перевірка доступності

**Функція:** `_checkAvailField(type, val, statusId)` → `GET /api/auth/check-availability?type=nick&value=X`

Спрацьовує з debounce 600мс при введенні ніка/email.

Відповідь:
- `{"available": true}` → `<span class="f-hint ok">✓ Вільний</span>`
- `{"available": false}` → `<span class="f-hint err">✗ Вже зайнятий</span>`
- `{"available": null, "error": "..."}` → помилка формату

**Endpoint:** `GET /api/auth/check-availability`  
Rate limit: 30 запитів/хвилину per IP.

#### 5.3.1 Frontend-логіка відправки коду

**Функція:** `doSendCode()`

```
1. _collectRegData() — зібрати всі поля в об'єкт f
2. _validateRegForm(f) — перевірити обов'язкові поля
3. Якщо помилка → showN(помилка, true) + focus на поле → повернути
4. POST /api/auth/send-code з усіма даними
5. Якщо відповідь d.registered=true → реєстрація одразу (без коду) → увійти
6. Якщо d.dev=true → показати код в DEV-mode
7. Показати #reg-code-row (поле введення коду)
8. _startResendTimer(60) → 60-секундний таймер "Надіслати повторно"
```

#### 5.3.2 Backend (крок 1)

**Endpoint:** `POST /api/auth/send-code`  
**Модель:** `SendCodeReq { last_name, first_name, middle_name, nickname, email, phone, password, terms_agreed }`

**Логіка:**
1. Rate limit: `_rl.check(f"reg_send:{ip}", 10, 3600)` → 10/год per IP
2. Rate limit per email: `_rl.check(f"reg_send_email:{email}", 3, 600)` → 3 коди / 10 хв
3. `_validate_reg_fields(u)` → перевіряє всі поля (ПІБ, нік, email, телефон, пароль)
4. `SELECT id FROM users WHERE email=%s` → якщо є → 400 "Email вже зареєстрований"
5. `SELECT id FROM users WHERE nickname=%s` → якщо є → 400 "Цей нік вже зайнятий"
6. Якщо `reg_require_email_verify=0` → `INSERT INTO users (...)` → повернути `{registered: true, user: {...}}`
7. Якщо `=1` → згенерувати 6-значний код: `secrets.choice("0123456789")`
8. Хешувати пароль: `hash_pass(u.password)` (bcrypt 12 rounds)
9. Зберегти в `_pending_reg[email]` (TTL 600с, макс. 5 спроб)
10. `_send_email(email, "Код підтвердження", html_body)` → SMTP
11. Повернути `{"ok": true}`

**Функція хешування:**
```python
def hash_pass(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=12)).decode()
```

#### 5.3.3 БД (крок 1)

**Таблиця:** `users`  
**Операції:** SELECT (перевірка унікальності). INSERT тільки якщо `reg_require_email_verify=0`.

```sql
-- Перевірка email
SELECT id FROM users WHERE email = %s

-- Перевірка ніка
SELECT id FROM users WHERE nickname = %s

-- Реєстрація без коду (якщо verify=0)
INSERT INTO users (name, first_name, last_name, middle_name, nickname, email, phone, password, role)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'user')
```

#### 5.3.4 Перевірки та обмеження

| Перевірка | Умова | Помилка |
|-----------|-------|---------|
| terms_agreed | False | 400 "Необхідно погодитись з умовами" |
| last_name | < 2 символів | 400 "Прізвище: мінімум 2 символи" |
| first_name | < 2 символів | 400 "Ім'я: мінімум 2 символи" |
| nickname | не відповідає `_NICK_RE` | 400 "Нік: 2–50 символів, літери, цифри, _ . -" |
| email | невірний формат | 400 "Невірний формат email" |
| phone | невірний формат (якщо required) | 400 "Телефон: формат +380XXXXXXXXX" |
| password | < min_len (конфігуровано) | 400 "Пароль: мінімум N символів" |
| password | без великої/малої/цифри | 400 "Пароль повинен містити..." |
| email зайнятий | EXISTS | 400 "Email вже зареєстрований" |
| нік зайнятий | EXISTS | 400 "Цей нік вже зайнятий" |
| rate limit IP | > 10/год | 429 "Забагато запитів. Зачекайте годину." |
| rate limit email | > 3/10хв | 429 "Код вже надіслано..." |

---

### 5.4 Реєстрація (крок 2 — підтвердження коду)

**Де:** `#preg2` (з'являється після відправки коду)  
**Поле:** `#r-code` (6-значний код)  
**Кнопки:** `#btn-do-register` → `onclick="doRegister()"`, `#btn-resend` → `onclick="doResendCode()"`

#### 5.4.1 Frontend-логіка

**Функція:** `doRegister()`

```
1. Зчитати код з #r-code
2. Якщо код != 6 цифр → помилка
3. POST /api/auth/register {email: _regEmail, code: code}
4. Успіх → curUser = d.user; localStorage.setItem('mu', JSON.stringify(curUser))
5. updateAuthUI() → показати кнопку "Вийти", сховати "Увійти"
6. closeAuth() + showN("Вітаємо, @nickname!")
7. Якщо помилка "знову" або "ліміт" → через 1.8с повернутись до кроку 1
```

**Фільтр поля коду:** `_fCode(el)` — дозволяє тільки цифри, максимум 6 знаків.

**Повторна відправка:** `doResendCode()` → повторно POST `/api/auth/send-code` → нові 60с очікування.

#### 5.4.2 Backend (крок 2)

**Endpoint:** `POST /api/auth/register`  
**Модель:** `UserReg { email: str, code: str }`

**Логіка:**
1. Rate limit: `_rl.check(f"reg_verify:{ip}", 10, 300)` → 10/5хв
2. `_pending_reg.get(email)` → якщо немає → 400 "Код не знайдено або минув термін дії (10 хв)"
3. `time.time() > expires` → 400 "Термін дії коду минув"
4. `attempts > _PENDING_MAX_ATTEMPTS(5)` → видалити pending → 400 "Перевищено ліміт спроб"
5. `pending["code"] != code` → increment attempts → 400 "Невірний код. Залишилось спроб: N"
6. Race condition guard: ще раз `SELECT id FROM users WHERE email=%s`
7. `INSERT INTO users (..., role='user')`
8. `_session_create(row["id"])` → cookie `admin_session`
9. `sec_log("REGISTER", ip, f"email={email} nick={nick}")`

#### 5.4.3 БД (крок 2)

**Таблиця:** `users`  
**Операція:** INSERT
```sql
INSERT INTO users (name, first_name, last_name, middle_name, nickname, email, phone, password, role)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'user')
```

#### 5.4.4 Перевірки

| Перевірка | Помилка |
|-----------|---------|
| Pending не існує (>10хв) | 400 "Код не знайдено або минув термін дії" |
| Термін минув | 400 "Термін дії коду минув. Натисніть 'Надіслати повторно'" |
| >5 спроб | 400 "Перевищено ліміт спроб. Почніть реєстрацію знову" |
| Невірний код | 400 "Невірний код. Залишилось спроб: N" |
| Email вже є (race cond.) | 400 "Email вже зареєстрований" |
| Нік вже є (race cond.) | 400 "Цей нік вже зайнятий" |

---

### 5.5 Google OAuth (вхід через Google)

**Де:** кнопка у модалі авторизації (якщо `reg_allow_google=1` у `colors`)  
**Функції:** `checkOAuthCallback()` → перевіряє URL на `?oauth=google` після редіректу

**Flow:**
1. Клік → `window.location = '/api/auth/google'`
2. Сервер редіректить на Google OAuth URL
3. Google редіректить на `/api/auth/google/callback?code=...`
4. Сервер верифікує код, знаходить або створює `users` запис
5. Встановлює cookie, редіректить на `/?oauth=google`
6. `checkOAuthCallback()` → `GET /api/auth/me` → оновлює `curUser`

**Endpoints:**
- `GET /api/auth/google` → 302 на Google OAuth URL
- `GET /api/auth/google/callback` → обробка коду, redirect до /

---

### 5.6 Logout

**Функція:** `doLogout()`  
**Endpoint:** `POST /api/auth/logout`

```javascript
async function doLogout() {
  await fetch(API + '/api/auth/logout', {method: 'POST'});
  curUser = null;
  localStorage.removeItem('mu');
  updateAuthUI();
  showN("До побачення!");
}
```

**Backend:** видаляє session token з `_sessions` dict. Видаляє cookie.

---

## 6. ПРОФІЛЬ КОРИСТУВАЧА

### 6.1 Відкриття профілю

**Функція:** `openProfile()`  
**Модал:** `#mprofile`  
**Вимога:** користувач має бути авторизований (`curUser != null`)

**Що відображається:**
- `#pf-fio` — повне ПІБ (read-only, незмінне після реєстрації)
- `#pf-nick` — нік (змінюваний)
- `#pf-public-link` — посилання `/user/nickname`
- `#pf-email` — email (змінюваний)
- `#pf-email2` — підтвердження email
- `#pf-phone` — телефон
- `#pf-oldpass` — поточний пароль (для зміни)
- `#pf-newpass` / `#pf-newpass2` — новий пароль / підтвердження

### 6.2 Збереження профілю

**Функція:** `doUpdateProfile()`  
**Endpoint:** `PUT /api/auth/profile`  
**Модель:** `UserProfileUpdate { nickname, email, email_confirm, phone, password, old_password }`

**Логіка backend:**
1. `require` — cookie сесія обов'язкова
2. `SELECT id,name,email,nickname,phone,password FROM users WHERE id=%s`
3. Нік (якщо змінено): regex `_NICK_RE`, унікальність, `UPDATE users SET nickname=%s`
4. Email (якщо змінено): формат + `email == email_confirm` + унікальність, `UPDATE users SET email=%s`
5. Телефон: формат +380XXXXXXXXX, `UPDATE users SET phone=%s`
6. Пароль (якщо `old_password` вказано): `verify_pass(old, current)` → якщо вірно → `hash_pass(new)` → `UPDATE users SET password=%s`

**БД:**
```sql
UPDATE users SET nickname=%s WHERE id=%s
UPDATE users SET email=%s WHERE id=%s
UPDATE users SET phone=%s WHERE id=%s
UPDATE users SET password=%s WHERE id=%s
```

**Помилки:**
- Нік зайнятий → 400
- Email зайнятий → 400
- Email не збігаються → 400
- Невірний поточний пароль → 400

### 6.3 Публічний профіль

**URL:** `/user/{nickname}`  
**Файл:** `profile.html`  
**Endpoint:** `GET /api/user/{nickname}`

**Відповідь API:**
```json
{
  "display_name": "Ім'я Прізвище",
  "role": "user",
  "created": 1234567890,
  "count": 5,
  "memorials": [{...}]  // тільки approved=1, is_banned=0
}
```

---

## 7. ПОШУК

### 7.1 Пошук в реальному часі

**Елемент:** поле `#search` (або `si` змінна)  
**Функція:** `doSearch(q)` → debounce 300ms  
**Dropdown:** `#sdrop`

**Логіка:**
1. Якщо `q.length < 2` → `closeDrop()` → повернути
2. `GET /api/search?q={q}` → отримати результати з сервера
3. Якщо сервер повернув результати → `renderDrop(results, q)`
4. Якщо помилка або 0 результатів → `clientScore()` (локальний fallback)
5. Підсвічування тексту: `hlText(str, q)` → HTML-escape + `<mark>` тег
6. При виборі: `pickRes(idx)` → `flyTo(x, y)` + відкрити картку

**Endpoint:** `GET /api/search?q=...`  
**Rate limit:** 30 запитів/хвилину per IP  
**Кеш:** Redis (якщо доступний)

**Backend-алгоритм пошуку:**
1. Якщо `len(q) >= 3`: FULLTEXT search `MATCH(last,first,mid,grp,loc,descr) AGAINST(%s IN BOOLEAN MODE)`
2. Потім додатково: fuzzy scoring через `_score_person(row, q)` та `_fuzzy_score(text, query)`
3. Результати сортуються за combined score

```sql
SELECT *, MATCH(last,first,mid,grp,loc,descr)
  AGAINST(%s IN BOOLEAN MODE) AS score
FROM memorials
WHERE approved=1 AND MATCH(last,first,mid,grp,loc,descr) AGAINST(%s IN BOOLEAN MODE)
ORDER BY score DESC LIMIT 50
```

### 7.2 Клавіатурна навігація в пошуку

| Клавіша | Дія |
|---------|-----|
| `↑ / ↓` | Переміщення по результатах |
| `Enter` | Вибрати поточний результат |
| `Escape` | Закрити dropdown |

### 7.3 Підсвічування на карті

**Функція:** `highlightMap(results)` — підсвічує маркери результатів, сірить решту.

---

## 8. КАРТКИ МЕМОРІАЛІВ

### 8.1 Відкриття картки

**Тригер:** клік на маркер-зірку або вибір з пошуку  
**Функція:** `openCard(p)` → двофазне завантаження  
**Модал:** `#card`

**Фаза 1 (швидка — з локальних даних):**
```javascript
// Одразу показати базову інформацію
_setText('cname', `${p.last} ${p.first} ${p.mid}`);
_setText('cdates', fd(p.birth) + ' — ' + fd(p.death));
document.getElementById('card').classList.add('open');
```

**Фаза 2 (повна — завантажити деталі):**
```javascript
// GET /api/memorial/{id} — повні дані
const full = await fetch(API + '/api/memorial/' + p.id);
_renderCardDetails(full);
// GET /api/memorial/{id}/awards — нагороди
```

### 8.2 Вміст картки

| Елемент | ID | Вміст |
|---------|-----|-------|
| Ім'я | `#cname` | Прізвище Ім'я По-батькові (Позивний) |
| Дати | `#cdates` | дд місяць рррр — дд місяць рррр |
| Місце поховання | `#cbury` | Текст або "Невідомо" |
| Підрозділ | `#cgrp` | Назва підрозділу |
| Фото | `#cpic` | Зображення або `img/foto_false.png` |
| Відео | `#cvideo-wrap` | YouTube embed або порожньо |
| Лічильник лайків | `#lcnt` | Число |
| Опис | `#cdesc` | Повний опис |
| Нагороди | Виклик `openAwards()` | Кнопка "Нагороди" |
| Дублікати | `#cdupes` | Посилання на інші записи з тим же ПІБ |

### 8.3 Функція `_renderCardDetails(p)`

**Що робить:**
- Форматує дати через `fd(s)` → ukrainian locale ("15 травня 2022")
- Рендерить фото з fallback `img/foto_false.png`
- Вбудовує YouTube відео через `_buildYtPreview(cont, ytId)` → `_ytExtractId(url)`
- Показує нагороди якщо `awards.length > 0`
- Показує секцію дублікатів якщо є збіги ПІБ

### 8.4 Slug-навігація

**URL-схема:** `/memorial/{slug}` (SEO-сторінка для Googlebot)  
**Для SPA:** `GET /api/memorial/by-slug/{slug}` → отримати ID → відкрити картку

**Формат slug:** `ivan-petrenko-42` (транслітерація KMU 2010 + суфікс id)  
**Генерація:** `seo_utils.make_slug(last, first, mid, id)` → при схваленні чи редагуванні

### 8.5 YouTube відео

**Перевірка доступності:** `GET /api/yt-check?vid={ytId}` → перевіряє чи відео відтворюється  
**Функція:** `_buildYtPreview(cont, ytId)` → embed з `youtube-nocookie.com`  
**Fallback:** `_ytFallback(cont, ytId)` → кнопка "Відкрити на YouTube"

---

## 9. ЛАЙКИ

### 9.1 Кнопка лайку

**Елемент:** `#lbtn` у картці меморіалу  
**Функція:** `doLike()`

### 9.2 Логіка лайку

```javascript
async function doLike() {
  if (!curUser) { showN("Для лайків потрібна авторизація"); openAuth(); return; }
  if (Date.now() - lastLike < 700) return; // debounce 700ms
  lastLike = Date.now();

  // Оптимістичне оновлення UI
  activePerson.likes++;
  document.getElementById('lcnt').textContent = activePerson.likes;
  // Ефект частинок

  // Відправити на сервер
  await fetch(API + '/api/like/' + activePerson.id, {method: 'POST'});
}
```

### 9.3 Backend лайку

**Endpoint:** `POST /api/like/{mid}`  
**Rate limit:** `_rl.check(f"like:{ip}", 60, 3600)` → 60 лайків/год per IP

**Логіка:**
1. Rate limit check
2. `SELECT id FROM likes_log WHERE memorial_id=%s AND fingerprint=%s AND ts > %s` — перевірка дублікату (вікно 1 год)
3. Якщо вже лайкнутий → повернути `{"ok": false, "already": true}`
4. `UPDATE memorials SET likes = likes + 1 WHERE id=%s`
5. `UPDATE memorials SET rating = ...` (перерахунок рейтингу)
6. `INSERT INTO likes_log (memorial_id, fingerprint, ts) VALUES (%s, %s, %s)`

**БД:**
```sql
-- Перевірка
SELECT id FROM likes_log
WHERE memorial_id=%s AND fingerprint=%s AND ts > %s

-- Додати лайк
UPDATE memorials SET likes = likes + 1, rating = (likes + 1) * 0.7 + ... WHERE id=%s

-- Записати в лог
INSERT INTO likes_log (memorial_id, fingerprint, ts) VALUES (%s, %s, unix_timestamp())
```

**Таблиці:** `memorials` (UPDATE), `likes_log` (SELECT + INSERT)

**Fingerprint:** хеш з IP + User-Agent + інших параметрів (ненадійний проти VPN, але достатній).

---

## 10. НАГОРОДИ

### 10.1 Перегляд нагород меморіалу

**Функція:** `openAwards()` → модал `#mawards`  
**Endpoint:** `GET /api/memorial/{id}/awards`

**Відповідь:**
```json
[{
  "id": 1,
  "name": "Орден Богдана Хмельницького I ст.",
  "img_file": "order_bogdan_1.png",
  "award_date": "2022-03-15",
  "descr": "...",
  "sort_order": 1
}]
```

**Відображення:** зображення з `/img/awards/{encodeURIComponent(img_file)}`  
**Zoom:** `medalZoom(src)` → `#medal-lightbox` → fullscreen зображення

### 10.2 Каталог нагород

**Endpoint:** `GET /api/awards/catalog`  
**Таблиця:** `awards_catalog` (31+ нагород)

```sql
SELECT id, name, img_file, category, description, sort_order
FROM awards_catalog ORDER BY sort_order
```

---

## 11. ДОДАВАННЯ МЕМОРІАЛУ

### 11.1 Відкриття форми

**Кнопка:** "Додати" (або "Увічнити")  
**Функція:** `onAdd()` → перевірка авторизації → `openAdd()`  
**Модал:** `#madd`

### 11.2 Поля форми

| ID | Поле | Тип | Обов'язково |
|----|------|-----|------------|
| `#flast` | Прізвище | text | Так |
| `#ffirst` | Ім'я | text | Так |
| `#fmid` | По батькові / Позивний | text | Ні |
| `#fbirth` | Дата народження | date | Ні |
| `#fdeath` | Дата загибелі | date | Ні |
| `#floc` | Місце загибелі | text | Ні |
| `#fbury` | Місце поховання | text | Ні |
| `#fcirc` | Обставини | text | Ні |
| `#fdesc` | Опис | textarea | Ні |
| `#fphoto` | URL фото | url | Ні |
| `#fvideo` | YouTube URL | url | Ні |
| `#fpx` / `#fpy` | Координати | hidden | Рекомендовано |

**Вибір координат:** `startPick()` → клік на карті → `#fpx`, `#fpy` встановлюються → `stopPick()`  
**Колір маркера:** кольорові кружечки `.csw` (4-7 варіантів з `colors` або захардкоджені)

### 11.3 Відправка форми

**Функція:** `submitAdd()`  
**Endpoint:** `POST /api/people`  
**Rate limit:** 5 заявок/год per IP

**Backend:**
1. Перевірка rate limit
2. Валідація `last` і `first` (обов'язкові, < 100 символів)
3. `_validate_photo_url(photo)` → SSRF-блокування
4. `_validate_color(color)` → перевірка hex/rgba
5. `_validate_yt_url(video_url)` → витягти YouTube ID
6. `_validate_date(birth)`, `_validate_date(death)` → YYYY-MM-DD
7. `_sanitize_text(last, 100)`, `_sanitize_text(first, 100)` та інші поля
8. `INSERT INTO memorials (..., approved=0)` → додано на модерацію

```sql
INSERT INTO memorials
  (last, first, mid, birth, death, loc, bury, circ, descr, photo,
   color, video_url, rank, position, unit, pos_x, pos_y, grp, added_by, approved)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
```

**Відповідь:** `{"ok": true, "id": 123, "message": "Надіслано на модерацію. Дякуємо!"}`

**Що бачить користувач:** toast "Надіслано на модерацію", форма закривається.  
**Права доступу:** тільки авторизовані (рекомендовано) — але технічно відкрито для будь-кого.

---

## 12. SEO-СТОРІНКА МЕМОРІАЛУ

**URL:** `/memorial/{slug}`  
**Призначення:** SSR-рендеринг для Googlebot і OpenGraph (шеринг в соцмережах)  
**Файл:** `templates/memorial.html` (Jinja2)  
**Кеш:** Redis TTL 300с

**Що включає:**
- `<title>` з ПІБ
- `<meta name="description">` з датами і локацією
- `<meta property="og:image">` (фото)
- Мікрозмітка Schema.org `Person`

**Endpoint:** `GET /memorial/{slug}`  
**Backend:**
1. `SELECT * FROM memorials WHERE slug=%s AND approved=1`
2. Якщо знайдено → `_TEMPLATES.TemplateResponse("memorial.html", {...})`
3. Якщо не знайдено → 404

---

## 13. СТОРІНКИ САЙТУ

| URL | Файл | Опис |
|-----|------|------|
| `/` | `index.html` | Головна (карта) |
| `/memorial/{slug}` | `templates/memorial.html` | SSR меморіал (Googlebot) |
| `/user/{nickname}` | `profile.html` | Публічний профіль |
| `/card` | `card.html` | Окрема сторінка картки |
| `/faq` | `faq.html` | Питання і відповіді |
| `/rules` | `rules.html` | Правила сайту |
| `/terms` | `terms.html` | Умови використання |
| `/privacy-policy` | `privacy-policy.html` | Політика конфіденційності |

---

## 14. ТАБЛИЦІ БД (user-level)

### 14.1 `memorials`

Основна таблиця записів загиблих захисників.

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT AUTO_INCREMENT | Первинний ключ |
| `last` | VARCHAR(100) | Прізвище |
| `first` | VARCHAR(100) | Ім'я |
| `mid` | VARCHAR(100) | По-батькові / позивний |
| `birth` | VARCHAR(20) | Дата народження |
| `death` | VARCHAR(20) | Дата загибелі |
| `loc` | VARCHAR(300) | Місце загибелі |
| `bury` | VARCHAR(300) | Місце поховання |
| `circ` | VARCHAR(500) | Обставини загибелі |
| `descr` | TEXT | Повний опис |
| `photo` | VARCHAR(500) | URL фото (https) |
| `color` | VARCHAR(20) | Колір маркера (#hex або rgba) |
| `pos_x` | DOUBLE | X на карті (0.0–1.0) |
| `pos_y` | DOUBLE | Y на карті (0.0–1.0) |
| `likes` | INT | Кількість лайків |
| `rating` | DOUBLE | Рейтинг (алгоритм) |
| `approved` | TINYINT | 0=модерація, 1=публіковано |
| `grp` | VARCHAR(100) | Позивний / підрозділ |
| `rank` | VARCHAR(100) | Звання |
| `position` | VARCHAR(100) | Посада |
| `unit` | VARCHAR(200) | Підрозділ |
| `slug` | VARCHAR(220) | SEO URL (унікальний) |

**Критичні індекси:**
- `FULLTEXT(last,first,mid,grp,loc,descr)` — для `/api/search`
- `idx_approved_rating(approved, rating DESC)` — для `/api/people`
- `idx_slug UNIQUE(slug)` — для `/memorial/{slug}`

### 14.2 `users`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT | Первинний ключ |
| `name` | VARCHAR(100) | Повне ПІБ |
| `first_name` | VARCHAR(100) | Ім'я (незмінне) |
| `last_name` | VARCHAR(100) | Прізвище (незмінне) |
| `middle_name` | VARCHAR(100) | По-батькові (незмінне) |
| `nickname` | VARCHAR(100) UNIQUE | Нік (змінюваний) |
| `email` | VARCHAR(120) UNIQUE | Email (логін) |
| `phone` | VARCHAR(20) | Телефон |
| `password` | VARCHAR(255) | bcrypt 12 rounds |
| `role` | VARCHAR(20) | admin / moder / user |
| `is_banned` | TINYINT | 1=заблокований |
| `ban_until` | INT | Unix timestamp кінця бану (0=назавжди) |
| `last_seen` | INT | Unix timestamp активності |
| `created` | INT | Unix timestamp реєстрації |

### 14.3 `likes_log`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT | Первинний ключ |
| `memorial_id` | INT | FK → memorials.id |
| `fingerprint` | VARCHAR(128) | Хеш браузера |
| `ts` | INT | Unix timestamp |

### 14.4 `memorial_awards`

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT | Первинний ключ |
| `memorial_id` | INT | FK → memorials.id |
| `name` | VARCHAR(200) | Назва нагороди |
| `img_file` | VARCHAR(300) | Ім'я файлу в img/awards/ |
| `award_date` | DATE | Дата нагородження |
| `descr` | TEXT | Опис |
| `sort_order` | INT | Порядок |

---

## 15. ПУБЛІЧНІ API ENDPOINTS (user-level)

| Метод | Endpoint | Rate Limit | Кеш | Опис |
|-------|----------|-----------|-----|------|
| GET | `/api/people?page=1&limit=50` | 60/хв | Redis 60с | Список меморіалів (пагінація) |
| GET | `/api/memorial/{id}` | — | — | Деталі меморіалу |
| GET | `/api/memorial/by-slug/{slug}` | — | — | Пошук за SEO-slug |
| GET | `/api/memorial/{id}/awards` | — | — | Нагороди меморіалу |
| GET | `/api/search?q=...` | 30/хв | Redis | Повнотекстовий пошук |
| GET | `/api/stats` | — | Redis 60с | Статистика (total, approved, likes) |
| GET | `/api/colors` | 60/хв | Redis 60с | Налаштування теми |
| GET | `/api/labels` | 60/хв | Redis 60с | Підписи областей на карті |
| GET | `/api/cities` | 60/хв | Redis 60с | Міста для карти |
| GET | `/api/awards/catalog` | — | — | Каталог нагород |
| GET | `/api/partners` | — | — | Партнери |
| POST | `/api/people` | 5/год | — | Додати меморіал (→ модерація) |
| POST | `/api/like/{id}` | 60/год | — | Лайкнути меморіал |
| POST | `/api/auth/send-code` | 10/год (IP) | — | Крок 1 реєстрації |
| POST | `/api/auth/register` | 10/5хв | — | Крок 2 реєстрації |
| POST | `/api/auth/login` | 10/5хв | — | Вхід |
| POST | `/api/auth/logout` | — | — | Вихід |
| GET | `/api/auth/me` | — | — | Поточний юзер |
| PUT | `/api/auth/profile` | — | — | Оновити профіль |
| GET | `/api/auth/check-availability` | 30/хв | — | Перевірка нік/email |
| GET | `/api/auth/google` | — | — | Google OAuth |
| POST | `/api/online/ping` | — | — | Репорт онлайн |
| GET | `/memorial/{slug}` | — | Redis 300с | SSR сторінка (SEO) |
| GET | `/sitemap.xml` | — | Redis 600с | Sitemap |
| GET | `/robots.txt` | — | — | Robots |
| GET | `/health` | — | — | Health check |

---

## 16. LOCALSTORAGE

| Ключ | Вміст | Призначення |
|------|-------|------------|
| `mu` | JSON об'єкт користувача | Відновлення сесії після перезавантаження |
| `cookieConsent` | `"accepted"` або `"declined"` | Cookie consent |
| `zp_smoke` | boolean | Пам'ятати стан smoke-ефекту |

---

## 17. БЕЗПЕКА (user-level)

| Механізм | Реалізація |
|----------|-----------|
| XSS | `html.escape()` на всіх входах, `_sanitize_text()`, `h(s)` у JS |
| SQL Injection | Параметризовані запити `cursor.execute(sql, (param,))` |
| SSRF | Блокування private IP в photo URL (`_SSRF_BLOCKED_HOSTS`) |
| Rate Limiting | `_RateLimiter.check()` per IP |
| Brute-force | 5 невдалих → 15-хв блокування (ip+email pair) |
| Password | bcrypt 12 rounds, мін. 10 символів, UPPER+lower+digit |
| Cookie | `httponly=True, samesite="lax"`, TTL 7 днів |
| Session | In-memory `_sessions` dict з TTL, thread-safe lock |

---

*Документ охоплює всі публічні та user-level функції сайту. Для функцій адміна/модератора — дивись ADMIN_DOCUMENTATION.md та MODERATOR_DOCUMENTATION.md*
