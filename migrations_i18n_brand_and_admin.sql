-- ============================================================
-- Бренд-назва (Zoryana Pamyat -> Memory Star для EN) + перші
-- ключі адмін-панелі (admin.html): infra, login, sidebar, topbar,
-- stats/mem/pend/users, authreg/emailcfg/mapeditor, colors..silence,
-- seo/card/version/google/density
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','brand','brand.name','Зоряна Памʼять'),
('uk','brand','brand.name_em','Зоряна'),
('uk','brand','brand.name_rest','Памʼять')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('en','brand','brand.name','Memory Star'),
('en','brand','brand.name_em','Memory'),
('en','brand','brand.name_rest','Star')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);

-- ── Виправлення застарілих EN-значень зі старою назвою бренду ──
UPDATE i18n_translations SET value='Memory Star — home' WHERE lang='en' AND `key`='logo.hint';
UPDATE i18n_translations SET value='"Memory Star" is an open memorial for fallen defenders of Ukraine. It was created with respect for the memory of every warrior.' WHERE lang='en' AND `key`='modal.rules.intro';
UPDATE i18n_translations SET value='Memory Star' WHERE lang='en' AND `key`='tour.logo.title';
