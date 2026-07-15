-- ============================================================
-- i18n ключі: OAuth-редірект в /admin (v3.3)
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','admin','adm.login.no_rights','У вас немає прав адміністратора або модератора'),
('en','admin','adm.login.no_rights','You don''t have administrator or moderator rights'),
('uk','admin','adm.login.oauth_failed','Помилка входу через Google'),
('en','admin','adm.login.oauth_failed','Google sign-in failed')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
