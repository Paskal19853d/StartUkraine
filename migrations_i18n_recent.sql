-- ============================================================
-- «Нові надходження» (v3.58): тексти блоку на сайті й розділу адмінки (uk/en).
-- Без цієї міграції блок і розділ показують вбудовані українські тексти.
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL. Повторний запуск безпечний
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','ui','recent.title','Нові надходження'),
('uk','ui','recent.added','додано'),
('en','ui','recent.title','New additions'),
('en','ui','recent.added','added'),
('uk','admin','nav.recent','Нові надходження'),
('uk','admin','adm.recent.title','Нові надходження'),
('en','admin','nav.recent','New additions'),
('en','admin','adm.recent.title','New additions')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
