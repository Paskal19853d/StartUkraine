# Підключення Google-сервісів — Зоряна Пам'ять

> Цей файл описує підключення Google OAuth (вхід через Google), Google Analytics, Google Search Console та Google Indexing API.

---

## ЗМІСТ

1. [Google OAuth — вхід через Google](#1-google-oauth--вхід-через-google)
2. [Google Analytics 4](#2-google-analytics-4)
3. [Google Search Console (верифікація сайту)](#3-google-search-console-верифікація-сайту)
4. [Google Indexing API (автоіндексація)](#4-google-indexing-api-автоіндексація)
5. [Перевірка та усунення помилок](#5-перевірка-та-усунення-помилок)

---

## 1. Google OAuth — вхід через Google

### Крок 1.1 — Створити проект у Google Cloud Console

1. Відкрити **https://console.cloud.google.com/**
2. У верхній панелі натиснути на назву проекту → **"New Project"**
3. Назва проекту: `Zoryana Pamyat` (або будь-яка)
4. Натиснути **"Create"** → дочекатися створення (~10 секунд)

### Крок 1.2 — Увімкнути Google People API

1. У меню зліва: **"APIs & Services"** → **"Library"**
2. У пошуку ввести: `Google Identity`
3. Клацнути **"Google Identity Toolkit API"** → **"Enable"**
4. Також увімкнути **"Google+ API"** або **"People API"** якщо є

> Без увімкнення API OAuth не повертатиме дані профілю.

### Крок 1.3 — Налаштувати OAuth Consent Screen

1. Перейти: **"APIs & Services"** → **"OAuth consent screen"**
2. Вибрати тип: **External** → **"Create"**
3. Заповнити обов'язкові поля:
   - **App name**: `Зоряна Пам'ять`
   - **User support email**: `treetex.g.ads@gmail.com`
   - **Developer contact email**: `treetex.g.ads@gmail.com`
   - **App logo**: завантажити favicon або логотип (не обов'язково)
   - **App domain**: `star-memory.org` або `зоряна-пам'ять.укр`
4. Натиснути **"Save and Continue"**
5. На кроці **Scopes**: натиснути **"Add or Remove Scopes"**
   - Додати: `.../auth/userinfo.email`
   - Додати: `.../auth/userinfo.profile`
   - Додати: `openid`
   - Натиснути **"Update"** → **"Save and Continue"**
6. На кроці **Test Users**: натиснути **"+ Add Users"**
   - Додати свій Gmail (поки додаток не верифікований, лише test users можуть логінитися)
7. Натиснути **"Save and Continue"** → **"Back to Dashboard"**

> **Увага**: Поки статус додатка "Testing" — тільки додані Test Users можуть авторизуватися. Щоб відкрити для всіх — треба пройти верифікацію Google (Publishing Status → "Publish App").

### Крок 1.4 — Створити OAuth 2.0 Client ID

1. Перейти: **"APIs & Services"** → **"Credentials"**
2. Натиснути **"+ Create Credentials"** → **"OAuth client ID"**
3. Тип застосунку: **Web application**
4. Назва: `Zoryana Web Client`
5. Розділ **"Authorized redirect URIs"** → **"+ Add URI"**:

   **Для локальної розробки (dev):**
   ```
   http://127.0.0.1:8000/api/auth/google/callback
   ```

   **Для продакшн (VPS):**
   ```
   https://xn----7sbbz2acglf0a4i2ag.xn--j1amh/api/auth/google/callback
   https://star-memory.org/api/auth/google/callback
   ```

6. Натиснути **"Create"**
7. З'явиться вікно з **Client ID** та **Client Secret** — скопіювати обидва!

> Формат: Client ID виглядає як `123456789-abc.apps.googleusercontent.com`, Client Secret як `GOCSPX-xxxxxxxxxxxx`

### Крок 1.5 — Заповнити .env файл

Відкрити файл `.env` у корені проекту і заповнити:

```env
# Google OAuth
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxx

# Для продакшн (VPS):
OAUTH_REDIRECT_BASE=https://xn----7sbbz2acglf0a4i2ag.xn--j1amh

# Для локальної розробки:
# OAUTH_REDIRECT_BASE=http://127.0.0.1:8000
```

> **Важливо**: `OAUTH_REDIRECT_BASE` має точно збігатися з тим що додано у Google Console (без `/` в кінці).

### Крок 1.6 — Перезапустити сервер

**На VPS:**
```bash
sudo systemctl restart zoryana
```

**Локально:**
```bash
# Зупинити uvicorn (Ctrl+C) та запустити знову
uvicorn Paskal:app --reload --port 8000
```

### Крок 1.7 — Увімкнути у адмін-панелі

1. Відкрити адмін-панель → секція **"Google"** (у лівому меню)
2. Знайти перемикач **"Дозволити вхід через Google OAuth"** → увімкнути
3. Переконатися що статус показує: `✓ OAuth налаштовано` (зелений)
4. Скопіювати показаний **Redirect URI** — він має збігатися з тим що в Google Console

---

## 2. Google Analytics 4

### Крок 2.1 — Створити ресурс GA4

1. Відкрити **https://analytics.google.com/**
2. Натиснути **"Start measuring"** або **"Admin"** → **"Create Property"**
3. Назва: `Зоряна Пам'ять`
4. Часовий пояс: `Ukraine (UTC+2)`
5. Валюта: `Ukrainian hryvnia`
6. Натиснути **"Next"** → описати бізнес → **"Create"**
7. Вибрати платформу: **Web**
8. URL сайту: `star-memory.org`
9. Назва потоку: `Зоряна Пам'ять Web`
10. Натиснути **"Create stream"**
11. Скопіювати **Measurement ID** — формат `G-XXXXXXXXXX`

### Крок 2.2 — Додати в адмін-панель

1. Адмін-панель → секція **"Google"**
2. Поле **"Google Analytics ID"** → вставити `G-XXXXXXXXXX`
3. Увімкнути перемикач **"Увімкнути Google Analytics"**
4. Натиснути **"Зберегти"**

Код GA4 автоматично вставляється на всі сторінки сайту.

---

## 3. Google Search Console (верифікація сайту)

### Крок 3.1 — Додати сайт у Search Console

1. Відкрити **https://search.google.com/search-console/**
2. Натиснути **"Add property"**
3. Вибрати **"URL prefix"** → ввести `https://star-memory.org`
4. Натиснути **"Continue"**
5. Вибрати метод верифікації: **"HTML tag"**
6. Скопіювати значення `content` з мета-тегу:
   ```html
   <meta name="google-site-verification" content="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" />
   ```
   Потрібно лише значення з `content="..."` (без лапок)

### Крок 3.2 — Додати в адмін-панель

1. Адмін-панель → секція **"Google"**
2. Поле **"Google Site Verification"** → вставити скопійоване значення
3. Натиснути **"Зберегти"**
4. Повернутися в Search Console → натиснути **"Verify"**

> Після верифікації Search Console почне індексувати сайт і показувати статистику через 1-3 дні.

---

## 4. Google Indexing API (автоіндексація)

Дозволяє автоматично повідомляти Google про нові меморіали для швидкої індексації.

### Крок 4.1 — Створити Service Account

1. Відкрити **https://console.cloud.google.com/**
2. Перейти: **"APIs & Services"** → **"Library"**
3. Знайти **"Web Search Indexing API"** → **"Enable"**
4. Перейти: **"APIs & Services"** → **"Credentials"**
5. Натиснути **"+ Create Credentials"** → **"Service account"**
6. Назва: `zoryana-indexing`
7. Натиснути **"Create and Continue"** → **"Done"**
8. Клацнути на створений service account → вкладка **"Keys"**
9. **"Add Key"** → **"Create new key"** → тип **JSON** → **"Create"**
10. JSON файл буде завантажено автоматично — зберегти як `google-service-account.json`

### Крок 4.2 — Завантажити JSON на сервер

Покласти файл `google-service-account.json` у корінь проекту:
```
/var/www/treete07/data/www/xn----7sbbz2acglf0a4i2ag.xn--j1amh/google-service-account.json
```

### Крок 4.3 — Додати email service account у Search Console

1. Відкрити Google Search Console → Settings → Users and permissions
2. Натиснути **"Add user"**
3. Email: `zoryana-indexing@your-project.iam.gserviceaccount.com` (з JSON файлу, поле `client_email`)
4. Permission: **Owner**
5. Натиснути **"Add"**

### Крок 4.4 — Вказати файл у .env

```env
GOOGLE_INDEXING_KEY_FILE=google-service-account.json
SITE_BASE_URL=https://xn----7sbbz2acglf0a4i2ag.xn--j1amh
```

### Крок 4.5 — Перезапустити сервер та перевірити

1. Перезапустити сервер
2. Адмін-панель → секція **"SEO"** → **"Google Indexing API"**
3. Статус має показувати: `✓ Indexing API налаштовано`
4. Натиснути **"Ping Google"** для тесту відправки URL

---

## 5. Перевірка та усунення помилок

### Перевірка OAuth

**API статус:**
```
GET /api/admin/google/status
```
Повертає:
```json
{
  "oauth_configured": true,       // CLIENT_ID і CLIENT_SECRET заповнені
  "oauth_enabled": true,          // вмикач в адмінці увімкнений
  "redirect_uri": "https://xn----7sbbz2acglf0a4i2ag.xn--j1amh/api/auth/google/callback"
}
```

**Тест кнопки**: Відкрити сайт → клацнути "Увійти через Google" → має відкритися вікно Google.

### Помилки та рішення

| Помилка | Причина | Рішення |
|---------|---------|---------|
| `oauth_error=google_not_configured` | Порожні `GOOGLE_CLIENT_ID` або `GOOGLE_CLIENT_SECRET` у .env | Заповнити .env та перезапустити сервер |
| `oauth_error=google_disabled` | Вимкнений перемикач в адмінці | Адмін → Google → увімкнути OAuth |
| `redirect_uri_mismatch` (Google помилка) | URL callback у Google Console не збігається з `OAUTH_REDIRECT_BASE` | Додати точний URI у Google Console |
| `access_denied` | Користувач не в Test Users (додаток у статусі Testing) | Додати email у Test Users або верифікувати додаток |
| `403 Forbidden` при Indexing API | Service account не має прав Owner у Search Console | Додати service account email у Search Console як Owner |

### Логи OAuth

```bash
# На VPS — перевірити журнал
journalctl -u zoryana -f | grep -i oauth

# Або перевірити logs/security.log
tail -f /var/www/treete07/data/www/xn----7sbbz2acglf0a4i2ag.xn--j1amh/logs/security.log
```

### Швидка перевірка .env

Правильне заповнення `.env` для продакшн:
```env
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxx
OAUTH_REDIRECT_BASE=https://xn----7sbbz2acglf0a4i2ag.xn--j1amh
GOOGLE_INDEXING_KEY_FILE=google-service-account.json
SITE_BASE_URL=https://xn----7sbbz2acglf0a4i2ag.xn--j1amh
```

---

*Оновлено: 2026-05-25. Проект: Зоряна Пам'ять v2.1*
