-- ============================================================
-- Універсалізація «Зоряна Пам'ять»: категорії людей (військовий/
-- цивільний/поза війною) + режим додавання (free/request через кол-центр)
-- Виконати на ПРОДІ через PhpMyAdmin: база zoryana_pamyat -> SQL
-- (якщо бачите помилку "База даних не вибрана" — спочатку відкрийте
-- базу zoryana_pamyat зліва в списку баз, потім вкладку SQL)
-- ============================================================

USE `zoryana_pamyat`;

-- 1) Нові колонки memorials
--    Якщо якась колонка вже існує (повторний запуск) — MariaDB 10.3+/MySQL 8+
--    підтримують ADD COLUMN IF NOT EXISTS. Якщо ваша версія старіша і видає
--    синтаксичну помилку — приберіть "IF NOT EXISTS" з рядка, що впав,
--    і запустіть решту окремо.
ALTER TABLE memorials
  ADD COLUMN IF NOT EXISTS category       VARCHAR(20) NOT NULL DEFAULT 'military' AFTER circ,
  ADD COLUMN IF NOT EXISTS death_reason   VARCHAR(40) NOT NULL DEFAULT ''         AFTER category,
  ADD COLUMN IF NOT EXISTS war_related    TINYINT     NOT NULL DEFAULT 1          AFTER death_reason,
  ADD COLUMN IF NOT EXISTS citizenship    VARCHAR(30) NOT NULL DEFAULT ''         AFTER war_related,
  ADD COLUMN IF NOT EXISTS nationality    VARCHAR(30) NOT NULL DEFAULT ''         AFTER citizenship,
  ADD COLUMN IF NOT EXISTS created_by_uid INT         NULL                       AFTER added_by,
  ADD COLUMN IF NOT EXISTS show_creator   TINYINT     NOT NULL DEFAULT 0         AFTER created_by_uid;

-- 2) Явно проставляємо старим записам category+war_related (ідемпотентно,
--    DEFAULT вище вже покриває нові рядки, це підтверджує намір і покриває
--    рядки що існували ДО ALTER, якщо DEFAULT з якоїсь причини не застосувався)
UPDATE memorials SET category='military', war_related=1
  WHERE category='' OR category IS NULL;

-- 3) Індекс для фільтра "Категорія" в адмінці
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_category (category);

-- 4) Нові ключі налаштувань (таблиця colors) — режим додавання людей
INSERT INTO colors (`key`, value, label) VALUES
('add_person_mode',   'free', 'Режим додавання: free/request'),
('callcenter_phone',  '',     'Телефон кол-центру'),
('callcenter_msg_uk', 'Наразі додавання доступне за заявкою. Зателефонуйте нам.', 'Повідомл. кол-центру (укр)'),
('callcenter_msg_en', 'Adding is currently available by request. Please call us.', 'Повідомл. кол-центру (англ)')
ON DUPLICATE KEY UPDATE label = VALUES(label);
