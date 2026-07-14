-- ============================================================
-- Виправлення i18n_translations: колізії ключів + відсутні рядки
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL (одним запуском)
--
-- ПРИЧИНА: унікальний індекс uq_lang_key(lang,key) не враховує section.
-- Кілька окремих рядків (map.title, chat.title, admin.title, info.title
-- / smoke.label, count.label) мали однаковий bare `key` ("title"/"label"),
-- тому ON DUPLICATE KEY UPDATE в migrations_i18n_uk2.sql затер їх одне
-- одним. Це виправлення дає кожному рядку власний унікальний key.
-- ============================================================

-- ── 1. Перейменувати існуючі конфліктні рядки на унікальні ключі
--       і повернути їм правильні значення ──────────────────────

-- map.title (зараз зіпсовано на "Інформація" / рядка en взагалі нема)
UPDATE i18n_translations SET `key`='map_title', value='Інтерактивна карта'
  WHERE lang='uk' AND section='map' AND `key`='title';
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('en','map','map_title','Interactive map')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- chat.title
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('uk','chat','chat_title','Чат'),
  ('en','chat','chat_title','Chat')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- admin.title (адмін-панель)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('uk','admin','admin_title','Адмін-панель'),
  ('en','admin','admin_title','Admin panel')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- info.title (зараз en зіпсовано на "Admin panel")
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('uk','info','info_title','Інформація'),
  ('en','info','info_title','Information')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- smoke.label (зараз зіпсовано на "у памʼяті" / "in memory")
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('uk','smoke','smoke_label','Дим'),
  ('en','smoke','smoke_label','Smoke')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- count.label (правильне значення "у памʼяті"/"in memory" — перенести на новий ключ)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
  ('uk','count','count_label','у памʼяті'),
  ('en','count','count_label','in memory')
  ON DUPLICATE KEY UPDATE value=VALUES(value), section=VALUES(section);

-- Видалити старі "осиротілі" bare title/label рядки (більше нічим не використовуються)
-- (uk/title вже перейменовано на map_title кроком вище, тому лишається лише en/title)
DELETE FROM i18n_translations WHERE `key`='title' AND section IN ('smoke','info') AND lang='en';
DELETE FROM i18n_translations WHERE `key`='label' AND section IN ('smoke','count');

-- ── 2. Додати решту ключів з migrations_i18n_uk2.sql, яких зовсім нема на prod ─

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','stats','people',   ' людей'),
('uk','stats','stars',    ' зірок'),
('uk','smoke','on',       ' увімкнено'),
('uk','smoke','off',      ' вимкнено'),
('uk','info','rules',     'Правила сайту'),
('uk','info','terms',     'Правила використання'),
('uk','info','faq',       'Питання — відповідь'),
('uk','card','locations', 'Місця'),
('uk','card','detail',    'Детальніше'),
('uk','card','like_btn',  'Зірка памʼяті'),
('uk','form','subtitle',  'Записи проходять модерацію. Вказуйте лише достовірні дані.')
ON DUPLICATE KEY UPDATE value = VALUES(value);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','stats','people',   ' people'),
('en','stats','stars',    ' stars'),
('en','smoke','on',       ' enabled'),
('en','smoke','off',      ' disabled'),
('en','info','rules',     'Site rules'),
('en','info','terms',     'Terms of use'),
('en','info','faq',       'FAQ'),
('en','card','locations', 'Locations'),
('en','card','detail',    'Details'),
('en','card','like_btn',  'Star of memory'),
('en','form','subtitle',  'Records go through moderation. Please provide only verified data.')
ON DUPLICATE KEY UPDATE value = VALUES(value);
