-- ============================================================
-- Ключ для посилання "Тарифи" (новий блок /pricing/) в #site-rules / #bb-popup
-- Виконати в PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','ui','pricing_nav','Тарифи'),
('en','ui','pricing_nav','Pricing')
ON DUPLICATE KEY UPDATE value = VALUES(value);
