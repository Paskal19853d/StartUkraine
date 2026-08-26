# SKILL.md — Зоряна Памʼять: Постійні правила роботи

> Цей файл читається Claude Code **автоматично** на початку кожної сесії разом з CLAUDE.md.
> Містить обовʼязкові навички та стандарти, які застосовуються до **кожного** завдання.
>
> **Пов'язана документація:** [CLAUDE.md](CLAUDE.md) (головний довідник) · [SECURITY_RULES.md](SECURITY_RULES.md) (детальні політики безпеки) · [SESSION_CHANGES.md](SESSION_CHANGES.md) (як ці навички застосовані в останній сесії)

---

## SKILL 1 — БЕЗПЕКА: перевірка від злому та витоку даних

### Застосовувати до кожного нового endpoint, форми, JS-функції

#### Backend (Paskal.py)

| Перевірка | Що робити |
|-----------|-----------|
| SQL Injection | ТІЛЬКИ параметризовані запити `cursor.execute(sql, (val,))`. Ніколи f-string в SQL крім динамічного `IN ({ph})` |
| SQL `IN` з list | `ph = ",".join(["%s"]*len(lst)); cursor.execute(f"...IN ({ph})", lst)` — ніколи не передавати list як один `%s` |
| XSS | Всі user inputs через `_sanitize_text()` або `html.escape()` перед записом в БД |
| SVG upload | Обовʼязково `_sanitize_svg()` — видаляє `<script>`, `on*`, `foreignObject`, `<use>` |
| SSRF | Photo URL валідувати через `_V.chkUrl()`, блокувати приватні IP: `127.x`, `10.x`, `192.168.x`, `0.0.0.0` |
| Auth на admin endpoints | Кожен `/api/admin/*` — починається з `require_admin(request)` |
| Rate limiting | Кожен новий публічний endpoint — додавати rate limit (60 req/IP/60s базовий) |
| Brute-force | Auth endpoints: 5 невдалих → lockout 15 хв per IP:email |
| Secrets у коді | `.env` тільки для секретів. Ніколи не хардкодити паролі, ключі, токени |
| Завантаження файлів | Перевіряти MIME type, обмежувати розмір, не зберігати в web-root без санітизації імені |

#### Frontend (JS)

| Перевірка | Що робити |
|-----------|-----------|
| `credentials:'include'` | ЗАВЖДИ додавати у fetch до `/api/admin/*` при cookie-auth (`AP=''`) |
| XSS через innerHTML | Не вставляти user-контент через `innerHTML`. Використовувати `textContent` або `_sanitize_text()` |
| Open redirect | Перевіряти що redirect URL починається з `/` або є власним доменом |
| Sensitive data у localStorage | Не зберігати токени, паролі, особисті дані в localStorage/sessionStorage |
| Console.log secrets | Не логувати токени, паролі, PII у console |
| CSRF | Всі мутуючі запити (POST/PUT/DELETE) йдуть через cookie-сесію, CORS middleware захищає |

#### Чеклист перед кожним новим модулем
```
[ ] Всі inputs — sanitize
[ ] SQL — тільки параметризовані
[ ] Admin endpoint — require_admin()
[ ] Rate limit — встановлено
[ ] credentials:'include' — у кожному admin fetch
[ ] Секрети — у .env, не в коді
[ ] Файли — MIME + розмір перевірено
[ ] redirect — відносний або власний домен
```

---

## SKILL 2 — АДАПТИВНИЙ ДИЗАЙН: від телефону до плазми

### Застосовувати до кожної нової UI-секції, компонента, сторінки

#### Брейкпоінти проекту

```
Телефон portrait  : ≤ 480px
Телефон landscape : ≤ 768px  (max-height ≤ 480px)
Планшет           : 769px – 1024px
Десктоп           : 1025px – 1440px
Wide / 2K         : 1441px – 2560px
4K / Плазма TV    : 2561px+
```

#### Обовʼязкові правила CSS

**1. Mobile-first або graceful degradation — обидва підходи ОК, але послідовно в одному файлі.**

**2. Тексти — відносні одиниці:**
```css
/* Добре */
font-size: clamp(12px, 1.5vw, 16px);
font-size: clamp(20px, 3vw, 36px);   /* заголовки */

/* Погано */
font-size: 14px;  /* фіксований px на заголовках */
```

**3. Контейнери — max-width + padding:**
```css
.container {
  width: 100%;
  max-width: 1400px;
  padding: 0 clamp(12px, 4vw, 48px);
  margin: 0 auto;
}
/* На 4K не розтягувати на весь екран — max-width обмежує */
```

**4. Зображення — завжди адаптивні:**
```css
img { max-width: 100%; height: auto; }
/* Фото в картках — object-fit: contain (не cover!) щоб не обрізати обличчя */
```

**5. Grid і Flex — автоматично адаптуються:**
```css
/* Grid — автоматична кількість колонок */
display: grid;
grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));

/* Flex — wrap дозволяє перенос */
display: flex;
flex-wrap: wrap;
gap: clamp(8px, 2vw, 24px);
```

**6. Touch-зони — мінімум 44×44px:**
```css
button, a, [role="button"] {
  min-height: 44px;
  min-width: 44px;  /* для іконок-кнопок */
}
```

**7. Горизонтальний scroll замість обрізання:**
```css
/* Якщо вміст не вміщається — скрол, не overflow:hidden */
.topbar, .tabs, .toolbar {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.topbar::-webkit-scrollbar { display: none; }
```

**8. 4K / Плазма TV (≥ 2560px):**
```css
@media (min-width: 2560px) {
  :root { --bar: 70px; font-size: 18px; }
  .container { max-width: 2000px; }
  /* Збільшити відступи, розміри іконок, кнопок */
}
```

#### Чеклист перед кожним новим UI-компонентом
```
[ ] Перевірено на 360px (маленький телефон)
[ ] Перевірено на 768px (планшет portrait)
[ ] Горизонтального скролу тіла сторінки немає
[ ] Touch-зони ≥ 44px
[ ] Текст не виходить за межі контейнера
[ ] Зображення не розтягнуті
[ ] На 1920px виглядає нормально (не розтягнуто на весь екран)
[ ] CSS var(--variable) — не хардкод кольорів
```

#### Специфіка проекту Зоряна Памʼять

```css
/* Топбар — scroll на мобільних (вже реалізовано) */
@media (pointer: coarse) {
  #topbar { overflow-x: auto; scrollbar-width: none; }
}

/* Картки — одна колонка на телефоні, 2-3 на планшеті */
@media (max-width: 480px) { .card-grid { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .card-grid { grid-template-columns: repeat(2, 1fr); } }

/* Форми — одна колонка на мобільних */
@media (max-width: 768px) { .fr { grid-template-columns: 1fr; } }

/* Заборона auto-zoom на iOS при фокусі */
@media (max-width: 768px) {
  input, select, textarea { font-size: 16px; }
}
```

---

## SKILL 3 — СТРУКТУРА ФАЙЛІВ: організація по папках і типах

### Застосовувати при кожному новому модулі, функції, компоненті

#### Правило: один тип — одна папка

```
treetex/
├── *.py               — тільки Python backend (Paskal.py, seo_utils.py, setup_*.py)
├── *.html             — тільки HTML сторінки (index, admin, card, profile, faq...)
├── Style.css          — єдиний глобальний CSS файл
├── script.js          — головний frontend JS
├── js/                — допоміжні JS модулі (sea.js, dat.gui.min.js тощо)
├── fonts/             — шрифти (woff2, woff, css) — тільки локальні
├── img/               — всі зображення, розбиті по підпапках:
│   ├── awards/        — нагороди (PNG)
│   ├── ranks/         — погони звань (PNG)
│   └── social/        — іконки соцмереж (PNG)
├── templates/         — Jinja2 шаблони для SSR (memorial.html)
├── Doc/               — SVG діаграми архітектури (не публічні)
├── logs/              — тільки логи (security.log тощо)
└── portfolio/         — окрема підсторінка /promo/ (свій index.html)
```

#### При додаванні нового модуля — обовʼязково

| Тип файлу | Куди класти |
|-----------|------------|
| Python скрипт / утиліта | корінь `/` поруч з Paskal.py |
| JS модуль (окрема логіка) | `js/` |
| Зображення нагород | `img/awards/` |
| Зображення погонів | `img/ranks/` |
| Іконки соцмереж | `img/social/` |
| Загальні зображення UI | `img/` |
| Шрифти | `fonts/` (локально, не CDN) |
| Jinja2 шаблон | `templates/` |
| Окрема публічна підсторінка | власна папка (`portfolio/`, `promo/`) з `index.html` |
| Тимчасові скрипти / міграції | корінь, але з чітким префіксом (`setup_`, `migrate_`, `fix_`) |

#### Що ЗАБОРОНЕНО

- Класти JS у корінь без причини (крім `script.js` — він головний)
- Класти зображення у корінь (тільки `favicon.ico` — виняток)
- Мікшувати типи в одній папці (CSS у `js/`, зображення у `fonts/`)
- Створювати глибоку вкладеність без потреби (максимум 2 рівні)
- Дублювати файли в різних папках
- Зберігати секрети у будь-якій папці крім `.env` (не комітити)

#### Іменування файлів

```
Python:     snake_case.py          (setup_awards.py, seo_utils.py)
JS модулі:  kebab-case.js          (sea.js, dat.gui.min.js)
HTML:       kebab-case.html        (admin.html, card.html)
CSS:        PascalCase.css         (Style.css — єдиний, не множити)
Зображення: snake_case або kebab   (foto_false.png, novidio.gif)
Конфіги:    kebab-case або крапка  (.env, gunicorn.conf.py)
```

#### Чеклист при кожному новому модулі
```
[ ] Файл лежить у правильній папці для свого типу
[ ] Назва файлу відповідає конвенції (snake/kebab/Pascal)
[ ] Зображення — у відповідній підпапці img/
[ ] JS логіка модуля — у js/ (якщо окремий файл потрібен)
[ ] Нема дублікатів існуючих файлів
[ ] Нема секретів поза .env
[ ] CLAUDE.md оновлено якщо зʼявилась нова папка або файл
```

---

## ЗАСТОСУВАННЯ

Claude Code застосовує всі три SKILL автоматично:

- При написанні **будь-якого нового endpoint** → SKILL 1 чеклист (безпека)
- При написанні **будь-якого нового CSS/HTML блоку** → SKILL 2 чеклист (адаптив)
- При **створенні нового модуля або файлу** → SKILL 3 чеклист (структура)
- При **code review** → перевіряти всі три чеклисти
- **Не питати** "чи потрібна адаптивність" — вона завжди потрібна
- **Не питати** "чи потрібна перевірка безпеки" — вона завжди потрібна
- **Не питати** "куди покласти файл" — SKILL 3 визначає структуру

---

*Оновлено: 2026-07-07*
