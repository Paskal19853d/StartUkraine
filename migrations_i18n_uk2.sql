-- ============================================================
-- i18n_translations — додаткові uk ключі (Фаза 4)
-- Виконати в PhpMyAdmin: база zoryana_pamyat → SQL
-- ============================================================

INSERT INTO i18n_translations (lang, section, `key`, value) VALUES

-- ── topbar / stats ──────────────────────────────────────────
('uk','stats','people',        ' людей'),
('uk','stats','stars',         ' зірок'),

-- ── smoke ───────────────────────────────────────────────────
('uk','smoke','label',         'Дим'),
('uk','smoke','on',            ' увімкнено'),
('uk','smoke','off',           ' вимкнено'),

-- ── count / info ────────────────────────────────────────────
('uk','count','label',         'у памʼяті'),
('uk','info','title',          'Інформація'),
('uk','info','rules',          'Правила сайту'),
('uk','info','terms',          'Правила використання'),
('uk','info','faq',            'Питання — відповідь'),

-- ── card (додаткові) ────────────────────────────────────────
('uk','card','locations',      'Місця'),
('uk','card','detail',         'Детальніше'),
('uk','card','like_btn',       'Зірка памʼяті'),

-- ── form (додаткові) ────────────────────────────────────────
('uk','form','subtitle',       'Записи проходять модерацію. Вказуйте лише достовірні дані.')

ON DUPLICATE KEY UPDATE value = VALUES(value);

-- ── en версії тих самих ключів ─────────────────────────────
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES

('en','stats','people',        ' people'),
('en','stats','stars',         ' stars'),
('en','smoke','label',         'Smoke'),
('en','smoke','on',            ' enabled'),
('en','smoke','off',           ' disabled'),
('en','count','label',         'in memory'),
('en','info','title',          'Information'),
('en','info','rules',          'Site rules'),
('en','info','terms',          'Terms of use'),
('en','info','faq',            'FAQ'),
('en','card','locations',      'Locations'),
('en','card','detail',         'Details'),
('en','card','like_btn',       'Star of memory'),
('en','form','subtitle',       'Records go through moderation. Please provide only verified data.')

ON DUPLICATE KEY UPDATE value = VALUES(value);
