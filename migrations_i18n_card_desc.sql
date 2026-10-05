-- ============================================================
-- «Опис» у боковій панелі (v3.63): кнопка «Розгорнути / Згорнути» (uk/en).
-- Без цієї міграції кнопка показує вбудований український текст.
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL. Повторний запуск безпечний
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','card','card.desc_more','Розгорнути'),
('uk','card','card.desc_less','Згорнути'),
('en','card','card.desc_more','Show more'),
('en','card','card.desc_less','Show less')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
