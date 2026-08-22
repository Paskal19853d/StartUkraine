-- ============================================================
-- Ключі для нового кроку туру "Перемикач мови" (#lang-toggle)
-- Виконати на ПРОДІ через PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','tour','tour.lang.title','Мова сайту'),
('en','tour','tour.lang.title','Site language'),
('uk','tour','tour.lang.text','Тут можна перемкнути мову сайту між українською та англійською в один клік.'),
('en','tour','tour.lang.text','Switch the site language between Ukrainian and English here in one click.')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
