# Деплой v3.44–v3.56: тарифные рамки, «Подарки погибшему», админка и поиск на карте «Світ»

> Составлено 2026-10-04. Охватывает изменения от v3.44 (тарифные рамки боковой панели) до v3.56 (поиск на карте «Світ»).
> Подробно о каждой версии — [CLAUDE.md](CLAUDE.md), раздел 15. Поверсионные блоки деплоя — [SESSION_CHANGES.md](SESSION_CHANGES.md), раздел 2.

**Коротко:**
- загрузить на сервер 7 файлов;
- выполнить в PhpMyAdmin один SQL-файл, `migrations_i18n_gifts.sql`;
- перезапустить бэкенд — колонку тарифа, 4 таблицы подарков и индекс он при старте создаст сам;
- разово, по желанию — вернуть на место звезду записи 669 и проверить, не обрезаны ли описания (раздел 3).

---

## 1. Перед началом

Сделайте копию базы (FastPanel → Базы данных → PhpMyAdmin → `zoryana_pamyat` → Экспорт) и копию файлов, которые будете заменять.

## 2. Файлы — в папку проекта на сервере (рядом с `Paskal.py`)

| Файл | Что в нём |
|---|---|
| `Paskal.py` | тарифный план; весь модуль подарков: каталог, заказы, оплата LiqPay, GIF, места у свечи, настройки; «Опис» до 10000 символов (правка, создание, импорт) |
| `admin.html` | поле «Тарифний план»; раздел «Подарунки загиблому»; карты админки (место звезды, модерация) берут тайлы с ключом CARTO из «Карта світу»; поле «Опис» — до 10000 символов |
| `card.html` | подарки у свечи, каталог, покупка, возврат с LiqPay, возложение |
| `index.html` | тарифная рамка боковой панели; поиск на карте «Світ» перелетает к точке гибели и показывает на звезде фокус, как на карте Украины |
| `mobile.html` | то же для планшетной версии |
| `Style.css` | металлическая рамка и перелив четырёх тарифов; подсветка найденной звезды на карте «Світ» |
| `mobile.css` | свечение рамки для нижнего листа |

`index.html`, `mobile.html` и `Style.css` содержат ещё и изменения v3.40–v3.43: скрытие оверлеев на телефоне, красную «×» и плавный зум. Если они уже на проде, ничего не изменится; если нет, уйдут вместе с этими файлами (они проверены). Версия стилей в них — `Style.css?v=20261004b`, так что браузеры возьмут новый CSS сразу, без Ctrl+F5. Публичный журнал `update_v/uddate_history.html` (v3.39) в этот диапазон не входит — залейте его отдельно, если его ещё нет на проде.

**Не заливать:**
- `.env` с компьютера: там локальные настройки (root/root, 127.0.0.1), прод с ним перестанет работать.
- `img/gifts/demo/` — локальные заглушки.

Документация (`CLAUDE.md`, `DATABASE.md`, `SESSION_CHANGES.md`, `MASTER_GUIDE.md`, `SECURITY_RULES.md`, `Gifts-for-fallen.md`, `.env.example`, этот файл) — по желанию, на работу сайта не влияет. Новых Python-пакетов и правок Nginx не нужно.

## 3. SQL в PhpMyAdmin

Выбрать базу `zoryana_pamyat` → вкладка SQL → вставить содержимое `migrations_i18n_gifts.sql` → выполнить.

- Это 190 строк текстов модуля на украинском и английском. Повторный запуск безопасен: тексты просто обновятся.
- Без этой миграции модуль работает на встроенных украинских текстах, а английского не будет.
- Если база не выбрана, будет ошибка `#1046`. Тогда добавьте первой строкой `USE zoryana_pamyat;`.

**Разово — запись 669 (Канцір Андрій).** Пока карта в админке не показывалась, метку этой записи поставили вслепую: координаты ушли в Индию (lat 24.7069, lng 79.2773), звезда пропала с карты Украины, а на карте «Світ» стоит в Индии. Запрос возвращает прежнее положение — Сватово, совпадает с местом гибели. Можно выполнить и до заливки; звезда вернётся через минуту-другую (кэш):

```sql
UPDATE memorials SET pos_x = 0.8475, pos_y = 0.3513, world_lat = NULL, world_lng = NULL WHERE id = 669;
SELECT id, pos_x, pos_y, world_lat, world_lng FROM memorials WHERE id = 669;   -- 0.8475, 0.3513, NULL, NULL
```

Точнее (село Стельмахівка) метку можно поставить после заливки: в админке карта уже будет видна.

**Разово — не обрезаны ли описания.** До v3.55 поле «Опис» в админке при любом вводе (даже стёртом символе) обрезало текст до 200 символов, а сервер — до 5000. Запрос покажет подозрительные записи: ровно 200 — вероятно, обрезаны полем в админке, ровно 5000 — старым пределом. Сам текст не восстановится — только из источника (например, страницы на ukraine-memorial.org), после заливки в поле помещается до 10000 символов:

```sql
SELECT id, `last`, `first`, CHAR_LENGTH(descr) AS len FROM memorials WHERE CHAR_LENGTH(descr) IN (200, 5000) ORDER BY len, id;
```

## 4. Перезапуск бэкенда

```
sudo systemctl restart zoryana
```

Имя сервиса укажите своё: в заметках о сервере встречаются `zoryana` и `zoryna`.

При старте бэкенд сам создаст:
- колонку `memorials.tier` (v3.44);
- таблицы `gift_categories`, `gifts`, `gift_i18n`, `memorial_gifts` (v3.45);
- индекс `idx_user_status` в `memorial_gifts` (v3.52).

Перезапуск делайте сразу после заливки: без него работает старый код, и тарифный план не сохранится.

## 5. Проверка

В PhpMyAdmin:

```sql
SHOW COLUMNS FROM memorials LIKE 'tier';                            -- 1 строка
SHOW TABLES LIKE 'gift%';                                           -- gift_categories, gift_i18n, gifts
SHOW TABLES LIKE 'memorial_gifts';                                  -- 1 строка
SHOW INDEX FROM memorial_gifts WHERE Key_name = 'idx_user_status';  -- 2 строки
SELECT lang, COUNT(*) FROM i18n_translations WHERE section = 'gifts' GROUP BY lang;  -- en 53, uk 53
```

На сайте (админку откройте с Ctrl+F5):
1. **Главная.** Карта загружается с точками. Если карта пустая, значит, не создалась колонка `tier` — см. раздел 6.
2. **Тариф.** Админка → любой погибший → «Тарифний план» → «Золото» → сохранить. На сайте его боковая панель получает золотую рамку с переливом.
3. **Раздел подарков.** Админка → «Подарунки загиблому» открывается, каталог пустой.
4. **Мемориал.** На любой странице `/card?slug=…` кнопки «Подарунки загиблому» нет (модуль по умолчанию выключен), свеча работает как раньше.
5. **Карта в админке.** «Всі записи» → «Редагувати» любого погибшего: «Місце Зірки на карті» показывает тёмную карту с меткой, а не «API KEY REQUIRED».
6. **«Опис».** Там же счётчик под «Опис» показывает «N/10000», а в длинное описание можно дописывать.
7. **Поиск на карте «Світ».** Переключить карту на «World» и найти погибшего в поиске: карта перелетает к точке гибели и приближается, вокруг звезды — золотое кольцо, свечение и расходящиеся кольца, как на карте Украины. После закрытия карточки фокус исчезает.

## 6. Только если проверка показала, что чего-то нет

Такое бывает, если у пользователя БД нет прав на ALTER или CREATE. Выполните в PhpMyAdmin только недостающее. Определения совпадают с кодом бэкенда (`init_db()` в `Paskal.py`):

```sql
USE zoryana_pamyat;

-- v3.44: колонка тарифа (только если её нет, иначе ошибка #1060)
ALTER TABLE memorials ADD COLUMN `tier` VARCHAR(10) NOT NULL DEFAULT '';

-- v3.45: таблицы подарков (безопасно и при существующих)
CREATE TABLE IF NOT EXISTS gift_categories (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  code        VARCHAR(40) NOT NULL,
  sort_order  INT NOT NULL DEFAULT 0,
  active      TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uq_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gifts (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  category_id  INT NULL,
  price_kop    INT NOT NULL DEFAULT 0,
  img_main     VARCHAR(300) NOT NULL DEFAULT '',
  gif_place    VARCHAR(300) NOT NULL DEFAULT '',
  img_final    VARCHAR(300) NOT NULL DEFAULT '',
  anim_ms      INT NOT NULL DEFAULT 0,
  active       TINYINT NOT NULL DEFAULT 1,
  sort_order   INT NOT NULL DEFAULT 0,
  place_scale  DECIMAL(4,2) NOT NULL DEFAULT 1.00,
  place_area   VARCHAR(20) NOT NULL DEFAULT 'auto',
  place_z      INT NOT NULL DEFAULT 0,
  created_at   INT NOT NULL DEFAULT 0,
  updated_at   INT NOT NULL DEFAULT 0,
  INDEX idx_active (active, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gift_i18n (
  entity     VARCHAR(10) NOT NULL,
  entity_id  INT NOT NULL,
  lang       VARCHAR(5) NOT NULL,
  name       VARCHAR(150) NOT NULL DEFAULT '',
  descr      VARCHAR(500) NOT NULL DEFAULT '',
  PRIMARY KEY (entity, entity_id, lang)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS memorial_gifts (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  memorial_id  INT NOT NULL,
  gift_id      INT NOT NULL,
  user_id      INT NULL,
  status       VARCHAR(16) NOT NULL DEFAULT 'created',
  price_kop    INT NOT NULL DEFAULT 0,
  currency     VARCHAR(3) NOT NULL DEFAULT 'UAH',
  order_id     VARCHAR(64) NOT NULL,
  payment_id   VARCHAR(64) NULL,
  slot         INT NULL,
  anim_state   VARCHAR(10) NOT NULL DEFAULT 'pending',
  img_snap     VARCHAR(300) NOT NULL DEFAULT '',
  gif_snap     VARCHAR(300) NOT NULL DEFAULT '',
  created_at   INT NOT NULL DEFAULT 0,
  paid_at      INT NULL,
  updated_at   INT NOT NULL DEFAULT 0,
  UNIQUE KEY uq_order (order_id),
  UNIQUE KEY uq_payment (payment_id),
  INDEX idx_mem_status (memorial_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- v3.52: индекс (только если его нет, иначе ошибка #1061)
ALTER TABLE memorial_gifts ADD INDEX idx_user_status (user_id, status);
```

## 7. Включение подарков — позже, когда будет готово

1. **Каталог.** «Подарунки загиблому» → «Категорії», потом «Каталог». Картинки — до 512×512 px и 300 КБ. В GIF подарок в конце стоит внизу по центру и занимает примерно треть ширины кадра. Папка `img/gifts/` создастся сама при первой загрузке.
2. **Модуль.** «Налаштування» → включить. Пока нет ключей LiqPay, посетители видят «Оплата незабаром», а класть подарки может только админ.
3. **Оплата.** По чек-листу в [MASTER_GUIDE.md](MASTER_GUIDE.md), раздел 17: ключи sandbox в `.env` → перезапуск → тестовая покупка. После неё в `logs/security.log` должна появиться запись `GIFT_PAID … src=callback`.
