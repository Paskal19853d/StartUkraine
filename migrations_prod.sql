-- ═══════════════════════════════════════════════════════════════
-- Міграція для продакшн БД zoryana_pamyat
-- Виконати через PhpMyAdmin або mysql CLI
-- Всі команди безпечні: IF NOT EXISTS / ігнорують дублікати
-- ═══════════════════════════════════════════════════════════════

USE zoryana_pamyat;

-- ── 1. Таблиця users: розширені поля профілю ──────────────────

ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name  VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name   VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS middle_name VARCHAR(100) NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname    VARCHAR(100) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone       VARCHAR(20)  NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS role        VARCHAR(20)  NOT NULL DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen   INT          DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_until   INT          DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notes       TEXT;

-- Оновити роль адміністраторів (якщо is_admin=1, але role ще 'user')
UPDATE users SET role='admin' WHERE is_admin=1 AND role='user';

-- Унікальний індекс на nickname (пропустити якщо вже є)
ALTER TABLE users ADD UNIQUE INDEX idx_nickname (nickname);

-- ── 2. Таблиця likes_log: прив'язка до авторизованого юзера ──

ALTER TABLE likes_log ADD COLUMN IF NOT EXISTS user_id INT NULL DEFAULT NULL;
ALTER TABLE likes_log ADD INDEX IF NOT EXISTS idx_user_likes (user_id, ts);

-- ── 3. Таблиця memorials: прив'язка до user_id автора ─────────

ALTER TABLE memorials ADD COLUMN IF NOT EXISTS added_by_uid INT NULL DEFAULT NULL;
ALTER TABLE memorials ADD INDEX IF NOT EXISTS idx_added_by_uid (added_by_uid, approved);

-- ── 4. Таблиця memorials: SEO slug ────────────────────────────

ALTER TABLE memorials ADD COLUMN IF NOT EXISTS slug VARCHAR(220) DEFAULT NULL;
ALTER TABLE memorials ADD UNIQUE INDEX IF NOT EXISTS idx_slug (slug);

-- ── 5. Таблиця memorials: географічні координати (карта світу) ──

ALTER TABLE memorials ADD COLUMN IF NOT EXISTS world_lat FLOAT DEFAULT NULL;
ALTER TABLE memorials ADD COLUMN IF NOT EXISTS world_lng FLOAT DEFAULT NULL;

-- ── 6. Перевірка: показати колонки після міграції ─────────────

SHOW COLUMNS FROM users;
SHOW COLUMNS FROM likes_log;
SHOW COLUMNS FROM memorials WHERE Field IN ('added_by_uid', 'slug', 'world_lat', 'world_lng');
