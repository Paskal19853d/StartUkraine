-- ============================================================
-- Новий модуль: «Відео-попап» (реклама/оголошення)
-- Виконати на ПРОДІ через PhpMyAdmin: база zoryana_pamyat -> SQL
-- (якщо бачите помилку "База даних не вибрана" — спочатку відкрийте
-- базу zoryana_pamyat зліва в списку баз, потім вкладку SQL)
-- ============================================================

USE `zoryana_pamyat`;

-- 1) Таблиця для сервер-перевіреного "показано сьогодні" (cookie zp_vid)
CREATE TABLE IF NOT EXISTS ad_video_views (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    visitor_id VARCHAR(64) NOT NULL,
    seen_at    INT NOT NULL,
    INDEX idx_visitor_seen (visitor_id, seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Нові ключі налаштувань (таблиця colors)
INSERT INTO colors (`key`, value, label) VALUES
('ad_video_enabled',     '0', 'Відео-попап — увімкнено (1=так, 0=ні)'),
('ad_video_url',         '',  'Відео-попап: посилання YouTube'),
('ad_video_title',       '',  'Відео-попап: назва відео (показується над плеєром)'),
('ad_video_preview_url', '',  'Відео-попап: URL превью-картинки (завантажується вручну)'),
('ad_video_channel_url', '',  'Відео-попап: посилання на YouTube-канал'),
('ad_video_channel_btn', 'Ми на YouTube', 'Відео-попап: текст кнопки каналу'),
('ad_video_freq_days',   '1', 'Відео-попап: частота показу одному відвідувачу (днів)')
ON DUPLICATE KEY UPDATE label = VALUES(label);
