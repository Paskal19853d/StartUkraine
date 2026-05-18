-- ============================================
-- Зоряна Пам'ять — Міграції БД
-- Запуск:
--   mysql -u root -p zoryana_pamyat < migrations.sql
-- ============================================

-- ── Міграція 001: Початкові індекси ──
-- Створено: 2025-05-06
-- Опис: Оптимізація запитів для 500+ користувачів

-- Індекс для фільтрації затверджених меморіалів
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_approved (approved);

-- Індекс для пошуку за прізвищем/ім'ям
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_name (last, first);

-- Індекс для пошуку з частковим покриттям
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_search (last(50), first(50), grp(50), loc(100));

-- Індекс для сортування за рейтингом + лайками
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_rating_likes (rating, likes);

-- Індекс для фільтрації за групою
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_grp (grp(50));

-- Комбінований індекс: approved + rating + likes (для /api/people)
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_approved_rating (approved, rating, likes);

-- FULLTEXT індекс для повнотекстового пошуку
ALTER TABLE memorials ADD FULLTEXT INDEX IF NOT EXISTS idx_fulltext_search (last, first, mid, grp, loc, descr);

-- Індекс для таблиці users (остання активність)
ALTER TABLE users ADD INDEX IF NOT EXISTS idx_last_seen (last_seen);

-- Індекс для логів пошуку
ALTER TABLE search_logs ADD INDEX IF NOT EXISTS idx_created_at (created_at);
ALTER TABLE search_logs ADD INDEX IF NOT EXISTS idx_query (query(50));

-- ── Міграція 002: Оптимізація таблиць ──
-- Створено: 2025-05-06
-- Опис: Аналіз та оптимізація для покращення продуктивності

ANALYZE TABLE memorials;
ANALYZE TABLE users;
ANALYZE TABLE search_logs;
ANALYZE TABLE cities;
ANALYZE TABLE colors;

-- ── Міграція 003: FK для likes_log → memorials (каскадне видалення) ──
-- Створено: 2026-05-17
-- Опис: Щоб orphan-записи не залишались після видалення меморіалу
ALTER TABLE likes_log
  ADD CONSTRAINT fk_likes_memorial
  FOREIGN KEY IF NOT EXISTS (memorial_id) REFERENCES memorials(id) ON DELETE CASCADE;

-- ── Міграція 004: Погодинна статистика ──
-- Створено: 2026-05-16
-- Опис: Таблиця для збереження погодинних відвідувань між рестартами сервера
CREATE TABLE IF NOT EXISTS hourly_stats (
    hour_ts INT PRIMARY KEY,
    views   INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Міграція 005: Партнери / Друзі ──
-- Створено: 2026-05-17
-- Опис: Блоки з лого партнерів на головній сторінці (керуються з адмінки)
CREATE TABLE IF NOT EXISTS partners (
    id         INT PRIMARY KEY AUTO_INCREMENT,
    name       VARCHAR(100) NOT NULL DEFAULT '',
    image_url  VARCHAR(500) NOT NULL DEFAULT '',
    link_url   VARCHAR(500) NOT NULL DEFAULT '',
    caption    VARCHAR(200) NOT NULL DEFAULT '',
    width      INT NOT NULL DEFAULT 120,
    opacity    DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    pos_x      INT NOT NULL DEFAULT 20,
    pos_y      INT NOT NULL DEFAULT 20,
    is_visible TINYINT NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    INDEX idx_vis (is_visible, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
