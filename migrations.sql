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
