-- ============================================================
-- Видалення інтеграції "Дія" (Diia eID) — авторизація/реєстрація
-- через Дія повністю прибрана з коду. Ці i18n-ключі більше не
-- використовуються — видаляємо з БД, щоб не лишати мертвих даних.
-- Виконати на ПРОДІ через PhpMyAdmin: база zoryana_pamyat -> SQL
-- ============================================================

USE `zoryana_pamyat`;

DELETE FROM i18n_translations WHERE `key` IN (
  'auth.continue_diia',
  'diia.unavailable',
  'errors.oauth_diia_cancelled',
  'errors.oauth_diia_no_email',
  'errors.oauth_diia_not_configured',
  'errors.oauth_diia_token',
  'errors.oauth_diia_userinfo',
  'howto.s1.diia_note'
);

-- Оновлюємо текст скріншота-підпису на how-to-add.html (howto.s1.shot2_cap) —
-- більше не згадує кнопку "Дія", лише Google
UPDATE i18n_translations SET value = 'Вікно входу. Натисніть «Продовжити з Google».'
  WHERE `key` = 'howto.s1.shot2_cap' AND lang = 'uk';
UPDATE i18n_translations SET value = 'Login window. Click "Continue with Google".'
  WHERE `key` = 'howto.s1.shot2_cap' AND lang = 'en';
