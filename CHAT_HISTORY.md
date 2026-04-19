# CHAT_HISTORY.md — Зоряна Памʼять
# Повна історія задач, змін і рішень з переписки

> Файл для швидкого відновлення контексту в нових сесіях.  
> Оновлювати після кожної сесії.  
> Останнє оновлення: 2026-04-19

---

## ПРОЄКТ — КОРОТКО

**Назва:** Зоряна Памʼять — вебзастосунок-меморіал загиблих захисників України  
**Стек:** Python FastAPI · MySQL (раніше SQLite) · Vanilla JS · SVG-карта · WebGL (дим) · Canvas 2D  
**Запуск:** `python Paskal.py` або `python -m uvicorn Paskal:app --reload --port 8000`  
**URL:** `http://localhost`  
**Файли:**
- `Paskal.py` — FastAPI backend (969 рядків), MySQL, всі API
- `index.html` — головна сторінка, вся JS-логіка (3000+ рядків)
- `admin.html` — адмін-панель
- `Style.css` — глобальні стилі, CSS-змінні
- `memorial.db` — (старий, SQLite) замінений на MySQL `zoryana_pamyat`
- `.env` — DB_HOST, DB_PORT, DB_USER=root, DB_PASS=root, DB_NAME=zoryana_pamyat
- `SECURITY_RULES.md` — детальний документ з вразливостями і планом виправлення
- `MASTER_GUIDE.md` — мастер-документ проєкту

---

## СЕСІЯ 1 (попередня) — Виправлення функцій карти та анімації

### Задача 1.1 — Кнопка дим не працювала
**Проблема:** Кнопка `btn-smoke` не вмикала/вимикала ефект диму.  
**Причина:** `PAUSED=true` зупиняє фізику WebGL, але `render()` продовжує малювати останній кадр — дим залишався видимим.  
**Рішення:** Ховати через `opacity: 0` замість `display:none`, додатково `PAUSED`.

**Код — `_applySmokeState()` в `index.html`:**
```javascript
let _smokeOn = true; // за замовчуванням увімкнено

function _applySmokeState() {
  const fl  = document.getElementById('fluid');
  const btn = document.getElementById('btn-smoke');
  if (fl) {
    fl.style.opacity       = _smokeOn ? '0.85' : '0';
    fl.style.pointerEvents = 'none';
  }
  if (window._fluidConfig) window._fluidConfig.PAUSED = !_smokeOn;
  if (btn) {
    btn.classList.toggle('active', _smokeOn);
    btn.title = _smokeOn ? 'Дим увімкнено' : 'Дим вимкнено';
  }
}

function toggleSmoke() {
  _smokeOn = !_smokeOn;
  _applySmokeState();
}
```

**CSS — `#fluid` отримав transition:**
```css
#fluid { transition: opacity .4s ease; }
```

**DOMContentLoaded — кнопка активна одразу (до WebGL):**
```javascript
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-smoke');
  if (btn) { btn.classList.add('active'); btn.title = 'Дим увімкнено'; }
});
window.addEventListener('load', _applySmokeState);
```

---

### Задача 1.2 — Zoom зміщувався при прокрутці (не тримав позицію курсора)
**Проблема:** При zoom колесом мишки карта дрейфувала від курсора.  
**Причина:** `clampTr()` обрізав `tr.s` після обчислення зміщення — фактор `af` рахувався з неклампленим значенням.

**Рішення — `zoomAt()` в `index.html`:**
```javascript
function zoomAt(cx, cy, f) {
  const zMin = window.ZOOM_MIN || 0.4;
  const zMax = window.ZOOM_MAX || 12;
  const newS = Math.max(zMin, Math.min(zMax, tr.s * f)); // clamp СПОЧАТКУ
  const af   = newS / tr.s;                               // реальний коефіцієнт
  tr.x = cx - (cx - tr.x) * af;
  tr.y = cy - (cy - tr.y) * af;
  tr.s = newS;
  clampTr();
  applyTr();
}
```

**Wheel event — пропорційний zoom (0.999^deltaY):**
```javascript
mw.addEventListener('wheel', e => {
  e.preventDefault();
  const r  = mw.getBoundingClientRect();
  let dy   = e.deltaY;
  if (e.deltaMode === 1) dy *= 30;
  else if (e.deltaMode === 2) dy *= 300;
  const f = Math.pow(0.999, dy);
  zoomAt(e.clientX - r.left, e.clientY - r.top, f);
}, { passive: false });
```

---

### Задача 1.3 — Клік на точку меморіалу: центрувати + zoom
**Вимога:** При кліку — анімовано центрувати точку і зумувати до неї (мінімум 3.5x).

**Рішення — клік у `index.html`:**
```javascript
if (p && !isPick) {
  openCard(p);
  flyTo(p.x, p.y, Math.max(tr.s, 3.5));
}
```

---

### Задача 1.4 — flyTo підвисала (не плавна)
**Проблема:** Анімація була на фіксованій кількості кадрів (32) — на повільних машинах повільніше, на швидких — рвана.  
**Також:** Формула цільової позиції не враховувала offset SVG в DOM.

**Рішення — `flyTo()` з time-based animation:**
```javascript
function flyTo(xr, yr, ts) {
  const b  = getSvgBounds();
  const tx = W / 2 - (b.x + xr * b.w) * ts; // враховує offset SVG
  const ty = H / 2 - (b.y + yr * b.h) * ts;
  const sx = tr.x, sy = tr.y, ss = tr.s;
  const dur = 520; // мілісекунд
  const t0  = performance.now();
  const ease = t => 1 - Math.pow(1 - t, 3); // cubic ease-out

  (function a(now) {
    const p = ease(Math.min((now - t0) / dur, 1));
    tr.x = sx + (tx - sx) * p;
    tr.y = sy + (ty - sy) * p;
    tr.s = ss + (ts - ss) * p;
    clampTr();
    applyTr();
    if (p < 1) requestAnimationFrame(a);
  })(t0);
}
```

---

### Задача 1.5 — Нитки між дублікатами (`drawNeonThreads`)
**Вимога:** Відображати анімовані неонові нитки між точками, що позначають одну людину.

**Версія 1 (скасована):** Збіг за ФІО + дата народження + дата смерті.  
**Версія 2 (поточна):** Збіг тільки за ФІО (`last|first|mid`).

**`_dupKey` — обчислення в `loadData()`:**
```javascript
people.forEach(p => {
  const last  = (p.last  || '').trim().toLowerCase();
  const first = (p.first || '').trim().toLowerCase();
  const mid   = (p.mid   || '').trim().toLowerCase();
  p._dupKey = (last || first) ? `${last}|${first}|${mid}` : '';
});

// Debug log — перевірити в F12 Console:
const dbg = {};
people.forEach(p => {
  if (p._dupKey) {
    if (!dbg[p._dupKey]) dbg[p._dupKey] = [];
    dbg[p._dupKey].push(p.id);
  }
});
Object.entries(dbg)
  .filter(([, ids]) => ids.length > 1)
  .forEach(([k, ids]) => console.log('🔗 Зв\'язок:', k, '→ ids:', ids));
```

**`drawNeonThreads()` — Canvas 2D, неонова крива Безʼє:**
```javascript
function drawNeonThreads() {
  ctx.save();
  ctx.globalAlpha = 1;
  const groups = {};
  for (const p of people) {
    if (!p._dupKey) continue;
    if (!groups[p._dupKey]) groups[p._dupKey] = [];
    groups[p._dupKey].push(p);
  }
  for (const grp of Object.values(groups)) {
    if (grp.length < 2) continue;
    for (let i = 0; i < grp.length; i++) {
      for (let j = i + 1; j < grp.length; j++) {
        const a = w2s(grp[i].x, grp[i].y);
        const b = w2s(grp[j].x, grp[j].y);
        const dist = Math.hypot(b.x - a.x, b.y - a.y);
        if (dist < 3) continue;
        // Хвиляста середня точка
        const mx = (a.x + b.x) / 2 + Math.sin(animT * 1.5 + i) * dist * 0.08;
        const my = (a.y + b.y) / 2 + Math.cos(animT * 1.2 + j) * dist * 0.08;
        const pulse = 0.5 + 0.5 * Math.sin(animT * 2 + i * 1.3);
        // Широкий glow
        ctx.beginPath(); ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo(mx, my, b.x, b.y);
        ctx.strokeStyle = `rgba(0,200,255,${(0.12 * pulse).toFixed(2)})`;
        ctx.lineWidth = 8; ctx.stroke();
        // Тонка яскрава лінія
        ctx.beginPath(); ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo(mx, my, b.x, b.y);
        ctx.strokeStyle = `rgba(0,200,255,${(0.5 + 0.45 * pulse).toFixed(2)})`;
        ctx.lineWidth = 1.5; ctx.stroke();
        // Точка-бігун
        const t = (Math.sin(animT * 1.8 + i) + 1) / 2;
        const dx = (1-t)*(1-t)*a.x + 2*(1-t)*t*mx + t*t*b.x;
        const dy = (1-t)*(1-t)*a.y + 2*(1-t)*t*my + t*t*b.y;
        ctx.beginPath(); ctx.arc(dx, dy, 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(120,240,255,${(0.7 + 0.3 * pulse).toFixed(2)})`;
        ctx.fill();
      }
    }
  }
  ctx.restore();
}
```

**Тестові дані в БД — "Панченко Леонід Ігорович":**
- ID=19, pos=(0.625, 0.73) — оригінальний
- ID=527, pos=(0.50, 0.42) — додано для тесту
- ID=528, pos=(0.38, 0.58) — додано для тесту
- Всі `approved=1`

**Статус ниток:** ⚠️ НЕВИРІШЕНО — нитки не відображались після кількох спроб. Можливі причини: сервер не перезапущено, JS-помилка до `drawNeonThreads()`, поля `last/first/mid` = null в API.  
Для діагностики: F12 Console → шукати `🔗 Зв'язок:`.

---

## СЕСІЯ 2 (поточна 2026-04-19) — Toggle switch + Вікі + Аудит безпеки

### Задача 2.1 — Перемикач диму (Toggle Switch)
**Вимога:** Замінити кнопку 💨 на CSS toggle switch з підписом збоку.  
- За замовчуванням: увімкнено
- Підпис: "Дим увімкнено" / "Дим вимкнено"

**Зміни в `index.html` (рядок ~89) — HTML:**
```html
<!-- БУЛО: -->
<button id="btn-smoke" onclick="toggleSmoke()" title="Ефект диму вкл/викл">💨</button>

<!-- СТАЛО: -->
<div id="smoke-ctrl" onclick="toggleSmoke()" title="Ефект диму вкл/викл">
  <span id="smoke-lbl">Дим увімкнено</span>
  <div id="btn-smoke" class="smoke-toggle active"><div class="smoke-thumb"></div></div>
</div>
```

**Зміни в `Style.css` (замінено старий `#btn-smoke`):**
```css
#smoke-ctrl {
  display: flex; align-items: center; gap: 7px;
  flex-shrink: 0; cursor: pointer; user-select: none;
}
#smoke-lbl {
  font-size: 12px; color: var(--muted);
  white-space: nowrap; transition: color .25s;
}
#smoke-ctrl:has(.smoke-toggle.active) #smoke-lbl { color: var(--accent); }
.smoke-toggle {
  width: 38px; height: 20px;
  background: rgba(255,255,255,.08);
  border: 1px solid var(--border2); border-radius: 10px;
  position: relative; flex-shrink: 0;
  transition: background .25s, border-color .25s, box-shadow .25s;
}
.smoke-toggle.active {
  background: rgba(0,200,255,.2);
  border-color: rgba(0,200,255,.55);
  box-shadow: 0 0 10px rgba(0,200,255,.2);
}
.smoke-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 14px; height: 14px;
  background: var(--muted); border-radius: 50%;
  transition: transform .25s cubic-bezier(.4,0,.2,1), background .25s;
}
.smoke-toggle.active .smoke-thumb {
  transform: translateX(18px); background: var(--accent);
}
#smoke-ctrl:hover .smoke-toggle { opacity: .85; }
```

**Зміни в `index.html` — JS `_applySmokeState()`:**
```javascript
function _applySmokeState() {
  const fl  = document.getElementById('fluid');
  const btn = document.getElementById('btn-smoke');
  const lbl = document.getElementById('smoke-lbl');
  if (fl) { fl.style.opacity = _smokeOn ? '0.85' : '0'; fl.style.pointerEvents = 'none'; }
  if (window._fluidConfig) window._fluidConfig.PAUSED = !_smokeOn;
  if (btn) btn.classList.toggle('active', _smokeOn);
  if (lbl) lbl.textContent = _smokeOn ? 'Дим увімкнено' : 'Дим вимкнено';
}

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('btn-smoke');
  const lbl = document.getElementById('smoke-lbl');
  if (btn) btn.classList.add('active');
  if (lbl) lbl.textContent = 'Дим увімкнено';
});
```

---

### Задача 2.2 — Створення бази знань (WIKI)
**Вимога:** Побудувати LLM Wiki за паттерном — структура папок, CLAUDE.md, index.md, log.md.  
**Розташування:** `d:\OSPanel\OpenServer\domains\localhost\WIKI_ANTIGRAVITY\treetex\`  
**Тема:** Проєкт Зоряна Памʼять

**Структура:**
```
WIKI_ANTIGRAVITY/treetex/
├── CLAUDE.md              — схема, правила для LLM
├── raw/                   — сирі джерела (незмінні)
│   ├── articles/
│   ├── docs/
│   ├── meetings/
│   ├── decisions/
│   └── assets/
└── wiki/
    ├── index.md           — каталог всіх сторінок
    ├── log.md             — хронологічний журнал
    ├── features/
    │   ├── smoke.md
    │   └── connection-threads.md
    ├── tech/
    │   ├── stack.md
    │   ├── coordinate-system.md
    │   ├── database.md
    │   └── api-endpoints.md
    ├── design/
    │   └── color-palette.md
    └── analyses/
        ├── smoke-toggle-design.md
        ├── zoom-cursor-fix.md
        ├── flyto-animation.md
        ├── duplicate-connections.md
        ├── security-audit-2026-04-19.md
        └── security-fixes-xss.md
```

**Примітка:** Директорія не збереглась (перевірено ls). Потрібно створити повторно або вибрати інше місце.

---

### Задача 2.3 — Аудит безпеки (security review)
**Проаналізовано:** `Paskal.py`, `index.html`, `SECURITY_RULES.md`, `.env`

#### ЗНАЙДЕНІ ВРАЗЛИВОСТІ

##### Vuln 1 — Stored XSS: tooltip (index.html:2448) — HIGH
```javascript
// НЕБЕЗПЕЧНО — p.last, p.first, p.bury з БД вставляються без екранування:
tip.innerHTML = `<div class="tn">${p.last} ${p.first}</div>
                 <div class="tl">&#9875; ${p.bury||'—'}</div>...`
```
**Вектор:** Submit меморіалу з XSS в `last` → схвалення → hover tooltip → виконання JS у браузері будь-якого відвідувача.

**Виправлення:**
```javascript
function esc(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
tip.innerHTML = `<div class="tn">${esc(p.last)} ${esc(p.first)}</div>
                 <div class="tl">&#9875; ${esc(p.bury||'—')}</div>...`;
```

##### Vuln 2 — Stored XSS: card circ (index.html:2677) — HIGH
```javascript
// НЕБЕЗПЕЧНО — p.circ з БД через innerHTML:
setHTML('ccirc', p.circ ? `<span class="badge">${p.circ}</span>` : '—');
// setHTML = просто el.innerHTML = html
```
**Виправлення:**
```javascript
setHTML('ccirc', p.circ ? `<span class="badge">${esc(p.circ)}</span>` : '—');
```

##### Vuln 3 — Stored XSS: card dupes added_by (index.html:2697) — HIGH
```javascript
// НЕБЕЗПЕЧНО — d.last, d.first, d.added_by (ім'я юзера!) без екранування:
setHTML('cdupes', dupes.map(d =>
  `<span class="dupe-chip">&#128279; ${d.last} ${d.first} (${d.added_by||'?'})</span>`
).join(''));
```
**Вектор:** Реєстрація з ім'ям-скриптом → додавання меморіалу → XSS у картці дубліката.

**Виправлення:**
```javascript
setHTML('cdupes', dupes.map(d =>
  `<span class="dupe-chip">&#128279; ${esc(d.last)} ${esc(d.first)} (${esc(d.added_by||'?')})</span>`
).join(''));
```

##### Vuln 4 — Stored XSS: пошукова видача (index.html:2741+2767) — HIGH
```javascript
// hlText екранує тільки regex-метасимволи в q, але НЕ HTML в str:
function hlText(str, q) {
  if (!q || !str) return str || ''; // str з БД — не екранований!
  const esc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return str.replace(new RegExp(`(${esc})`, 'gi'), '<mark class="shl">$1</mark>');
}
sd.innerHTML = results.map(p => {
  const name = hlText(`${p.last} ${p.first}...`, q); // p.last без HTML escape!
  ...
```
**Виправлення:**
```javascript
function hlText(str, q) {
  const safe = esc(str); // HTML-escape СПОЧАТКУ
  if (!q) return safe;
  const re = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return safe.replace(new RegExp(`(${re})`, 'gi'), '<mark class="shl">$1</mark>');
}
```

##### Vuln 5 — SHA256 без солі (Paskal.py:72) — HIGH
```python
def hash_pass(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()  # Без солі — rainbow tables!
```
**Виправлення:**
```python
import bcrypt
def hash_pass(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(12)).decode()
def verify_pass(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
# ПІСЛЯ ПЕРЕХОДУ: скинути паролі всіх існуючих юзерів!
```

##### Vuln 6 — Захардкожений адмін (Paskal.py:181) — HIGH
```python
# При КОЖНОМУ старті — якщо адміна немає, створюється:
c.execute("INSERT INTO users ... VALUES (%s,%s,%s,1)",
          ("Admin", "admin@admin.com", hash_pass("Admin")))
```
**Виправлення:**
```python
admin_email = os.getenv("ADMIN_EMAIL")
admin_pass  = os.getenv("ADMIN_PASS")
if admin_email and admin_pass:
    c.execute("SELECT id FROM users WHERE email=%s", (admin_email,))
    if not c.fetchone():
        c.execute("INSERT INTO users (name,email,password,is_admin) VALUES (%s,%s,%s,1)",
                  ("Admin", admin_email, hash_pass(admin_pass)))
```
**Додати в `.env`:** `ADMIN_EMAIL=your@email.ua` · `ADMIN_PASS=SuperSecretPass123!`

##### Vuln 7 — Credentials у query params (Paskal.py:797+) — MEDIUM
```
GET /api/admin/pending?email=admin@admin.com&password=Admin
# → потрапляє в access.log, браузер history, Referer заголовки
```
**Виправлення:** JWT Bearer token. Детально — `SECURITY_RULES.md §4.1`

#### Що добре ✅
- Всі SQL запити параметризовані (`%s`) — SQL injection захищений
- FastAPI автоматично валідує типи в path params (int)
- `likes_log` — дедублікат за fingerprint+ts
- `is_banned` перевіряється при вході
- `approved=0` для нових записів — обов'язкова модерація

---

## CSS ЗМІННІ (Style.css)

```css
:root {
  --surface:   #03070e;
  --surface2:  #0a1220;
  --border:    rgba(255,255,255,.07);
  --border2:   rgba(255,255,255,.12);
  --text:      #d0dce8;
  --text2:     #8a9cb0;
  --muted:     #3a5068;
  --accent:    #00c8ff;
  --accent2:   #0088bb;
  --yellow:    #d4a800;
}
```

---

## API ЕНДПОІНТИ (Paskal.py)

### Публічні
| Метод | Шлях | Опис |
|-------|------|------|
| GET | `/api/people` | Всі approved меморіали |
| GET | `/api/search?q=` | Fuzzy пошук |
| GET | `/api/stats` | total + likes |
| GET | `/api/colors` | Конфіг кольорів |
| GET | `/api/labels` | Підписи областей |
| POST | `/api/people` | Додати (approved=0) |
| POST | `/api/like/{mid}` | Лайк |
| POST | `/api/auth/register` | Реєстрація |
| POST | `/api/auth/login` | Вхід |

### Адмін (email+password у query params — небезпечно)
| Метод | Шлях | Опис |
|-------|------|------|
| GET | `/api/admin/pending` | На модерації |
| POST | `/api/admin/approve/{mid}` | Схвалити |
| DELETE | `/api/admin/memorial/{mid}` | Видалити |
| PUT | `/api/admin/memorial/{mid}` | Редагувати |
| GET | `/api/admin/users` | Юзери |
| POST | `/api/admin/ban/{uid}` | Бан |
| PUT | `/api/admin/color` | Оновити колір |
| GET | `/api/admin/stats` | Статистика |
| GET | `/api/admin/server-stats` | CPU/RAM/uptime |
| WS | `/ws/online` | WebSocket онлайн |

---

## СХЕМА БАЗИ ДАНИХ (MySQL)

### `memorials`
`id, last, first, mid, birth, death, loc, bury, circ, descr, photo, color, pos_x, pos_y, likes, rating, approved, grp, added_by`

### `users`
`id, name, email, password (SHA256!), is_admin, is_banned, last_seen, created`

### `colors`
`key, value, label` — конфіг: акцент, дим, zoom_min/max, тощо

### `map_labels`
`id, name, x, y, type, color, size` — підписи областей

### `search_logs`
`id, query, results_count, created_at` — обмежено 10 000 записів

### `likes_log`
`id, memorial_id, fingerprint, ts` — антиспам лайків

---

## НЕВИРІШЕНІ ПИТАННЯ / BACKLOG

| # | Задача | Пріоритет | Примітка |
|---|--------|-----------|---------|
| 1 | ⛔ XSS — `esc()` у tooltip, card, search | КРИТИЧНО | 10 хв роботи, патч готовий у цьому файлі |
| 2 | ⛔ bcrypt замість SHA256 | КРИТИЧНО | Скинути паролі після переходу |
| 3 | ⛔ Адмін з .env, не захардкожено | КРИТИЧНО | Додати ADMIN_EMAIL/ADMIN_PASS в .env |
| 4 | ⛔ Нитки не видно на карті | Висока | Перевірити F12 Console → `🔗 Зв'язок:` |
| 5 | ⛔ JWT для адмін API | До публікації | SECURITY_RULES.md §4.1 |
| 6 | ⛔ CORS обмежити домен | До публікації | Зараз `allow_origins=["*"]` |
| 7 | ⛔ buymeacoffee.com — реальний URL | Малий | Замінити placeholder в index.html |
| 8 | ⛔ Вікі (`WIKI_ANTIGRAVITY`) не збереглась | — | Потрібно створити повторно |

---

## ЯК КОРИСТУВАТИСЬ ЦИМ ФАЙЛОМ

Дай цей файл Claude на початку нової сесії:  
> "Ось наша попередня переписка: [вставити CHAT_HISTORY.md]"

або:  
> "Читай CHAT_HISTORY.md і продовжуй роботу з задачею #4"

Файл містить весь контекст: стек, код, вразливості, статуси задач.
