-- ============================================================
-- Нова функція: "Підказки сайту" — увімкнення/вимкнення онбординг-туру
-- + відео-інструкція замість туру, коли він вимкнений
-- Виконати на ПРОДІ через PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

-- 1) Нові ключі налаштувань (таблиця colors)
INSERT INTO colors (`key`, value, label) VALUES
('tour_enabled',   '1', 'Підказки (онбординг-тур) — показувати новим відвідувачам (1=так, 0=ні)'),
('tour_video_url', '',  'Посилання на відео-інструкцію (показується замість туру, якщо tour_enabled=0)')
ON DUPLICATE KEY UPDATE label = VALUES(label);

-- 2) Нові i18n ключі для модалки відео-інструкції (index.html)
INSERT INTO i18n_translations (lang, section, `key`, value) VALUES
('uk','tour','tour.video.title','Відео-інструкція'),
('en','tour','tour.video.title','Video tutorial'),
('uk','tour','tour.video.watch','Дивитись відео'),
('en','tour','tour.video.watch','Watch video')
ON DUPLICATE KEY UPDATE value = VALUES(value), section = VALUES(section);
