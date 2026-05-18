# AGENTS.md — Зоряна Памʼять (Zoryana Memory)

> Цей файл читається AI-агентами (Claude Code, Codex, Gemini та ін.) для розуміння проекту.
> Головний файл інструкцій: `CLAUDE.md` — читати ПЕРШИМ.

---

## Короткий огляд

**Зоряна Памʼять** — українська меморіальна платформа для загиблих захисників України.
- Backend: **FastAPI** (Python) → `Paskal.py` (~6000 рядків)
- Frontend: **Vanilla JS + HTML5** → `index.html` (~4930 рядків), `admin.html` (~10550 рядків)
- DB: **MySQL/MariaDB** → схема `zoryana_pamyat`
- Prod: **Gunicorn + Nginx** | Dev: `uvicorn Paskal:app --reload --port 8000`

---

## Структура файлів (критичні)

| Файл | Роль | Розмір |
|------|------|--------|
| `Paskal.py` | Весь backend (FastAPI, endpoints, DB, auth) | ~6000 рядків |
| `index.html` | Головна публічна сторінка | ~4930 рядків |
| `admin.html` | Адмін-панель | ~10550 рядків |
| `Style.css` | Глобальні стилі | 36 KB |
| `seo_utils.py` | Транслітерація KMU 2010, slug-генератор | — |
| `migrations.sql` | Міграції БД (індекси, нові таблиці) | — |
| `js/script.js` | WebGL fluid simulation (smoke effect) | MIT |
| `js/sea.js` | SVG хвилі моря (feTurbulence) | — |
| `silence-module.js` | Хвилина мовчання | — |
| `CLAUDE.md` | Повні інструкції для Claude Code | **читати першим** |
| `DATABASE.md` | Детальна схема БД | — |
| `SECURITY_RULES.md` | Правила безпеки | — |

---

## База даних — таблиці

| Таблиця | Призначення |
|---------|-------------|
| `memorials` | Основна: дані загиблих (ПІБ, фото, позиція на карті, slug) |
| `users` | Акаунти (bcrypt, Google OAuth, Дія) |
| `colors` | Всі налаштування сайту (60+ ключів: кольори, smoke, sea, соцмережі) |
| `partners` | Блоки партнерів/друзів на головній (logo + link + позиція) |
| `memorial_awards` | Нагороди прив'язані до конкретного меморіалу |
| `awards_catalog` | Каталог всіх нагород (31+ PNG у `img/awards/`) |
| `cities` | Міста на карті (400+) |
| `map_labels` | Підписи областей |
| `likes_log` | Дедублікація лайків |
| `search_logs` | Аналітика пошуку |
| `hourly_stats` | Погодинна статистика відвідувань |
| `minute_silence_settings` | Налаштування хвилини мовчання |

---

## API Endpoints (ключові)

### Публічні
```
GET  /api/people?page=1&limit=50   — список меморіалів (Redis кеш 60с)
GET  /api/memorial/{id}            — деталі запису
GET  /api/search?q=NAME            — FULLTEXT пошук (limit 50)
GET  /api/stats                    — лічильники
GET  /api/colors                   — всі налаштування (кольори, smoke, sea, тощо)
GET  /api/cities                   — міста на карті
GET  /api/labels                   — підписи областей
GET  /api/partners                 — партнери/друзі (is_visible=1)
POST /api/like/{id}                — лайк (fingerprint dedup)
GET  /api/awards/catalog           — каталог нагород
GET  /memorial/{slug}              — SSR-сторінка (Jinja2, для Googlebot)
GET  /sitemap.xml                  — XML sitemap
```

### Авторизація
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
PUT  /api/auth/profile
GET  /api/auth/google              — Google OAuth
```

### Адмін (Basic Auth або cookie `admin_session`)
```
GET/PUT/POST/DELETE /api/admin/memorial/{id}
GET/POST/DELETE     /api/admin/city/*
GET/PUT             /api/admin/label/*
PUT                 /api/admin/color
PUT                 /api/admin/colors/batch
GET/POST/DELETE     /api/admin/users/*
GET/POST/PUT/DELETE /api/admin/partner*    — партнери
GET                 /api/admin/export/csv
POST                /api/admin/import/apply
GET                 /api/admin/stats
GET                 /api/admin/server-stats
GET/POST/…          /api/admin/seo/*       — SEO dashboard
```

---

## Правила безпеки (ОБОВ'ЯЗКОВО)

1. **SQL** — тільки параметризовані запити: `cursor.execute(sql, (params,))`
2. **User input** → `_sanitize_text()` або `html.escape()`
3. **Photo URL** → `_V.chkUrl()`, блокувати приватні IP (SSRF)
4. **SVG** → `_sanitize_svg()` (видаляє script, on*, foreignObject)
5. **Rate limiting** → 60 req/IP/60с публічні; не додавати endpoints без rate limit
6. **`.env`** — не комітити, містить секрети DB, OAuth

---

## Frontend правила

### admin.html — SVG іконки
- **Тільки** inline sprite: `<svg class="adm-ico"><use href="#ico-NAME"/></svg>`
- **Заборонено** емодзі в nav-item, sec-title, кнопках `.btn`
- Доступні іконки: `stats`, `doc`, `hourglass`, `users`, `auth`, `email`, `palette`, `share`, `smoke`, `waves`, `star`, `photo`, `city`, `candle`, `search`, `check`, `cross`, `edit`, `trash`, `plus`, `map`

### CSS
- Теми через `var(--variable)`: `--bg`, `--surface`, `--text`, `--accent`, `--border`
- `.btn` — чорний фон `#111318`; `.btn-p` — з синьою рамкою; `.btn-r/g/b` — з кольоровою рамкою

### BroadcastChannel (синхронізація між вкладками)
| Канал | Призначення |
|-------|-------------|
| `zoryana_colors` | Оновлення кольорів з адмінки → index.html |
| `zoryana_silence` | Хвилина мовчання |
| `zoryana_partners` | Оновлення партнерів з адмінки → index.html |

---

## Специфіка WebGL (smoke effect)

- Файл: `js/script.js` — MIT, Pavel Dobryakov
- Canvas: `<canvas id="fluid">` — `position:fixed; z-index:900; mix-blend-mode:screen`
- `_applySmokeState()` в `index.html` керує opacity (0 або 0.85)
- `window._fluidConfig` — НІКОЛИ не присвоюється, всі перевірки є no-op
- `smoke_enabled` ключ в таблиці `colors` — `'0'` вимикає smoke для всіх

---

## DB Connection Pattern

```python
db = get_db()
try:
    with db.cursor() as c:
        c.execute("SELECT ... WHERE id=%s", (id,))
        result = c.fetchall()
    db.commit()  # тільки для DML (INSERT/UPDATE/DELETE)
    return result
finally:
    db.close()
```

Ніколи не забувати `finally: db.close()` — повертає з'єднання до пулу.

---

## Що НЕ змінювати без явного запиту

- Структуру БД — тільки через `migrations.sql` + `init_db()` в `Paskal.py`
- `.env` — секрети
- `memorial.db` — старий SQLite, **ігнорувати**
- Алгоритм рейтингу (`rating` field)
- Систему сесій (in-memory dict, thread-safe)
- Gunicorn/Nginx конфіги

---

## Запуск (dev)

```bash
# Windows
cd D:\OSPanel\OpenServer\domains\localhost\treetex
venv\Scripts\activate
uvicorn Paskal:app --reload --port 8000
```

URL: `http://127.0.0.1:8000` | Адмін: `http://127.0.0.1:8000/admin`

---

*Останнє оновлення: 2026-05-18 | v2.42 beta*
*Детальніше: `CLAUDE.md`, `DATABASE.md`, `SECURITY_RULES.md`*
