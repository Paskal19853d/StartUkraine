-- ============================================================
-- «Регулятор зірок» (v3.70): назва розділу адмінки (uk/en).
-- Без цієї міграції розділ показує вбудовані українські тексти.
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL. Повторний запуск безпечний
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','admin','nav.stars','Регулятор зірок'),
('uk','admin','adm.stars.title','Регулятор зірок'),
('en','admin','nav.stars','Star controls'),
('en','admin','adm.stars.title','Star controls')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
