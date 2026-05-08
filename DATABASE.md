# DATABASE.md — База даних zoryana_pamyat

> MySQL/MariaDB · Хост: 127.0.0.1:3306 · Користувач: root · Кодування: utf8mb4_unicode_ci  
> Оновлено: 2026-05-07 · Поточний стан: 8 таблиць, ~960+ рядків

---

## Підключення

```python
# .env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=root
DB_NAME=zoryana_pamyat
```

```bash
# CLI (Windows, OpenServer)
D:\OSPanel\modules\MySQL-8.4\bin\mysql.exe -h 127.0.0.1 -P 3306 -u root -proot zoryana_pamyat
```

---

## Огляд таблиць

| Таблиця | Рядків | Призначення |
|---------|--------|-------------|
| `memorials` | 123 | Записи загиблих — основна таблиця |
| `users` | 1 | Адміністратори та зареєстровані користувачі |
| `colors` | 88 | ВСІ налаштування сайту (кольори + конфіг) |
| `cities` | 463 | Міста України на карті |
| `map_labels` | 24 | Підписи областей на SVG-карті |
| `memorial_awards` | 152 | Нагороди/відзнаки до меморіалів |
| `likes_log` | 0 | Журнал лайків (дедублікація) |
| `search_logs` | 123 | Аналітика пошукових запитів |

---

## Таблиця `memorials` (основна)

**Призначення:** Зберігає кожного загиблого захисника. Записи проходять модерацію (`approved=0 → 1`).

### Колонки

| Колонка | Тип | NULL | За замовч. | Опис |
|---------|-----|------|-----------|------|
| `id` | INT AUTO_INCREMENT | NO | — | Первинний ключ |
| `last` | VARCHAR(100) | NO | — | Прізвище |
| `first` | VARCHAR(100) | NO | — | Імʼя |
| `mid` | VARCHAR(100) | YES | — | Позивний / по батькові |
| `birth` | VARCHAR(20) | YES | — | Дата народження (YYYY-MM-DD або рядок) |
| `death` | VARCHAR(20) | YES | — | Дата загибелі |
| `loc` | VARCHAR(300) | YES | — | Місце загибелі |
| `bury` | VARCHAR(300) | YES | — | Місце поховання |
| `circ` | VARCHAR(500) | YES | — | Обставини загибелі |
| `descr` | TEXT | YES | — | Повний опис (може бути HTML) |
| `photo` | VARCHAR(500) | YES | — | URL фотографії (https://) |
| `color` | VARCHAR(20) | YES | `#4fc3f7` | Колір маркера на карті (hex/rgba) |
| `pos_x` | DOUBLE | YES | `0.5` | X-позиція на карті (0.0–1.0, нормалізована) |
| `pos_y` | DOUBLE | YES | `0.5` | Y-позиція на карті (0.0–1.0, нормалізована) |
| `likes` | INT | YES | `0` | Кількість лайків |
| `rating` | DOUBLE | YES | `0` | Рейтинг (алгоритм: likes + boost) |
| `approved` | TINYINT | YES | `0` | **0** = на модерації, **1** = опубліковано |
| `grp` | VARCHAR(100) | YES | — | Позивний / позначення групи |
| `added_by` | VARCHAR(100) | YES | — | Хто додав (email або ім'я) |
| `video_url` | VARCHAR(500) | NO | `''` | YouTube URL (валідується /api/yt-check) |
| `rank` | VARCHAR(100) | NO | `''` | Військове звання |
| `position` | VARCHAR(100) | NO | `''` | Посада |
| `unit` | VARCHAR(200) | NO | `''` | Військовий підрозділ (напр. "81 ОАеМБр") |

### Індекси

| Назва | Тип | Колонки | Призначення |
|-------|-----|---------|-------------|
| `PRIMARY` | BTREE | `id` | Первинний ключ |
| `idx_approved` | BTREE | `approved` | Фільтр опублікованих |
| `idx_name` | BTREE | `last, first` | Сортування/пошук за іменем |
| `idx_search` | BTREE | `last(50), first(50), grp(50), loc(100)` | Часткові індекси пошуку |
| `idx_rating_likes` | BTREE | `rating DESC, likes DESC` | Сортування за популярністю |
| `idx_grp` | BTREE | `grp(50)` | Фільтр за підрозділом |
| `idx_approved_rating` | BTREE | `approved, rating DESC, likes DESC` | **Критичний** — `/api/people` пагінація |
| `idx_fulltext_search` | **FULLTEXT** | `last, first, mid, grp, loc, descr` | Швидкий текстовий пошук `/api/search` |

### Поточний стан даних
```
Всього записів: 123
Опублікованих (approved=1): 123
На модерації (approved=0): 0
```

### Ключові запити (Paskal.py)

```sql
-- /api/people (список з пагінацією)
SELECT id,last,first,mid,birth,death,bury,loc,photo,color,pos_x,pos_y,
       grp,`rank`,`position`,unit,likes,rating,video_url,approved,added_by
FROM memorials WHERE approved=1
ORDER BY rating DESC, likes DESC
LIMIT %s OFFSET %s

-- /api/search (повнотекстовий)
SELECT *, MATCH(last,first,mid,grp,loc,descr)
  AGAINST(%s IN BOOLEAN MODE) AS score
FROM memorials
WHERE approved=1 AND MATCH(last,first,mid,grp,loc,descr) AGAINST(%s IN BOOLEAN MODE)
ORDER BY score DESC LIMIT 50

-- /api/memorial/{id}
SELECT * FROM memorials WHERE id=%s

-- Схвалення
UPDATE memorials SET approved=1 WHERE id=%s

-- Лайк
UPDATE memorials SET likes=likes+1, rating=... WHERE id=%s
```

---

## Таблиця `users`

**Призначення:** Облікові записи (адміни, модератори, публічні користувачі).

### Колонки

| Колонка | Тип | NULL | За замовч. | Опис |
|---------|-----|------|-----------|------|
| `id` | INT AUTO_INCREMENT | NO | — | Первинний ключ |
| `name` | VARCHAR(100) | NO | — | Відображуване ім'я |
| `email` | VARCHAR(120) | NO | — | Email (унікальний, логін) |
| `password` | VARCHAR(255) | NO | — | bcrypt (12 rounds) або legacy SHA256 |
| `is_admin` | TINYINT | YES | `0` | Застарілий прапор (мігровано в `role`) |
| `is_banned` | TINYINT | YES | `0` | 1 = заблокований |
| `last_seen` | INT | YES | `0` | Unix timestamp останньої активності |
| `created` | INT | YES | `unix_timestamp()` | Unix timestamp реєстрації |
| `ban_until` | INT | NO | `0` | Unix timestamp кінця блокування (0 = назавжди) |
| `notes` | TEXT | YES | — | Нотатки адміна |
| `role` | VARCHAR(20) | NO | `user` | **admin** / **moder** / **user** |

### Індекси

| Назва | Тип | Колонки | Призначення |
|-------|-----|---------|-------------|
| `PRIMARY` | BTREE | `id` | — |
| `email` | UNIQUE BTREE | `email` | Унікальний логін |
| `idx_last_seen` | BTREE | `last_seen` | Визначення "онлайн" (last_seen > now-300) |

### Поточні акаунти
```
id=1  Admin  admin@admin.com  role=admin  is_banned=0
```

### Ролі
| Роль | Доступ |
|------|--------|
| `admin` | Повний доступ до всіх `/api/admin/*` |
| `moder` | Модерація (`approve`, перегляд черги) |
| `user` | Публічний API, лайки, реєстрація |

---

## Таблиця `colors` (конфігурація)

**Призначення:** Ключ-значення сховище для **ВСІХ** налаштувань сайту. Не лише кольори!

### Схема
```sql
key   VARCHAR(50) PRIMARY KEY
value TEXT NOT NULL
label VARCHAR(100)  -- Опис для адмін-панелі
```

### Групи ключів (88 записів)

#### 🎨 Кольори UI
| Ключ | Значення | Опис |
|------|----------|------|
| `bg` | `#03070e` | Фон сторінки |
| `surface` | `#133fa0` | Поверхня карток |
| `accent` | `#00c8ff` | Акцент синій |
| `text_primary` | `#d0dce8` | Основний текст |
| `text_secondary` | `#8a9cb0` | Другорядний текст |
| `bar_bg` | `rgba(3,7,14,.96)` | Фон шапки |
| `card_bg` | `rgba(4,9,18,.98)` | Фон картки |
| `map_bg` | `#03070e` | Фон карти |
| `yellow` | `#d4a800` | Жовтий |
| `yellow2` | `#f0c030` | Жовтий яскравий |

#### 🗺 Карта
| Ключ | Значення | Опис |
|------|----------|------|
| `oblast_fill` | `#0d2240` | Заливка областей |
| `oblast_stroke` | `#ededed` | Межі міст/сіл |
| `neon_blue` | `#00ccff` | Межа країни |
| `neon_yellow` | `#d4a800` | Межа областей |
| `label_opacity` | `0.3` | Прозорість підписів |
| `city_border` | `#d0dce8` | Колір меж районів |
| `city_border_zoom` | `4` | Зум для появи меж |
| `glow_color` | `#ffffff` | Свічення кордону |
| `glow_spread` | `28` | Розсіювання свічення (px) |
| `glow_outer_color` | `#efd62e` | Зовнішнє свічення |
| `glow_outer_spread` | `25` | Розсіювання зовн. свічення |
| `thread_color` | `rgba(0,200,255,1)` | Нитки між дублікатами |
| `zoom_min` | `2` | Мінімальний зум |
| `zoom_max` | `8` | Максимальний зум |

#### ⭐ Маркери-зірки (dots)
| Ключ | Значення | Опис |
|------|----------|------|
| `dot_pulse_speed` | `2` | Швидкість мерехтіння (0.2–4.0) |
| `dot_pulse_amp` | `0.75` | Амплітуда пульсації (0.0–1.0) |
| `dot_glow_intensity` | `0.85` | Інтенсивність свічення |
| `dot_glow_size` | `0.7` | Розмір свічення (0.0–3.0) |
| `dot_twinkle` | `0.65` | Сила спалахів (0.0–1.0) |

#### 💨 Ефект диму (smoke)
| Ключ | Значення | Опис |
|------|----------|------|
| `smoke_enabled` | `1` | Увімкнено (1/0) |
| `smoke_density` | `0.97` | Затухання (0.8–1.0) |
| `smoke_velocity` | `0.92` | Швидкість (0.8–1.0) |
| `smoke_splat_radius` | `0.11` | Розмір хмари (0.1–1.0) |
| `smoke_splat_force` | `8000` | Сила (1000–15000) |
| `smoke_curl` | `24` | Завихрення (0–50) |
| `smoke_opacity` | `0.4` | Прозорість (0.1–1.0) |
| `smoke_color_from` | `#5400d1` | Колір від |
| `smoke_color_to` | `#04bdfb` | Колір до |

#### 🌊 Море (sea)
| Ключ | Значення | Опис |
|------|----------|------|
| `sea_enabled` | `0` | Показувати море (1/0) |
| `sea_wave_color` | `#1100ff` | Колір хвиль |
| `sea_wave_count` | `4` | Кількість хвиль |
| `sea_wave_intensity` | `46` | Інтенсивність (10–100) |
| `sea_wave_speed` | `5` | Швидкість (0–10) |
| `sea_wave_dir` | `45` | Напрямок (градуси) |
| `sea_shore_impact` | `82` | Удар об сушу (0–100) |
| `sea_blur` | `11` | Розмитість (px) |
| `sea_glow_on` | `1` | Свічення (1/0) |
| `sea_glow_color` | `#1b0aff` | Колір свічення |
| `sea_glow_spread` | `80` | Розсіювання свічення |
| `sea_svg_tx` | `0` | SVG зміщення X |
| `sea_svg_ty` | `0` | SVG зміщення Y |
| `sea_svg_scale` | `1` | SVG масштаб |
| `sea_svg_content` | *(SVG текст)* | Кастомний SVG overlay |

#### 🖼 Фото на карті
| Ключ | Значення | Опис |
|------|----------|------|
| `map_photo_url` | *(URL)* | URL зображення (порожньо = вимкнено) |
| `map_photo_opacity` | `0.42` | Прозорість (0.05–0.5) |
| `map_photo_blend` | `normal` | Blend mode (screen/overlay/soft-light/luminosity/normal) |
| `map_photo_feather` | `53` | Розмитість країв % (20–80) |
| `map_photo_scale` | `90` | Масштаб % (10–100) |

#### 🕐 Хвилина Мовчання
| Ключ | Значення | Опис |
|------|----------|------|
| `minute_enabled` | `1` | Увімкнено (1/0) |
| `minute_timezone` | `Europe/Kyiv` | Часовий пояс |
| `minute_color_overlay` | `#000000` | Колір заглушки |
| `minute_color_clock` | `#ffffff` | Колір циферблата |
| `minute_blur_amount` | `5` | Сила розмиття (px) |
| `minute_font` | `digital` | Шрифт (digital/regular/strict/monospace/serif) |
| `minute_font_size` | `24` | Розмір шрифта (px) |
| `minute_show_seconds` | `1` | Показувати секунди |
| `minute_sound_enabled` | `1` | Звук тиканья |

#### 🌐 Соціальні мережі
| Ключ | Значення | Опис |
|------|----------|------|
| `social_order` | `facebook,twitter,linkedin,youtube,instagram,telegram,tiktok,viber` | Порядок відображення |
| `social_facebook` | `1` | Показувати (1/0) |
| `social_facebook_url` | `''` | URL |
| `social_twitter` | `1` | — |
| `social_twitter_url` | `''` | — |
| `social_instagram` | `0` | — |
| `social_instagram_url` | `''` | — |
| `social_youtube` | `1` | — |
| `social_youtube_url` | `''` | — |
| `social_telegram` | `0` | — |
| `social_telegram_url` | `''` | — |
| `social_tiktok` | `0` | — |
| `social_tiktok_url` | `''` | — |
| `social_linkedin` | `1` | — |
| `social_linkedin_url` | `''` | — |
| `social_viber` | `0` | — |
| `social_viber_url` | `''` | — |

#### 🎭 Іконки сайту
| Ключ | Значення | Опис |
|------|----------|------|
| `icon_logo` | `★` | Символ у назві «Зоряна Памʼять» |
| `icon_likes` | `✨` | Поряд з лічильником зірок |
| `icon_people` | `👥` | Поряд з лічильником записів |

#### 🔤 Логотип
| Ключ | Значення |
|------|----------|
| `logo_star` | `#f0c030` |
| `logo_text` | `#f0c030` |
| `logo_accent` | `#00c8ff` |

#### 🔘 Кнопки UI
| Ключ | Значення |
|------|----------|
| `btn_add_bg` | `#0e2860` |
| `btn_add_text` | `#a8e0f8` |

#### ⚙️ Адмін-панель
| Ключ | Значення | Опис |
|------|----------|------|
| `admin_theme` | `light` | dark / light |
| `admin_nav_order` | `mapeditor,stats,pend,...` | Порядок пунктів меню (drag-and-drop) |
| `admin_logo_url` | *(URL)* | Логотип в сайдбарі |
| `admin_logo_height` | `30` | Висота логотипу (px) |
| `admin_logo_radius` | `0` | Заокруглення (px) |

#### Інше
| Ключ | Значення | Опис |
|------|----------|------|
| `use_cookies` | `1` | Зберігати налаштування в cookies |
| `surface` | `#133fa0` | Поверхня карток |

---

## Таблиця `cities`

**Призначення:** Міста/районні центри на інтерактивній карті.

### Колонки

| Колонка | Тип | За замовч. | Опис |
|---------|-----|-----------|------|
| `id` | INT AUTO_INCREMENT | — | PK |
| `name` | VARCHAR(100) | — | Назва міста |
| `pos_x` | DOUBLE | `0` | X-позиція (0.0–1.0, нормалізована) |
| `pos_y` | DOUBLE | `0` | Y-позиція (0.0–1.0, нормалізована) |
| `tier` | INT | `0` | Рівень важливості (0–3) |
| `color` | VARCHAR(20) | `#a0d7ff` | Колір крапки |

### Рівні `tier`

| tier | Кількість | Опис |
|------|-----------|------|
| `0` | 435 | Звичайні міста/смт |
| `1` | 21 | Обласні центри |
| `2` | 5 | Великі міста |
| `3` | 2 | Столиця (Київ) |

### Індекси
- `PRIMARY (id)`
- `idx_shown (pos_x)` — для фільтрації видимих

> ⚠️ **Координати** `pos_x / pos_y` нормалізовані (0.0–1.0), не пікселі SVG

---

## Таблиця `map_labels`

**Призначення:** Текстові підписи 24 областей на SVG-карті. Позиція задається у пікселях SVG (не нормалізована!).

### Колонки

| Колонка | Тип | За замовч. | Опис |
|---------|-----|-----------|------|
| `id` | INT AUTO_INCREMENT | — | PK |
| `name` | VARCHAR(100) | — | Назва (напр. "Закарпатська") |
| `x` | DOUBLE | — | **SVG пікселі** (великі числа, ~1000–12000) |
| `y` | DOUBLE | — | **SVG пікселі** |
| `type` | VARCHAR(20) | `oblast` | Тип підпису |
| `color` | VARCHAR(50) | `rgba(160,195,220,0.45)` | Колір тексту |
| `size` | INT | `145` | Розмір шрифта (SVG units) |

> ⚠️ **Важливо:** `map_labels.x/y` — це координати у просторі SVG (`ukraine-map.svg`, 14000×10000 умовних одиниць), **НЕ** нормалізовані 0–1 як у `cities` та `memorials`!

### Поточні 24 області
```
Закарпатська, Львівська, Волинська, Івано-Франківська, Чернівецька,
Тернопільська, Рівненська, Хмельницька, Вінницька, Житомирська,
Київська, Черкаська, Кіровоградська, Одеська, Миколаївська,
Херсонська, Запорізька, Дніпропетровська, Полтавська, Харківська,
Сумська, Чернігівська, Луганська, Донецька
```

---

## Таблиця `memorial_awards`

**Призначення:** Нагороди та відзнаки, прив'язані до конкретного меморіалу.

### Колонки

| Колонка | Тип | NULL | Опис |
|---------|-----|------|------|
| `id` | INT AUTO_INCREMENT | NO | PK |
| `memorial_id` | INT | NO | FK → `memorials.id` |
| `name` | VARCHAR(200) | NO | Назва нагороди |
| `img_file` | VARCHAR(300) | YES | Назва файлу (Wikimedia Commons) |
| `award_date` | DATE | YES | Дата нагородження |
| `descr` | TEXT | YES | Опис |
| `sort_order` | INT | NO, `0` | Порядок відображення |

### Як підвантажуються зображення
```javascript
// В admin.html
function _wikiImg(file, w) {
  return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(file)}?width=${w}`;
}
// img_file = "badge_oath.png" → повний Wikimedia URL
```

### Поточні дані
```
152 записи нагород для різних меморіалів
Приклади: "Відзнака «За вірність присязі»", "Орден «За мужність» II ст."
```

---

## Таблиця `likes_log`

**Призначення:** Дедублікація лайків — один fingerprint не може лайкнути двічі.

### Колонки

| Колонка | Тип | Опис |
|---------|-----|------|
| `id` | INT AUTO_INCREMENT | PK |
| `memorial_id` | INT | FK → `memorials.id` |
| `fingerprint` | VARCHAR(128) | Хеш браузера (IP + UserAgent + ...) |
| `ts` | INT | Unix timestamp лайку |

### Індекси
- `idx_likes (memorial_id, fingerprint, ts)` — перевірка дублікатів

### Поточний стан
```
0 записів (лайки не використовувались або лог очищено)
```

---

## Таблиця `search_logs`

**Призначення:** Аналітика пошукових запитів для дашборду.

### Колонки

| Колонка | Тип | За замовч. | Опис |
|---------|-----|-----------|------|
| `id` | INT AUTO_INCREMENT | — | PK |
| `query` | VARCHAR(200) | — | Текст пошуку |
| `results_count` | INT | `0` | Кількість знайдених |
| `created_at` | INT | `unix_timestamp()` | Unix timestamp |

### Індекси
- `idx_created_at (created_at)` — часові ряди
- `idx_query (query(50))` — групування схожих запитів

### Поточний стан
```
123 записи — всі пошуки з 2026-05-06
Приклади: "Шевченко", "Шевченк", "admin@admin.com"
```

---

## Відносини між таблицями

```
memorials (id)
    ├─── memorial_awards.memorial_id  (1:N)
    └─── likes_log.memorial_id        (1:N)

users (id)
    └─── (немає FK, але memorials.added_by = users.email)

colors (key)
    └─── Незалежна конфігураційна таблиця

map_labels / cities / search_logs
    └─── Незалежні таблиці
```

---

## Типові SQL патерни (Paskal.py)

```sql
-- Завжди параметризовані запити!
cursor.execute("SELECT * FROM memorials WHERE id=%s", (mid,))
cursor.execute("UPDATE memorials SET approved=1 WHERE id=%s", (mid,))

-- Batch update кольорів
INSERT INTO colors (`key`, value, label)
VALUES (%s, %s, %s)
ON DUPLICATE KEY UPDATE value=VALUES(value)

-- Перевірка лайку
SELECT id FROM likes_log
WHERE memorial_id=%s AND fingerprint=%s AND ts > %s

-- Онлайн користувачі
SELECT COUNT(*) FROM users WHERE last_seen > %s AND is_banned=0
```

---

## Міграції та індекси

Файл: `migrations.sql`

```sql
-- Виконувати при першому деплої або після змін схеми
-- Додає всі необхідні індекси для продуктивності
-- Не руйнує існуючі дані
```

---

## Важливі особливості

| Особливість | Деталь |
|-------------|--------|
| Кодування | utf8mb4_unicode_ci — повна підтримка Unicode, емодзі |
| `colors` = всі налаштування | Не лише кольори! Smoke, sea, social, icons, admin — все тут |
| `map_labels.x/y` | Пікселі SVG (~1000–12000), НЕ нормалізовані |
| `cities.pos_x/y` | Нормалізовані 0.0–1.0 (як `memorials`) |
| `approved=0` | Нові записи — на модерації (default) |
| `rating` | Обчислюється динамічно (likes + admin boost), не input користувача |
| `memorial_awards.img_file` | Ім'я файлу Wikimedia Commons, підвантажується через їх CDN |
| `password` | bcrypt 12 rounds; legacy SHA256 автоматично мігрується при логіні |

---

*Оновлено: 2026-05-07 · Дані актуальні на момент вивчення БД*
