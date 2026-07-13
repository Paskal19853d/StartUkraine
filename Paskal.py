"""
Зоряна Пам'ять — FastAPI Backend (MySQL edition)
Запуск: python -m uvicorn Paskal:app --reload --port 8000
БД:     MySQL / MariaDB (налаштування у .env)
"""
import os, time, asyncio, hashlib, threading, re, base64, secrets, string, html as _html, json, logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.request, urllib.error, urllib.parse
import bcrypt
from typing import Optional, List

import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB

try:
    import redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False

try:
    import psutil as _psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
import csv, io
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from seo_utils import make_slug, gen_seo_title, gen_seo_description, gen_seo_keywords, calc_seo_score

load_dotenv()

# ── Security Logging ─────────────────────────────────────
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
_sec_logger = logging.getLogger("security")
_sec_logger.setLevel(logging.INFO)
_fh = logging.FileHandler(os.path.join(log_dir, "security.log"), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_sec_logger.addHandler(_fh)

def sec_log(event: str, ip: str, detail: str = ""):
    _sec_logger.info(f"[{event}] IP={ip} {detail}")

# ── OAuth Config (з .env) ────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
DIIA_CLIENT_ID       = os.getenv("DIIA_CLIENT_ID", "")
DIIA_CLIENT_SECRET   = os.getenv("DIIA_CLIENT_SECRET", "")
OAUTH_REDIRECT_BASE  = os.getenv("OAUTH_REDIRECT_BASE", "http://127.0.0.1:8000")
DIIA_AUTH_URL        = os.getenv("DIIA_AUTH_URL",      "https://id.diia.gov.ua/oauth/authorize")
DIIA_TOKEN_URL       = os.getenv("DIIA_TOKEN_URL",     "https://id.diia.gov.ua/oauth/token")
DIIA_USERINFO_URL    = os.getenv("DIIA_USERINFO_URL",  "https://id.diia.gov.ua/oauth/userinfo")

# ── MySQL Config (з .env) ────────────────────────────────
_DB_CFG = {
    "host":     os.getenv("DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit":  False,
}
_DB_NAME = os.getenv("DB_NAME", "zoryana_pamyat")

# ── Connection Pool ──────────────────────────────────────
# Ініціалізується після init_db() щоб БД точно існувала
_POOL: PooledDB | None = None

def _init_pool():
    global _POOL
    _POOL = PooledDB(
        creator=pymysql,
        maxconnections=50,   # макс. одночасних з'єднань (для 500+ users)
        mincached=5,         # мін. з'єднань у режимі очікування
        maxcached=20,        # макс. з'єднань у режимі очікування
        blocking=True,       # чекати вільне з'єднання (не кидати помилку)
        host=_DB_CFG["host"],
        port=_DB_CFG["port"],
        user=_DB_CFG["user"],
        password=_DB_CFG["password"],
        database=_DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def get_db():
    """Повертає з'єднання з пулу."""
    _h = int(time.time() // 3600) * 3600
    _db_queries_hourly[_h] = _db_queries_hourly.get(_h, 0) + 1
    if len(_db_queries_hourly) > 15:
        _cutoff = _h - 13 * 3600
        for _k in [k for k in list(_db_queries_hourly) if k < _cutoff]:
            del _db_queries_hourly[_k]
    if _POOL is None:
        # fallback до прямого з'єднання якщо пул ще не готовий (init_db)
        cfg = {**_DB_CFG, "database": _DB_NAME}
        return pymysql.connect(**cfg)
    return _POOL.connection()


# ── Redis Cache ───────────────────────────────────────────
_redis: redis.Redis | None = None

def _init_redis():
    global _redis
    if not _HAS_REDIS:
        return
    rurl = os.getenv("REDIS_URL")
    if rurl:
        try:
            _redis = redis.from_url(rurl, decode_responses=True, socket_connect_timeout=2)
            _redis.ping()
            print("[INFO] Redis connected", flush=True)
        except Exception as e:
            print(f"[WARN] Redis unavailable ({e}), caching disabled", flush=True)
            _redis = None
    else:
        # Пробуємо localhost за замовчуванням
        try:
            _redis = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
            _redis.ping()
            print("[INFO] Redis connected (localhost)", flush=True)
        except Exception:
            _redis = None

def cache_get(key: str):
    if not _redis:
        return None
    try:
        return _redis.get(key)
    except Exception:
        return None

def cache_set(key: str, value, ttl: int = 60):
    if not _redis:
        return
    try:
        _redis.setex(key, ttl, value)
    except Exception:
        pass

def cache_delete(key: str):
    if not _redis:
        return
    try:
        _redis.delete(key)
    except Exception:
        pass

def cache_flush_all():
    """Invalidate all cached data after bulk changes."""
    cache_delete("stats")
    cache_delete("colors")
    cache_delete("labels")
    cache_delete("cities")
    cache_delete("map_points")
    for k in range(1, 100):
        cache_delete(f"people:p{k}:l50")
        cache_delete(f"people:p{k}:l100")

def cache_flush_memorials():
    """Invalidate memorial-related caches (stats, labels, people pages)."""
    cache_delete("stats")
    cache_delete("labels")
    cache_delete("map_points")
    for k in range(1, 100):
        cache_delete(f"people:p{k}:l50")
        cache_delete(f"people:p{k}:l100")


def hash_pass(p: str) -> str:
    """Hash password with bcrypt (new standard)."""
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=12)).decode()

def _is_sha256_hash(h: str) -> bool:
    return len(h) == 64 and all(c in '0123456789abcdef' for c in h)

def verify_pass(plain: str, stored: str) -> bool:
    """Verify password against bcrypt or legacy SHA256 hash."""
    if _is_sha256_hash(stored):
        return hashlib.sha256(plain.encode()).hexdigest() == stored
    try:
        return bcrypt.checkpw(plain.encode(), stored.encode())
    except Exception:
        return False


# ── Ініціалізація БД ─────────────────────────────────────
def init_db():
    # Спочатку підключаємось без БД — щоб створити її, якщо не існує
    raw = pymysql.connect(
        host=_DB_CFG["host"], port=_DB_CFG["port"],
        user=_DB_CFG["user"], password=_DB_CFG["password"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    with raw.cursor() as c:
        c.execute(
            f"CREATE DATABASE IF NOT EXISTS `{_DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    raw.commit()
    raw.close()

    db = get_db()
    with db.cursor() as c:
        # ── memorials ──────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS memorials (
                id       INT PRIMARY KEY AUTO_INCREMENT,
                last     VARCHAR(100) NOT NULL,
                first    VARCHAR(100) NOT NULL,
                mid      VARCHAR(100) DEFAULT '',
                birth    VARCHAR(20)  DEFAULT NULL,
                death    VARCHAR(20)  DEFAULT NULL,
                loc      VARCHAR(300) DEFAULT '',
                bury     VARCHAR(300) DEFAULT '',
                circ     VARCHAR(500) DEFAULT '',
                descr    TEXT         DEFAULT NULL,
                photo    VARCHAR(500) DEFAULT '',
                color    VARCHAR(20)  DEFAULT '#4fc3f7',
                pos_x    DOUBLE       DEFAULT 0.5,
                pos_y    DOUBLE       DEFAULT 0.5,
                likes    INT          DEFAULT 0,
                rating   DOUBLE       DEFAULT 0,
                approved TINYINT      DEFAULT 0,
                grp      VARCHAR(100) DEFAULT '',
                added_by VARCHAR(100) DEFAULT '',
                INDEX idx_approved (approved),
                INDEX idx_name     (last, first),
                INDEX idx_search   (last(50), first(50), grp(50), loc(100)),
                INDEX idx_rating_likes (rating DESC, likes DESC),
                INDEX idx_grp (grp(50)),
                INDEX idx_approved_rating (approved, rating DESC, likes DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # ── likes_log ─────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS likes_log (
                id          INT PRIMARY KEY AUTO_INCREMENT,
                memorial_id INT,
                fingerprint VARCHAR(128),
                ts          INT,
                INDEX idx_likes (memorial_id, fingerprint, ts)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── users ─────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id        INT PRIMARY KEY AUTO_INCREMENT,
                name      VARCHAR(100) NOT NULL,
                email     VARCHAR(120) NOT NULL UNIQUE,
                password  VARCHAR(255) NOT NULL,
                is_admin  TINYINT DEFAULT 0,
                is_banned TINYINT DEFAULT 0,
                last_seen INT     DEFAULT 0,
                created   INT     DEFAULT (UNIX_TIMESTAMP())
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # ── colors ────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS colors (
                `key`   VARCHAR(50)  PRIMARY KEY,
                value   TEXT         NOT NULL,
                label   VARCHAR(200) DEFAULT ''
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Миграция: расширяем value если ещё VARCHAR(100)
        c.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'colors'
              AND COLUMN_NAME  = 'value'
        """)
        row = c.fetchone()
        if row:
            dtype = list(row.values())[0] if isinstance(row, dict) else row[0]
            if dtype.lower() != 'text':
                c.execute("ALTER TABLE colors MODIFY COLUMN value TEXT NOT NULL")

        # ── map_labels ────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS map_labels (
                id    INT PRIMARY KEY AUTO_INCREMENT,
                name  VARCHAR(100) NOT NULL,
                x     DOUBLE NOT NULL,
                y     DOUBLE NOT NULL,
                type  VARCHAR(20)  DEFAULT 'oblast',
                color VARCHAR(50)  DEFAULT 'rgba(160,195,220,0.45)',
                size  INT          DEFAULT 145
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── search_logs ───────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                query         VARCHAR(200) NOT NULL,
                results_count INT          DEFAULT 0,
                created_at    INT          DEFAULT (UNIX_TIMESTAMP())
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── cities ────────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS cities (
                id    INT PRIMARY KEY AUTO_INCREMENT,
                name  VARCHAR(100) NOT NULL,
                pos_x DOUBLE NOT NULL DEFAULT 0,
                pos_y DOUBLE NOT NULL DEFAULT 0,
                tier  INT NOT NULL DEFAULT 0,
                color VARCHAR(20) NOT NULL DEFAULT '#a0d7ff',
                INDEX idx_shown (pos_x)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Migration: add color column to existing installations
        try:
            c.execute("ALTER TABLE cities ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT '#a0d7ff'")
        except Exception:
            pass  # column already exists
        # ── partners ──────────────────────────────────────────
        c.execute("""
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Migration: add ban_until and notes to users
        try:
            c.execute("ALTER TABLE users ADD COLUMN ban_until INT NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE users ADD COLUMN notes TEXT")
        except Exception:
            pass
        # Migration: add video_url to memorials
        try:
            c.execute("ALTER TABLE memorials ADD COLUMN video_url VARCHAR(500) NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD COLUMN `rank` VARCHAR(100) NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD COLUMN `position` VARCHAR(100) NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD COLUMN `unit` VARCHAR(200) NOT NULL DEFAULT ''")
        except Exception:
            pass
        # Migration: add role to users
        try:
            c.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
        except Exception:
            pass
        try:
            c.execute("UPDATE users SET role='admin' WHERE is_admin=1 AND role='user'")
        except Exception:
            pass
        # Migration: FULLTEXT index for fast search
        try:
            c.execute("ALTER TABLE memorials ADD FULLTEXT INDEX idx_fulltext_search (last, first, mid, grp, loc, descr)")
        except Exception:
            pass  # index already exists or engine doesn't support it
        # Migration: performance indexes
        try:
            c.execute("ALTER TABLE memorials ADD INDEX idx_rating_likes (rating DESC, likes DESC)")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD INDEX idx_grp (grp(50))")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD INDEX idx_approved_rating (approved, rating DESC, likes DESC)")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE users ADD INDEX idx_last_seen (last_seen)")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE search_logs ADD INDEX idx_created_at (created_at)")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE search_logs ADD INDEX idx_query (query(50))")
        except Exception:
            pass
        # Migration: extended user profile fields
        for _col, _sql in [
            ("first_name",  "ALTER TABLE users ADD COLUMN first_name  VARCHAR(100) NOT NULL DEFAULT ''"),
            ("last_name",   "ALTER TABLE users ADD COLUMN last_name   VARCHAR(100) NOT NULL DEFAULT ''"),
            ("middle_name", "ALTER TABLE users ADD COLUMN middle_name VARCHAR(100) NOT NULL DEFAULT ''"),
            ("nickname",    "ALTER TABLE users ADD COLUMN nickname     VARCHAR(100) DEFAULT NULL"),
            ("phone",       "ALTER TABLE users ADD COLUMN phone        VARCHAR(20)  NOT NULL DEFAULT ''"),
        ]:
            try:
                c.execute(_sql)
            except Exception:
                pass
        try:
            c.execute("ALTER TABLE users ADD UNIQUE INDEX idx_nickname (nickname)")
        except Exception:
            pass

        # ── memorial_awards ───────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS memorial_awards (
                id           INT PRIMARY KEY AUTO_INCREMENT,
                memorial_id  INT NOT NULL,
                name         VARCHAR(200) NOT NULL,
                img_file     VARCHAR(300) DEFAULT '',
                award_date   DATE         DEFAULT NULL,
                descr        TEXT         DEFAULT NULL,
                sort_order   INT          NOT NULL DEFAULT 0,
                FOREIGN KEY (memorial_id) REFERENCES memorials(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── bot_visits ────────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS bot_visits (
                id         INT PRIMARY KEY AUTO_INCREMENT,
                bot_name   VARCHAR(60)  NOT NULL,
                path       VARCHAR(500) NOT NULL,
                user_agent VARCHAR(300) DEFAULT '',
                created_at INT          NOT NULL,
                INDEX idx_bv_bot_ts  (bot_name, created_at),
                INDEX idx_bv_ts      (created_at),
                INDEX idx_bv_path    (path(100))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── daily_stats ───────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date  DATE PRIMARY KEY,
                views INT  NOT NULL DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── hourly_stats ──────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS hourly_stats (
                hour_ts     INT PRIMARY KEY,
                views       INT NOT NULL DEFAULT 0,
                human_views INT NOT NULL DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # міграція: додати human_views якщо таблиця вже існує без неї
        try:
            c.execute("ALTER TABLE hourly_stats ADD COLUMN human_views INT NOT NULL DEFAULT 0")
        except Exception:
            pass

        # ── minute_silence_settings ───────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS minute_silence_settings (
                `key`   VARCHAR(50) PRIMARY KEY,
                `value` TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        for _sk, _sv in [
            ("enabled",            "0"),
            ("time_hhmm",          "10:00"),
            ("duration_sec",       "60"),
            ("overlay_text",       "Хвилина мовчання"),
            ("overlay_subtext",    "Схиляємо голови перед пам'яттю Захисників України"),
            ("overlay_height",     "15"),
            ("overlay_bg_color",   "#000000"),
            ("overlay_text_color", "#ffffff"),
            ("clock_enabled",      "1"),
            ("clock_x",            "10"),
            ("clock_y",            "10"),
            ("clock_font",         "monospace"),
            ("clock_font_size",    "20"),
            ("clock_opacity",      "1"),
            ("clock_color",        "#ffffff"),
            ("clock_bg",           "rgba(0,0,0,0.5)"),
            ("audio_file",         ""),
            ("audio_volume",       "0.7"),
            ("force_active",       "0"),
        ]:
            c.execute(
                "INSERT IGNORE INTO minute_silence_settings (`key`,`value`) VALUES (%s,%s)",
                (_sk, _sv)
            )
        # Migration: normalize old CSS font-family values → simple keys
        _FONT_MIGRATE = {
            "'LetsGoDigital', monospace": "letsgodigital",
            "'Cristal', sans-serif":      "cristal",
            "'POCKC', sans-serif":        "pockc",
            "'Courier New', monospace":   "courier",
            "'Unbounded', sans-serif":    "unbounded",
            "'Geologica', sans-serif":    "geologica",
            "'Arial', sans-serif":        "arial",
            "'Georgia', serif":           "georgia",
            "'Times New Roman', serif":   "times",
        }
        c.execute("SELECT `value` FROM minute_silence_settings WHERE `key`='clock_font'")
        _frow = c.fetchone()
        if _frow:
            _fval = (_frow.get("value") if isinstance(_frow, dict) else _frow[0]) or ""
            if _fval in _FONT_MIGRATE:
                c.execute(
                    "UPDATE minute_silence_settings SET `value`=%s WHERE `key`='clock_font'",
                    (_FONT_MIGRATE[_fval],)
                )

    # ── Admin user ──────────────────────────────────────
    with db.cursor() as c:
        # Якщо будь-який адмін вже існує (напр. створений інсталятором) — не дублюємо
        c.execute("SELECT id FROM users WHERE is_admin=1 OR role='admin' LIMIT 1")
        if not c.fetchone():
            _init_pass = os.getenv("ADMIN_INIT_PASS") or (
                "".join(secrets.choice(string.ascii_letters + string.digits + "!@#$%") for _ in range(16))
            )
            c.execute(
                "INSERT INTO users (name,email,password,is_admin,role) VALUES (%s,%s,%s,1,'admin')",
                ("Admin", "admin@admin.com", hash_pass(_init_pass))
            )
            print(f"[INIT] Admin created: admin@admin.com / {_init_pass}", flush=True)
        # SHA256 → bcrypt migration happens lazily at login time (see _upgrade_to_bcrypt)

    # ── Default colors ──────────────────────────────────
    defaults = [
        ("bg",              "#03070e",              "Фон сторінки"),
        ("surface",         "#070d1a",              "Поверхня карток"),
        ("text_primary",    "#d0dce8",              "Основний текст"),
        ("text_secondary",  "#8a9cb0",              "Другорядний текст"),
        ("accent",          "#00c8ff",              "Акцент (синій)"),
        ("yellow",          "#d4a800",              "Жовтий (логотип)"),
        ("yellow2",         "#f0c030",              "Жовтий яскравий"),
        ("neon_blue",       "#00ccff",              "Неон синій (межа країни)"),
        ("neon_yellow",     "#d4a800",              "Неон жовтий (межа областей)"),
        ("oblast_fill",     "#0d2240",              "Заливка областей"),
        ("oblast_stroke",   "#1e4a7a",              "Межі областей"),
        ("thread_color",    "rgba(0,200,255,1)",    "Нитки між дублікатами"),
        ("map_bg",          "#03070e",              "Фон карти"),
        ("bar_bg",          "rgba(3,7,14,.96)",     "Фон шапки"),
        ("logo_star",       "#f0c030",              "Зірка логотипу"),
        ("logo_text",       "#f0c030",              "Текст логотипу"),
        ("logo_accent",     "#00c8ff",              "Акцент логотипу"),
        ("btn_add_bg",      "#0e2860",              "Кнопка Додати (фон)"),
        ("btn_add_text",    "#a8e0f8",              "Кнопка Додати (текст)"),
        ("card_bg",         "rgba(4,9,18,.98)",     "Фон картки"),
        ("label_opacity",   "0.45",                 "Прозорість підписів областей"),
        ("glow_color",      "#ffd700",              "Колір свічення меж областей"),
        ("glow_spread",     "28",                   "Розсіювання меж областей (px, 6–120)"),
        ("glow_outer_color","#ffd700",              "Колір зовнішнього свічення країни"),
        ("glow_outer_spread","55",                  "Розсіювання зовнішнього свічення (px, 10–200)"),
        ("zoom_min",              "0.4",      "Мінімальний зум карти"),
        ("zoom_max",              "12",       "Максимальний зум карти"),
        ("city_border",           "rgba(40,110,180,.55)", "Колір меж районів при збільшенні"),
        ("city_border_zoom",      "2.5",      "Зум для появи меж районів"),
        ("smoke_density",         "0.995",    "Дим — затухання густини (0.8–1.0)"),
        ("smoke_velocity",        "0.98",     "Дим — затухання швидкості (0.8–1.0)"),
        ("smoke_splat_radius",    "0.22",     "Дим — радіус хмари (0.1–1.0)"),
        ("smoke_splat_force",     "14000",    "Дим — сила (1000–15000)"),
        ("smoke_curl",            "35",       "Дим — завихрення (0–50)"),
        ("smoke_opacity",         "0.85",     "Дим — прозорість (0.1–1.0)"),
        ("smoke_color_from",      "#0057B7",  "Дим — колір від"),
        ("smoke_color_to",        "#00BFFF",  "Дим — колір до"),
        ("use_cookies",           "1",        "Зберігати налаштування користувача в куках (1=так, 0=ні)"),
        ("map_photo_url",         "",         "Фото на карті — URL зображення (порожньо = вимкнено)"),
        ("map_photo_opacity",     "0.35",     "Фото на карті — прозорість (0.05–0.5)"),
        ("map_photo_blend",       "normal",   "Фото на карті — режим змішування (normal / screen / overlay / soft-light / luminosity)"),
        ("map_photo_feather",     "55",       "Фото на карті — розмитість країв % (20–80)"),
        ("map_photo_scale",       "100",      "Фото на карті — масштаб відображення % (10–100)"),
        ("app_version",           "3.0.3","Версія додатку — відображається на всіх сторінках"),
        ("admin_theme",           "dark",     "Тема адмін-панелі (dark / light)"),
        ("admin_logo_url",        "",         "Логотип адмінки — URL для темної теми (порожньо = без логотипу)"),
        ("admin_logo_url_light",  "",         "Логотип адмінки — URL для світлої теми (порожньо = як темна)"),
        ("admin_logo_height",     "60",       "Логотип адмінки — висота px (30–140)"),
        ("admin_logo_radius",     "8",        "Логотип адмінки — заокруглення px (0–70)"),
        ("sea_enabled",           "1",        "Море — показувати на карті (1=так, 0=ні)"),
        ("sea_wave_color",        "#a0d7ff",  "Море — колір хвиль (hex)"),
        ("sea_wave_count",        "20",       "Море — кількість хвиль (5–40)"),
        ("sea_wave_intensity",    "42",       "Море — інтенсивність (10–100)"),
        ("sea_shore_impact",      "50",       "Море — удар об сушу (0–100)"),
        ("sea_blur",              "0",        "Море — розмитість px (0–8)"),
        ("sea_wave_dir",          "45",       "Море — напрямок хвиль (градуси 0–360)"),
        ("sea_wave_speed",        "5",        "Море — швидкість хвиль (0–10)"),
        ("sea_glow_on",           "1",        "Море — свічення (1=увімк, 0=вимк)"),
        ("sea_glow_color",        "#60b8ff",  "Море — колір свічення (hex)"),
        ("sea_glow_spread",       "30",       "Море — розмах свічення px"),
        ("sea_svg_tx",            "0",        "Море SVG — зміщення X"),
        ("sea_svg_ty",            "0",        "Море SVG — зміщення Y"),
        ("sea_svg_scale",         "1",        "Море SVG — масштаб"),
        ("social_order",           "facebook,twitter,instagram,youtube,telegram,tiktok,linkedin,viber", "Соцмережі — порядок відображення"),
        ("social_facebook",       "1",        "Соцмережі — Facebook (1=показати, 0=сховати)"),
        ("social_facebook_url",   "",         "Соцмережі — Facebook URL"),
        ("social_twitter",        "1",        "Соцмережі — Twitter/X (1=показати, 0=сховати)"),
        ("social_twitter_url",    "",         "Соцмережі — Twitter/X URL"),
        ("social_instagram",      "1",        "Соцмережі — Instagram (1=показати, 0=сховати)"),
        ("social_instagram_url",  "",         "Соцмережі — Instagram URL"),
        ("social_youtube",        "1",        "Соцмережі — YouTube (1=показати, 0=сховати)"),
        ("social_youtube_url",    "",         "Соцмережі — YouTube URL"),
        ("social_telegram",       "1",        "Соцмережі — Telegram (1=показати, 0=сховати)"),
        ("social_telegram_url",   "",         "Соцмережі — Telegram URL"),
        ("social_tiktok",         "1",        "Соцмережі — TikTok (1=показати, 0=сховати)"),
        ("social_tiktok_url",     "",         "Соцмережі — TikTok URL"),
        ("social_linkedin",       "1",        "Соцмережі — LinkedIn (1=показати, 0=сховати)"),
        ("social_linkedin_url",   "",         "Соцмережі — LinkedIn URL"),
        ("social_viber",          "1",        "Соцмережі — Viber (1=показати, 0=сховати)"),
        ("social_viber_url",      "",         "Соцмережі — Viber URL"),
        ("smtp_host",                "",           "SMTP — хост (напр. smtp.gmail.com)"),
        ("smtp_port",                "587",        "SMTP — порт (587=STARTTLS, 465=SSL, 25=без шифрування)"),
        ("smtp_user",                "",           "SMTP — логін/email відправника"),
        ("smtp_pass",                "",           "SMTP — пароль або App Password"),
        ("smtp_from",                "",           "SMTP — ім'я відправника (напр. Зоряна Пам'ять <noreply@mail.com>)"),
        ("smtp_secure",              "starttls",   "SMTP — тип шифрування (starttls/ssl/none)"),
        ("smtp_enabled",             "1",          "SMTP — увімкнути відправку листів (1=так, 0=вимкнути)"),
        ("reg_enabled",              "1",          "Реєстрація — дозволити нову реєстрацію (1=так, 0=ні)"),
        ("reg_allow_google",         "1",          "Реєстрація — дозволити вхід через Google OAuth (1=так, 0=ні)"),
        ("reg_field_mid",            "required",   "Реєстрація — поле По батькові (required/optional/hidden)"),
        ("reg_field_phone",          "optional",   "Реєстрація — поле Телефон (required/optional/hidden)"),
        ("reg_require_phone",        "0",          "Реєстрація — обов'язковий телефон [застаріле, використовуй reg_field_phone]"),
        ("reg_require_email_verify", "1",          "Реєстрація — підтвердження email кодом (1=так, 0=без підтвердження)"),
        ("reg_require_phone_verify", "0",          "Реєстрація — підтвердження телефону SMS (1=так, 0=ні) [потребує SMS API]"),
        ("reg_min_pass_len",         "10",         "Реєстрація — мінімальна довжина пароля (8–20)"),
        ("reg_welcome_msg",          "Вітаємо на Зоряна Пам'ять!", "Реєстрація — повідомлення після успішної реєстрації"),
        # ── Керування доступом за пристроєм ──────────────────────────────────
        ("device_desktop_enabled", "1", "Доступ — ПК/ноутбук (1=так, 0=ні)"),
        ("device_tablet_enabled",  "1", "Доступ — Планшет (1=так, 0=ні)"),
        ("device_mobile_enabled",  "1", "Доступ — Смартфон (1=так, 0=ні)"),
        ("device_block_msg",       "Версія сайту для вашого пристрою тимчасово недоступна.", "Повідомлення при блокуванні пристрою"),
        ("show_coffee",            "1", "Кнопка «Кава адміну» на головній (1=показати, 0=сховати)"),
        ("dev_mode",               "0", "Режим розробки — показувати попередження на сайті (1=так, 0=ні)"),
        ("dev_icon",               "🚧", "Режим розробки — іконка/emoji над заголовком"),
        ("dev_title",              "Режим розробки", "Режим розробки — заголовок модального вікна"),
        ("dev_text1",              "Сайт працює в тестовому режимі.\nУсі імена, прізвища, дані та записи є вигаданими і використовуються виключно для перевірки функціоналу проєкту.", "Режим розробки — текст першої колонки"),
        ("dev_text2",              "💻 Сайт оптимізовано для ПК та планшетів. Мобільна версія наразі в розробці — рекомендуємо використовувати ПК або планшет.\nБудь-яка схожість із реальними особами є випадковою.", "Режим розробки — текст другої колонки"),
        ("dev_btn_text",           "Зрозуміло", "Режим розробки — текст кнопки закриття"),
        ("dev_btn_color",          "#f5a623", "Режим розробки — колір кнопки (hex)"),
        ("worldmap_enabled",       "1", "Карта світу активна (1=так, 0=ні)"),
        ("worldmap_default",       "0", "Карта за замовчуванням (0=Україна, 1=Світ)"),
        ("worldmap_tile_url",      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", "URL тайлів карти світу"),
        # ── Мікро-чат ────────────────────────────────────────────────────────
        ("chat_enabled",       "1",    "Мікро-чат активний (1=так, 0=ні)"),
        ("chat_history_count", "50",   "Кількість повідомлень в чаті"),
        ("chat_poll_interval", "4000", "Інтервал оновлення чату (мс)"),
        # ── Картка меморіалу (card.html) ─────────────────────────────────────
        ("card_accent",        "#f0b54a",                       "Картка: колір акценту"),
        ("card_bg",            "#050507",                       "Картка: колір фону"),
        ("card_show_bio",      "1",                             "Картка: показ секції Про захисника (1/0)"),
        ("card_show_timeline", "1",                             "Картка: показ хроніки (1/0)"),
        ("card_show_video",    "1",                             "Картка: показ відео (1/0)"),
        ("card_show_awards",   "1",                             "Картка: показ нагород (1/0)"),
        ("card_show_ribbon",   "1",                             "Картка: показ траурної стрічки (1/0)"),
        ("card_show_candle",   "1",                             "Картка: показ секції свічки (1/0)"),
        ("card_no_photo_bg",     "/img/bgcard.webp",              "Картка: URL фото-заглушки"),
        ("card_footer_text",     "Вічна памʼять Героям України",  "Картка: текст футера"),
        ("card_likes_refresh",       "60",  "Картка: інтервал оновлення лічильника вшанувань (секунди; 0 = вимкнено)"),
        ("google_site_verification", "",   "Google Search Console: код верифікації сайту (html meta-tag content)"),
        ("google_analytics_id",      "",   "Google Analytics 4: Measurement ID (G-XXXXXXXXXX)"),
        ("google_analytics_enabled", "0",  "Google Analytics 4: вмикач (1=так, 0=ні)"),
        ("density_config", '{"weights":{"likes":0.45,"rating":0.35,"views":0.15,"activity":0.05},"zoomLevels":[{"zoom":0.4,"minScore":200},{"zoom":1.0,"minScore":50},{"zoom":3.0,"minScore":10},{"zoom":8.0,"minScore":0}],"decay":{"enabled":false,"rate":0.95,"hours":24}}', "Алгоритм щільності зірок на карті: ваги, zoom-рівні, decay"),
        # ── Спадщина пам'яті ─────────────────────────────────────────────────
        ("legacy_enabled",  "0",   "Спадщина — модуль увімкнено (1=так, 0=ні)"),
        ("legacy_refund",   "0",   "Спадщина — дозволити повернення коштів (1=так, 0=ні)"),
        ("legacy_price",    "0",   "Спадщина — ціна підключення"),
        ("legacy_currency", "USD", "Спадщина — валюта (USD/EUR/UAH)"),
        # ── Вартість проекту ──────────────────────────────────────────────────
        ("proj_cost_server_usd",   "0",   "Вартість проекту — сервер, $/міс"),
        ("proj_cost_domains_usd",  "0",   "Вартість проекту — домени, $/рік"),
        ("proj_cost_ai_usd",       "0",   "Вартість проекту — Claude Code, $/міс"),
        ("proj_cost_other_usd",    "0",   "Вартість проекту — інші витрати, $/міс"),
        ("proj_cost_months",       "5",   "Вартість проекту — місяців розробки"),
        ("proj_usd_rate",          "0",   "Вартість проекту — курс USD/UAH (НБУ, авто)"),
        ("proj_usd_rate_updated",  "0",   "Вартість проекту — timestamp оновлення курсу"),
        ("proj_cost_per_user_usd", "1.0", "Вартість проекту — CPM ціна одного користувача, $"),
    ]
    with db.cursor() as c:
        for key, val, label in defaults:
            c.execute(
                "INSERT IGNORE INTO colors (`key`,value,label) VALUES (%s,%s,%s)",
                (key, val, label)
            )
        # Гарантуємо наявність proj_cost_per_user_usd (доданий пізніше — INSERT IGNORE міг пропустити)
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES ('proj_cost_per_user_usd','1.0','Вартість проекту — CPM ціна одного користувача, $')"
            " ON DUPLICATE KEY UPDATE label=VALUES(label)"
        )
        # Мігруємо порожні social-ключі (старий формат URL) → '1' (показати)
        for _sk in ('social_facebook','social_twitter','social_instagram','social_youtube'):
            c.execute("UPDATE colors SET value='1' WHERE `key`=%s AND value=''", (_sk,))
        # Мігруємо density_config: старі "conceptual zoom" (5,7,9,11,13) → реальний масштаб (0.4,1,3,8)
        c.execute("SELECT value FROM colors WHERE `key`='density_config'")
        _dc_row = c.fetchone()
        if _dc_row:
            try:
                _dc = json.loads(_dc_row["value"] or "{}")
                _lvs = _dc.get("zoomLevels", [])
                if _lvs and all(lv.get("zoom", 0) >= 4 for lv in _lvs):
                    _dc["zoomLevels"] = [
                        {"zoom": 0.4, "minScore": 200},
                        {"zoom": 1.0, "minScore": 50},
                        {"zoom": 3.0, "minScore": 10},
                        {"zoom": 8.0, "minScore": 0},
                    ]
                    c.execute("UPDATE colors SET value=%s WHERE `key`='density_config'",
                              (json.dumps(_dc, ensure_ascii=False),))
            except Exception:
                pass
        # Синхронізуємо кольори областей із новою схемою (як в адмінці)
        c.execute("UPDATE colors SET value=%s WHERE `key`='oblast_fill'  AND value IN ('#03070e','#040f1e')", ("#0d2240",))
        c.execute("UPDATE colors SET value=%s WHERE `key`='oblast_stroke' AND value IN ('rgba(90,110,130,.3)','rgba(90,110,130,0.3)')", ("#1e4a7a",))
        # Видаляємо застарілі sea-ключі (еліпси прибрано в favor SVG-режиму)
        c.execute("""DELETE FROM colors WHERE `key` IN (
            'sea_size_x','sea_size_y',
            'sea_black_cx','sea_black_cy','sea_black_rx','sea_black_ry',
            'sea_azov_cx','sea_azov_cy','sea_azov_rx','sea_azov_ry'
        )""")

    # ── Default map labels ───────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM map_labels")
        if c.fetchone()["cnt"] == 0:
            labels = [
                ("Закарпатська",      700,  4400),
                ("Львівська",        1500,  3700),
                ("Волинська",        1950,  2100),
                ("Івано-Франківська",2650,  5200),
                ("Чернівецька",      2900,  5650),
                ("Тернопільська",    3430,  3150),
                ("Рівненська",       3440,  1600),
                ("Хмельницька",      4030,  3100),
                ("Житомирська",      4800,  2000),
                ("Вінницька",        4790,  4600),
                ("Одеська",          5560,  6200),
                ("Київська",         6200,  2200),
                ("Кіровоградська",   6300,  5000),
                ("Черкаська",        7180,  3900),
                ("Полтавська",       7960,  3200),
                ("Чернігівська",     6800,  1400),
                ("Миколаївська",     7220,  6100),
                ("Херсонська",       8810,  6600),
                ("Дніпропетровська", 8510,  5200),
                ("Сумська",          8920,   900),
                ("Запорізька",       9770,  5700),
                ("Харківська",      10280,  3500),
                ("Донецька",        11400,  6000),
                ("Луганська",       12100,  4100),
                ("АР Крим",          9700,  8100),
            ]
            c.executemany(
                "INSERT INTO map_labels (name,x,y,type) VALUES (%s,%s,%s,'oblast')",
                labels
            )

    # ── Ensure АР Крим label exists (для існуючих БД) ────
    with db.cursor() as c:
        c.execute("SELECT id FROM map_labels WHERE name=%s", ("АР Крим",))
        if not c.fetchone():
            c.execute(
                "INSERT INTO map_labels (name,x,y,type) VALUES (%s,%s,%s,'oblast')",
                ("АР Крим", 9700, 8100)
            )

    # ── Default cities ───────────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM cities")
        if c.fetchone()["cnt"] == 0:
            # pos_x, pos_y (0-1 normalized), tier (3=столиця,2=велике,1=обл.центр,0=місто)
            # Координати калібровані по SVG viewBox 0 0 14000 9500
            _C = {
                'Авдіївка':(0.826,0.574,0),'Алчевськ':(0.915,0.526,0),
                'Амвросіївка':(0.872,0.643,0),'Антрацит':(0.913,0.542,0),
                'Апостолове':(0.662,0.617,0),'Балаклія':(0.759,0.377,0),
                'Балта':(0.409,0.757,0),'Бар':(0.307,0.402,0),
                'Бахмут':(0.848,0.511,0),'Бердичів':(0.357,0.341,0),
                'Бердянськ':(0.777,0.753,0),'Берислав':(0.616,0.668,0),
                'Білгород-Дністровський':(0.451,0.810,0),
                'Білопілля':(0.684,0.141,0),'Богодухів':(0.716,0.288,0),
                'Богуслав':(0.529,0.355,0),'Болград':(0.358,0.898,0),
                'Бориспіль':(0.484,0.283,0),'Боярка':(0.449,0.304,0),
                'Бровари':(0.487,0.251,0),'Буча':(0.446,0.256,0),
                'Бучач':(0.270,0.486,0),'Біла Церква':(0.459,0.326,0),
                'Вараш':(0.209,0.130,0),'Василівка':(0.718,0.624,0),
                'Васильків':(0.449,0.305,0),'Вилкове':(0.424,0.951,0),
                'Вінниця':(0.361,0.428,1),'Вишгород':(0.455,0.228,0),
                'Вовчанськ':(0.766,0.291,0),'Вознесенськ':(0.503,0.644,0),
                'Волноваха':(0.818,0.670,0),'Вугледар':(0.805,0.634,0),
                'Гадяч':(0.648,0.280,0),'Гайсин':(0.399,0.485,0),
                'Генічеськ':(0.693,0.830,0),'Глухів':(0.642,0.108,0),
                'Горлівка':(0.854,0.524,0),"Горішні Плавні":(0.629,0.460,0),
                'Дебальцеве':(0.851,0.531,0),'Дергачі':(0.757,0.295,0),
                'Дніпро':(0.690,0.529,2),'Дніпрорудне':(0.694,0.572,0),
                'Добропілля':(0.790,0.553,0),'Довжанськ':(0.915,0.539,0),
                'Долинська':(0.574,0.505,0),'Донецьк':(0.829,0.590,1),
                'Дрогобич':(0.111,0.412,0),'Дружківка':(0.805,0.499,0),
                'Дубно':(0.202,0.273,0),'Єнакієве':(0.851,0.547,0),
                'Енергодар':(0.687,0.656,0),'Житомир':(0.370,0.292,1),
                'Жмеринка':(0.331,0.455,0),'Жовті Води':(0.667,0.532,0),
                'Запоріжжя':(0.697,0.611,1),'Звягель':(0.304,0.250,0),
                "Знам'янка":(0.559,0.542,0),'Золотоноша':(0.544,0.409,0),
                'Ізмаїл':(0.370,0.934,0),'Ізюм':(0.825,0.432,0),
                'Ірпінь':(0.446,0.261,0),'Ічня':(0.562,0.205,0),
                'Іллічівськ (Чорноморськ)':(0.468,0.800,0),
                'Івано-Франківськ':(0.172,0.469,1),
                'Кагарлик':(0.479,0.309,0),'Калуш':(0.127,0.488,0),
                "Кам'янець-Подільський":(0.260,0.489,0),
                "Кам'янка":(0.547,0.441,0),
                "Кам'янка-Дніпровська":(0.693,0.636,0),
                "Кам'янське":(0.681,0.493,0),
                'Канів':(0.511,0.431,0),'Каховка':(0.616,0.701,0),
                'Керч':(0.904,0.893,0),'Київ':(0.463,0.267,3),
                'Кілія':(0.392,0.925,0),'Ковель':(0.145,0.167,0),
                'Козятин':(0.369,0.363,0),'Коломия':(0.164,0.525,0),
                'Конотоп':(0.598,0.164,0),'Коростень':(0.360,0.202,0),
                'Коростишів':(0.386,0.269,0),'Корсунь-Шевченківський':(0.500,0.432,0),
                'Костянтинівка':(0.818,0.523,0),'Краматорськ':(0.811,0.495,0),
                'Кременчук':(0.609,0.449,0),'Кремінна':(0.876,0.404,0),
                'Кривий Ріг':(0.640,0.600,1),'Кропивницький':(0.551,0.523,1),
                'Кролевець':(0.615,0.112,0),"Куп'янськ":(0.832,0.365,0),
                'Ладижин':(0.390,0.498,0),'Лебедин':(0.674,0.252,0),
                'Лиман':(0.831,0.452,0),'Лисичанськ':(0.888,0.471,0),
                'Лозова':(0.747,0.472,0),'Лубни':(0.594,0.326,0),
                'Луганськ':(0.905,0.515,1),'Лутугине':(0.931,0.481,0),
                'Луцьк':(0.203,0.229,1),'Львів':(0.137,0.347,2),
                'Люботин':(0.754,0.294,0),'Макіївка':(0.851,0.590,0),
                'Малин':(0.394,0.202,0),'Марганець':(0.674,0.592,0),
                'Маріуполь':(0.816,0.709,1),"Мар'їнка":(0.819,0.597,0),
                'Мелітополь':(0.707,0.742,0),'Мена':(0.521,0.128,0),
                'Мерефа':(0.759,0.332,0),'Миколаїв':(0.575,0.742,1),
                'Миргород':(0.628,0.324,0),'Мирноград':(0.791,0.570,0),
                'Миронівка':(0.484,0.336,0),'Могилів-Подільський':(0.314,0.475,0),
                'Мукачево':(0.072,0.532,0),'Надвірна':(0.139,0.543,0),
                'Немирів':(0.369,0.463,0),'Ніжин':(0.544,0.187,0),
                'Нікополь':(0.658,0.647,0),'Нова Каховка':(0.616,0.754,0),
                'Нова Одеса':(0.529,0.681,0),'Новгород-Сіверський':(0.598,0.092,0),
                'Нова Каховка':(0.616,0.754,0),'Нововолинськ':(0.115,0.210,0),
                'Обухів':(0.466,0.316,0),'Овруч':(0.368,0.139,0),
                'Одеса':(0.474,0.790,2),'Олевськ':(0.306,0.150,0),
                'Олександрія':(0.600,0.501,0),'Олешки':(0.580,0.769,0),
                'Оріхів':(0.745,0.583,0),'Остер':(0.488,0.183,0),
                'Острог':(0.244,0.256,0),'Охтирка':(0.654,0.286,0),
                'Очаків':(0.516,0.768,0),'Павлоград':(0.749,0.467,0),
                'Первомайськ':(0.479,0.587,0),'Переяслав':(0.514,0.307,0),
                'Пирятин':(0.568,0.296,0),'Покровськ':(0.786,0.554,0),
                'Пологи':(0.755,0.624,0),'Полтава':(0.665,0.380,1),
                'Прилуки':(0.561,0.250,0),'Рахів':(0.111,0.562,0),
                'Рені':(0.341,0.934,0),'Рівне':(0.249,0.245,1),
                'Ровеньки':(0.932,0.536,0),'Ромни':(0.620,0.228,0),
                'Рубіжне':(0.884,0.459,0),'Самбір':(0.064,0.402,0),
                'Сарни':(0.249,0.137,0),'Сватове':(0.914,0.364,0),
                'Світловодськ':(0.603,0.448,0),'Святогірськ':(0.819,0.406,0),
                'Севастополь':(0.622,0.929,0),'Селидове':(0.794,0.585,0),
                'Сєвєродонецьк':(0.890,0.467,0),'Сімферополь':(0.765,0.884,0),
                'Скадовськ':(0.590,0.751,0),'Сквира':(0.418,0.323,0),
                "Слов'янськ":(0.812,0.477,0),'Сміла':(0.534,0.482,0),
                'Снігурівка':(0.555,0.685,0),'Сновськ':(0.536,0.093,0),
                'Соледар':(0.859,0.499,0),'Старобільськ':(0.914,0.380,0),
                'Стрий':(0.099,0.432,0),'Суми':(0.678,0.207,1),
                'Тальне':(0.469,0.474,0),'Тернівка':(0.681,0.507,0),
                'Тернопіль':(0.217,0.384,1),'Токмак':(0.741,0.736,0),
                'Торецьк':(0.836,0.513,0),'Тростянець':(0.702,0.263,0),
                'Трускавець':(0.081,0.426,0),'Тульчин':(0.370,0.475,0),
                'Тячів':(0.062,0.510,0),'Ужгород':(0.051,0.508,1),
                'Умань':(0.456,0.480,0),'Фастів':(0.428,0.316,0),
                'Феодосія':(0.836,0.935,0),'Харків':(0.750,0.328,2),
                'Харцизьк':(0.859,0.597,0),'Херсон':(0.569,0.768,1),
                'Хмельницький':(0.286,0.403,1),'Хмільник':(0.322,0.384,0),
                'Хорол':(0.643,0.412,0),'Хотин':(0.243,0.558,0),
                'Христинівка':(0.429,0.433,0),'Хрустальний':(0.915,0.503,0),
                'Хуст':(0.070,0.510,0),'Часів Яр':(0.862,0.485,0),
                'Черкаси':(0.541,0.400,1),'Чернівці':(0.234,0.552,1),
                'Чернігів':(0.503,0.129,1),'Чигирин':(0.535,0.446,0),
                'Чоп':(0.019,0.519,0),'Чорнобиль':(0.470,0.176,0),
                'Чорноморськ':(0.468,0.800,0),'Чортків':(0.205,0.455,0),
                'Чугуїв':(0.777,0.332,0),'Шостка':(0.607,0.164,0),
                'Шпола':(0.535,0.460,0),'Щастя':(0.931,0.445,0),
                'Яворів':(0.092,0.358,0),'Яготин':(0.505,0.263,0),
                'Ялта':(0.732,0.941,0),'Ямпіль':(0.319,0.518,0),
                'Яремче':(0.138,0.543,0),'Ясинувата':(0.841,0.562,0),
            }
            _NAMES = [
                'Авдіївка','Алмазна','Алупка','Алушта','Алчевськ',
                'Амвросіївка','Ананьїв','Андрушівка','Антрацит','Апостолове',
                'Армянськ','Арциз','Багачеве','Балаклія','Балта','Бар',
                'Баранівка','Барвінкове','Батурин','Бахмач','Бахмут',
                'Бахчисарай','Баштанка','Белз','Бердичів','Бердянськ',
                'Берегове','Бережани','Березань','Березівка','Березне',
                'Берестечко','Берестин','Берислав','Бершадь','Бібрка',
                'Біла Церква','Білгород-Дністровський','Білицьке','Білогірськ',
                'Білозерське','Білопілля','Біляївка','Благовіщенське',
                'Бобринець','Бобровиця','Богодухів','Богуслав','Боково-Хрустальне',
                'Болград','Болехів','Борзна','Борислав','Бориспіль','Борщів',
                'Боярка','Бровари','Броди','Брянка','Бунге','Буринь',
                'Бурштин','Буськ','Буча','Бучач','Валки','Вараш','Василівка',
                'Васильків','Вашківці','Великі Мости','Верхівцеве',
                'Верхньодніпровськ','Вижниця','Вилкове','Винники','Виноградів',
                'Вишгород','Вишневе','Вільногірськ','Вільнянськ','Вінниця',
                'Вовчанськ','Вознесенівка','Вознесенськ','Волноваха','Володимир',
                'Волочиськ','Ворожба','Вуглегірськ','Вугледар','Гадяч',
                'Гайворон','Гайсин','Галич','Генічеськ','Герца','Гірник',
                'Гірське','Глиняни','Глобине','Глухів','Гнівань','Гола Пристань',
                'Голубівка','Горішні Плавні','Горлівка','Городенка','Городище',
                'Городня','Городок','Городок','Горохів','Гребінка','Гуляйполе',
                'Дебальцеве','Деражня','Дергачі','Джанкой','Дніпро',
                'Дніпрорудне','Добромиль','Добропілля','Довжанськ','Докучаєвськ',
                'Долина','Долинська','Донецьк','Дрогобич','Дружківка','Дубляни',
                'Дубно','Дубровиця','Дунаївці','Енергодар','Євпаторія',
                'Єнакієве','Жашків','Жданівка','Жидачів','Житомир','Жмеринка',
                'Жовква','Жовті Води','Заводське','Залізне','Заліщики',
                'Запоріжжя','Заставна','Збараж','Зборів','Звенигородка',
                'Звягель','Здолбунів','Зеленодольськ',"Зимогір'я",'Зіньків',
                'Златопіль','Зміїв',"Знам'янка",'Золоте','Золотоноша',
                'Золочів','Зоринськ','Зугрес','Івано-Франківськ','Ізмаїл',
                'Ізюм','Ізяслав','Іллінці','Іловайськ','Інкерман','Ірміно',
                'Ірпінь','Іршава','Ічня','Кагарлик','Кадіївка','Калинівка',
                'Калуш','Кальміуське','Камінь-Каширський',
                "Кам'янець-Подільський","Кам'янка","Кам'янка-Бузька",
                "Кам'янка-Дніпровська","Кам'янське",'Канів','Карлівка',
                'Каховка','Керч','Київ','Кипуче','Ківерці','Кілія','Кіцмань',
                'Кобеляки','Ковель','Кодима','Козятин','Коломия','Комарно',
                'Конотоп','Копичинці','Корець','Коростень','Коростишів',
                'Корсунь-Шевченківський','Корюківка','Косів','Костопіль',
                'Костянтинівка','Краматорськ','Красилів','Красногорівка',
                'Кременець','Кременчук','Кремінна','Кривий Ріг','Кролевець',
                'Кропивницький',"Куп'янськ",'Курахове','Ладижин','Ланівці',
                'Лебедин','Лиман','Липовець','Лисичанськ','Лозова','Лохвиця',
                'Лубни','Луганськ','Лутугине','Луцьк','Львів','Любомль',
                'Люботин','Макіївка','Мала Виска','Малин','Марганець',
                'Маріуполь',"Мар'їнка",'Мелітополь','Мена','Мерефа',
                'Миколаїв','Миколаїв','Миколаївка','Миргород','Мирноград',
                'Миронівка','Міусинськ','Могилів-Подільський','Молочанськ',
                'Монастириська','Монастирище','Моршин','Моспине','Мостиська',
                'Мукачево','Надвірна','Немирів','Нетішин','Ніжин','Нікополь',
                'Нова Каховка','Нова Одеса','Новгород-Сіверський','Новий Буг',
                'Новий Калинів','Новий Розділ','Новоазовськ','Нововолинськ',
                'Новогродівка','Новодністровськ','Новодружеськ','Новомиргород',
                'Новоселиця','Новоукраїнка','Новояворівськ','Носівка','Обухів',
                'Овруч','Одеса','Олевськ','Олександрівськ','Олександрія',
                'Олешки','Олика','Оріхів','Остер','Острог','Отаманівка',
                'Охтирка','Очаків','Павлоград','Первомайськ','Перевальськ',
                'Перемишляни','Перечин','Перещепине','Переяслав',
                'Петрово-Красносілля','Пирятин','Південне','Південне',
                'Південноукраїнськ','Підгайці','Підгороднє','Погребище',
                'Подільськ','Покров','Покровськ','Пологи','Полонне','Полтава',
                'Помічна','Попасна','Почаїв','Привілля','Прилуки','Приморськ',
                "Прип'ять",'Пустомити','Путивль',"П'ятихатки",'Рава-Руська',
                'Радехів','Радивилів','Радомишль','Рахів','Рені','Решетилівка',
                'Ржищів','Рівне','Ровеньки','Рогатин','Родинське','Рожище',
                'Роздільна','Ромни','Рубіжне','Рудки','Саки','Самар','Самбір',
                'Сарни','Свалява','Сватове','Світловодськ','Світлодарськ',
                'Святогірськ','Севастополь','Селидове','Семенівка',
                'Середина-Буда','Синельникове','Сіверськ','Сєвєродонецьк',
                'Сімферополь','Скадовськ','Скалат','Сквира','Сколе','Славута',
                'Славутич','Слобожанське',"Слов'янськ",'Сміла','Снігурівка',
                'Сніжне','Сновськ','Снятин','Сокаль','Сокиряни','Сокологірськ',
                'Соледар','Сорокине','Соснівка','Старий Крим','Старий Самбір',
                'Старобільськ','Старокостянтинів','Стебник','Сторожинець',
                'Стрий','Судак','Судова Вишня','Суми','Суходільськ','Таврійськ',
                'Тальне','Тараща','Татарбунари','Теплодар','Теребовля',
                'Тернівка','Тернопіль','Тетіїв','Тисмениця','Тлумач','Токмак',
                'Торецьк','Тростянець','Трускавець','Тульчин','Турка','Тячів',
                'Угнів','Ужгород','Узин','Українка','Українськ','Умань',
                'Устилуг','Фастів','Феодосія','Харків','Харцизьк','Херсон',
                'Хирів','Хмельницький','Хмільник','Ходорів','Хорол',
                'Хоростків','Хотин','Хрестівка','Христинівка','Хрустальний',
                'Хуст','Хутір-Михайлівський','Часів Яр','Черкаси','Чернівці',
                'Чернігів','Чигирин','Чистякове','Чоп','Чорнобиль',
                'Чорноморськ','Чортків','Чугуїв','Чуднів','Шаргород',
                'Шахтарськ','Шахтарське','Шепетівка','Шептицький','Шостка',
                'Шпола','Шумськ','Щастя','Щолкіне','Яворів','Яготин','Ялта',
                'Ямпіль','Яни Капу','Яремче','Ясинувата',
            ]
            rows = [(n, *_C.get(n, (0.0, 0.0, 0))) for n in _NAMES]
            c.executemany(
                "INSERT INTO cities (name,pos_x,pos_y,tier) VALUES (%s,%s,%s,%s)",
                rows
            )
    db.commit()

    # ── Seed memorials ───────────────────────────────────
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials")
        if c.fetchone()["cnt"] == 0:
            seed = [
                ("Шевченко","Олег","Миколайович","1985-03-14","2022-03-01",
                 "Херсон","Херсон, Центральний цвинтар","Ракетний удар",
                 "Майор ЗСУ, захисник Херсона. Нагороджений орденом посмертно.",
                 "#4fc3f7",0.630,0.720,142,5.2,1,"Херсон-1","Марія Шевченко"),
                ("Іваненко","Сергій","Петрович","1990-07-22","2022-04-15",
                 "Маріуполь, Азовсталь","Маріуполь","Прямий контакт",
                 "Захисник Маріуполя, боєць полку Азов. 82 дні оборони.",
                 "#c8b060",0.847,0.730,389,8.1,1,"Маріуполь-1","Наталія Іваненко"),
                ("Іваненко","Сергій","Петрович","1990-07-22","2022-04-15",
                 "Маріуполь","Маріуполь","Прямий контакт",
                 "Боєць 36-ї бригади. Захисник Маріуполя.",
                 "#ffd54f",0.851,0.736,210,6.4,1,"Маріуполь-1","Максим Сидоренко"),
                ("Коваль","Андрій","Олексійович","1978-11-05","2022-08-20",
                 "Харків","Харків, Лісове кладовище","Артилерія",
                 "Підполковник ЗСУ, 25 років служби.",
                 "#a5d6a7",0.782,0.400,78,3.9,1,"","Тетяна Коваль"),
                ("Мельник","Василь","Іванович","1995-01-30","2023-01-10",
                 "Бахмут, 93-тя бригада","Бахмут","Міна",
                 "Молодший лейтенант, оборона Бахмута.",
                 "#ef9a9a",0.820,0.590,210,6.4,1,"Бахмут-1","Іван Мельник"),
                ("Мельник","Василь","Іванович","1995-01-30","2023-01-10",
                 "Бахмут","Бахмут","Міна","Герой оборони Бахмута.",
                 "#ff8a65",0.825,0.596,89,4.1,1,"Бахмут-1","Школа №5"),
                ("Власенко","Григорій","Петрович","1969-01-12","2022-03-25",
                 "Буча","Київ, Берківське кладовище","Прямий контакт",
                 "Ветеран АТО, загинув у боях за Бучу.",
                 "#c8b060",0.475,0.295,891,11.4,1,"Київ-1","Олена Власенко"),
                ("Власенко","Григорій","Петрович","1969-01-12","2022-03-25",
                 "Буча","Київ","Прямий контакт","Захисник Бучі.",
                 "#ffd54f",0.470,0.302,234,6.8,1,"Київ-1","Меморіал Бучі"),
                ("Саченко","Олег","Михайлович","1976-07-09","2022-04-28",
                 "Чернігів","Чернігів, Яцево","Ракетний удар",
                 "Льотчик-ас, Герой України посмертно.",
                 "#c8b060",0.490,0.220,743,10.6,1,"Чернігів-1","ВПС України"),
                ("Саченко","Олег","Михайлович","1976-07-09","2022-04-28",
                 "Чернігів","Чернігів","Ракетний удар","Герой-льотчик.",
                 "#ffd54f",0.494,0.228,312,7.2,1,"Чернігів-1","Аеропорт Чернігів"),
                ("Гаврилюк","Тарас","Михайлович","1993-08-27","2023-02-28",
                 "Кремінна","Луганська обл.","Артилерія",
                 "Стрілець 53-ї бригади.",
                 "#ce93d8",0.865,0.400,167,5.8,1,"","Родина Гаврилюків"),
                ("Литвин","Іван","Олегович","1980-02-14","2022-06-30",
                 "Лисичанськ","Лисичанськ","Прямий контакт",
                 "Командир взводу, прикривав відхід підрозділу.",
                 "#ef9a9a",0.840,0.440,445,8.9,1,"","Людмила Литвин"),
                ("Петренко","Роман","Андрійович","1997-09-11","2023-07-04",
                 "Куп'янськ","Куп'янськ","Міна",
                 "Наймолодший у роті. Загинув під час розмінування.",
                 "#a5d6a7",0.790,0.340,523,9.2,1,"","Батьки"),
                ("Романенко","Олександр","Юрійович","1975-04-03","2022-11-14",
                 "Миколаїв","Миколаїв","Ракетний удар",
                 "Капітан ВМС, загинув під час ракетного удару.",
                 "#80cbc4",0.516,0.668,98,4.1,1,"","ВМС України"),
                ("Лисенко","Денис","Юрійович","1992-04-07","2023-08-11",
                 "Роботине","Запорізька обл.","Авіабомба",
                 "Учасник контрнаступу 2023.",
                 "#ff8a65",0.750,0.680,412,8.4,1,"","Бойові побратими"),
                ("Стець","Маркіян","Ярославович","1988-09-29","2023-01-28",
                 "Соледар","Дрогобич","Міна",
                 "Прикарпатець, батько двох дітей.",
                 "#c8b060",0.180,0.490,321,7.5,1,"","Марʼяна Стець"),
                ("Зінченко","Антон","Васильович","1994-06-03","2023-06-15",
                 "Лиман","Лиман","Снайпер",
                 "Розвідник, загинув під час розвідки позицій.",
                 "#4fc3f7",0.790,0.470,145,5.3,1,"","Розвідувальна рота"),
                ("Хоменко","Артем","Вікторович","1990-01-25","2023-02-14",
                 "Вугледар","Вугледар","Авіабомба",
                 "Знищив 4 одиниці бронетехніки до загибелі.",
                 "#a5d6a7",0.800,0.650,345,7.7,1,"","112-а бригада"),
                ("Панченко","Леонід","Ігорович","1979-03-31","2022-09-18",
                 "Херсон","Херсон","Артилерія",
                 "Морський піхотинець, тримав позицію на Дніпрі.",
                 "#4fc3f7",0.625,0.730,178,5.7,1,"Херсон-1","Морська піхота"),
                ("Тищенко","Михайло","Олексійович","1985-10-14","2023-11-07",
                 "Кремінна","Кремінна","Снайпер",
                 "Командир відділення у лісах поблизу Кремінної.",
                 "#ce93d8",0.860,0.430,234,6.6,1,"","Кремінська громада"),
            ]
            c.executemany("""
                INSERT INTO memorials
                (last,first,mid,birth,death,loc,bury,circ,descr,color,pos_x,pos_y,likes,rating,approved,grp,added_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, seed)

    # ── SEO: slug column + seo_index_log ───────────────────
    with db.cursor() as c:
        try:
            c.execute("ALTER TABLE memorials ADD COLUMN slug VARCHAR(220) DEFAULT NULL")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE memorials ADD UNIQUE INDEX idx_slug (slug)")
        except Exception:
            pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS seo_index_log (
                id                INT PRIMARY KEY AUTO_INCREMENT,
                url               VARCHAR(500) NOT NULL,
                notification_type VARCHAR(30)  NOT NULL DEFAULT 'URL_UPDATED',
                status            VARCHAR(20)  NOT NULL DEFAULT 'sent',
                response          TEXT,
                created_at        INT          NOT NULL,
                INDEX idx_sil_ts (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS seo_broken_links (
                id           INT PRIMARY KEY AUTO_INCREMENT,
                memorial_id  INT NOT NULL,
                url          VARCHAR(500) NOT NULL,
                link_type    VARCHAR(20)  DEFAULT 'photo',
                status_code  INT          DEFAULT NULL,
                last_checked INT          NOT NULL,
                is_broken    TINYINT      DEFAULT 0,
                UNIQUE KEY uq_sbl_mid_type (memorial_id, link_type),
                INDEX idx_sbl_broken (is_broken, last_checked)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS seo_score_history (
                id            INT PRIMARY KEY AUTO_INCREMENT,
                snapshot_date DATE         NOT NULL,
                total_count   INT          DEFAULT 0,
                avg_score     DECIMAL(5,2) DEFAULT 0,
                count_a       INT          DEFAULT 0,
                count_b       INT          DEFAULT 0,
                count_c       INT          DEFAULT 0,
                count_d       INT          DEFAULT 0,
                UNIQUE KEY uq_ssh_date (snapshot_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    # ── Backfill slugs for existing records ─────────────────
    from seo_utils import make_slug as _make_slug
    with db.cursor() as c:
        c.execute("SELECT id, first, last FROM memorials WHERE slug IS NULL OR slug=''")
        rows_no_slug = c.fetchall()
    if rows_no_slug:
        with db.cursor() as c:
            for r in rows_no_slug:
                _sl = _make_slug(r['first'], r['last'], r['id'])
                try:
                    c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (_sl, r['id']))
                except Exception:
                    pass

    # ── Мікро-чат ────────────────────────────────────────
    with db.cursor() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT NULL,
                message    TEXT NOT NULL,
                created_at BIGINT NOT NULL,
                is_deleted TINYINT DEFAULT 0,
                guest_fp   VARCHAR(64) NULL,
                guest_ip   VARCHAR(45) NULL,
                is_guest   TINYINT DEFAULT 0,
                INDEX idx_chat_created (created_at),
                INDEX idx_chat_user (user_id),
                INDEX idx_chat_guest_fp (guest_fp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_reports (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                msg_id      INT NOT NULL,
                reporter_id INT NOT NULL,
                reason      VARCHAR(200),
                created_at  BIGINT NOT NULL,
                UNIQUE KEY uq_report (msg_id, reporter_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_banned_words (
                id       INT AUTO_INCREMENT PRIMARY KEY,
                word     VARCHAR(200) NOT NULL,
                category VARCHAR(50) DEFAULT 'profanity',
                UNIQUE KEY uq_word (word)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_bot_phrases (
                id        INT AUTO_INCREMENT PRIMARY KEY,
                phrase    TEXT NOT NULL,
                category  VARCHAR(50) DEFAULT 'general',
                is_active TINYINT DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        # Додати колонки ботів якщо ще не існують
        try:
            c.execute("ALTER TABLE chat_messages ADD COLUMN is_bot TINYINT DEFAULT 0")
        except Exception:
            pass
        try:
            c.execute("ALTER TABLE chat_messages ADD COLUMN bot_name VARCHAR(100) NULL")
        except Exception:
            pass
        # Заповнити початкові фрази якщо таблиця порожня
        c.execute("SELECT COUNT(*) as cnt FROM chat_bot_phrases")
        if c.fetchone()['cnt'] == 0:
            _BOT_INITIAL_PHRASES = [
                ("Дуже важливий проєкт, дякую що зберігаєте пам'ять про героїв 🙏", "positive"),
                ("Нещодавно знайшла тут запис про свого дядька. Дякую вам.", "personal"),
                ("Чи можна додати фільтр за областю?", "suggestion"),
                ("Зіркова карта виглядає дуже красиво ✨", "positive"),
                ("Показав друзям — всі були вражені. Чудова робота!", "positive"),
                ("Я б додав можливість завантажити фото з телефону простіше.", "suggestion"),
                ("Дякую за цей проєкт. Моя родина шукала інформацію тут.", "personal"),
                ("Чи планується мобільний додаток?", "suggestion"),
                ("Яскраві зірки на карті — дуже символічно 💫", "positive"),
                ("Знайшов тут свого однокласника. Вічна пам'ять.", "personal"),
                ("Сайт дуже швидкий, приємно користуватись.", "positive"),
                ("Може додати можливість поділитись записом у Telegram?", "suggestion"),
                ("Ромашки б гарно виглядали як символ на карті 🌼", "suggestion"),
                ("Дуже зворушливий проєкт. Слава Україні!", "positive"),
                ("Чи є спосіб повідомити якщо знайшов помилку в записі?", "suggestion"),
                ("Карта завантажується миттєво, молодці розробники!", "positive"),
                ("Додав свого брата. Дякую що є такий сайт.", "personal"),
                ("Пам'ять про героїв живе завдяки таким проєктам ❤️", "positive"),
                ("Чи можна переглянути записи за роком загибелі?", "suggestion"),
                ("Нехай кожна зірка світить вічно 🌟", "positive"),
            ]
            c.executemany(
                "INSERT INTO chat_bot_phrases (phrase, category) VALUES (%s, %s)",
                _BOT_INITIAL_PHRASES
            )
        # Додати ключ chat_bots_enabled якщо відсутній
        c.execute("INSERT IGNORE INTO colors (`key`, value, label) VALUES ('chat_bots_enabled', '1', 'Чат-боти увімкнені')")

    db.commit()
    db.close()


# ── Visit tracking ───────────────────────────────────────
_visits_hourly: dict = {}   # {hour_ts: count}
_visits_daily:  dict = {}   # {date_str 'YYYY-MM-DD': count}  — flushed to daily_stats
_request_count: int  = 0
_server_start: float = time.time()
_db_queries_hourly: dict = {}   # {hour_ts: count} — кількість звернень до БД
_cpu_ram_snapshots: list = []   # [{ts, cpu, ram}] — знімки щохвилини
_pageviews_hourly:  dict = {}   # {hour_ts: count} — лише HTML-сторінки (не API/статика)
_human_pv_hourly:   dict = {}   # {hour_ts: count} — HTML-сторінки БЕЗ ботів
_unique_visitors:   dict = {}   # {ip_hash: hour_ts} — унікальні люди, TTL 24г

# ── Bot detection ─────────────────────────────────────────
_BOT_PATTERNS: list = [
    ("Googlebot",            re.compile(r"Googlebot",            re.I)),
    ("Google-Inspection",    re.compile(r"Google-InspectionTool",re.I)),
    ("Google AdsBot",        re.compile(r"AdsBot-Google",        re.I)),
    ("Bingbot",              re.compile(r"bingbot",              re.I)),
    ("YandexBot",            re.compile(r"YandexBot",            re.I)),
    ("DuckDuckBot",          re.compile(r"DuckDuckBot",          re.I)),
    ("Baiduspider",          re.compile(r"Baiduspider",          re.I)),
    ("Yahoo Slurp",          re.compile(r"\bSlurp\b",            re.I)),
    ("AhrefsBot",            re.compile(r"AhrefsBot",            re.I)),
    ("SemrushBot",           re.compile(r"SemrushBot",           re.I)),
    ("MJ12bot",              re.compile(r"MJ12bot",              re.I)),
    ("FacebookBot",          re.compile(r"facebookexternalhit|FacebookBot", re.I)),
    ("Twitterbot",           re.compile(r"Twitterbot",           re.I)),
    ("LinkedInBot",          re.compile(r"LinkedInBot",          re.I)),
    ("Applebot",             re.compile(r"Applebot",             re.I)),
    ("PetalBot",             re.compile(r"PetalBot",             re.I)),
    ("Bytespider",           re.compile(r"Bytespider",           re.I)),
    ("DataForSeo",           re.compile(r"DataForSeoBot",        re.I)),
    ("GPTBot",               re.compile(r"GPTBot",               re.I)),
    ("ClaudeBot",            re.compile(r"ClaudeBot",            re.I)),
]

def _detect_bot(ua: str) -> Optional[str]:
    for name, pat in _BOT_PATTERNS:
        if pat.search(ua):
            return name
    return None

_bot_log_lock = threading.Lock()
_bot_log_queue: list = []   # [(bot_name, path, ua, ts), ...]  — flushed in background

def _flush_bot_queue():
    """Write queued bot visits to DB and trim rows older than 30 days."""
    with _bot_log_lock:
        batch, _bot_log_queue[:] = _bot_log_queue[:], []
    if not batch:
        return
    try:
        db = get_db()
        with db.cursor() as c:
            for bot_name, path, ua, ts in batch:
                c.execute(
                    "INSERT INTO bot_visits (bot_name,path,user_agent,created_at)"
                    " VALUES (%s,%s,%s,%s)",
                    (bot_name, path[:500], ua[:300], ts)
                )
            cutoff = int(time.time()) - 30 * 86400
            c.execute("DELETE FROM bot_visits WHERE created_at < %s", (cutoff,))
        db.commit()
        db.close()
    except Exception:
        pass

def _flush_daily_visits():
    """Persist in-memory daily visit counters to daily_stats table."""
    today = time.strftime("%Y-%m-%d")
    cnt = _visits_daily.get(today, 0)
    if cnt == 0:
        return
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT INTO daily_stats (date, views) VALUES (%s,%s)"
                " ON DUPLICATE KEY UPDATE views=%s",
                (today, cnt, cnt)
            )
        db.commit()
        db.close()
    except Exception:
        pass


def _snapshot_cpu_ram():
    """Знімок CPU/RAM кожну хвилину для діаграми реалтайм."""
    if not _HAS_PSUTIL:
        return
    try:
        cpu = _psutil.cpu_percent(interval=0)
        ram = _psutil.virtual_memory().percent
        now = int(time.time())
        _cpu_ram_snapshots.append({"ts": now, "cpu": round(cpu, 1), "ram": round(ram, 1)})
        cutoff = now - 13 * 3600
        while _cpu_ram_snapshots and _cpu_ram_snapshots[0]["ts"] < cutoff:
            _cpu_ram_snapshots.pop(0)
    except Exception:
        pass


def _flush_hourly_visits():
    """Persist in-memory hourly visit counters to hourly_stats table."""
    if not _visits_hourly and not _human_pv_hourly:
        return
    try:
        db = get_db()
        with db.cursor() as c:
            all_hours = set(_visits_hourly) | set(_human_pv_hourly)
            for hour_ts in all_hours:
                views = _visits_hourly.get(hour_ts, 0)
                human = _human_pv_hourly.get(hour_ts, 0)
                c.execute(
                    "INSERT INTO hourly_stats (hour_ts, views, human_views) VALUES (%s,%s,%s)"
                    " ON DUPLICATE KEY UPDATE views=%s, human_views=%s",
                    (hour_ts, views, human, views, human)
                )
            cutoff = int(time.time() // 3600) * 3600 - 49 * 3600
            c.execute("DELETE FROM hourly_stats WHERE hour_ts < %s", (cutoff,))
        db.commit()
        db.close()
    except Exception:
        pass


def _load_hourly_visits():
    """Load last 48h hourly visit counts from hourly_stats into _visits_hourly/_human_pv_hourly on startup."""
    try:
        db = get_db()
        with db.cursor() as c:
            cutoff = int(time.time() // 3600) * 3600 - 48 * 3600
            c.execute(
                "SELECT hour_ts, views, human_views FROM hourly_stats WHERE hour_ts >= %s",
                (cutoff,)
            )
            rows = c.fetchall()
        db.close()
        for r in rows:
            _visits_hourly[r["hour_ts"]] = r["views"]
            if r.get("human_views"):
                _human_pv_hourly[r["hour_ts"]] = r["human_views"]
    except Exception:
        pass


# ── Rate limiter ─────────────────────────────────────────
class _RateLimiter:
    """Thread-safe sliding-window in-memory rate limiter with bounded key count."""
    _MAX_KEYS = 50_000

    def __init__(self):
        self._data: dict = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window: int) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        now = time.time()
        with self._lock:
            if len(self._data) > self._MAX_KEYS:
                # Evict 10% oldest keys to stay bounded
                evict = list(self._data.keys())[:self._MAX_KEYS // 10]
                for k in evict:
                    del self._data[k]
            ts = [t for t in self._data.get(key, []) if now - t < window]
            if len(ts) >= limit:
                self._data[key] = ts
                return False
            ts.append(now)
            self._data[key] = ts
            return True

    def blocked(self, key: str, limit: int, window: int) -> bool:
        """Перевіряє блокування без споживання токену."""
        now = time.time()
        with self._lock:
            ts = [t for t in self._data.get(key, []) if now - t < window]
            return len(ts) >= limit

    def purge(self, max_age: int = 3600):
        now = time.time()
        with self._lock:
            for k in list(self._data):
                self._data[k] = [t for t in self._data[k] if now - t < max_age]
                if not self._data[k]:
                    del self._data[k]

_rl = _RateLimiter()


# ── Admin session store (cookie-based auth) ───────────────
_sessions: dict = {}
_sessions_lock = threading.Lock()

# ── Pending email verifications ────────────────────────────
# {email: {code, hash_pw, data{...}, expires, attempts}}
_pending_reg: dict = {}
_pending_reg_lock = threading.Lock()
_PENDING_TTL = 600        # 10 хвилин
_PENDING_MAX_ATTEMPTS = 5 # максимум спроб введення коду

def _pending_cleanup():
    now = time.time()
    with _pending_reg_lock:
        expired = [k for k, v in _pending_reg.items() if v["expires"] < now]
        for k in expired:
            del _pending_reg[k]

def _session_create(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = time.time() + 86400 * 7  # 7 днів
    with _sessions_lock:
        _sessions[token] = {"user_id": user_id, "expires": expires}
    return token

def _session_get(token: str):
    with _sessions_lock:
        sess = _sessions.get(token)
        if not sess:
            return None
        if sess["expires"] < time.time():
            del _sessions[token]
            return None
        return sess

def _session_delete(token: str):
    with _sessions_lock:
        _sessions.pop(token, None)

def _sessions_purge():
    now = time.time()
    with _sessions_lock:
        expired = [k for k, v in _sessions.items() if v["expires"] < now]
        for k in expired:
            del _sessions[k]


# ── Login failure tracker (brute-force lockout) ──────────
_fail_data: dict = {}
_fail_lock = threading.Lock()
_LOCKOUT_MAX    = 5    # невдалих спроб
_LOCKOUT_WINDOW = 900  # 15 хвилин

def _record_fail(ip: str, email: str):
    key = f"{ip}:{email.lower()}"
    now = time.time()
    with _fail_lock:
        ts = [t for t in _fail_data.get(key, []) if now - t < _LOCKOUT_WINDOW]
        ts.append(now)
        _fail_data[key] = ts

def _is_locked(ip: str, email: str) -> bool:
    key = f"{ip}:{email.lower()}"
    now = time.time()
    with _fail_lock:
        ts = [t for t in _fail_data.get(key, []) if now - t < _LOCKOUT_WINDOW]
        _fail_data[key] = ts
        return len(ts) >= _LOCKOUT_MAX

def _clear_fails(ip: str, email: str):
    with _fail_lock:
        _fail_data.pop(f"{ip}:{email.lower()}", None)


# ── SVG sanitizer ────────────────────────────────────────
def _sanitize_svg(svg: str) -> str:
    """Remove script tags, event handlers, javascript: URIs from SVG."""
    svg = re.sub(r'<script[\s\S]*?</script>', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'<script[^>]*/>', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'\s+on\w+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]*)', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'(href|xlink:href|src)\s*=\s*["\']?\s*javascript:[^"\'>\s]*["\']?', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'<foreignObject[\s\S]*?</foreignObject>', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'<use[^>]*/>', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'<use[\s\S]*?</use>', '', svg, flags=re.IGNORECASE)
    svg = re.sub(r'data:[^;"\'\s]*;base64', 'data:text/plain;base64', svg, flags=re.IGNORECASE)
    return svg


_TRUSTED_PROXIES = {"127.0.0.1", "::1"}

def _get_ip(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    # Only trust X-Forwarded-For when the direct connection comes from a known proxy
    if client_host in _TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_host

# ── APP ──────────────────────────────────────────────────
_DEBUG = os.getenv("DEBUG", "0") == "1"
_IS_PROD = os.getenv("ENVIRONMENT", "development") == "production"
app = FastAPI(
    title="Зоряна Памʼять API",
    version="2.0",
    docs_url="/docs" if _DEBUG else None,
    redoc_url="/redoc" if _DEBUG else None,
    openapi_url="/openapi.json" if _DEBUG else None,
)
_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

def _is_browser(request: Request) -> bool:
    return 'text/html' in request.headers.get('accept', '')

@app.exception_handler(404)
async def handler_404(request: Request, exc):
    if _is_browser(request):
        return FileResponse('404.html', status_code=404)
    return JSONResponse({'detail': 'Not found'}, status_code=404)

@app.exception_handler(403)
async def handler_403(request: Request, exc):
    if _is_browser(request):
        return FileResponse('403.html', status_code=403)
    return JSONResponse({'detail': str(getattr(exc, 'detail', 'Forbidden'))}, status_code=403)

@app.exception_handler(429)
async def handler_429(request: Request, exc):
    if _is_browser(request):
        return FileResponse('429.html', status_code=429)
    return JSONResponse({'detail': str(getattr(exc, 'detail', 'Too many requests'))}, status_code=429)

@app.exception_handler(500)
async def handler_500(request: Request, exc):
    if _is_browser(request):
        return FileResponse('500.html', status_code=500)
    return JSONResponse({'detail': 'Server error'}, status_code=500)

# ── Maintenance mode ──────────────────────────────────────
_maintenance_mode: bool = False

_MAINTENANCE_ALLOW = (
    "/admin", "/api/admin/", "/api/auth/",
    "/api/install/", "/install",
    "/api/maintenance-message",
    "/img/", "/js/", "/fonts/", "/audio/",
    "/health", "/metrics",
)

def _session_is_admin(token: str) -> bool:
    sess = _session_get(token)
    if not sess:
        return False
    u = _get_user_by_id(sess["user_id"])
    return bool(u and (u.get("role") == "admin" or u.get("is_admin")) and not u.get("is_banned"))

def _maintenance_response():
    from fastapi.responses import FileResponse as _FR
    resp = _FR("offline.html", status_code=503)
    resp.headers["Retry-After"] = "3600"
    return resp

@app.middleware("http")
async def maintenance_middleware(request: Request, call_next):
    if _maintenance_mode:
        path = request.url.path
        if not any(path == p.rstrip("/") or path.startswith(p) for p in _MAINTENANCE_ALLOW):
            token = request.cookies.get("admin_session", "")
            if not token or not _session_is_admin(token):
                return _maintenance_response()
    return await call_next(request)

@app.middleware("http")
async def track_visits(request, call_next):
    global _request_count
    _request_count += 1
    now = time.time()
    # Hourly buckets (48h window)
    hour = int(now // 3600) * 3600
    _visits_hourly[hour] = _visits_hourly.get(hour, 0) + 1
    cutoff = hour - 48 * 3600
    for k in [k for k in _visits_hourly if k < cutoff]:
        del _visits_hourly[k]
    # Bot detection (раніше — щоб використати результат нижче)
    ua = request.headers.get("user-agent", "")
    bot = _detect_bot(ua) if ua else None
    if bot:
        path = str(request.url.path)
        with _bot_log_lock:
            _bot_log_queue.append((bot, path, ua, int(now)))
    # Pageviews — тільки реальні HTML-сторінки (без API і статики)
    _path = request.url.path
    if (
        _path in ('/', '/admin') or
        _path.startswith('/memorial/') or
        _path.startswith('/user/') or
        _path.endswith('.html')
    ):
        _pageviews_hourly[hour] = _pageviews_hourly.get(hour, 0) + 1
        for k in [k for k in _pageviews_hourly if k < cutoff]:
            del _pageviews_hourly[k]
        if not bot:
            # Унікальний відвідувач: рахуємо IP один раз за 24г
            ip = _get_ip(request)
            ip_hash = hashlib.md5(ip.encode()).hexdigest()
            cutoff_24h = now - 86400
            last_seen = _unique_visitors.get(ip_hash, 0)
            if last_seen < cutoff_24h:
                _unique_visitors[ip_hash] = now
                _human_pv_hourly[hour] = _human_pv_hourly.get(hour, 0) + 1
            # Чистимо старі записи рідко (раз на ~1000 req через _request_count)
            for k in [k for k in _human_pv_hourly if k < cutoff]:
                del _human_pv_hourly[k]
    # Daily counter (persisted to DB every 1000 req)
    today = time.strftime("%Y-%m-%d")
    _visits_daily[today] = _visits_daily.get(today, 0) + 1
    # Periodic maintenance every ~1000 requests
    if _request_count % 1000 == 0:
        _rl.purge(3600)
        _sessions_purge()
        _flush_daily_visits()
        _flush_hourly_visits()
        _flush_bot_queue()
        # Чистимо _unique_visitors старше 24г
        _uv_cutoff = time.time() - 86400
        for _k in [_k for _k, _v in _unique_visitors.items() if _v < _uv_cutoff]:
            del _unique_visitors[_k]
    return await call_next(request)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    if _IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "frame-src https://www.youtube.com https://www.youtube-nocookie.com; "
        "connect-src 'self' ws: wss: data: https://www.youtube.com https://analytics.google.com https://www.google.com/g/collect;"
    )
    return response

# Статичні файли (img)
app.mount("/img",   StaticFiles(directory="img"),   name="img")
app.mount("/js",    StaticFiles(directory="js"),    name="js")
app.mount("/css",   StaticFiles(directory="css"),   name="css")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")
os.makedirs("img/audio", exist_ok=True)
app.mount("/audio", StaticFiles(directory="img/audio"), name="audio")
os.makedirs("promo",     exist_ok=True)
os.makedirs("portfolio", exist_ok=True)
app.mount("/promo",     StaticFiles(directory="promo",     html=True), name="promo")
app.mount("/portfolio", StaticFiles(directory="portfolio", html=True), name="portfolio")

# Jinja2 templates (for SEO SSR pages)
_TEMPLATES = Jinja2Templates(directory="templates")
_SITE_BASE_URL = os.getenv("SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# ── Чат-боти ─────────────────────────────────────────────────
_bot_online_count: int = 0
_bots_enabled: bool = True
_bot_lock = threading.Lock()
_BOT_NAMES = ["Rom4ik89", "Goshinskiy", "Vetal_UA", "Max1mko", "AndriyKh", "Taras_V", "Serg1977", "OlenaM", "Pavlo_33", "DanyloK", "Ruslan88", "NataM"]

def _bot_loop():
    """Фонова задача: боти пишуть повідомлення кожні 2-4 хвилини."""
    import random as _rnd
    global _bot_online_count, _bots_enabled
    # Початкова затримка щоб сервер встиг запуститись
    time.sleep(30)
    _last_online_update = 0.0
    while True:
        try:
            # Оновлювати кількість ботів онлайн кожні 60 секунд
            now = time.time()
            if now - _last_online_update >= 60:
                with _bot_lock:
                    _bot_online_count = _rnd.randint(3, 8)
                _last_online_update = now

            delay = _rnd.uniform(120, 240)
            time.sleep(delay)

            if not _bots_enabled:
                continue

            # Вибираємо фразу і ім'я бота
            try:
                db = get_db()
                with db.cursor() as c:
                    c.execute("SELECT id, phrase FROM chat_bot_phrases WHERE is_active=1 ORDER BY RAND() LIMIT 1")
                    row = c.fetchone()
                db.close()
            except Exception:
                continue
            if not row:
                continue

            bot_name = _rnd.choice(_BOT_NAMES)
            phrase = row['phrase']
            now_ms = int(time.time() * 1000)
            try:
                db = get_db()
                with db.cursor() as c:
                    c.execute(
                        "INSERT INTO chat_messages (user_id, message, created_at, is_guest, is_bot, bot_name)"
                        " VALUES (NULL, %s, %s, 0, 1, %s)",
                        (phrase, now_ms, bot_name)
                    )
                db.commit()
                db.close()
            except Exception:
                pass
        except Exception:
            time.sleep(60)


@app.on_event("startup")
def startup():
    global _maintenance_mode, _bots_enabled
    init_db()
    _init_pool()
    _init_redis()
    _load_hourly_visits()
    try:
        _maintenance_mode = _get_color_val("maintenance_mode", "0") == "1"
    except Exception:
        pass
    try:
        _bots_enabled = _get_color_val("chat_bots_enabled", "1") == "1"
    except Exception:
        pass
    # Початковий випадковий лічильник ботів онлайн
    import random as _rnd
    with _bot_lock:
        _bot_online_count = _rnd.randint(3, 8)
    def _cpu_ram_loop():
        while True:
            _snapshot_cpu_ram()
            time.sleep(60)
    threading.Thread(target=_cpu_ram_loop, daemon=True).start()
    threading.Thread(target=_bot_loop, daemon=True).start()

    def _currency_rate_loop():
        while True:
            try:
                now = time.time()
                last = float(_get_color_val("proj_usd_rate_updated", "0") or 0)
                if now - last > 82800:  # оновлювати не частіше ніж раз на 23 год
                    url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode())
                    rate = str(round(float(data[0]["rate"]), 2))
                    db = get_db()
                    with db.cursor() as c:
                        for k, v in [("proj_usd_rate", rate), ("proj_usd_rate_updated", str(int(now)))]:
                            c.execute("INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') ON DUPLICATE KEY UPDATE value=%s", (k, v, v))
                    db.commit()
                    db.close()
            except Exception:
                pass
            time.sleep(3600)
    threading.Thread(target=_currency_rate_loop, daemon=True).start()

@app.on_event("shutdown")
def shutdown():
    _flush_hourly_visits()
    _flush_daily_visits()


# ── Health & Metrics ──────────────────────────────────────
_app_start_time = time.time()

@app.get("/health")
def health_check():
    """Ендпоінт для моніторингу — перевірка стану сервісу."""
    status = {"status": "ok", "uptime": round(time.time() - _app_start_time, 1)}
    # Перевірка БД
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("SELECT 1")
        db.close()
        status["db"] = "connected"
    except Exception as e:
        status["db"] = f"error: {str(e)[:80]}"
        status["status"] = "degraded"
    # Перевірка Redis
    if _redis:
        try:
            _redis.ping()
            status["redis"] = "connected"
        except Exception as e:
            status["redis"] = f"error: {str(e)[:80]}"
    else:
        status["redis"] = "not configured"
    # Системні метрики
    if _HAS_PSUTIL:
        status["cpu"] = round(_psutil.cpu_percent(), 1)
        status["memory_mb"] = round(_psutil.Process().memory_info().rss / 1024 / 1024, 1)
    return status

# ── Maintenance endpoints ──────────────────────────────────

@app.get("/api/maintenance-message")
def maintenance_message_public():
    """Публічний endpoint — повертає повідомлення заглушки (для offline.html)."""
    return {"message": _get_color_val("maintenance_msg", "Сайт тимчасово недоступний. Проводяться технічні роботи.")}

@app.get("/api/admin/maintenance")
def get_maintenance(request: Request):
    require_admin(request)
    return {
        "enabled": _maintenance_mode,
        "message": _get_color_val("maintenance_msg", ""),
    }

class MaintenanceUpdate(BaseModel):
    enabled: bool
    message: str = ""

@app.put("/api/admin/maintenance")
def set_maintenance(body: MaintenanceUpdate, request: Request):
    global _maintenance_mode
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES ('maintenance_mode',%s,'Режим обслуговування') "
            "ON DUPLICATE KEY UPDATE value=%s",
            (("1" if body.enabled else "0"),) * 2
        )
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES ('maintenance_msg',%s,'Повідомлення заглушки') "
            "ON DUPLICATE KEY UPDATE value=%s",
            (_sanitize_text(body.message),) * 2
        )
    db.commit()
    db.close()
    _maintenance_mode = body.enabled
    cache_delete("colors")
    return {"ok": True, "enabled": _maintenance_mode}

_METRICS_TOKEN = os.getenv("METRICS_TOKEN", "")

@app.get("/metrics")
def metrics(request: Request):
    """Prometheus-style метрики для моніторингу."""
    if _METRICS_TOKEN:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != _METRICS_TOKEN:
            return Response(content="Unauthorized", status_code=401,
                            headers={"WWW-Authenticate": "Bearer realm=\"metrics\""})
    db = get_db()
    m = []
    # Загальна статистика
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1")
        m.append(f'zoryna_memorials_total {c.fetchone()["cnt"]}')
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=0")
        m.append(f'zoryna_memorials_pending {c.fetchone()["cnt"]}')
        c.execute("SELECT COUNT(*) AS cnt FROM users WHERE banned=0")
        m.append(f'zoryna_users_active {c.fetchone()["cnt"]}')
    db.close()
    # Uptime
    uptime = time.time() - _app_start_time
    m.append(f'zoryna_uptime_seconds {uptime:.0f}')
    # Cache status
    m.append(f'zoryna_redis_enabled {_redis is not None}')
    # System
    if _HAS_PSUTIL:
        m.append(f'zoryna_cpu_percent {_psutil.cpu_percent()}')
        m.append(f'zoryna_memory_bytes {_psutil.Process().memory_info().rss}')
    return "\n".join(m), 200, {"Content-Type": "text/plain"}


# ── Static routes ─────────────────────────────────────────
_TABLET_UA = re.compile(r'(iPad|Tablet)', re.IGNORECASE)
_MOB_UA    = re.compile(r'(Mobile|Android|iPhone|iPod|BlackBerry|IEMobile|Opera Mini|webOS)', re.IGNORECASE)

def _detect_device(ua: str) -> str:
    if _TABLET_UA.search(ua):
        return "tablet"
    if _MOB_UA.search(ua):
        return "mobile"
    return "desktop"

def _is_mobile(request: Request) -> bool:
    ua = request.headers.get("user-agent", "")
    return _detect_device(ua) in ("mobile", "tablet")

def _get_device_settings(db) -> dict:
    with db.cursor() as c:
        c.execute(
            "SELECT `key`, value FROM colors WHERE `key` IN "
            "('device_desktop_enabled','device_tablet_enabled','device_mobile_enabled','device_block_msg')"
        )
        rows = {r["key"]: r["value"] for r in c.fetchall()}
    return {
        "desktop": rows.get("device_desktop_enabled", "1") != "0",
        "tablet":  rows.get("device_tablet_enabled",  "1") != "0",
        "mobile":  rows.get("device_mobile_enabled",  "1") != "0",
        "block_msg": rows.get("device_block_msg", "Версія сайту для вашого пристрою тимчасово недоступна."),
    }

def _device_block_html(msg: str) -> str:
    return f"""<!DOCTYPE html><html lang="uk"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Зоряна Пам'ять</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#03070e;color:#d0dce8;font-family:sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px}}
.wrap{{max-width:480px}}
.star{{font-size:52px;margin-bottom:20px;opacity:.7}}
h1{{font-size:18px;font-weight:600;margin-bottom:12px;color:#f0c030}}
p{{font-size:14px;color:#8a9cb0;line-height:1.6}}
</style></head><body>
<div class="wrap">
  <div class="star">&#9733;</div>
  <h1>Зоряна Памʼять</h1>
  <p>{msg}</p>
</div>
</body></html>"""

@app.get("/api/device-status")
def device_status():
    db = get_db()
    try:
        settings = _get_device_settings(db)
    finally:
        db.close()
    return JSONResponse(settings)

@app.get("/index")
@app.get("/index.html")
def index_redirect(): return RedirectResponse(url="/", status_code=301)

@app.get("/")
def index(request: Request):
    db = get_db()
    try:
        _ds = _get_device_settings(db)
        if not _ds.get("desktop", True):
            return HTMLResponse(content=_device_block_html(_ds["block_msg"]), status_code=200)
        with db.cursor() as c:
            c.execute("SELECT value FROM colors WHERE `key`='sea_enabled'")
            row = c.fetchone()
    finally:
        db.close()
    sea_on = (row["value"] if row else "1") != "0"
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    script = f'<script>window.SEA_ENABLED={str(sea_on).lower()};</script>'
    html = html.replace("</head>", f"{script}\n</head>", 1)
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})

@app.get("/mobile")
def mobile_page(request: Request):
    if request.cookies.get("preferred_view") == "desktop":
        return RedirectResponse(url="/", status_code=302)
    db = get_db()
    try:
        _ds = _get_device_settings(db)
    finally:
        db.close()
    _dev = _detect_device(request.headers.get("user-agent", ""))
    if _dev == "tablet" and not _ds.get("tablet", True):
        return RedirectResponse(url="/", status_code=302)
    if _dev == "mobile" and not _ds.get("mobile", True):
        return RedirectResponse(url="/", status_code=302)
    return FileResponse("mobile.html", headers={"Cache-Control": "no-store"})

@app.get("/admin")
def admin_page(): return FileResponse("admin.html")

@app.get("/load-test")
def load_test_page(): return FileResponse("load-test.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon(): return FileResponse("favicon.ico")

@app.get("/Style.css")
def css_file(): return FileResponse("Style.css", media_type="text/css")

@app.get("/ukraine-map.svg")
def svg_map(): return FileResponse("ukraine-map.svg", media_type="image/svg+xml")

@app.get("/card")
def card_page(): return FileResponse("card.html")

@app.get("/user/{nickname}")
def user_profile_page(nickname: str):
    return FileResponse("profile.html")

@app.get("/api/user/{nickname}")
def get_user_profile(nickname: str, request: Request):
    # Власник може бачити свій профіль навіть якщо is_banned
    token = request.cookies.get("admin_session")
    sess = _session_get(token) if token else None
    caller_id = sess["user_id"] if sess else None

    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, name, first_name, last_name, nickname, role, created, is_banned "
                "FROM users WHERE nickname=%s",
                (nickname,)
            )
            user = c.fetchone()
            if not user:
                raise HTTPException(404, "Користувача не знайдено")
            # Забанений — доступ тільки самому власнику
            if user["is_banned"] and caller_id != user["id"]:
                raise HTTPException(404, "Користувача не знайдено")
            c.execute(
                "SELECT id, last, first, mid, slug, photo, likes, rating, color, death "
                "FROM memorials WHERE added_by=%s AND approved=1 ORDER BY id DESC LIMIT 100",
                (user["name"],)
            )
            mems = c.fetchall()
    finally:
        db.close()
    for m in mems:
        if m.get("death"):
            m["death"] = str(m["death"])
    full_name = " ".join(filter(None, [user.get("first_name") or "", user.get("last_name") or ""])) or user["name"]
    return {
        "nickname": user["nickname"],
        "display_name": full_name,
        "role": user["role"],
        "created": user["created"],
        "count": len(mems),
        "memorials": mems,
    }

@app.get("/api/card/settings")
def get_card_settings():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT `key`, value FROM colors WHERE `key` LIKE 'card_%' OR `key`='app_version'")
        rows = c.fetchall()
    db.close()
    defaults = {
        "card_accent": "#f0b54a", "card_bg": "#050507",
        "card_show_bio": "1", "card_show_timeline": "1",
        "card_show_video": "1", "card_show_awards": "1",
        "card_show_ribbon": "1", "card_show_candle": "1",
        "card_no_photo_bg": "/img/bgcard.webp",
        "card_footer_text": "Вічна памʼять Героям України",
        "card_likes_refresh": "60",
        "app_version": "2.42 beta",
    }
    result = dict(defaults)
    for r in rows:
        result[r["key"]] = r["value"]
    return result

@app.get("/api/admin/google/status")
def google_status(request: Request):
    require_moder(request)
    _key_file = os.getenv("GOOGLE_INDEXING_KEY_FILE", "")
    return {
        "oauth_configured":    bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "oauth_enabled":       _get_color_val("reg_allow_google", "1") == "1",
        "indexing_configured": bool(_key_file and os.path.exists(_key_file)),
        "site_verification":   _get_color_val("google_site_verification", ""),
        "analytics_id":        _get_color_val("google_analytics_id", ""),
        "analytics_enabled":   _get_color_val("google_analytics_enabled", "0") == "1",
        "redirect_uri":        f"{OAUTH_REDIRECT_BASE}/api/auth/google/callback",
    }

@app.get("/api/admin/density-settings")
def get_density_settings(request: Request):
    require_moder(request)
    raw = _get_color_val("density_config", "{}")
    try:
        return json.loads(raw)
    except Exception:
        return {}

@app.post("/api/admin/density-settings")
async def save_density_settings(request: Request):
    require_moder(request)
    body = await request.json()
    value = json.dumps(body, ensure_ascii=False)
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE colors SET value=%s WHERE `key`='density_config'", (value,))
    db.commit()
    db.close()
    cache_delete("colors")
    return {"ok": True}

@app.get("/api/admin/density-heatmap")
def get_density_heatmap(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, pos_x, pos_y, likes, rating FROM memorials "
            "WHERE approved=1 AND pos_x IS NOT NULL AND pos_y IS NOT NULL"
        )
        rows = cur.fetchall()
    db.close()
    return [
        {"id": r["id"], "x": float(r["pos_x"]), "y": float(r["pos_y"]),
         "likes": r["likes"] or 0, "rating": float(r["rating"] or 0)}
        for r in rows
    ]

@app.get("/api/admin/density-stats")
def get_density_stats(request: Request):
    require_moder(request)
    raw = _get_color_val("density_config", "{}")
    try:
        cfg = json.loads(raw)
    except Exception:
        cfg = {}
    weights = cfg.get("weights", {"likes": 0.45, "rating": 0.35, "views": 0.15, "activity": 0.05})
    zoom_levels = sorted(cfg.get("zoomLevels", []), key=lambda x: x.get("zoom", 0))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, last, first, mid, likes, rating FROM memorials WHERE approved=1")
        rows = cur.fetchall()
    db.close()
    scores = []
    for r in rows:
        score = (r["likes"] or 0) * weights.get("likes", 0.45) + \
                (r["rating"] or 0) * weights.get("rating", 0.35)
        name_parts = [r.get("last", "") or "", r.get("first", "") or "", r.get("mid", "") or ""]
        name = " ".join(p for p in name_parts if p).strip() or "—"
        scores.append({"id": r["id"], "name": name, "score": round(score, 2),
                        "likes": r["likes"] or 0, "rating": float(r["rating"] or 0)})
    scores.sort(key=lambda x: x["score"], reverse=True)
    zoom_dist = [
        {"zoom": lv["zoom"], "minScore": lv["minScore"],
         "visible": sum(1 for s in scores if s["score"] >= lv["minScore"])}
        for lv in zoom_levels
    ]
    avg = round(sum(s["score"] for s in scores) / len(scores), 2) if scores else 0
    return {
        "total": len(scores),
        "avg_score": avg,
        "top5": scores[:5],
        "zoom_dist": zoom_dist,
    }

@app.get("/rules.html")
def rules_page(): return FileResponse("rules.html")

@app.get("/terms.html")
def terms_page(): return FileResponse("terms.html")

@app.get("/faq.html")
def faq_page(): return FileResponse("faq.html")

@app.get("/privacy-policy")
def privacy_policy_page(): return FileResponse("privacy-policy.html")

@app.get("/google{code}.html")
def google_verify(code: str): return FileResponse(f"google{code}.html")

@app.get("/privacy-policy.html")
def privacy_policy_html_page(): return FileResponse("privacy-policy.html")

@app.get("/silence-module.js")
def silence_js(): return FileResponse("silence-module.js", media_type="application/javascript")

@app.get("/silence-module.css")
def silence_css(): return FileResponse("silence-module.css", media_type="text/css")


# ── WebSocket онлайн ─────────────────────────────────────
connected: set = set()
online_users: dict = {}  # {id(ws): {"name": str, "role": str}}
_online_pings: dict = {}  # IP -> timestamp (HTTP polling fallback)

def _online_users_list():
    return [{"name": v["name"], "role": v["role"]}
            for v in online_users.values() if v.get("name")]

async def broadcast(data: dict):
    dead = set()
    for ws in connected:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    connected.difference_update(dead)

@app.websocket("/ws/online")
async def ws_online(ws: WebSocket):
    await ws.accept()
    connected.add(ws)
    # Видаляємо HTTP-ping записи для цього IP — клієнт тепер через WS
    ip = ws.client.host if ws.client else None
    if ip:
        for k in list(_online_pings.keys()):
            if k == ip or k.startswith(ip + "|"):
                del _online_pings[k]
    await broadcast({"event": "join", "online": len(connected), "users": _online_users_list()})

    async def _ping_loop():
        while ws in connected:
            try:
                await asyncio.sleep(30)
                await ws.send_json({"event": "ping"})
            except Exception:
                break

    ping_task = asyncio.create_task(_ping_loop())
    try:
        while True:
            msg = await ws.receive_text()
            if msg.startswith("user:"):
                parts = msg[5:].split("|", 1)
                name = _html.escape(parts[0][:50])
                role = parts[1][:10] if len(parts) > 1 else "user"
                if role not in ("admin", "moder"):
                    role = "user"
                online_users[id(ws)] = {"name": name, "role": role}
                await broadcast({"event": "update", "online": len(connected), "users": _online_users_list()})
    except Exception:
        pass
    finally:
        ping_task.cancel()
        connected.discard(ws)
        online_users.pop(id(ws), None)
        await broadcast({"event": "leave", "online": len(connected), "users": _online_users_list()})

@app.post("/api/online/ping")
async def online_ping(request: Request):
    # Ключ = IP + tab_id з тіла або заголовка — один IP може мати N вкладок
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    tab_id = str(body.get("tab_id", ""))[:64]
    ip = request.client.host
    key = f"{ip}|{tab_id}" if tab_id else ip
    now = time.time()
    _online_pings[key] = now
    stale = [k for k, v in _online_pings.items() if now - v > 180]
    for k in stale:
        del _online_pings[k]
    # HTTP ping рахуємо окремо; WS клієнти самі отримують total через broadcast
    # Total = WS (кожна вкладка = окремий WS) + HTTP-only (ті що без WS)
    return {"online": len(connected) + len(_online_pings)}

@app.get("/api/online/count")
async def online_count_http():
    now = time.time()
    active = sum(1 for v in _online_pings.values() if now - v <= 180)
    return {"online": len(connected) + active}


# ── Magic bytes MIME validation (без зовнішніх залежностей) ─────
_AUDIO_SIGNATURES: list[tuple[bytes, int]] = [
    (b"ID3",       0),   # MP3 з ID3-тегом
    (b"\xff\xfb",  0),   # MP3
    (b"\xff\xf3",  0),   # MP3
    (b"\xff\xf2",  0),   # MP3
    (b"RIFF",      0),   # WAV (перевіряємо окремо)
    (b"OggS",      0),   # OGG
    (b"ftyp",      4),   # M4A/MP4 (4 байти offset)
]
_IMAGE_SIGNATURES: list[tuple[bytes, int]] = [
    (b"\x89PNG",    0),  # PNG
    (b"\xff\xd8\xff", 0),# JPEG
    (b"GIF87a",     0),  # GIF
    (b"GIF89a",     0),  # GIF
    (b"RIFF",       0),  # WEBP (перевіряємо "WEBP" на offset 8)
]

def _check_audio_magic(data: bytes) -> bool:
    for sig, off in _AUDIO_SIGNATURES:
        if data[off:off+len(sig)] == sig:
            if sig == b"RIFF":
                return data[8:12] == b"WAVE"
            return True
    return False

def _check_image_magic(data: bytes, ext: str) -> bool:
    if ext == ".svg":
        head = data[:200].lstrip()
        return head.startswith(b"<svg") or head.startswith(b"<?xml") or b"<svg" in head[:500]
    for sig, off in _IMAGE_SIGNATURES:
        if data[off:off+len(sig)] == sig:
            if sig == b"RIFF":
                return data[8:12] == b"WEBP"
            return True
    return False

# ── Validation helpers ────────────────────────────────────
_PRIVATE_IP_RE = re.compile(
    r'^(https?://)?(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|0\.0\.0\.0|::1)',
    re.IGNORECASE,
)
_HEX_COLOR_RE  = re.compile(r'^#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?$')
_RGBA_COLOR_RE = re.compile(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+')

_SSRF_BLOCKED_HOSTS = frozenset({
    "metadata.google.internal", "169.254.169.254",
    "instance-data", "instance-data.ec2.internal",
    "169.254.170.2",  # AWS ECS metadata
})

def _validate_photo_url(url: str) -> str:
    if not url:
        return url
    if not url.startswith(('http://', 'https://')):
        raise HTTPException(400, "URL фото має починатись з http:// або https://")
    if _PRIVATE_IP_RE.match(url):
        raise HTTPException(400, "Недопустиме URL фото")
    # Перевірка hostname: блокуємо userinfo-обхід та хмарні metadata endpoints
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = (parsed.hostname or '').lower()
        if hostname in _SSRF_BLOCKED_HOSTS or hostname.endswith(".internal") or hostname.endswith(".local"):
            raise HTTPException(400, "Недопустиме URL фото")
        # Блокуємо userinfo (http://user@host — може приховувати адресу)
        if parsed.username or parsed.password:
            raise HTTPException(400, "Недопустиме URL фото")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Недопустиме URL фото")
    return url[:500]

def _sanitize_text(s: str, maxlen: int = 200) -> str:
    if not s:
        return ''
    return _html.escape(str(s).strip())[:maxlen]

_USER_HIDDEN_FIELDS = frozenset({'password', 'ban_until', 'notes'})
def _safe_user(row: dict) -> dict:
    """Видаляє чутливі поля перед поверненням у відповідь API."""
    return {k: v for k, v in row.items() if k not in _USER_HIDDEN_FIELDS}

# Межі України для конвертації lat/lng → SVG 0..1
_UA_LAT_MIN, _UA_LAT_MAX = 43.95, 52.37
_UA_LNG_MIN, _UA_LNG_MAX = 22.15, 41.03

def _latLngToSvg(lat: float, lng: float):
    """Конвертує географічні координати в нормалізовані 0..1 для SVG-карти України."""
    x = round((lng - _UA_LNG_MIN) / (_UA_LNG_MAX - _UA_LNG_MIN), 4)
    y = round(1.0 - (lat - _UA_LAT_MIN) / (_UA_LAT_MAX - _UA_LAT_MIN), 4)
    return x, y

_DATE_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')

def _validate_date(s) -> str | None:
    if not s:
        return None
    s = str(s).strip()
    if not _DATE_RE.match(s):
        raise HTTPException(400, f"Невалідний формат дати (очікується РРРР-ММ-ДД): {s[:20]}")
    return s

_PASS_RE = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]{10,72}$')
_NICK_RE = re.compile(r'^[Ѐ-ӿa-zA-Z0-9_.\-]{2,50}$')  # Cyrillic + Latin + digits + _.-
_PHONE_RE = re.compile(r'^380[3-9]\d{8}$')

def _email_verification_html(code: str, nickname: str) -> str:
    nickname = _html.escape(nickname)
    code     = _html.escape(code)
    return f"""<!DOCTYPE html>
<html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:20px;background:#060e1a;font-family:Arial,sans-serif">
<div style="max-width:480px;margin:0 auto">
  <div style="background:#0d1f35;border-radius:14px;overflow:hidden;border:1px solid #1a3a5c">
    <div style="background:linear-gradient(135deg,#0e2060,#0a1840);padding:24px;text-align:center">
      <div style="font-size:32px">★</div>
      <h1 style="margin:6px 0 0;color:#f0c030;font-size:18px;letter-spacing:1px">ЗОРЯНА ПАМ'ЯТЬ</h1>
      <p style="color:#8ab0d0;font-size:12px;margin:4px 0 0">Меморіальна платформа</p>
    </div>
    <div style="padding:28px 28px 20px">
      <h2 style="color:#00c8ff;margin:0 0 12px;font-size:16px">Підтвердження реєстрації</h2>
      <p style="color:#a0b8d0;font-size:14px;margin:0 0 20px">
        Вітаємо, <strong style="color:#d0dce8">@{nickname}</strong>!<br>
        Ваш код підтвердження email:
      </p>
      <div style="background:#05101e;border:2px solid #00c8ff;border-radius:12px;
                  padding:22px 0;text-align:center;margin:0 0 20px">
        <span style="font-size:40px;font-weight:700;letter-spacing:14px;color:#f0c030;
                     font-family:'Courier New',monospace">{code}</span>
      </div>
      <p style="color:#607080;font-size:12px;margin:0;line-height:1.6">
        ⏱ Код дійсний <strong style="color:#8a9cb0">10 хвилин</strong>.<br>
        🔒 Нікому не передавайте цей код.<br>
        Якщо ви не реєструвались — просто проігноруйте цей лист.
      </p>
    </div>
    <div style="background:#040c18;padding:12px 28px;text-align:center;
                font-size:11px;color:#3a5060;border-top:1px solid #0d2040">
      © Зоряна Пам'ять · Цей лист надіслано автоматично, не відповідайте на нього
    </div>
  </div>
</div>
</body></html>"""

def _get_smtp_config() -> dict:
    """Зчитує SMTP-налаштування: DB має пріоритет над .env."""
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT `key`, value FROM colors WHERE `key` LIKE 'smtp_%'")
        rows = {r["key"]: r["value"] for r in c.fetchall()}
    db.close()
    def pick(db_key, env_key, default=""):
        return rows.get(db_key, "") or os.getenv(env_key, "") or default
    host    = pick("smtp_host",    "SMTP_HOST")
    port_s  = pick("smtp_port",    "SMTP_PORT", "587")
    user    = pick("smtp_user",    "SMTP_USER")
    pw      = pick("smtp_pass",    "SMTP_PASS")
    from_   = pick("smtp_from",    "SMTP_FROM") or user
    secure  = rows.get("smtp_secure", "starttls") or "starttls"
    enabled = rows.get("smtp_enabled", "1")
    try:
        port = int(port_s)
    except (ValueError, TypeError):
        port = 587
    return {"host": host, "port": port, "user": user, "pw": pw,
            "from": from_, "secure": secure, "enabled": enabled}

def _send_email(to_addr: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Надсилає email. DB-налаштування мають пріоритет над .env."""
    cfg = _get_smtp_config()
    if cfg["enabled"] == "0":
        return False, "Відправка листів вимкнена в налаштуваннях"
    if not cfg["host"] or not cfg["user"]:
        logging.warning(f"[DEV] Email to {to_addr}: {subject}\n{html_body[:200]}")
        return False, "SMTP не налаштований"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["from"]
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg["secure"] == "ssl":
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15, context=ctx) as srv:
                srv.login(cfg["user"], cfg["pw"])
                srv.sendmail(cfg["from"], [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as srv:
                srv.ehlo()
                if cfg["secure"] == "starttls":
                    srv.starttls()
                if cfg["user"]:
                    srv.login(cfg["user"], cfg["pw"])
                srv.sendmail(cfg["from"], [to_addr], msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Помилка авторизації (перевірте логін/пароль)"
    except smtplib.SMTPException as e:
        return False, f"SMTP помилка: {str(e)[:120]}"
    except Exception as e:
        return False, f"Помилка з'єднання: {str(e)[:120]}"

def _validate_password(pw: str):
    if not _PASS_RE.match(pw):
        raise HTTPException(400, "Пароль: мінімум 10 символів, великі та малі латинські літери, цифри")

def _get_color_val(key: str, default: str = "") -> str:
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT value FROM colors WHERE `key`=%s", (key,))
        row = c.fetchone()
    db.close()
    return row["value"] if row else default

def _validate_color(v: str) -> str:
    if not v:
        return '#4fc3f7'
    if _HEX_COLOR_RE.match(v) or _RGBA_COLOR_RE.match(v):
        return v
    raise HTTPException(400, "Невалідний формат кольору")

_YT_ID_RE = re.compile(r'(?:youtu\.be/|[?&]v=|/embed/)([a-zA-Z0-9_-]{11})')

def _validate_yt_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip()[:500]
    if not _YT_ID_RE.search(url):
        raise HTTPException(400, "Невалідне посилання YouTube")
    return url

# ── Schemas ───────────────────────────────────────────────
class AwardSimple(BaseModel):
    name:     str = Field(..., max_length=200)
    img_file: str = Field("", max_length=300)
    category: str = Field("", max_length=30)

class PersonIn(BaseModel):
    last:  str = Field(..., min_length=1, max_length=100)
    first: str = Field(..., min_length=1, max_length=100)
    mid:   Optional[str] = Field("", max_length=100)
    birth: Optional[str] = None
    death: Optional[str] = None
    loc:   Optional[str] = Field("", max_length=300)
    bury:  Optional[str] = Field("", max_length=300)
    circ:  Optional[str] = Field("", max_length=200)
    descr: Optional[str] = Field("", max_length=5000)
    photo: Optional[str] = Field("", max_length=500)
    color: Optional[str] = Field("#4fc3f7", max_length=30)
    video_url: Optional[str] = Field("", max_length=500)
    rank:     Optional[str] = Field("", max_length=100)
    position: Optional[str] = Field("", max_length=100)
    unit:     Optional[str] = Field("", max_length=200)
    pos_x: float = Field(0.0)
    pos_y: float = Field(0.0)
    world_lat: Optional[float] = None
    world_lng: Optional[float] = None
    grp:      Optional[str] = Field("", max_length=100)
    added_by: Optional[str] = Field("", max_length=100)
    awards:   List[AwardSimple] = []

class PersonUpdate(BaseModel):
    last: Optional[str] = None; first: Optional[str] = None
    mid: Optional[str] = None; birth: Optional[str] = None
    death: Optional[str] = None; loc: Optional[str] = None
    bury: Optional[str] = None; circ: Optional[str] = None
    descr: Optional[str] = None; photo: Optional[str] = None
    color: Optional[str] = None; pos_x: Optional[float] = None
    pos_y: Optional[float] = None; approved: Optional[int] = None
    grp: Optional[str] = None; video_url: Optional[str] = None
    rank: Optional[str] = None; position: Optional[str] = None
    unit: Optional[str] = None; world_lat: Optional[float] = None
    world_lng: Optional[float] = None

class SendCodeReq(BaseModel):
    last_name: str
    first_name: str
    middle_name: str
    nickname: str
    email: str
    phone: str = ""
    password: str
    terms_agreed: bool

class UserReg(BaseModel):
    email: str
    code:  str

class UserLogin(BaseModel):
    email: str; password: str

class UserProfileUpdate(BaseModel):
    nickname:      Optional[str] = None
    email:         Optional[str] = None
    email_confirm: Optional[str] = None
    phone:         Optional[str] = None
    password:      Optional[str] = None
    old_password:  Optional[str] = None

class ColorUpdate(BaseModel):
    key: str; value: str

class LabelUpdate(BaseModel):
    id: int; x: float; y: float
    name:  Optional[str] = None
    color: Optional[str] = None; size: Optional[int] = None

class CityUpdate(BaseModel):
    name:  Optional[str]   = None
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    tier:  Optional[int]   = None
    color: Optional[str]   = None

class CityCreate(BaseModel):
    name: str

class PartnerCreate(BaseModel):
    name: str = ''
    image_url: str
    link_url: str = ''
    caption: str = ''
    width: int = 120
    opacity: float = 1.0
    pos_x: int = 20
    pos_y: int = 20
    is_visible: int = 1
    sort_order: int = 0

class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None
    link_url: Optional[str] = None
    caption: Optional[str] = None
    width: Optional[int] = None
    opacity: Optional[float] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None
    is_visible: Optional[int] = None
    sort_order: Optional[int] = None

class BanRequest(BaseModel):
    duration: int = 0   # seconds; 0 = permanent
    reason: str = ""

class UserUpdate(BaseModel):
    name:     Optional[str] = None
    email:    Optional[str] = None
    is_admin: Optional[int] = None
    notes:    Optional[str] = None
    tier: Optional[int] = 0
    color: Optional[str] = '#a0d7ff'


# ── AUTH helpers ──────────────────────────────────────────
def get_user(email: str, password: str):
    """Fetch user by email and verify password (supports bcrypt and legacy SHA256)."""
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM users WHERE email=%s", (email.lower(),))
        row = c.fetchone()
    db.close()
    if not row or not verify_pass(password, row["password"]):
        return None
    return row

def _upgrade_to_bcrypt(email: str, plain: str):
    """Lazily migrate a SHA256 password hash to bcrypt after successful login."""
    new_hash = hash_pass(plain)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE users SET password=%s WHERE email=%s", (new_hash, email.lower()))
    db.commit()
    db.close()

def get_admin(email: str, password: str):
    u = get_user(email, password)
    if not u or not u["is_admin"]:
        return None
    return u

def _get_user_by_id(user_id: int):
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,email,is_admin,is_banned,role FROM users WHERE id=%s", (user_id,)
        )
        row = c.fetchone()
    db.close()
    return row

def _basic_auth_user(request: Request):
    """Parse Basic Auth header and return verified user or raise 403/429."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        raise HTTPException(403, "Доступ заборонено")
    ip = _get_ip(request)
    fail_key = f"admin_fail:{ip}"
    if _rl.blocked(fail_key, 10, 300):
        sec_log("ADMIN_RATE_LIMIT", ip)
        raise HTTPException(429, "Забагато спроб. Зачекайте 5 хвилин.")
    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        email, password = decoded.split(":", 1)
    except Exception:
        _rl.check(fail_key, 10, 300)
        sec_log("AUTH_MALFORMED", ip, "bad basic auth header")
        raise HTTPException(403, "Доступ заборонено")
    u = get_user(email, password)
    if not u or u.get("is_banned"):
        _rl.check(fail_key, 10, 300)
        sec_log("AUTH_FAIL", ip, f"email={email[:50]}")
        raise HTTPException(403, "Доступ заборонено")
    return u

def require_admin(request: Request):
    """Тільки role='admin'."""
    token = request.cookies.get("admin_session")
    if token:
        sess = _session_get(token)
        if sess:
            u = _get_user_by_id(sess["user_id"])
            if u and u.get("role") == "admin" and not u["is_banned"]:
                return u
    u = _basic_auth_user(request)
    if u.get("role") != "admin":
        raise HTTPException(403, "Потрібні права адміністратора")
    return u

def require_moder(request: Request):
    """role='admin' або role='moder'."""
    token = request.cookies.get("admin_session")
    if token:
        sess = _session_get(token)
        if sess:
            u = _get_user_by_id(sess["user_id"])
            if u and u.get("role") in ("admin", "moder") and not u["is_banned"]:
                return u
    u = _basic_auth_user(request)
    if u.get("role") not in ("admin", "moder"):
        raise HTTPException(403, "Потрібні права модератора або адміністратора")
    return u


# ── Пошук: нормалізація та scoring ───────────────────────
def _normalize(s: str) -> str:
    s = (s or "").lower().strip()
    translit = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','є':'ye',
        'ж':'zh','з':'z','и':'i','і':'i','й':'y','к':'k','л':'l',
        'м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t',
        'у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
        'щ':'shch','ю':'yu','я':'ya','ь':'','ї':'yi','ё':'yo',
    }
    return "".join(translit.get(ch, ch) for ch in s)

def _fuzzy_score(text: str, query: str) -> float:
    t, q = _normalize(text), _normalize(query)
    if not t or not q: return 0.0
    if t == q: return 1.0
    if t.startswith(q): return 0.92
    if q in t: return 0.80
    for word in t.split():
        if word.startswith(q): return 0.75
        if q in word: return 0.65
    if len(q) >= 2:
        matches = sum(1 for c in q if c in t)
        ratio = matches / max(len(q), len(t))
        if ratio > 0.6:
            return ratio * 0.55
    return 0.0

def _score_person(row: dict, q: str) -> float:
    fields = [
        (row.get("last", ""),  2.0),
        (row.get("first", ""), 1.8),
        (row.get("mid", ""),   1.2),
        (row.get("grp", ""),   1.5),
        (row.get("loc", ""),   1.3),
        (row.get("bury", ""),  1.0),
        (row.get("circ", ""),  0.8),
        (row.get("descr", ""), 0.6),
    ]
    best = max((_fuzzy_score(v, q) * w for v, w in fields), default=0.0)
    full = f"{row.get('last','')} {row.get('first','')} {row.get('mid','')}".strip()
    return max(best, _fuzzy_score(full, q) * 2.0)


# ── PUBLIC API ────────────────────────────────────────────

_YT_VID_RE = re.compile(r'^[a-zA-Z0-9_-]{11}$')

@app.get("/api/yt-check")
def yt_check(vid: str):
    """Перевіряє чи дозволяє відео вбудовування (server-side, без CORS)."""
    vid = vid.strip()[:12]
    if not _YT_VID_RE.match(vid):
        return {"embeddable": False}
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5):
            return {"embeddable": True}
    except urllib.error.HTTPError as e:
        return {"embeddable": e.code not in (401, 403)}
    except Exception:
        return {"embeddable": True}

@app.get("/api/people")
def get_people(page: int = 1, limit: int = 50, request: Request = None):
    ip = _get_ip(request) if request else "unknown"
    if not _rl.check(f"pub:{ip}", 60, 60):
        sec_log("RATE_LIMIT", ip, "pub endpoint"); raise HTTPException(429, "Забагато запитів. Зачекайте.")
    page = max(1, page)
    limit = max(1, min(limit, 100))
    # Redis cache
    cache_key = f"people:p{page}:l{limit}"
    cached = cache_get(cache_key)
    if cached:
        return json.loads(cached)
    offset = (page - 1) * limit
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1")
            total = c.fetchone()["cnt"]
            c.execute(
                "SELECT id,last,first,mid,birth,death,bury,loc,photo,color,pos_x,pos_y,"
                "grp,`rank`,`position`,unit,likes,rating,video_url,approved,added_by,slug,"
                "world_lat,world_lng "
                "FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC "
                "LIMIT %s OFFSET %s",
                (limit, offset)
            )
            rows = c.fetchall()
    finally:
        db.close()
    result = {"items": rows, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}
    cache_set(cache_key, json.dumps(result, ensure_ascii=False), ttl=60)
    return result

@app.get("/api/map-points")
def get_map_points(request: Request = None):
    """Легкий endpoint тільки для карти — мінімум полів, один запит, Redis TTL 90с."""
    ip = _get_ip(request) if request else "unknown"
    if not _rl.check(f"pub:{ip}", 60, 60):
        raise HTTPException(429, "Забагато запитів. Зачекайте.")
    cached = cache_get("map_points")
    if cached:
        return json.loads(cached)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id, last, first, mid, birth, death, bury, loc, pos_x, pos_y, "
                "color, likes, rating, grp, slug, world_lat, world_lng "
                "FROM memorials WHERE approved=1 ORDER BY rating DESC, likes DESC"
            )
            rows = c.fetchall()
    finally:
        db.close()
    result = {"items": rows, "total": len(rows)}
    cache_set("map_points", json.dumps(result, ensure_ascii=False), ttl=90)
    return result

@app.get("/api/memorial/{mid}")
def get_memorial(mid: int):
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM memorials WHERE id=%s AND approved=1", (mid,))
            row = c.fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(404, "Не знайдено")
    return row

@app.get("/api/search")
def search(q: str = "", request: Request = None):
    ip = _get_ip(request) if request else "unknown"
    # 30 запитів / хв з одного IP
    if not _rl.check(f"search:{ip}", 30, 60):
        sec_log("RATE_LIMIT", ip, "search endpoint"); raise HTTPException(429, "Забагато пошукових запитів. Зачекайте хвилину.")
    q = q.strip()[:200]
    if len(q) < 2:
        return []
    db = get_db()
    try:
        with db.cursor() as c:
            # FULLTEXT пошук через MATCH...AGAINST — набагато швидше ніж LIKE
            try:
                # Boolean mode підтримує короткі запити (min 3 символи за замовчуванням)
                c.execute("""
                    SELECT * FROM memorials WHERE approved=1 AND MATCH(last,first,mid,grp,loc,descr)
                    AGAINST(%s IN BOOLEAN MODE)
                """, (q,))
                rows = c.fetchall()
            except Exception:
                # Fallback на LIKE якщо FULLTEXT ще не створено
                like = f"%{q}%"
                c.execute("""
                    SELECT * FROM memorials WHERE approved=1 AND (
                        last LIKE %s OR first LIKE %s OR mid LIKE %s OR grp LIKE %s OR loc LIKE %s
                        OR bury LIKE %s OR circ LIKE %s OR descr LIKE %s
                    )
                """, (like, like, like, like, like, like, like, like))
                rows = c.fetchall()

        scored = []
        for r in rows:
            score = _score_person(r, q)
            if score > 0.3:
                scored.append((score, r))
        scored.sort(key=lambda x: (-x[0], -(x[1].get("rating") or 0)))

        results = []
        for score, r in scored[:10]:
            results.append({
                "id":       r["id"],
                "name":     f"{r['last']} {r['first']} {r.get('mid','') or ''}".strip(),
                "last":     r["last"],
                "first":    r["first"],
                "mid":      r.get("mid", "") or "",
                "callsign": r.get("grp", "") or "",
                "location": r.get("loc", "") or "",
                "bury":     r.get("bury", "") or "",
                "color":    r.get("color", "#4fc3f7"),
                "x":        r.get("pos_x", 0.5),
                "y":        r.get("pos_y", 0.5),
                "likes":    r.get("likes", 0),
                "score":    round(score, 3),
            })

        # Логуємо запит (обмежуємо до 10000 записів)
        try:
            with db.cursor() as c:
                c.execute(
                    "INSERT INTO search_logs (query, results_count, created_at) VALUES (%s,%s,%s)",
                    (q, len(results), int(time.time()))
                )
                # Видаляємо записи старше 30 днів та обмежуємо до 10000 записів
                cutoff = int(time.time()) - 30 * 86400
                c.execute("DELETE FROM search_logs WHERE created_at < %s", (cutoff,))
                c.execute("""
                    DELETE FROM search_logs
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id FROM search_logs ORDER BY id DESC LIMIT 10000
                        ) AS t
                    )
                """)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
    return results

@app.post("/api/search/log")
def search_log(data: dict, request: Request = None):
    ip = _get_ip(request) if request else "unknown"
    if not _rl.check(f"slog:{ip}", 20, 60):
        return {"ok": True}  # тихо ігноруємо спам, не розкриваємо 429
    try:
        q   = str(data.get("query", ""))[:200]
        cnt = int(data.get("results_count", 0))
        db  = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT INTO search_logs (query, results_count, created_at) VALUES (%s,%s,%s)",
                (q, cnt, int(time.time()))
            )
        db.commit()
        db.close()
    except Exception:
        pass
    return {"ok": True}

@app.get("/api/search/stats")
def search_stats(request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM search_logs")
        total = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM search_logs WHERE results_count=0")
        empty = c.fetchone()["cnt"]
        c.execute("""
            SELECT query, COUNT(*) AS cnt FROM search_logs
            GROUP BY LOWER(TRIM(query)) ORDER BY cnt DESC LIMIT 10
        """)
        top = c.fetchall()
        c.execute(
            "SELECT query, results_count, created_at FROM search_logs ORDER BY id DESC LIMIT 20"
        )
        recent = c.fetchall()
    db.close()
    return {
        "total_searches": total,
        "empty_results":  empty,
        "top_queries":    [{"query": r["query"], "count": r["cnt"]} for r in top],
        "recent":         recent,
    }

@app.get("/api/stats")
def get_stats():
    cached = cache_get("stats")
    if cached:
        return json.loads(cached)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(likes),0) AS likes FROM memorials WHERE approved=1"
        )
        row = c.fetchone()
        # visitors_24h: з БД (переживає рестарт) + поточна година з пам'яті
        now_hour = int(time.time() // 3600) * 3600
        cutoff = now_hour - 23 * 3600
        c.execute(
            "SELECT COALESCE(SUM(human_views),0) AS v FROM hourly_stats WHERE hour_ts >= %s AND hour_ts < %s",
            (cutoff, now_hour)
        )
        db_visitors = int(c.fetchone()["v"])
    db.close()
    cur_hour_visitors = _human_pv_hourly.get(now_hour, 0)
    visitors_24h = db_visitors + cur_hour_visitors
    result = {"total": int(row["total"]), "likes": int(row["likes"]), "visitors_24h": visitors_24h}
    cache_set("stats", json.dumps(result), ttl=30)
    return result

@app.get("/api/colors")
def get_colors(request: Request):
    ip = _get_ip(request)
    if not _rl.check(f"pub:{ip}", 60, 60):
        raise HTTPException(429, "Забагато запитів. Зачекайте.")
    cached = cache_get("colors")
    if cached:
        return json.loads(cached)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT `key`, value, label FROM colors")
        rows = c.fetchall()
    db.close()
    result = {}
    for r in rows:
        # smtp_pass не повертаємо публічно — замість нього булевий флаг
        if r["key"] == "smtp_pass":
            result["smtp_pass_set"] = {"value": "1" if r["value"] else "0", "label": ""}
        else:
            result[r["key"]] = {"value": r["value"], "label": r["label"]}
    cache_set("colors", json.dumps(result, ensure_ascii=False), ttl=300)
    return result

@app.get("/api/labels")
def get_labels(request: Request):
    ip = _get_ip(request)
    if not _rl.check(f"pub:{ip}", 60, 60):
        raise HTTPException(429, "Забагато запитів. Зачекайте.")
    cached = cache_get("labels")
    if cached:
        return json.loads(cached)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM map_labels ORDER BY id")
        rows = c.fetchall()
    db.close()
    cache_set("labels", json.dumps(rows, ensure_ascii=False), ttl=300)
    return rows

@app.get("/api/cities")
def get_cities(request: Request):
    ip = _get_ip(request)
    if not _rl.check(f"pub:{ip}", 60, 60):
        raise HTTPException(429, "Забагато запитів. Зачекайте.")
    cached = cache_get("cities")
    if cached:
        return json.loads(cached)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id,name,pos_x,pos_y,tier,color FROM cities WHERE pos_x > 0 ORDER BY tier DESC, name")
        rows = c.fetchall()
    db.close()
    cache_set("cities", json.dumps(rows, ensure_ascii=False), ttl=300)
    return rows

@app.get("/api/admin/cities")
def admin_get_cities(request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id,name,pos_x,pos_y,tier,color FROM cities ORDER BY name")
        rows = c.fetchall()
    db.close()
    return rows

@app.put("/api/admin/city/{cid}")
def admin_update_city(cid: int, u: CityUpdate, request: Request):
    require_admin(request)
    fields, vals = [], []
    if u.name  is not None: fields.append("name=%s");  vals.append(u.name[:100])
    if u.pos_x is not None: fields.append("pos_x=%s"); vals.append(u.pos_x)
    if u.pos_y is not None: fields.append("pos_y=%s"); vals.append(u.pos_y)
    if u.tier  is not None: fields.append("tier=%s");  vals.append(u.tier)
    if u.color is not None: fields.append("color=%s"); vals.append(u.color[:20])
    if not fields:
        raise HTTPException(400, "Нічого оновлювати")
    vals.append(cid)
    db = get_db()
    with db.cursor() as c:
        c.execute(f"UPDATE cities SET {','.join(fields)} WHERE id=%s", vals)
    db.commit(); db.close()
    cache_delete("cities")
    return {"ok": True}

@app.post("/api/admin/city")
def admin_create_city(u: CityCreate, request: Request):
    require_admin(request)
    name = u.name.strip()[:100]
    if not name:
        raise HTTPException(400, "Назва міста обов'язкова")
    color = u.color or '#a0d7ff'
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO cities (name, tier, color, pos_x, pos_y) VALUES (%s,%s,%s,0,0)",
            (name, u.tier or 0, color[:20])
        )
        new_id = c.lastrowid
    db.commit(); db.close()
    cache_delete("cities")
    return {"ok": True, "id": new_id}

@app.delete("/api/admin/city/{cid}")
def admin_delete_city(cid: int, request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("DELETE FROM cities WHERE id=%s", (cid,))
    db.commit(); db.close()
    cache_delete("cities")
    return {"ok": True}

# ── Partners / Friends ────────────────────────────────────────────────────────

@app.get("/api/partners")
def get_partners():
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM partners WHERE is_visible=1 ORDER BY sort_order, id")
            return c.fetchall()
    finally:
        db.close()

@app.get("/api/admin/partners")
def admin_get_partners(request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM partners ORDER BY sort_order, id")
            return c.fetchall()
    finally:
        db.close()

@app.post("/api/admin/partner")
def admin_create_partner(u: PartnerCreate, request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "INSERT INTO partners (name,image_url,link_url,caption,width,opacity,pos_x,pos_y,is_visible,sort_order)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    _sanitize_text(u.name)[:100],
                    u.image_url[:500],
                    u.link_url[:500],
                    _sanitize_text(u.caption)[:200],
                    max(20, min(800, u.width)),
                    round(max(0.0, min(1.0, u.opacity)), 2),
                    u.pos_x, u.pos_y, u.is_visible, u.sort_order,
                )
            )
            new_id = c.lastrowid
        db.commit()
        return {"ok": True, "id": new_id}
    finally:
        db.close()

@app.put("/api/admin/partner/{pid}")
def admin_update_partner(pid: int, u: PartnerUpdate, request: Request):
    require_admin(request)
    fields, vals = [], []
    if u.name is not None:       fields.append("name=%s");       vals.append(_sanitize_text(u.name)[:100])
    if u.image_url is not None:  fields.append("image_url=%s");  vals.append(u.image_url[:500])
    if u.link_url is not None:   fields.append("link_url=%s");   vals.append(u.link_url[:500])
    if u.caption is not None:    fields.append("caption=%s");    vals.append(_sanitize_text(u.caption)[:200])
    if u.width is not None:      fields.append("width=%s");      vals.append(max(20, min(800, u.width)))
    if u.opacity is not None:    fields.append("opacity=%s");    vals.append(round(max(0.0, min(1.0, u.opacity)), 2))
    if u.pos_x is not None:      fields.append("pos_x=%s");      vals.append(u.pos_x)
    if u.pos_y is not None:      fields.append("pos_y=%s");      vals.append(u.pos_y)
    if u.is_visible is not None: fields.append("is_visible=%s"); vals.append(u.is_visible)
    if u.sort_order is not None: fields.append("sort_order=%s"); vals.append(u.sort_order)
    if not fields:
        raise HTTPException(400, "Нічого оновлювати")
    vals.append(pid)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(f"UPDATE partners SET {','.join(fields)} WHERE id=%s", vals)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@app.delete("/api/admin/partner/{pid}")
def admin_delete_partner(pid: int, request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM partners WHERE id=%s", (pid,))
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@app.post("/api/people")
def add_person(p: PersonIn, request: Request):
    ip = _get_ip(request)
    # 5 заявок / год з одного IP
    if not _rl.check(f"addperson:{ip}", 5, 3600):
        raise HTTPException(429, "Забагато заявок. Спробуйте пізніше.")
    # Базова валідація довжин
    if not p.last.strip() or len(p.last) > 100:
        raise HTTPException(400, "Прізвище обов'язкове (макс. 100 символів)")
    if not p.first.strip() or len(p.first) > 100:
        raise HTTPException(400, "Ім'я обов'язкове (макс. 100 символів)")
    if p.descr and len(p.descr) > 5000:
        raise HTTPException(400, "Опис занадто довгий (макс. 5000 символів)")
    photo     = _validate_photo_url(p.photo or '')
    color     = _validate_color(p.color or '')
    video_url = _validate_yt_url(p.video_url or '')
    birth     = _validate_date(p.birth)
    death     = _validate_date(p.death)
    last  = _sanitize_text(p.last,  100)
    first = _sanitize_text(p.first, 100)
    mid   = _sanitize_text(p.mid or '', 100)
    loc   = _sanitize_text(p.loc or '', 300)
    bury  = _sanitize_text(p.bury or '', 300)
    circ  = _sanitize_text(p.circ or '', 200)
    grp   = _sanitize_text(p.grp or '', 100)
    rank  = _sanitize_text(p.rank or '', 100)
    pos   = _sanitize_text(p.position or '', 100)
    unit  = _sanitize_text(p.unit or '', 200)
    descr = (p.descr or '')[:5000]
    # Якщо передано world_lat/lng — автообчислити pos_x/pos_y
    pos_x, pos_y = p.pos_x, p.pos_y
    world_lat = p.world_lat
    world_lng = p.world_lng
    if world_lat is not None and world_lng is not None:
        pos_x, pos_y = _latLngToSvg(world_lat, world_lng)
    db = get_db()
    with db.cursor() as c:
        c.execute("""
            INSERT INTO memorials
            (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,video_url,`rank`,`position`,`unit`,pos_x,pos_y,world_lat,world_lng,grp,added_by,approved)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
        """, (last, first, mid, birth, death, loc, bury,
              circ, descr, photo, color, video_url,
              rank, pos, unit,
              pos_x, pos_y, world_lat, world_lng, grp, p.added_by))
        new_id = c.lastrowid
        for aw in p.awards[:10]:
            aw_name = _sanitize_text(aw.name, 200)
            aw_file = (aw.img_file or '')[:300]
            aw_cat  = (aw.category or '')[:30]
            if aw_name:
                c.execute(
                    "INSERT INTO memorial_awards (memorial_id,name,img_file,category,sort_order) VALUES (%s,%s,%s,%s,0)",
                    (new_id, aw_name, aw_file, aw_cat)
                )
    db.commit()
    db.close()
    return {"ok": True, "id": new_id, "message": "Надіслано на модерацію. Дякуємо!"}

@app.post("/api/like/{mid}")
def like(mid: int, fp: Optional[str] = "anon", request: Request = None):
    ip = _get_ip(request) if request else "unknown"
    # 60 лайків / год з одного IP (проти накрутки)
    if not _rl.check(f"like:{ip}", 60, 3600):
        raise HTTPException(429, "Забагато лайків з одного IP. Зачекайте.")
    now = int(time.time())
    fp  = (fp or "anon")[:64]
    db  = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT COUNT(*) AS cnt FROM likes_log WHERE memorial_id=%s AND fingerprint=%s AND ts>%s",
                (mid, fp, now - 2)
            )
            if c.fetchone()["cnt"]:
                return {"ok": False, "reason": "cooldown"}
            c.execute(
                "INSERT INTO likes_log (memorial_id,fingerprint,ts) VALUES (%s,%s,%s)",
                (mid, fp, now)
            )
            c.execute("UPDATE memorials SET likes=likes+1 WHERE id=%s", (mid,))
            db.commit()
            c.execute("SELECT likes FROM memorials WHERE id=%s", (mid,))
            row = c.fetchone()
    finally:
        db.close()
    cache_delete("stats")  # likes changed
    return {"ok": True, "likes": row["likes"] if row else 0}

def _validate_reg_fields(u) -> dict:
    """Спільна валідація полів реєстрації. Повертає dict підготовлених даних."""
    if _get_color_val("reg_enabled", "1") != "1":
        raise HTTPException(403, "Реєстрація тимчасово закрита")
    if not u.terms_agreed:
        raise HTTPException(400, "Необхідно погодитись з умовами використання")
    last  = _sanitize_text(u.last_name.strip(),  100)
    first = _sanitize_text(u.first_name.strip(), 100)
    if len(last) < 2:  raise HTTPException(400, "Прізвище: мінімум 2 символи")
    if len(first) < 2: raise HTTPException(400, "Ім'я: мінімум 2 символи")
    # По батькові — залежно від налаштування
    field_mid = _get_color_val("reg_field_mid", "required")
    mid = _sanitize_text(u.middle_name.strip(), 100)
    if field_mid == "required" and len(mid) < 2:
        raise HTTPException(400, "По батькові: мінімум 2 символи")
    if field_mid == "hidden":
        mid = ""
    nick  = u.nickname.strip()
    if not _NICK_RE.match(nick):
        raise HTTPException(400, "Нік: 2–50 символів, літери (укр/лат), цифри, _ . -")
    if len(u.email) > 120 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', u.email):
        raise HTTPException(400, "Невірний формат email")
    # Телефон — залежно від налаштування
    field_phone = _get_color_val("reg_field_phone", "optional")
    phone = ""
    if field_phone != "hidden" and u.phone.strip():
        digits = re.sub(r'\D', '', u.phone)
        if digits.startswith('0') and len(digits) == 10:  digits = '38' + digits
        if digits.startswith('8') and len(digits) == 11:  digits = '3' + digits
        if not _PHONE_RE.match(digits):
            raise HTTPException(400, "Телефон: формат +380XXXXXXXXX або 0XXXXXXXXX")
        phone = f"+{digits}"
    elif field_phone == "required" and not u.phone.strip():
        raise HTTPException(400, "Номер телефону обов'язковий")
    # Пароль — мінімальна довжина з налаштувань
    try:
        min_len = max(8, min(20, int(_get_color_val("reg_min_pass_len", "10") or "10")))
    except ValueError:
        min_len = 10
    if len(u.password) < min_len:
        raise HTTPException(400, f"Пароль: мінімум {min_len} символів")
    _validate_password(u.password)
    name_parts = [last, first, mid] if mid else [last, first]
    return {"last": last, "first": first, "mid": mid, "nick": nick,
            "email": u.email.lower(), "phone": phone,
            "name": " ".join(name_parts)}


@app.post("/api/auth/send-code")
def send_code(u: SendCodeReq, request: Request):
    """Крок 1: валідує дані, надсилає 6-значний код підтвердження на email."""
    ip = _get_ip(request)
    # Валідація полів ПЕРЕД рейт-лімітером — помилки заповнення не спалюють ліміт
    data = _validate_reg_fields(u)
    if not _rl.check(f"reg_send:{ip}", 10, 3600):
        raise HTTPException(429, "Забагато запитів. Зачекайте годину.")
    email_key = f"reg_send_email:{data['email']}"
    if not _rl.check(email_key, 3, 600):
        raise HTTPException(429, "Код вже надіслано. Перевірте пошту або зачекайте 10 хвилин.")
    # Перевіряємо унікальність email і ніку ДО відправки листа
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id FROM users WHERE email=%s", (data["email"],))
        if c.fetchone():
            db.close()
            raise HTTPException(400, "Email вже зареєстрований")
        c.execute("SELECT id FROM users WHERE nickname=%s", (data["nick"],))
        if c.fetchone():
            db.close()
            raise HTTPException(400, "Цей нік вже зайнятий")
    db.close()
    # Якщо підтвердження email вимкнено — реєструємо одразу без коду
    if _get_color_val("reg_require_email_verify", "1") == "0":
        pw_hash = hash_pass(u.password)
        db2 = get_db()
        with db2.cursor() as c:
            c.execute(
                "INSERT INTO users (name,first_name,last_name,middle_name,nickname,email,phone,password,role)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'user')",
                (data["name"], data["first"], data["last"], data["mid"],
                 data["nick"], data["email"], data["phone"], pw_hash)
            )
            db2.commit()
            c.execute(
                "SELECT id,name,first_name,last_name,middle_name,nickname,email,phone,role"
                " FROM users WHERE email=%s", (data["email"],)
            )
            row = c.fetchone()
        db2.close()
        welcome = _get_color_val("reg_welcome_msg", "Вітаємо!")
        sec_log("REGISTER_DIRECT", ip, f"email={data['email']} nick={data['nick']}")
        token = _session_create(row["id"])
        resp = JSONResponse({"ok": True, "registered": True, "user": row, "welcome": welcome})
        resp.set_cookie(key="admin_session", value=token, httponly=True,
                        secure=_IS_PROD, samesite="lax", max_age=86400 * 7, path="/")
        return resp
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    pw_hash = hash_pass(u.password)  # хешуємо пароль одразу
    with _pending_reg_lock:
        _pending_cleanup()
        _pending_reg[data["email"]] = {
            "code":     code,
            "pw_hash":  pw_hash,
            "data":     data,
            "expires":  time.time() + _PENDING_TTL,
            "attempts": 0,
        }
    html_body = _email_verification_html(code, data["nick"])
    ok, err = _send_email(data["email"], "Код підтвердження реєстрації — Зоряна Пам'ять", html_body)
    if not ok:
        # Dev-режим: повертаємо code у відповіді якщо SMTP не налаштований
        _c = _get_smtp_config()
        smtp_configured = bool(_c["host"] and _c["user"] and _c["enabled"] != "0")
        if not smtp_configured:
            sec_log("REG_CODE_DEV", ip, f"email={data['email']} code={code}")
            return {"ok": True, "dev": True, "code": code,
                    "message": "SMTP не налаштований — код повернуто для тестування"}
        raise HTTPException(503, f"Не вдалось надіслати лист: {err}")
    sec_log("REG_CODE_SENT", ip, f"email={data['email']}")
    return {"ok": True, "message": "Код підтвердження надіслано на вашу пошту"}


@app.post("/api/auth/register")
def register(u: UserReg, request: Request):
    """Крок 2: перевіряє код і створює акаунт."""
    ip = _get_ip(request)
    if not _rl.check(f"reg_verify:{ip}", 10, 300):
        raise HTTPException(429, "Забагато спроб. Зачекайте.")
    email = u.email.lower().strip()
    code  = u.code.strip()
    with _pending_reg_lock:
        pending = _pending_reg.get(email)
        if not pending:
            raise HTTPException(400, "Код не знайдено або минув термін дії (10 хв). Почніть реєстрацію знову.")
        if time.time() > pending["expires"]:
            del _pending_reg[email]
            raise HTTPException(400, "Термін дії коду минув. Натисніть 'Надіслати повторно'.")
        pending["attempts"] += 1
        if pending["attempts"] > _PENDING_MAX_ATTEMPTS:
            del _pending_reg[email]
            raise HTTPException(400, "Перевищено ліміт спроб. Почніть реєстрацію знову.")
        if pending["code"] != code:
            left = _PENDING_MAX_ATTEMPTS - pending["attempts"]
            raise HTTPException(400, f"Невірний код. Залишилось спроб: {left}")
        # Код вірний — беремо дані та видаляємо pending
        reg_data = pending["data"]
        pw_hash  = pending["pw_hash"]
        del _pending_reg[email]
    # Ще раз перевіряємо унікальність (race condition guard)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id FROM users WHERE email=%s", (email,))
        if c.fetchone():
            db.close()
            raise HTTPException(400, "Email вже зареєстрований")
        c.execute("SELECT id FROM users WHERE nickname=%s", (reg_data["nick"],))
        if c.fetchone():
            db.close()
            raise HTTPException(400, "Цей нік вже зайнятий")
        c.execute(
            "INSERT INTO users (name,first_name,last_name,middle_name,nickname,email,phone,password,role)"
            " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'user')",
            (reg_data["name"], reg_data["first"], reg_data["last"], reg_data["mid"],
             reg_data["nick"], email, reg_data["phone"], pw_hash)
        )
        db.commit()
        c.execute(
            "SELECT id,name,first_name,last_name,middle_name,nickname,email,phone,role"
            " FROM users WHERE email=%s", (email,)
        )
        row = c.fetchone()
    db.close()
    sec_log("REGISTER", ip, f"email={email} nick={reg_data['nick']}")
    token = _session_create(row["id"])
    resp = JSONResponse({"ok": True, "user": row})
    resp.set_cookie(key="admin_session", value=token, httponly=True,
                    secure=_IS_PROD, samesite="lax", max_age=86400 * 7, path="/")
    return resp

@app.post("/api/auth/login")
def login(u: UserLogin, request: Request):
    ip = _get_ip(request)

    # IP-rate-limit: 10 спроб / 5 хв
    if not _rl.check(f"login_ip:{ip}", 10, 300):
        sec_log("LOGIN_RATE_LIMIT", ip, f"email={u.email[:50]}")
        raise HTTPException(429, "Забагато спроб входу. Зачекайте 5 хвилин.")

    # Lockout по email+IP після 5 невдалих спроб
    if _is_locked(ip, u.email):
        sec_log("LOGIN_LOCKOUT", ip, f"email={u.email[:50]}")
        raise HTTPException(429, "Акаунт тимчасово заблоковано через підозрілу активність. Зачекайте 15 хвилин.")

    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,email,is_admin,is_banned,ban_until,password,role FROM users WHERE email=%s",
            (u.email.lower(),)
        )
        row = c.fetchone()
    if not row or not verify_pass(u.password, row["password"]):
        if row:
            db.close()
        _record_fail(ip, u.email)
        sec_log("LOGIN_FAIL", ip, f"email={u.email[:50]}")
        raise HTTPException(401, "Невірний email або пароль")
    if row["is_banned"]:
        bu = row.get("ban_until") or 0
        now_ts = int(time.time())
        if bu > 0 and bu <= now_ts:
            # temp ban expired — auto-unban
            with db.cursor() as c:
                c.execute("UPDATE users SET is_banned=0, ban_until=0 WHERE id=%s", (row["id"],))
            db.commit()
        else:
            db.close()
            if bu > 0:
                rem = bu - now_ts
                raise HTTPException(403, f"Акаунт тимчасово заблоковано. Залишилось: {rem // 3600}г {(rem % 3600) // 60}хв")
            raise HTTPException(403, "Акаунт заблоковано")
    _clear_fails(ip, u.email)
    stored_hash = row["password"]
    with db.cursor() as c:
        c.execute("UPDATE users SET last_seen=%s WHERE email=%s",
                  (int(time.time()), u.email.lower()))
        # Lazy migration: якщо пароль ще SHA256 — одразу оновлюємо до bcrypt
        if _is_sha256_hash(stored_hash):
            c.execute("UPDATE users SET password=%s WHERE email=%s",
                      (hash_pass(u.password), u.email.lower()))
    db.commit()
    db.close()
    row = _safe_user(row)
    token = _session_create(row["id"])
    resp = JSONResponse({"ok": True, "user": row})
    resp.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=_IS_PROD,
        samesite="lax",
        max_age=86400 * 7,
        path="/",
    )
    return resp


@app.post("/api/auth/logout")
def logout(request: Request):
    token = request.cookies.get("admin_session")
    if token:
        _session_delete(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("admin_session", path="/")
    return resp


@app.get("/api/auth/me")
def auth_me(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(401, "Не авторизовано")
    sess = _session_get(token)
    if not sess:
        raise HTTPException(401, "Сесія застаріла")
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,first_name,last_name,middle_name,nickname,email,phone,is_admin,role"
            " FROM users WHERE id=%s", (sess["user_id"],)
        )
        row = c.fetchone()
    db.close()
    if not row:
        raise HTTPException(401, "Користувача не знайдено")
    return {"ok": True, "user": row}


@app.put("/api/auth/profile")
def update_profile(u: UserProfileUpdate, request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(401, "Не авторизовано")
    sess = _session_get(token)
    if not sess:
        raise HTTPException(401, "Сесія застаріла")
    user_id = sess["user_id"]
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,first_name,last_name,middle_name,nickname,email,phone,password,role"
            " FROM users WHERE id=%s", (user_id,)
        )
        cur = c.fetchone()
    if not cur:
        db.close()
        raise HTTPException(404, "Користувача не знайдено")
    updates = {}
    # nickname
    if u.nickname is not None:
        nick = u.nickname.strip()
        if not _NICK_RE.match(nick):
            db.close()
            raise HTTPException(400, "Нік: 2–50 символів, літери (укр/лат), цифри, _ . -")
        with db.cursor() as c:
            c.execute("SELECT id FROM users WHERE nickname=%s AND id!=%s", (nick, user_id))
            if c.fetchone():
                db.close()
                raise HTTPException(400, "Цей нік вже зайнятий")
        updates["nickname"] = nick
    # email
    if u.email is not None:
        if u.email != u.email_confirm:
            db.close()
            raise HTTPException(400, "Email адреси не збігаються")
        if len(u.email) > 120 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', u.email):
            db.close()
            raise HTTPException(400, "Невірний формат email")
        with db.cursor() as c:
            c.execute("SELECT id FROM users WHERE email=%s AND id!=%s", (u.email.lower(), user_id))
            if c.fetchone():
                db.close()
                raise HTTPException(400, "Email вже зареєстрований")
        updates["email"] = u.email.lower()
    # phone
    if u.phone is not None:
        if u.phone.strip():
            digits = re.sub(r'\D', '', u.phone)
            if digits.startswith('0') and len(digits) == 10:
                digits = '38' + digits
            if digits.startswith('8') and len(digits) == 11:
                digits = '3' + digits
            if not _PHONE_RE.match(digits):
                db.close()
                raise HTTPException(400, "Телефон: формат +380XXXXXXXXX або 0XXXXXXXXX")
            updates["phone"] = f"+{digits}"
        else:
            updates["phone"] = ""
    # password
    if u.password:
        if not verify_pass(u.old_password or "", cur["password"]):
            db.close()
            raise HTTPException(400, "Поточний пароль невірний")
        _validate_password(u.password)
        updates["password"] = hash_pass(u.password)
    if not updates:
        db.close()
        return {"ok": True, "user": cur}
    # При зміні ніку — зберегти старий в aliases
    if "nickname" in updates:
        old_nick = cur.get("nickname")
        new_nick = updates["nickname"]
        if old_nick and old_nick != new_nick:
            with db.cursor() as c:
                c.execute(
                    "INSERT IGNORE INTO user_nickname_aliases (user_id, old_nickname, created_at)"
                    " VALUES (%s, %s, UNIX_TIMESTAMP())",
                    (user_id, old_nick)
                )
                # Новий нік звільняємо з aliases (якщо хтось раніше мав його як старий)
                c.execute("DELETE FROM user_nickname_aliases WHERE old_nickname=%s", (new_nick,))
    cols = ", ".join(f"`{k}`=%s" for k in updates)
    vals = list(updates.values()) + [user_id]
    with db.cursor() as c:
        c.execute(f"UPDATE users SET {cols} WHERE id=%s", vals)
    db.commit()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,first_name,last_name,middle_name,nickname,email,phone,role"
            " FROM users WHERE id=%s", (user_id,)
        )
        row = c.fetchone()
    db.close()
    return {"ok": True, "user": row}


# ══════════════════════════════════════════════════════════════
# МОДУЛЬ «СПАДЩИНА ПАМ'ЯТІ» — Legacy Module
# ══════════════════════════════════════════════════════════════

# ── Pydantic моделі ──────────────────────────────────────────

class LegacyContentBody(BaseModel):
    memory_photo:       Optional[str] = None
    epitaph:            Optional[str] = None
    biography:          Optional[str] = None
    final_message:      Optional[str] = None
    video_url:          Optional[str] = None
    wishes:             Optional[str] = None
    family_advice:      Optional[str] = None
    instructions:       Optional[str] = None
    achievements:       Optional[str] = None
    publish_all:        Optional[int] = None
    allow_bio_edit:     Optional[int] = None
    allow_memories:     Optional[int] = None
    allow_new_photos:   Optional[int] = None
    lock_after_memorial:Optional[int] = None

class LegacyTrustedBody(BaseModel):
    nickname: str

class LegacyTrustedRespondBody(BaseModel):
    action: str  # 'confirm' | 'reject'

class LegacyLockWillBody(BaseModel):
    password: str

class LegacyReportDeathBody(BaseModel):
    death_date: Optional[str] = None
    comment:    Optional[str] = None

class LegacySettingsBody(BaseModel):
    legacy_enabled:  Optional[str] = None
    legacy_price:    Optional[str] = None
    legacy_currency: Optional[str] = None
    legacy_refund:   Optional[str] = None

class LegacyActivateBody(BaseModel):
    notes: Optional[str] = None

class LegacyRequestUpdateBody(BaseModel):
    status:      str          # 'review' | 'confirmed' | 'rejected'
    mod_comment: Optional[str] = None

# ── Допоміжні функції ────────────────────────────────────────

def _legacy_log(user_id, action: str, request: Request, metadata=None):
    db = get_db()
    try:
        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")[:300]
        meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else None
        ts = int(time.time())
        with db.cursor() as c:
            c.execute(
                "INSERT INTO legacy_logs (user_id,action,ip,browser,metadata,created_at)"
                " VALUES (%s,%s,%s,%s,%s,%s)",
                (user_id, action, ip, ua, meta_str, ts)
            )
        db.commit()
    finally:
        db.close()

def _is_legacy_active(user_id: int, c) -> bool:
    c.execute("SELECT activated FROM legacy_accounts WHERE user_id=%s AND activated=1", (user_id,))
    return bool(c.fetchone())

def _get_legacy_session(request: Request):
    token = request.cookies.get("admin_session")
    if not token:
        raise HTTPException(401, "Потрібна авторизація")
    sess = _session_get(token)
    if not sess:
        raise HTTPException(401, "Сесія закінчилась")
    return sess

# ── ПУБЛІЧНІ ЕНДПОІНТИ (для власника) ───────────────────────

@app.get("/api/legacy/status")
def legacy_status(request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    price    = _get_color_val("legacy_price", "82")
    currency = _get_color_val("legacy_currency", "USD")
    enabled  = _get_color_val("legacy_enabled", "1")
    db = get_db()
    try:
        with db.cursor() as c:
            published = _is_legacy_active(uid, c)  # чи сплачено публікацію
            c.execute("SELECT * FROM legacy_accounts WHERE user_id=%s", (uid,))
            acc = c.fetchone()
            # Перевіряємо чи є незвітований запит для довіреної особи
            c.execute(
                "SELECT ltc.id, u.nickname as owner_nick, u.first_name, u.last_name"
                " FROM legacy_trusted_contacts ltc"
                " JOIN users u ON u.id=ltc.user_id"
                " WHERE ltc.trusted_user_id=%s AND ltc.status='pending'",
                (uid,)
            )
            pending_invite = c.fetchone()
    finally:
        db.close()
    return {
        "enabled":        enabled == "1",
        "active":         True,       # форма завжди доступна
        "published":      published,  # чи сплачена публікація картки
        "price":          price,
        "currency":       currency,
        "account":        acc,
        "pending_invite": pending_invite,
    }


@app.get("/api/legacy/content")
def legacy_get_content(request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM legacy_content WHERE user_id=%s", (uid,))
            row = c.fetchone()
    finally:
        db.close()
    return row or {}


@app.put("/api/legacy/content")
def legacy_save_content(body: LegacyContentBody, request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id, will_locked FROM legacy_content WHERE user_id=%s", (uid,))
            existing = c.fetchone()
            if existing and existing.get("will_locked"):
                raise HTTPException(403, "Воля зафіксована — редагування заблоковано")
        ts = int(time.time())
        fields = {k: v for k, v in body.dict().items() if v is not None}
        if not fields:
            return {"ok": True}
        # Валідація
        if "epitaph" in fields and len(fields["epitaph"]) > 300:
            raise HTTPException(400, "Епітафія — максимум 300 символів")
        if "memory_photo" in fields:
            fields["memory_photo"] = _html.escape(fields["memory_photo"])
        if "video_url" in fields:
            fields["video_url"] = _html.escape(fields["video_url"])
        for tf in ("biography","final_message","wishes","family_advice","instructions","achievements","epitaph"):
            if tf in fields:
                fields[tf] = _sanitize_text(fields[tf])
        with db.cursor() as c:
            c.execute("SELECT id FROM legacy_content WHERE user_id=%s", (uid,))
            ex = c.fetchone()
            if ex:
                cols = ", ".join(f"`{k}`=%s" for k in fields)
                vals = list(fields.values())
                c.execute(f"UPDATE legacy_content SET {cols}, updated_at=%s WHERE user_id=%s",
                          vals + [ts, uid])
            else:
                fields["user_id"] = uid
                fields["created_at"] = ts
                fields["updated_at"] = ts
                cols = ", ".join(f"`{k}`" for k in fields)
                phs  = ", ".join(["%s"] * len(fields))
                c.execute(f"INSERT INTO legacy_content ({cols}) VALUES ({phs})",
                          list(fields.values()))
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, "content_saved", request)
    return {"ok": True}


@app.get("/api/legacy/trusted")
def legacy_get_trusted(request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT ltc.*, u.nickname, u.first_name, u.last_name"
                " FROM legacy_trusted_contacts ltc"
                " JOIN users u ON u.id=ltc.trusted_user_id"
                " WHERE ltc.user_id=%s",
                (uid,)
            )
            row = c.fetchone()
    finally:
        db.close()
    return row or {}


@app.post("/api/legacy/trusted")
def legacy_set_trusted(body: LegacyTrustedBody, request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    nick = _sanitize_text(body.nickname.strip())
    if not nick:
        raise HTTPException(400, "Нікнейм не вказано")
    db = get_db()
    try:
        with db.cursor() as c:
            # Знаходимо довірену особу за ніком
            c.execute("SELECT id, nickname FROM users WHERE nickname=%s AND is_banned=0", (nick,))
            trusted_user = c.fetchone()
            if not trusted_user:
                raise HTTPException(404, f"Користувача «{nick}» не знайдено")
            if trusted_user["id"] == uid:
                raise HTTPException(400, "Не можна призначити себе довіреною особою")
            ts = int(time.time())
            c.execute(
                "INSERT INTO legacy_trusted_contacts (user_id, trusted_user_id, status, created_at, updated_at)"
                " VALUES (%s,%s,'pending',%s,%s)"
                " ON DUPLICATE KEY UPDATE trusted_user_id=%s, status='pending', updated_at=%s",
                (uid, trusted_user["id"], ts, ts, trusted_user["id"], ts)
            )
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, "trusted_invited", request, {"trusted_nick": nick})
    return {"ok": True}


@app.delete("/api/legacy/trusted")
def legacy_remove_trusted(request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM legacy_trusted_contacts WHERE user_id=%s", (uid,))
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, "trusted_removed", request)
    return {"ok": True}


@app.post("/api/legacy/trusted/respond")
def legacy_trusted_respond(body: LegacyTrustedRespondBody, request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    if body.action not in ("confirm", "reject"):
        raise HTTPException(400, "action має бути confirm або reject")
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute(
                "SELECT id FROM legacy_trusted_contacts WHERE trusted_user_id=%s AND status='pending'",
                (uid,)
            )
            row = c.fetchone()
            if not row:
                raise HTTPException(404, "Запрошення не знайдено")
            ts = int(time.time())
            if body.action == "confirm":
                c.execute(
                    "UPDATE legacy_trusted_contacts SET status='confirmed', confirmed_at=%s, updated_at=%s"
                    " WHERE id=%s",
                    (ts, ts, row["id"])
                )
            else:
                c.execute(
                    "UPDATE legacy_trusted_contacts SET status='rejected', updated_at=%s WHERE id=%s",
                    (ts, row["id"])
                )
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, f"trusted_{body.action}ed", request)
    return {"ok": True}


@app.post("/api/legacy/lock-will")
def legacy_lock_will(body: LegacyLockWillBody, request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            # Перевіряємо пароль
            c.execute("SELECT password FROM users WHERE id=%s", (uid,))
            u = c.fetchone()
            if not u or not verify_pass(body.password, u["password"]):
                raise HTTPException(400, "Невірний пароль")
            ts = int(time.time())
            c.execute("SELECT id FROM legacy_content WHERE user_id=%s", (uid,))
            ex = c.fetchone()
            if ex:
                c.execute(
                    "UPDATE legacy_content SET will_locked=1, will_locked_at=%s, updated_at=%s WHERE user_id=%s",
                    (ts, ts, uid)
                )
            else:
                c.execute(
                    "INSERT INTO legacy_content (user_id,will_locked,will_locked_at,created_at,updated_at)"
                    " VALUES (%s,1,%s,%s,%s)",
                    (uid, ts, ts, ts)
                )
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, "will_locked", request)
    return {"ok": True}


@app.post("/api/legacy/unlock-will")
def legacy_unlock_will(body: LegacyLockWillBody, request: Request):
    sess = _get_legacy_session(request)
    uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT password FROM users WHERE id=%s", (uid,))
            u = c.fetchone()
            if not u or not verify_pass(body.password, u["password"]):
                raise HTTPException(400, "Невірний пароль")
            ts = int(time.time())
            c.execute(
                "UPDATE legacy_content SET will_locked=0, updated_at=%s WHERE user_id=%s",
                (ts, uid)
            )
        db.commit()
    finally:
        db.close()
    _legacy_log(uid, "will_unlocked", request)
    return {"ok": True}


@app.post("/api/legacy/report-death")
def legacy_report_death(body: LegacyReportDeathBody, request: Request):
    sess = _get_legacy_session(request)
    trusted_uid = sess["user_id"]
    db = get_db()
    try:
        with db.cursor() as c:
            # Перевіряємо чи ця людина є підтвердженою довіреною особою
            c.execute(
                "SELECT user_id FROM legacy_trusted_contacts"
                " WHERE trusted_user_id=%s AND status='confirmed'",
                (trusted_uid,)
            )
            tc = c.fetchone()
            if not tc:
                raise HTTPException(403, "Ви не є підтвердженою довіреною особою")
            owner_id = tc["user_id"]
            # Перевіряємо чи немає вже активної заявки
            c.execute(
                "SELECT id FROM legacy_requests WHERE user_id=%s AND status IN ('new','review')",
                (owner_id,)
            )
            if c.fetchone():
                raise HTTPException(400, "Заявка вже подана і розглядається")
            ts = int(time.time())
            comment = _sanitize_text(body.comment or "")[:1000]
            c.execute(
                "INSERT INTO legacy_requests"
                " (user_id, trusted_user_id, status, death_date, comment, created_at, updated_at)"
                " VALUES (%s,%s,'new',%s,%s,%s,%s)",
                (owner_id, trusted_uid, body.death_date, comment, ts, ts)
            )
        db.commit()
    finally:
        db.close()
    _legacy_log(trusted_uid, "death_reported", request, {"owner_id": owner_id})
    return {"ok": True}


# ── АДМІН ЕНДПОІНТИ ─────────────────────────────────────────

@app.get("/api/admin/legacy/settings")
def adm_legacy_settings(request: Request):
    require_admin(request)
    return {
        "legacy_enabled":  _get_color_val("legacy_enabled", "1"),
        "legacy_price":    _get_color_val("legacy_price", "82"),
        "legacy_currency": _get_color_val("legacy_currency", "USD"),
        "legacy_refund":   _get_color_val("legacy_refund", "0"),
    }


@app.put("/api/admin/legacy/settings")
def adm_legacy_save_settings(body: LegacySettingsBody, request: Request):
    require_admin(request)
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"ok": True}
    db = get_db()
    try:
        with db.cursor() as c:
            for k, v in updates.items():
                c.execute(
                    "INSERT INTO colors (`key`,value) VALUES (%s,%s)"
                    " ON DUPLICATE KEY UPDATE value=%s",
                    (k, v, v)
                )
        db.commit()
    finally:
        db.close()
    return {"ok": True}


@app.get("/api/admin/legacy/accounts")
def adm_legacy_accounts(request: Request, page: int = 1, limit: int = 50):
    require_admin(request)
    limit = max(1, min(limit, 200))
    offset = (page - 1) * limit
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT COUNT(*) as cnt FROM legacy_accounts")
            total = c.fetchone()["cnt"]
            c.execute(
                "SELECT la.id, la.user_id, la.payment_amount, la.payment_currency,"
                " la.activated_at, la.activated_by_admin, la.notes,"
                " u.nickname, u.first_name, u.last_name, u.email"
                " FROM legacy_accounts la"
                " JOIN users u ON u.id=la.user_id"
                " ORDER BY la.activated_at DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
            rows = c.fetchall()
    finally:
        db.close()
    return {"total": total, "items": rows}


@app.post("/api/admin/legacy/activate/{uid}")
def adm_legacy_activate(uid: int, body: LegacyActivateBody, request: Request):
    require_admin(request)
    sess = _get_legacy_session(request)
    admin_id = sess["user_id"]
    notes = _sanitize_text(body.notes or "", 200)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM users WHERE id=%s", (uid,))
            if not c.fetchone():
                raise HTTPException(404, "Користувача не знайдено")
            ts = int(time.time())
            c.execute(
                "INSERT INTO legacy_accounts"
                " (user_id, activated_at, activated_by_admin, notes)"
                " VALUES (%s, %s, 1, %s)"
                " ON DUPLICATE KEY UPDATE"
                " activated_at=%s, activated_by_admin=1, notes=%s",
                (uid, ts, notes, ts, notes)
            )
        db.commit()
    finally:
        db.close()
    _legacy_log(admin_id, "admin_activated", request, {"target_user": uid})
    return {"ok": True}


@app.get("/api/admin/legacy/trusted")
def adm_legacy_trusted(request: Request, page: int = 1, limit: int = 50,
                        status: str = ""):
    require_admin(request)
    if status not in ("", "pending", "confirmed", "rejected"):
        status = ""
    limit = max(1, min(limit, 500))
    offset = (page - 1) * limit
    db = get_db()
    try:
        with db.cursor() as c:
            if status:
                c.execute(
                    "SELECT COUNT(*) as cnt FROM legacy_trusted lt WHERE lt.status=%s",
                    (status,)
                )
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT lt.id, lt.owner_id, lt.trusted_id, lt.status, lt.created_at,"
                    " u1.nickname as owner_nick, u2.nickname as trusted_nick"
                    " FROM legacy_trusted lt"
                    " LEFT JOIN users u1 ON u1.id=lt.owner_id"
                    " LEFT JOIN users u2 ON u2.id=lt.trusted_id"
                    " WHERE lt.status=%s ORDER BY lt.created_at DESC LIMIT %s OFFSET %s",
                    (status, limit, offset)
                )
            else:
                c.execute("SELECT COUNT(*) as cnt FROM legacy_trusted lt")
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT lt.id, lt.owner_id, lt.trusted_id, lt.status, lt.created_at,"
                    " u1.nickname as owner_nick, u2.nickname as trusted_nick"
                    " FROM legacy_trusted lt"
                    " LEFT JOIN users u1 ON u1.id=lt.owner_id"
                    " LEFT JOIN users u2 ON u2.id=lt.trusted_id"
                    " ORDER BY lt.created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            rows = c.fetchall()
    finally:
        db.close()
    return {"total": total, "items": rows}


@app.get("/api/admin/legacy/requests")
def adm_legacy_requests(request: Request, page: int = 1, limit: int = 50,
                         status: str = ""):
    require_admin(request)
    if status not in ("", "new", "review", "confirmed", "rejected"):
        status = ""
    limit = max(1, min(limit, 500))
    offset = (page - 1) * limit
    db = get_db()
    try:
        with db.cursor() as c:
            if status:
                c.execute(
                    "SELECT COUNT(*) as cnt FROM legacy_requests lr WHERE lr.status=%s",
                    (status,)
                )
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT lr.id, lr.owner_id, lr.trusted_id, lr.first_name, lr.last_name,"
                    " lr.death_date, lr.status, lr.mod_comment, lr.created_at,"
                    " u1.nickname as owner_nick, u2.nickname as trusted_nick"
                    " FROM legacy_requests lr"
                    " LEFT JOIN users u1 ON u1.id=lr.owner_id"
                    " LEFT JOIN users u2 ON u2.id=lr.trusted_id"
                    " WHERE lr.status=%s ORDER BY lr.created_at DESC LIMIT %s OFFSET %s",
                    (status, limit, offset)
                )
            else:
                c.execute("SELECT COUNT(*) as cnt FROM legacy_requests lr")
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT lr.id, lr.owner_id, lr.trusted_id, lr.first_name, lr.last_name,"
                    " lr.death_date, lr.status, lr.mod_comment, lr.created_at,"
                    " u1.nickname as owner_nick, u2.nickname as trusted_nick"
                    " FROM legacy_requests lr"
                    " LEFT JOIN users u1 ON u1.id=lr.owner_id"
                    " LEFT JOIN users u2 ON u2.id=lr.trusted_id"
                    " ORDER BY lr.created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            rows = c.fetchall()
    finally:
        db.close()
    return {"total": total, "items": rows}


@app.put("/api/admin/legacy/requests/{rid}")
def adm_legacy_request_update(rid: int, body: LegacyRequestUpdateBody, request: Request):
    require_admin(request)
    if body.status not in ("review", "confirmed", "rejected"):
        raise HTTPException(400, "Невірний статус")
    sess = _get_legacy_session(request)
    admin_id = sess["user_id"]
    comment = _sanitize_text(body.mod_comment or "", 300)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT id FROM legacy_requests WHERE id=%s", (rid,))
            if not c.fetchone():
                raise HTTPException(404, "Заявку не знайдено")
            c.execute(
                "UPDATE legacy_requests SET status=%s, mod_comment=%s WHERE id=%s",
                (body.status, comment, rid)
            )
        db.commit()
    finally:
        db.close()
    _legacy_log(admin_id, f"request_{body.status}", request, {"request_id": rid})
    return {"ok": True}


@app.get("/api/admin/legacy/logs")
def adm_legacy_logs(request: Request, page: int = 1, limit: int = 100,
                     user_id: int = 0, action: str = ""):
    require_admin(request)
    offset = (page - 1) * max(1, min(limit, 500))
    db = get_db()
    try:
        with db.cursor() as c:
            if user_id and action:
                c.execute(
                    "SELECT COUNT(*) as cnt FROM legacy_logs ll"
                    " WHERE ll.user_id=%s AND ll.action=%s",
                    (user_id, action)
                )
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT ll.*, u.nickname FROM legacy_logs ll"
                    " LEFT JOIN users u ON u.id=ll.user_id"
                    " WHERE ll.user_id=%s AND ll.action=%s"
                    " ORDER BY ll.created_at DESC LIMIT %s OFFSET %s",
                    (user_id, action, limit, offset)
                )
            elif user_id:
                c.execute(
                    "SELECT COUNT(*) as cnt FROM legacy_logs ll WHERE ll.user_id=%s",
                    (user_id,)
                )
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT ll.*, u.nickname FROM legacy_logs ll"
                    " LEFT JOIN users u ON u.id=ll.user_id"
                    " WHERE ll.user_id=%s ORDER BY ll.created_at DESC LIMIT %s OFFSET %s",
                    (user_id, limit, offset)
                )
            elif action:
                c.execute(
                    "SELECT COUNT(*) as cnt FROM legacy_logs ll WHERE ll.action=%s",
                    (action,)
                )
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT ll.*, u.nickname FROM legacy_logs ll"
                    " LEFT JOIN users u ON u.id=ll.user_id"
                    " WHERE ll.action=%s ORDER BY ll.created_at DESC LIMIT %s OFFSET %s",
                    (action, limit, offset)
                )
            else:
                c.execute("SELECT COUNT(*) as cnt FROM legacy_logs ll")
                total = c.fetchone()["cnt"]
                c.execute(
                    "SELECT ll.*, u.nickname FROM legacy_logs ll"
                    " LEFT JOIN users u ON u.id=ll.user_id"
                    " ORDER BY ll.created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
            rows = c.fetchall()
    finally:
        db.close()
    return {"total": total, "items": rows}


# ══════════════════════════════════════════════════════════════
# END LEGACY MODULE
# ══════════════════════════════════════════════════════════════


def _oauth_login_or_create(email: str, name: str) -> dict:
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id,name,email,is_admin,role,nickname FROM users WHERE email=%s", (email,))
        row = c.fetchone()
        if not row:
            # Генерація унікального нікнейму з імені
            base = re.sub(r'[^a-zA-Z0-9_]', '', name.replace(' ', '_'))[:20] or 'user'
            nick = base
            suffix = 1
            while True:
                c.execute("SELECT id FROM users WHERE nickname=%s", (nick,))
                if not c.fetchone():
                    break
                nick = f"{base}{suffix}"
                suffix += 1
            c.execute(
                "INSERT INTO users (name,email,password,nickname) VALUES (%s,%s,%s,%s)",
                (name, email, hash_pass(secrets.token_hex(16)), nick)
            )
            db.commit()
            c.execute("SELECT id,name,email,is_admin,role,nickname FROM users WHERE email=%s", (email,))
            row = c.fetchone()
        elif not row.get("nickname"):
            # Існуючий юзер без нікнейму — присвоюємо
            base = re.sub(r'[^a-zA-Z0-9_]', '', (name or email.split('@')[0]).replace(' ', '_'))[:20] or 'user'
            nick = base
            suffix = 1
            while True:
                c.execute("SELECT id FROM users WHERE nickname=%s AND id!=%s", (nick, row["id"]))
                if not c.fetchone():
                    break
                nick = f"{base}{suffix}"
                suffix += 1
            c.execute("UPDATE users SET nickname=%s WHERE id=%s", (nick, row["id"]))
            db.commit()
            row["nickname"] = nick
    db.close()
    return row


def _oauth_set_session(resp: RedirectResponse, user_id: int) -> RedirectResponse:
    token = _session_create(user_id)
    resp.set_cookie(key="admin_session", value=token, httponly=True,
                    secure=_IS_PROD, samesite="lax", max_age=86400 * 7, path="/")
    return resp


# ── Google OAuth ──────────────────────────────────────────

@app.get("/api/auth/google")
def auth_google():
    if not GOOGLE_CLIENT_ID:
        return RedirectResponse("/?oauth_error=google_not_configured", status_code=302)
    if _get_color_val("reg_allow_google", "1") != "1":
        return RedirectResponse("/?oauth_error=google_disabled", status_code=302)
    params = urllib.parse.urlencode({
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  f"{OAUTH_REDIRECT_BASE}/api/auth/google/callback",
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}", status_code=302)


@app.get("/api/auth/google/callback")
def auth_google_callback(code: str = None, error: str = None):
    if error or not code:
        return RedirectResponse("/?oauth_error=google_cancelled", status_code=302)
    token_data = urllib.parse.urlencode({
        "code":          code,
        "client_id":     GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri":  f"{OAUTH_REDIRECT_BASE}/api/auth/google/callback",
        "grant_type":    "authorization_code",
    }).encode()
    try:
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            token_json = json.loads(r.read())
    except Exception:
        return RedirectResponse("/?oauth_error=google_token", status_code=302)
    access_token = token_json.get("access_token")
    if not access_token:
        return RedirectResponse("/?oauth_error=google_token", status_code=302)
    try:
        req2 = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req2, timeout=10) as r:
            info = json.loads(r.read())
    except Exception:
        return RedirectResponse("/?oauth_error=google_userinfo", status_code=302)
    email = info.get("email", "").lower()
    if not email:
        return RedirectResponse("/?oauth_error=google_no_email", status_code=302)
    name = info.get("name") or email.split("@")[0]
    user = _oauth_login_or_create(email, name)
    resp = RedirectResponse("/?oauth=success", status_code=302)
    return _oauth_set_session(resp, user["id"])


# ── Дія OAuth ─────────────────────────────────────────────

@app.get("/api/auth/diia")
def auth_diia():
    if not DIIA_CLIENT_ID:
        return RedirectResponse("/?oauth_error=diia_not_configured", status_code=302)
    params = urllib.parse.urlencode({
        "client_id":     DIIA_CLIENT_ID,
        "redirect_uri":  f"{OAUTH_REDIRECT_BASE}/api/auth/diia/callback",
        "response_type": "code",
        "scope":         "openid email profile",
    })
    return RedirectResponse(f"{DIIA_AUTH_URL}?{params}", status_code=302)


@app.get("/api/auth/diia/callback")
def auth_diia_callback(code: str = None, error: str = None):
    if error or not code:
        return RedirectResponse("/?oauth_error=diia_cancelled", status_code=302)
    token_data = urllib.parse.urlencode({
        "code":          code,
        "client_id":     DIIA_CLIENT_ID,
        "client_secret": DIIA_CLIENT_SECRET,
        "redirect_uri":  f"{OAUTH_REDIRECT_BASE}/api/auth/diia/callback",
        "grant_type":    "authorization_code",
    }).encode()
    try:
        req = urllib.request.Request(
            DIIA_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            token_json = json.loads(r.read())
    except Exception:
        return RedirectResponse("/?oauth_error=diia_token", status_code=302)
    access_token = token_json.get("access_token")
    if not access_token:
        return RedirectResponse("/?oauth_error=diia_token", status_code=302)
    try:
        req2 = urllib.request.Request(
            DIIA_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        with urllib.request.urlopen(req2, timeout=10) as r:
            info = json.loads(r.read())
    except Exception:
        return RedirectResponse("/?oauth_error=diia_userinfo", status_code=302)
    email = info.get("email", "").lower()
    if not email:
        return RedirectResponse("/?oauth_error=diia_no_email", status_code=302)
    name = info.get("name") or info.get("rnokpp") or email.split("@")[0]
    user = _oauth_login_or_create(email, name)
    resp = RedirectResponse("/?oauth=success", status_code=302)
    return _oauth_set_session(resp, user["id"])


@app.get("/api/admin/me")
def admin_me(request: Request):
    u = require_moder(request)
    return u


@app.get("/api/banned-words")
def public_banned_words():
    words = _get_banned_words_cached()
    return {"words": words}

# ── МІКРО-ЧАТ ────────────────────────────────────────────

_banned_words_cache: list = []
_banned_words_ts: float = 0.0
_CHAT_URL_RE = re.compile(r'https?://|www\.|\.(com|ua|org|net|io|ru)\b', re.I)
_CHAT_HTML_RE = re.compile(r'<[^>]{1,100}>')

def _get_banned_words_cached() -> list:
    global _banned_words_cache, _banned_words_ts
    if time.time() - _banned_words_ts > 60:
        try:
            db = get_db()
            with db.cursor() as c:
                c.execute("SELECT word FROM chat_banned_words")
                _banned_words_cache = [r['word'].lower() for r in c.fetchall()]
            db.close()
        except Exception:
            pass
        _banned_words_ts = time.time()
    return _banned_words_cache

def _chat_filter(text: str):
    """Повертає (ok: bool, cleaned_text | reason: str)."""
    text = _sanitize_text(text, 100)
    if not text:
        return False, "Порожнє повідомлення"
    if len(text) > 100:
        return False, "Повідомлення не може перевищувати 100 символів"
    if _CHAT_URL_RE.search(text):
        return False, "Посилання заборонені в чаті"
    if _CHAT_HTML_RE.search(text):
        return False, "HTML заборонено в чаті"
    lower = text.lower()
    for w in _get_banned_words_cached():
        if w and w in lower:
            return False, "Повідомлення містить заборонені слова"
    if re.search(r'\b(здох|умри|вбий|щоб\s+ти\s+здох|смерть\s+тоб[іи]|kill\s+you|die)\b', lower):
        return False, "Погрози заборонені в чаті"
    return True, text

class ChatSendBody(BaseModel):
    message: str
    fp: Optional[str] = None

def _chat_get_user(request: Request):
    """Повертає dict з user або None."""
    token = request.cookies.get("admin_session")
    if not token:
        return None
    sess = _session_get(token)
    if not sess:
        return None
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("SELECT id, name, email, nickname, role, is_banned, ban_until FROM users WHERE id=%s", (sess["user_id"],))
            row = c.fetchone()
        db.close()
        return row
    except Exception:
        return None

@app.get("/api/chat/messages")
def chat_messages(since: int = 0, request: Request = None):
    ip = (request.client.host if request else "0")
    if not _rl.check(f"{ip}|chat_read", 60, 60):
        raise HTTPException(429, "Занадто багато запитів")
    # Адміни бачать всі повідомлення включно з гостьовими старіше 2 хв
    caller = _chat_get_user(request) if request else None
    is_admin = caller and caller.get('role') in ('admin', 'moder')
    now_ms = int(time.time() * 1000)
    guest_cutoff_ms = now_ms - 120_000  # 2 хвилини
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("SELECT value FROM colors WHERE `key`='chat_enabled'")
            row = c.fetchone()
            if row and row.get('value', '1') == '0':
                db.close()
                return {"ok": True, "messages": [], "disabled": True}
            c.execute("SELECT value FROM colors WHERE `key`='chat_history_count'")
            row2 = c.fetchone()
            limit = int(row2['value']) if row2 else 50
            # Для не-адмінів фільтруємо гостьові старіше 2 хвилин
            guest_filter = "" if is_admin else f" AND NOT (m.is_guest=1 AND m.created_at<%s)"
            if since == 0:
                if is_admin:
                    c.execute(
                        "SELECT * FROM ("
                        " SELECT m.id, m.user_id, m.message, m.created_at, m.is_guest, m.is_bot, m.bot_name,"
                        " u.nickname, u.role"
                        " FROM chat_messages m"
                        " LEFT JOIN users u ON m.user_id=u.id"
                        " WHERE m.is_deleted=0"
                        " ORDER BY m.created_at DESC LIMIT %s"
                        ") sub ORDER BY created_at ASC",
                        (limit,)
                    )
                else:
                    c.execute(
                        "SELECT * FROM ("
                        " SELECT m.id, m.user_id, m.message, m.created_at, m.is_guest, m.is_bot, m.bot_name,"
                        " u.nickname, u.role"
                        " FROM chat_messages m"
                        " LEFT JOIN users u ON m.user_id=u.id"
                        " WHERE m.is_deleted=0"
                        " AND NOT (m.is_guest=1 AND m.created_at<%s)"
                        " ORDER BY m.created_at DESC LIMIT %s"
                        ") sub ORDER BY created_at ASC",
                        (guest_cutoff_ms, limit)
                    )
            else:
                if is_admin:
                    c.execute(
                        "SELECT m.id, m.user_id, m.message, m.created_at, m.is_guest, m.is_bot, m.bot_name,"
                        " u.nickname, u.role"
                        " FROM chat_messages m"
                        " LEFT JOIN users u ON m.user_id=u.id"
                        " WHERE m.is_deleted=0 AND m.created_at>%s"
                        " ORDER BY m.created_at ASC LIMIT %s",
                        (since, limit)
                    )
                else:
                    c.execute(
                        "SELECT m.id, m.user_id, m.message, m.created_at, m.is_guest, m.is_bot, m.bot_name,"
                        " u.nickname, u.role"
                        " FROM chat_messages m"
                        " LEFT JOIN users u ON m.user_id=u.id"
                        " WHERE m.is_deleted=0 AND m.created_at>%s"
                        " AND NOT (m.is_guest=1 AND m.created_at<%s)"
                        " ORDER BY m.created_at ASC LIMIT %s",
                        (since, guest_cutoff_ms, limit)
                    )
            raw = c.fetchall()
        db.close()
        # Підставляємо дані для гостей і ботів
        msgs = []
        for m in raw:
            m = dict(m)
            if m.get('is_bot'):
                m['nickname'] = None
                m['role'] = 'user'
            elif m.get('is_guest'):
                m['nickname'] = None
                m['role'] = 'guest'
            # Ніколи не повертати email/name/password у публічному chat API
            m.pop('email', None)
            m.pop('name', None)
            m.pop('password', None)
            msgs.append(m)
        return {"ok": True, "messages": msgs}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/chat/send")
async def chat_send(body: ChatSendBody, request: Request):
    # Перевірка чи чат увімкнений
    try:
        _db_c = get_db()
        with _db_c.cursor() as _cc:
            _cc.execute("SELECT value FROM colors WHERE `key`='chat_enabled'")
            _cr = _cc.fetchone()
        _db_c.close()
        if _cr and _cr.get('value', '1') == '0':
            raise HTTPException(403, "Чат тимчасово вимкнений")
    except HTTPException:
        raise
    except Exception:
        pass

    user = _chat_get_user(request)
    ip = _get_ip(request)

    if not user:
        # ── Анонімний режим: 1 повідомлення / 10 хв ──
        fp = re.sub(r'[^a-z0-9]', '', (body.fp or "").strip().lower())[:64]
        if len(fp) < 4:
            raise HTTPException(400, "Для гостей потрібен fingerprint")
        # IP rate limit
        if not _rl.check(f"{ip}|anon_chat", 1, 600):
            raise HTTPException(429, "Гості можуть писати 1 раз на 10 хвилин")
        ok, result = _chat_filter(body.message)
        if not ok:
            raise HTTPException(400, result)
        ts = int(time.time() * 1000)
        cutoff_ms = ts - 600_000
        try:
            db = get_db()
            with db.cursor() as c:
                # Fingerprint cooldown: перевіряємо в БД
                c.execute(
                    "SELECT id FROM chat_messages WHERE guest_fp=%s AND created_at>%s LIMIT 1",
                    (fp, cutoff_ms)
                )
                if c.fetchone():
                    db.close()
                    raise HTTPException(429, "Ви вже писали нещодавно. Зачекайте 10 хвилин")
                c.execute(
                    "INSERT INTO chat_messages (user_id, message, created_at, guest_fp, guest_ip, is_guest)"
                    " VALUES (NULL,%s,%s,%s,%s,1)",
                    (result, ts, fp, ip[:45])
                )
                msg_id = c.lastrowid
            db.commit()
            db.close()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))
        msg_data = {
            "id": msg_id, "user_id": None, "is_guest": 1,
            "message": result, "created_at": ts,
            "nickname": None, "name": "Гість", "email": None, "role": "guest"
        }
        await broadcast({"event": "chat_msg", "msg": msg_data})
        return {"ok": True, "msg": msg_data}

    # ── Авторизований режим ──
    if user.get('is_banned'):
        ban_until = user.get('ban_until')
        if ban_until is None or (isinstance(ban_until, str) and ban_until > time.strftime('%Y-%m-%d %H:%M:%S')):
            raise HTTPException(403, "Ваш акаунт заблоковано")
    if not _rl.check(f"{user['id']}|chat_send", 5, 60):
        raise HTTPException(429, "Ви надсилаєте повідомлення занадто часто")
    ok, result = _chat_filter(body.message)
    if not ok:
        raise HTTPException(400, result)
    ts = int(time.time() * 1000)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT INTO chat_messages (user_id, message, created_at) VALUES (%s,%s,%s)",
                (user['id'], result, ts)
            )
            msg_id = c.lastrowid
        db.commit()
        db.close()
        msg_data = {
            "id": msg_id, "user_id": user['id'], "is_guest": 0,
            "message": result, "created_at": ts,
            "nickname": user.get('nickname'), "role": user.get('role', 'user')
        }
        await broadcast({"event": "chat_msg", "msg": msg_data})
        return {"ok": True, "msg": msg_data}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/chat/report/{msg_id}")
def chat_report(msg_id: int, request: Request):
    user = _chat_get_user(request)
    if not user:
        raise HTTPException(401, "Потрібна авторизація")
    ts = int(time.time() * 1000)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT IGNORE INTO chat_reports (msg_id, reporter_id, reason, created_at)"
                " VALUES (%s,%s,%s,%s)",
                (msg_id, user['id'], "user_report", ts)
            )
            c.execute("SELECT COUNT(*) as cnt FROM chat_reports WHERE msg_id=%s", (msg_id,))
            cnt = (c.fetchone() or {}).get('cnt', 0)
            if cnt >= 3:
                c.execute("UPDATE chat_messages SET is_deleted=1 WHERE id=%s", (msg_id,))
        db.commit()
        db.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

# Адмінські ендпоінти чату
@app.get("/api/admin/chat/messages")
def adm_chat_messages(request: Request, page: int = 1, limit: int = 100, deleted: int = 0):
    require_moder(request)
    offset = (page - 1) * limit
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "SELECT m.id, m.user_id, m.message, m.created_at, m.is_deleted, m.is_guest, m.is_bot, m.bot_name,"
                " u.nickname, u.name, u.role,"
                " (SELECT COUNT(*) FROM chat_reports r WHERE r.msg_id=m.id) as reports"
                " FROM chat_messages m LEFT JOIN users u ON m.user_id=u.id"
                " WHERE m.is_deleted=%s"
                " ORDER BY m.created_at DESC LIMIT %s OFFSET %s",
                (deleted, limit, offset)
            )
            raw = c.fetchall()
            msgs = []
            for row in raw:
                row = dict(row)
                if row.get('is_bot'):
                    row['name'] = row.get('bot_name') or 'Бот'
                    row['nickname'] = None
                    row['role'] = 'user'
                elif row.get('is_guest'):
                    row['name'] = 'Гість'
                    row['nickname'] = None
                    row['role'] = 'guest'
                msgs.append(row)
            c.execute("SELECT COUNT(*) as cnt FROM chat_messages WHERE is_deleted=%s", (deleted,))
            total = (c.fetchone() or {}).get('cnt', 0)
        db.close()
        return {"ok": True, "messages": msgs, "total": total}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/admin/chat/history")
async def adm_chat_clear_history(request: Request):
    require_admin(request)
    ip = _get_ip(request)
    if not _rl.check(f"chat_clear:{ip}", 3, 60):
        raise HTTPException(429, "Забагато запитів")
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM chat_messages")
        db.commit()
        sec_log("CHAT_CLEAR", ip, "all chat history deleted")
    finally:
        db.close()
    return {"ok": True}

@app.delete("/api/admin/chat/{msg_id}")
async def adm_chat_delete(msg_id: int, request: Request):
    require_moder(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("UPDATE chat_messages SET is_deleted=1 WHERE id=%s", (msg_id,))
        db.commit()
        db.close()
        await broadcast({"event": "chat_delete", "id": msg_id})
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/admin/chat/reports")
def adm_chat_reports(request: Request):
    require_moder(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "SELECT r.id, r.msg_id, r.reason, r.created_at,"
                " m.message, m.is_deleted,"
                " u.nickname as reporter_nick, u.name as reporter_name,"
                " mu.nickname as author_nick, mu.name as author_name"
                " FROM chat_reports r"
                " JOIN chat_messages m ON r.msg_id=m.id"
                " JOIN users u ON r.reporter_id=u.id"
                " JOIN users mu ON m.user_id=mu.id"
                " ORDER BY r.created_at DESC LIMIT 200"
            )
            rows = c.fetchall()
        db.close()
        return {"ok": True, "reports": rows}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/admin/chat/banned-words")
def adm_banned_words_get(request: Request):
    require_moder(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("SELECT id, word, category FROM chat_banned_words ORDER BY category, word")
            rows = c.fetchall()
        db.close()
        return {"ok": True, "words": rows}
    except Exception as e:
        raise HTTPException(500, str(e))

class BannedWordBody(BaseModel):
    word: str
    category: str = "profanity"

@app.post("/api/admin/chat/banned-words")
def adm_banned_words_add(body: BannedWordBody, request: Request):
    require_moder(request)
    word = _sanitize_text(body.word, 200).lower().strip()
    if not word:
        raise HTTPException(400, "Слово не може бути порожнім")
    cat = body.category if body.category in ("profanity", "threat", "spam") else "profanity"
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT IGNORE INTO chat_banned_words (word, category) VALUES (%s,%s)",
                (word, cat)
            )
        db.commit()
        db.close()
        global _banned_words_ts
        _banned_words_ts = 0  # інвалідуємо кеш
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

class BannedWordsImportBody(BaseModel):
    text: str
    category: str = "profanity"

@app.post("/api/admin/chat/banned-words/import")
def adm_banned_words_import(body: BannedWordsImportBody, request: Request):
    require_moder(request)
    cat = body.category if body.category in ("profanity", "threat", "spam") else "profanity"
    # Розбиваємо по комах і переносах рядків, чистимо кожне слово
    raw = body.text.replace("\n", ",").replace(";", ",")
    words = [_sanitize_text(w, 200).lower().strip() for w in raw.split(",")]
    words = [w for w in words if w and len(w) >= 2]
    if not words:
        raise HTTPException(400, "Не знайдено жодного слова")
    if len(words) > 1000:
        raise HTTPException(400, "Максимум 1000 слів за один імпорт")
    try:
        db = get_db()
        added = 0
        with db.cursor() as c:
            for w in words:
                res = c.execute(
                    "INSERT IGNORE INTO chat_banned_words (word, category) VALUES (%s,%s)",
                    (w, cat)
                )
                added += res
        db.commit()
        db.close()
        global _banned_words_ts
        _banned_words_ts = 0
        return {"ok": True, "added": added, "total": len(words)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/admin/chat/banned-words/{word_id}")
def adm_banned_words_del(word_id: int, request: Request):
    require_moder(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("DELETE FROM chat_banned_words WHERE id=%s", (word_id,))
        db.commit()
        db.close()
        global _banned_words_ts
        _banned_words_ts = 0
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Чат-боти: адмін endpoints ────────────────────────────

class BotPhraseBody(BaseModel):
    phrase: str
    category: str = "general"

class BotConfigBody(BaseModel):
    enabled: bool

@app.get("/api/admin/chat/bots")
def adm_bots_get(request: Request):
    require_moder(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("SELECT id, phrase, category, is_active FROM chat_bot_phrases ORDER BY id")
            phrases = c.fetchall()
        db.close()
        with _bot_lock:
            cnt = _bot_online_count
        return {
            "ok": True,
            "enabled": _bots_enabled,
            "bot_online_count": cnt,
            "bot_names": _BOT_NAMES,
            "phrases": [dict(p) for p in phrases],
        }
    except Exception as e:
        raise HTTPException(500, str(e))

@app.put("/api/admin/chat/bots/config")
def adm_bots_config(body: BotConfigBody, request: Request):
    require_admin(request)
    global _bots_enabled
    try:
        db = get_db()
        with db.cursor() as c:
            val = '1' if body.enabled else '0'
            c.execute(
                "INSERT INTO colors (`key`, value, label) VALUES ('chat_bots_enabled', %s, 'Чат-боти увімкнені')"
                " ON DUPLICATE KEY UPDATE value=%s",
                (val, val)
            )
        db.commit()
        db.close()
        _bots_enabled = body.enabled
        return {"ok": True, "enabled": _bots_enabled}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/admin/chat/bots/phrase")
def adm_bots_phrase_add(body: BotPhraseBody, request: Request):
    require_admin(request)
    phrase = _sanitize_text(body.phrase.strip())[:500]
    if not phrase:
        raise HTTPException(400, "Фраза порожня")
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "INSERT INTO chat_bot_phrases (phrase, category) VALUES (%s, %s)",
                (phrase, body.category[:50])
            )
            new_id = c.lastrowid
        db.commit()
        db.close()
        return {"ok": True, "id": new_id}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/admin/chat/bots/phrase/{phrase_id}")
def adm_bots_phrase_del(phrase_id: int, request: Request):
    require_admin(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("DELETE FROM chat_bot_phrases WHERE id=%s", (phrase_id,))
        db.commit()
        db.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.put("/api/admin/chat/bots/phrase/{phrase_id}/toggle")
def adm_bots_phrase_toggle(phrase_id: int, request: Request):
    require_admin(request)
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute("UPDATE chat_bot_phrases SET is_active = 1 - is_active WHERE id=%s", (phrase_id,))
        db.commit()
        db.close()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── ADMIN API ─────────────────────────────────────────────

@app.get("/api/admin/pending")
def pending(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM memorials WHERE approved=0 ORDER BY id DESC")
        rows = c.fetchall()
    db.close()
    return rows

@app.get("/api/awards/catalog")
def get_awards_catalog():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id,name,img_file,category,description,sort_order FROM awards_catalog ORDER BY sort_order,name")
        rows = c.fetchall()
    db.close()
    return rows

@app.get("/api/admin/memorials")
def admin_all_memorials(page: int = 1, limit: int = 100, request: Request = None):
    require_moder(request)
    page = max(1, page)
    limit = max(1, min(limit, 500))
    offset = (page - 1) * limit
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials")
        total = c.fetchone()["cnt"]
        c.execute(
            "SELECT * FROM memorials ORDER BY id DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        rows = c.fetchall()
    db.close()
    return {"items": rows, "total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit}

@app.post("/api/admin/approve/{mid}")
def approve(mid: int, request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE memorials SET approved=1 WHERE id=%s", (mid,))
        c.execute("SELECT id, first, last, slug FROM memorials WHERE id=%s", (mid,))
        row = c.fetchone()
        if row and not row.get('slug'):
            sl = make_slug(row['first'], row['last'], row['id'])
            try:
                c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, mid))
            except Exception:
                pass
    db.commit()
    db.close()
    cache_flush_memorials()
    cache_delete("sitemap")
    return {"ok": True}

@app.post("/api/admin/unapprove/{mid}")
def unapprove(mid: int, request: Request):
    require_moder(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE memorials SET approved=0 WHERE id=%s", (mid,))
        db.commit()
    finally:
        db.close()
    cache_flush_memorials()
    return {"ok": True}

@app.post("/api/admin/memorial")
def admin_add_person(p: PersonIn, request: Request):
    require_moder(request)
    # Якщо передано world_lat/lng — автообчислити pos_x/pos_y
    pos_x, pos_y = p.pos_x, p.pos_y
    if p.world_lat is not None and p.world_lng is not None:
        pos_x, pos_y = _latLngToSvg(p.world_lat, p.world_lng)
    db = get_db()
    with db.cursor() as c:
        c.execute("""
            INSERT INTO memorials
            (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,`rank`,`position`,`unit`,pos_x,pos_y,world_lat,world_lng,grp,added_by,approved)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
        """, (p.last.strip(), p.first.strip(), p.mid or '', p.birth or None, p.death or None,
              p.loc or '', p.bury or '', p.circ or '', p.descr or '', p.photo or '',
              p.color or '#4fc3f7', p.rank or '', p.position or '', p.unit or '',
              pos_x, pos_y, p.world_lat, p.world_lng, p.grp or '', 'admin'))
        new_id = c.lastrowid
        sl = make_slug(p.first.strip(), p.last.strip(), new_id)
        try:
            c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, new_id))
        except Exception:
            pass
    db.commit()
    db.close()
    cache_flush_memorials()
    cache_delete("sitemap")
    return {"ok": True, "id": new_id}

@app.delete("/api/admin/memorial/{mid}")
def delete_memorial(mid: int, request: Request):
    me = require_admin(request)
    ip = _get_ip(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT last, first FROM memorials WHERE id=%s", (mid,))
            m = c.fetchone()
            c.execute("DELETE FROM memorials WHERE id=%s", (mid,))
        db.commit()
    finally:
        db.close()
    name = f"{m['last']} {m['first']}" if m else "?"
    sec_log("DELETE_MEMORIAL", ip, f"id={mid} name={name} by={me.get('email','?')}")
    cache_flush_memorials()
    return {"ok": True}

# ── CSV Export / Import ────────────────────────────────────

_CSV_COLS = ['id','last','first','mid','birth','death','loc','bury','circ',
             'descr','photo','color','pos_x','pos_y','grp','rank','position','unit',
             'video_url','added_by','approved','likes','rating']

# ── Portfolio: Thanks block ────────────────────────────────
class ThanksItem(BaseModel):
    name: str
    sort_order: Optional[int] = 0
    is_visible: Optional[int] = 1

@app.get("/api/portfolio/thanks")
def portfolio_thanks_get():
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("CREATE TABLE IF NOT EXISTS portfolio_thanks ("
                      "id INT PRIMARY KEY AUTO_INCREMENT, "
                      "name VARCHAR(200) NOT NULL, "
                      "sort_order INT NOT NULL DEFAULT 0, "
                      "is_visible TINYINT NOT NULL DEFAULT 1"
                      ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4")
            db.commit()
            c.execute("SELECT id, name, sort_order, is_visible FROM portfolio_thanks ORDER BY sort_order, id")
            rows = c.fetchall()
    finally:
        db.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/portfolio/thanks")
def portfolio_thanks_add(item: ThanksItem, request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("INSERT INTO portfolio_thanks (name, sort_order, is_visible) VALUES (%s,%s,%s)",
                      (_sanitize_text(item.name), item.sort_order, item.is_visible))
            new_id = c.lastrowid
        db.commit()
    finally:
        db.close()
    return {"id": new_id}

# reorder МУСИТЬ бути перед /{item_id} — інакше FastAPI намагається парсити "reorder" як int
@app.put("/api/admin/portfolio/thanks/reorder")
def portfolio_thanks_reorder(items: List[dict], request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            for it in items:
                c.execute("UPDATE portfolio_thanks SET sort_order=%s WHERE id=%s",
                          (it.get("sort_order", 0), it["id"]))
        db.commit()
    finally:
        db.close()
    return {"ok": True}

@app.put("/api/admin/portfolio/thanks/{item_id}")
def portfolio_thanks_update(item_id: int, item: ThanksItem, request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE portfolio_thanks SET name=%s, sort_order=%s, is_visible=%s WHERE id=%s",
                      (_sanitize_text(item.name), item.sort_order, item.is_visible, item_id))
        db.commit()
    finally:
        db.close()
    return {"ok": True}

@app.delete("/api/admin/portfolio/thanks/{item_id}")
def portfolio_thanks_delete(item_id: int, request: Request):
    require_admin(request)
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("DELETE FROM portfolio_thanks WHERE id=%s", (item_id,))
        db.commit()
    finally:
        db.close()
    return {"ok": True}

@app.get("/api/admin/export/csv")
def export_csv(request: Request):
    require_moder(request)
    ip = _get_ip(request)
    if not _rl.check(f"adm_export:{ip}", 5, 60):
        raise HTTPException(429, "Занадто багато запитів на експорт")
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,last,first,mid,birth,death,loc,bury,circ,descr,photo,color,"
            "pos_x,pos_y,grp,`rank`,`position`,`unit`,video_url,added_by,approved,likes,rating "
            "FROM memorials ORDER BY id"
        )
        rows = c.fetchall()
    db.close()

    buf = io.StringIO()
    buf.write('﻿')  # BOM для коректного відкриття в Excel
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(_CSV_COLS)
    for r in rows:
        w.writerow(['' if r.get(col) is None else r.get(col, '') for col in _CSV_COLS])

    fname = f"memorials_{__import__('datetime').date.today()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/admin/export/json")
def export_json(request: Request):
    """Повний список записів у JSON — для XLSX-експорту на клієнті."""
    require_moder(request)
    ip = _get_ip(request)
    if not _rl.check(f"adm_export:{ip}", 5, 60):
        raise HTTPException(429, "Занадто багато запитів на експорт")
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,last,first,mid,birth,death,loc,bury,circ,descr,photo,color,"
            "pos_x,pos_y,grp,`rank`,`position`,`unit`,video_url,added_by,approved,likes,rating "
            "FROM memorials ORDER BY id"
        )
        rows = c.fetchall()
    db.close()
    for r in rows:
        for k in ('birth', 'death'):
            if r.get(k):
                r[k] = str(r[k])
    return rows


@app.post("/api/admin/import/csv")
async def import_csv(request: Request, file: UploadFile = File(...)):
    require_admin(request)
    raw = await file.read()
    try:
        text = raw.decode('utf-8-sig')  # utf-8 з BOM або без
    except UnicodeDecodeError:
        text = raw.decode('cp1251', errors='replace')  # fallback для Windows-кодування

    reader = csv.DictReader(io.StringIO(text))
    inserted, skipped = 0, 0
    errors: list[str] = []

    db = get_db()
    for i, row in enumerate(reader, 1):
        last  = (row.get('last')  or '').strip()
        first = (row.get('first') or '').strip()
        if not last or not first:
            skipped += 1
            errors.append(f"Рядок {i}: пропущено — відсутнє прізвище або ім'я")
            continue
        if len(last) > 100 or len(first) > 100:
            skipped += 1
            errors.append(f"Рядок {i}: пропущено — прізвище/ім'я надто довге")
            continue
        try:
            pos_x = float(row.get('pos_x') or 0)
            pos_y = float(row.get('pos_y') or 0)
        except ValueError:
            pos_x, pos_y = 0.0, 0.0
        try:
            with db.cursor() as c:
                c.execute("""
                    INSERT INTO memorials
                    (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,
                     pos_x,pos_y,grp,`rank`,`position`,video_url,added_by,approved)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
                """, (
                    _sanitize_text(last, 100),
                    _sanitize_text(first, 100),
                    _sanitize_text((row.get('mid')       or '')[:100],  100),
                    (row.get('birth') or None) or None,
                    (row.get('death') or None) or None,
                    _sanitize_text((row.get('loc')       or '')[:300],  300),
                    _sanitize_text((row.get('bury')      or '')[:300],  300),
                    _sanitize_text((row.get('circ')      or '')[:500],  500),
                    _sanitize_text((row.get('descr')     or '')[:5000], 5000),
                    _validate_photo_url((row.get('photo') or '')[:500]),
                    _validate_color(row.get('color') or ''),
                    pos_x, pos_y,
                    _sanitize_text((row.get('grp')       or '')[:100],  100),
                    _sanitize_text((row.get('rank')      or '')[:100],  100),
                    _sanitize_text((row.get('position')  or '')[:100],  100),
                    _sanitize_text((row.get('video_url') or '')[:500],  500),
                    _sanitize_text((row.get('added_by')  or 'csv-import')[:100], 100),
                ))
            db.commit()
            inserted += 1
        except HTTPException as ex:
            skipped += 1
            errors.append(f"Рядок {i} ({last} {first}): {ex.detail}")
        except Exception as ex:
            skipped += 1
            errors.append(f"Рядок {i} ({last} {first}): {str(ex)[:120]}")

    db.close()
    return {"ok": True, "inserted": inserted, "skipped": skipped,
            "errors": errors[:50]}


@app.post("/api/admin/import/preview")
async def import_csv_preview(request: Request, file: UploadFile = File(...)):
    require_moder(request)
    raw = await file.read()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1251', errors='replace')

    reader = csv.DictReader(io.StringIO(text))
    rows, parse_errors = [], []

    for i, row in enumerate(reader, 1):
        last  = (row.get('last')  or '').strip()
        first = (row.get('first') or '').strip()
        if not last or not first:
            parse_errors.append(f"Рядок {i}: пропущено — відсутнє прізвище або ім'я")
            continue
        try:
            px = float(row.get('pos_x') or 0)
            py = float(row.get('pos_y') or 0)
        except (ValueError, TypeError):
            px, py = 0.0, 0.0
        rows.append({
            '_row': i, '_status': 'new', '_matches': [],
            'last':      last[:100],
            'first':     first[:100],
            'mid':       (row.get('mid')       or '').strip()[:100],
            'birth':     (row.get('birth')      or '').strip()[:20],
            'death':     (row.get('death')      or '').strip()[:20],
            'loc':       (row.get('loc')        or '').strip()[:300],
            'bury':      (row.get('bury')       or '').strip()[:300],
            'circ':      (row.get('circ')       or '').strip()[:500],
            'descr':     (row.get('descr')      or '').strip(),
            'photo':     (row.get('photo')      or '').strip()[:500],
            'color':     (row.get('color')      or '#4fc3f7'),
            'pos_x': px, 'pos_y': py,
            'grp':       (row.get('grp')        or '').strip()[:100],
            'rank':      (row.get('rank')       or '').strip()[:100],
            'position':  (row.get('position')   or '').strip()[:100],
            'unit':      (row.get('unit')       or '').strip()[:200],
            'video_url': (row.get('video_url')  or '').strip()[:500],
            'added_by':  (row.get('added_by')   or 'csv-import').strip()[:100],
        })

    if rows:
        db = get_db()
        with db.cursor() as c:
            c.execute("""
                SELECT m.id, m.last, m.first, m.birth, m.death,
                       COUNT(a.id) AS awards_count
                FROM memorials m
                LEFT JOIN memorial_awards a ON a.memorial_id = m.id
                GROUP BY m.id
            """)
            existing = c.fetchall()
        db.close()
        ex_map: dict = {}
        for r in existing:
            key = (r['last'].strip().lower(), r['first'].strip().lower())
            ex_map.setdefault(key, []).append(r)
        for row in rows:
            key = (row['last'].lower(), row['first'].lower())
            matches = ex_map.get(key, [])
            if matches:
                row['_status'] = 'duplicate'
                row['_matches'] = [
                    {'id': m['id'], 'last': m['last'], 'first': m['first'],
                     'birth': str(m.get('birth') or ''), 'death': str(m.get('death') or ''),
                     'awards_count': int(m.get('awards_count') or 0)}
                    for m in matches
                ]
    return {'rows': rows, 'parse_errors': parse_errors}


@app.post("/api/admin/import/apply")
async def import_csv_apply(request: Request):
    me = require_moder(request)
    ip = _get_ip(request)
    if not _rl.check(f"adm_import:{ip}", 3, 60):
        raise HTTPException(429, "Занадто часто. Зачекайте хвилину.")
    rows = await request.json()
    if not isinstance(rows, list):
        rows = rows.get('rows', [])
    inserted, skipped, errors = 0, 0, []
    db = get_db()
    try:
        for i, row in enumerate(rows, 1):
            last  = (row.get('last')  or '').strip()
            first = (row.get('first') or '').strip()
            if not last or not first:
                skipped += 1; continue
            try:
                px = float(row.get('pos_x') or 0)
                py = float(row.get('pos_y') or 0)
            except (ValueError, TypeError):
                px, py = 0.0, 0.0
            try:
                new_id = None
                with db.cursor() as c:
                    c.execute("""
                        INSERT INTO memorials
                        (last,first,mid,birth,death,loc,bury,circ,descr,photo,color,
                         pos_x,pos_y,grp,`rank`,`position`,`unit`,video_url,added_by,approved)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
                    """, (
                        _sanitize_text(last, 100),
                        _sanitize_text(first, 100),
                        _sanitize_text((row.get('mid')       or '')[:100], 100),
                        (row.get('birth') or None) or None,
                        (row.get('death') or None) or None,
                        _sanitize_text((row.get('loc')       or '')[:300], 300),
                        _sanitize_text((row.get('bury')      or '')[:300], 300),
                        _sanitize_text((row.get('circ')      or '')[:500], 500),
                        _sanitize_text((row.get('descr')     or '')[:5000], 5000),
                        _validate_photo_url((row.get('photo') or '')[:500]),
                        _validate_color(row.get('color') or ''),
                        px, py,
                        _sanitize_text((row.get('grp')       or '')[:100], 100),
                        _sanitize_text((row.get('rank')      or '')[:100], 100),
                        _sanitize_text((row.get('position')  or '')[:100], 100),
                        _sanitize_text((row.get('unit')      or '')[:200], 200),
                        _sanitize_text((row.get('video_url') or '')[:500], 500),
                        _sanitize_text((row.get('added_by')  or 'csv-import')[:100], 100),
                    ))
                    new_id = c.lastrowid
                inserted += 1
                awards = row.get('_awards') or []
                if awards and new_id:
                    try:
                        with db.cursor() as c:
                            for sort_idx, aw in enumerate(awards):
                                c.execute(
                                    "INSERT INTO memorial_awards (memorial_id,name,img_file,sort_order) VALUES (%s,%s,%s,%s)",
                                    (new_id, (aw.get('name') or '')[:200], (aw.get('img_file') or '')[:300], sort_idx)
                                )
                    except Exception:
                        pass
            except HTTPException as ex:
                skipped += 1
                errors.append(f"Рядок {i} ({last} {first}): {ex.detail}")
            except Exception as ex:
                skipped += 1
                errors.append(f"Рядок {i} ({last} {first}): {str(ex)[:120]}")
        db.commit()
    finally:
        db.close()
    cache_flush_memorials()
    sec_log("CSV_IMPORT", ip, f"inserted={inserted} skipped={skipped} by={me.get('email','?')}")
    return {"ok": True, "inserted": inserted, "skipped": skipped, "errors": errors[:50]}


_MEMORIAL_COL_MAP = {
    'last':    '`last`=%s',    'first': '`first`=%s', 'mid':    '`mid`=%s',
    'birth':   '`birth`=%s',   'death': '`death`=%s', 'loc':    '`loc`=%s',
    'bury':    '`bury`=%s',    'circ':  '`circ`=%s',  'descr':  '`descr`=%s',
    'photo':   '`photo`=%s',   'color': '`color`=%s', 'pos_x':  '`pos_x`=%s',
    'pos_y':   '`pos_y`=%s',   'approved':'`approved`=%s', 'grp': '`grp`=%s',
    'video_url': '`video_url`=%s',
    'rank':      '`rank`=%s',
    'position':  '`position`=%s',
    'unit':      '`unit`=%s',
    'world_lat': '`world_lat`=%s',
    'world_lng': '`world_lng`=%s',
}
_MEMORIAL_ALLOWED_FIELDS = set(_MEMORIAL_COL_MAP)

@app.put("/api/admin/memorial/{mid}")
def update_memorial(mid: int, p: PersonUpdate, request: Request):
    require_moder(request)
    db = get_db()
    _TEXT_MAXLEN = {
        'last':100,'first':100,'mid':100,'loc':300,'bury':300,
        'circ':200,'grp':100,'rank':100,'position':100,'unit':200,
    }
    fields, vals = [], []
    for f, v in p.model_dump(exclude_none=True).items():
        if f not in _MEMORIAL_COL_MAP:
            raise HTTPException(400, f"Поле '{f}' не дозволено")
        if f in _TEXT_MAXLEN and v is not None:
            v = _sanitize_text(str(v), _TEXT_MAXLEN[f])
        elif f == 'descr' and v is not None:
            v = str(v)[:5000]
        elif f == 'photo' and v:
            v = _validate_photo_url(v)
        elif f == 'color' and v:
            v = _validate_color(v)
        elif f == 'video_url':
            v = _validate_yt_url(v or '')
        elif f in ('birth', 'death'):
            v = _validate_date(v)
        elif f in ('pos_x', 'pos_y') and v is not None:
            v = float(v)
        elif f in ('world_lat', 'world_lng') and v is not None:
            v = float(v)
        fields.append(_MEMORIAL_COL_MAP[f])
        vals.append(v)
    if not fields:
        db.close()
        return {"ok": False}
    # Якщо передано world_lat/lng — автообчислити pos_x/pos_y
    update_data = p.model_dump(exclude_none=True)
    if p.world_lat is not None and p.world_lng is not None:
        svx, svy = _latLngToSvg(p.world_lat, p.world_lng)
        for fname, fval in [('pos_x', svx), ('pos_y', svy)]:
            if fname not in update_data:
                fields.append(_MEMORIAL_COL_MAP[fname])
                vals.append(fval)
    vals.append(mid)
    old_slug = None
    with db.cursor() as c:
        c.execute("SELECT slug FROM memorials WHERE id=%s", (mid,))
        old_row = c.fetchone()
        if old_row:
            old_slug = old_row.get('slug')
        c.execute("UPDATE memorials SET " + ",".join(fields) + " WHERE id=%s", vals)
        if 'first' in update_data or 'last' in update_data:
            c.execute("SELECT first, last FROM memorials WHERE id=%s", (mid,))
            nr = c.fetchone()
            if nr:
                new_slug = make_slug(nr['first'], nr['last'], mid)
                try:
                    c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (new_slug, mid))
                    old_slug = old_slug  # will delete old slug cache below
                except Exception:
                    pass
    db.commit()
    db.close()
    cache_flush_memorials()
    if old_slug:
        cache_delete(f"seo:{old_slug}")
    cache_delete("sitemap")
    return {"ok": True}

@app.get("/api/memorial/{mid}/awards")
def get_awards(mid: int):
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,img_file,category,award_date,descr,sort_order FROM memorial_awards "
            "WHERE memorial_id=%s ORDER BY sort_order,id",
            (mid,)
        )
        rows = c.fetchall()
    db.close()
    for r in rows:
        if r.get("award_date"):
            r["award_date"] = str(r["award_date"])
    return rows

class AwardIn(BaseModel):
    name:       str
    img_file:   Optional[str] = ""
    category:   Optional[str] = ""
    award_date: Optional[str] = None
    descr:      Optional[str] = ""
    sort_order: Optional[int] = 0

@app.post("/api/admin/memorial/{mid}/awards")
def add_award(mid: int, a: AwardIn, request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO memorial_awards (memorial_id,name,img_file,category,award_date,descr,sort_order) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (mid, a.name.strip(), a.img_file or '', a.category or '', a.award_date or None, a.descr or '', a.sort_order or 0)
        )
        db.commit()
        new_id = c.lastrowid
    db.close()
    return {"ok": True, "id": new_id}

@app.delete("/api/admin/awards/{award_id}")
def delete_award(award_id: int, request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("DELETE FROM memorial_awards WHERE id=%s", (award_id,))
        db.commit()
    db.close()
    return {"ok": True}

@app.get("/api/admin/users")
def get_users(request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,name,email,is_admin,is_banned,ban_until,notes,last_seen,created,role FROM users ORDER BY id DESC"
        )
        rows = c.fetchall()
    db.close()
    now = int(time.time())
    for r in rows:
        r["online"] = (now - (r["last_seen"] or 0)) < 120
        bu = r.get("ban_until") or 0
        if r["is_banned"]:
            if bu > 0:
                remaining = bu - now
                if remaining <= 0:
                    r["ban_status"] = "expired"
                    r["ban_remaining"] = 0
                else:
                    r["ban_status"] = "temp"
                    r["ban_remaining"] = remaining
            else:
                r["ban_status"] = "perm"
                r["ban_remaining"] = 0
        else:
            r["ban_status"] = "active"
            r["ban_remaining"] = 0
    return rows

@app.post("/api/admin/ban/{uid}")
def ban_user(uid: int, body: BanRequest, request: Request):
    require_admin(request)
    ban_until = (int(time.time()) + body.duration) if body.duration > 0 else 0
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "UPDATE users SET is_banned=1, ban_until=%s WHERE id=%s AND is_admin=0",
            (ban_until, uid)
        )
    db.commit()
    db.close()
    return {"ok": True}

@app.post("/api/admin/unban/{uid}")
def unban_user(uid: int, request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("UPDATE users SET is_banned=0, ban_until=0 WHERE id=%s", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

@app.put("/api/admin/user/{uid}")
def update_user(uid: int, body: UserUpdate, request: Request):
    me = require_admin(request)
    fields, vals = [], []
    if body.name is not None:
        fields.append("name=%s"); vals.append(_sanitize_text(body.name, 100))
    if body.email is not None:
        fields.append("email=%s"); vals.append(body.email.lower().strip()[:120])
    if body.is_admin is not None:
        if uid == me["id"]:
            raise HTTPException(400, "Не можна змінити власну роль")
        fields.append("is_admin=%s"); vals.append(1 if body.is_admin else 0)
    if body.notes is not None:
        fields.append("notes=%s"); vals.append(body.notes[:1000])
    if not fields:
        return {"ok": True}
    vals.append(uid)
    db = get_db()
    with db.cursor() as c:
        c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=%s", vals)
    db.commit()
    db.close()
    return {"ok": True}

@app.delete("/api/admin/user/{uid}")
def delete_user(uid: int, request: Request):
    me = require_admin(request)
    if uid == me["id"]:
        raise HTTPException(400, "Не можна видалити власний акаунт")
    db = get_db()
    with db.cursor() as c:
        c.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid,))
    db.commit()
    db.close()
    return {"ok": True}

class RoleUpdate(BaseModel):
    role: str

@app.put("/api/admin/users/{uid}/role")
def set_user_role(uid: int, body: RoleUpdate, request: Request):
    me = require_admin(request)
    ip = _get_ip(request)
    if uid == me["id"]:
        raise HTTPException(400, "Не можна змінити власну роль")
    role = body.role.strip()
    if role not in ("admin", "moder", "user"):
        raise HTTPException(400, "Невірна роль")
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT email, role FROM users WHERE id=%s", (uid,))
        target = c.fetchone()
        c.execute("UPDATE users SET role=%s, is_admin=%s WHERE id=%s",
                  (role, 1 if role == "admin" else 0, uid))
    db.commit()
    db.close()
    old_role = target['role'] if target else '?'
    target_email = target['email'] if target else '?'
    sec_log("ROLE_CHANGE", ip, f"uid={uid} email={target_email} {old_role}->{role} by={me.get('email','?')}")
    return {"ok": True}

@app.put("/api/admin/color")
def update_color(c_body: ColorUpdate, request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') "
            "ON DUPLICATE KEY UPDATE value=%s",
            (c_body.key, c_body.value, c_body.value)
        )
    db.commit()
    db.close()
    cache_delete("colors")
    return {"ok": True}

@app.put("/api/admin/colors/batch")
def update_colors_batch(colors: List[ColorUpdate], request: Request):
    me = require_admin(request)
    ip = _get_ip(request)
    db = get_db()
    with db.cursor() as c:
        for col in colors:
            c.execute(
                "INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') "
                "ON DUPLICATE KEY UPDATE value=%s",
                (col.key, col.value, col.value)
            )
    db.commit()
    db.close()
    cache_delete("colors")
    sec_log("COLORS_BATCH", ip, f"keys={len(colors)} by={me.get('email','?')}")
    return {"ok": True}

class SmtpTestReq(BaseModel):
    to: str

@app.post("/api/admin/email/test")
def email_test(body: SmtpTestReq, request: Request):
    """Надсилає тестовий лист для перевірки SMTP."""
    require_admin(request)
    to = body.to.strip()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', to):
        raise HTTPException(400, "Невірний email для тесту")
    html = ("<h2 style='color:#00aadd'>✅ SMTP працює!</h2>"
            "<p>Тестовий лист надіслано з адмін-панелі <b>Зоряна Пам'ять</b>.</p>"
            "<p style='color:#888;font-size:12px'>Якщо ви отримали цей лист — "
            "налаштування пошти вірні.</p>")
    ok, err = _send_email(to, "Тест SMTP — Зоряна Пам'ять", html)
    if not ok:
        raise HTTPException(503, err)
    return {"ok": True, "message": f"Тестовий лист надіслано на {to}"}

# ── Installer endpoints ────────────────────────────────────────────────────────
# Активні ТІЛЬКИ поки існує файл install.html.
# Після успішної установки install.html видаляється — всі endpoints повертають 403.

_INSTALL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "install.html")

def _install_guard():
    if not os.path.isfile(_INSTALL_FILE):
        raise HTTPException(403, "Інсталятор вже завершено або недоступний")

@app.get("/install")
@app.get("/install.html")
def install_page():
    if not os.path.isfile(_INSTALL_FILE):
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/", status_code=302)
    return FileResponse(_INSTALL_FILE)

class InstallDbParams(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    name: str = "zoryana_pamyat"

class InstallSmtpParams(BaseModel):
    host:    str = ""
    port:    int = 587
    user:    str = ""
    password: str = ""
    from_:   str = ""
    secure:  str = "starttls"
    enabled: bool = False

class InstallSiteParams(BaseModel):
    base_url:         str = "http://127.0.0.1:8000"
    oauth_redirect:   str = ""
    allowed_origins:  str = ""
    environment:      str = "production"

class InstallAdminParams(BaseModel):
    name:     str
    email:    str
    password: str

class InstallRunParams(BaseModel):
    db:    InstallDbParams
    site:  InstallSiteParams
    admin: InstallAdminParams
    smtp:  InstallSmtpParams = InstallSmtpParams()

@app.post("/api/install/test-db")
def install_test_db(body: InstallDbParams):
    _install_guard()
    try:
        conn = pymysql.connect(
            host=body.host, port=body.port,
            user=body.user, password=body.password,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        with conn.cursor() as c:
            c.execute("SELECT VERSION() AS v")
            ver = (c.fetchone() or {}).get("v", "")
            c.execute(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",
                (body.name,)
            )
            db_exists = c.fetchone() is not None
        conn.close()
        return {"ok": True, "version": ver, "db_exists": db_exists}
    except Exception as e:
        raise HTTPException(400, f"Помилка підключення: {e}")

@app.post("/api/install/run")
def install_run(body: InstallRunParams):
    _install_guard()

    # Валідація
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', body.admin.email):
        raise HTTPException(400, "Невірний email адміністратора")
    if len(body.admin.password) < 8:
        raise HTTPException(400, "Пароль має бути не менше 8 символів")
    if not body.site.base_url.startswith("http"):
        raise HTTPException(400, "SITE_BASE_URL має починатись з http:// або https://")

    progress = []
    conn = None
    try:
        # 1. Підключення до MySQL
        progress.append("Підключення до БД...")
        conn = pymysql.connect(
            host=body.db.host, port=body.db.port,
            user=body.db.user, password=body.db.password,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )

        # 2. Створення бази даних
        progress.append("Створення бази даних...")
        with conn.cursor() as c:
            c.execute(
                f"CREATE DATABASE IF NOT EXISTS `{body.db.name}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            c.execute(f"USE `{body.db.name}`")
        conn.commit()

        # 3. Створення таблиці users (мінімум для адміна)
        progress.append("Створення таблиць...")
        with conn.cursor() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id        INT PRIMARY KEY AUTO_INCREMENT,
                    name      VARCHAR(100) NOT NULL DEFAULT '',
                    email     VARCHAR(120) NOT NULL UNIQUE,
                    password  VARCHAR(255) NOT NULL,
                    is_admin  TINYINT DEFAULT 0,
                    is_banned TINYINT DEFAULT 0,
                    role      VARCHAR(20) NOT NULL DEFAULT 'user',
                    last_seen INT DEFAULT 0,
                    created   INT DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()

        # 4. Створення адміністратора
        progress.append("Створення облікового запису адміністратора...")
        admin_hash = hash_pass(body.admin.password)
        with conn.cursor() as c:
            c.execute("SELECT id FROM users WHERE email=%s", (body.admin.email,))
            if c.fetchone():
                c.execute(
                    "UPDATE users SET password=%s, is_admin=1, role='admin', name=%s WHERE email=%s",
                    (admin_hash, _sanitize_text(body.admin.name), body.admin.email)
                )
            else:
                c.execute(
                    "INSERT INTO users (name,email,password,is_admin,role,created) VALUES (%s,%s,%s,1,'admin',UNIX_TIMESTAMP())",
                    (_sanitize_text(body.admin.name), body.admin.email, admin_hash)
                )
        conn.close()
        conn = None

        # 5. Запис .env файлу
        progress.append("Запис файлу конфігурації .env...")
        oauth_base = (body.site.oauth_redirect or body.site.base_url).rstrip("/")
        base_url   = body.site.base_url.rstrip("/")
        origins    = body.site.allowed_origins.strip() or base_url
        secret_key = secrets.token_hex(32)
        smtp_enabled = "1" if body.smtp.enabled else "0"

        env_lines = [
            "# Зоряна Пам'ять — auto-generated by installer",
            f"# Дата: {__import__('datetime').date.today()}",
            "",
            "# ── База даних ──────────────────────────",
            f"DB_HOST={body.db.host}",
            f"DB_PORT={body.db.port}",
            f"DB_USER={body.db.user}",
            f"DB_PASS={body.db.password}",
            f"DB_NAME={body.db.name}",
            "",
            "# ── Домен ───────────────────────────────",
            f"SITE_BASE_URL={base_url}",
            f"OAUTH_REDIRECT_BASE={oauth_base}",
            f"ALLOWED_ORIGINS={origins}",
            "",
            "# ── Gunicorn ────────────────────────────",
            "GUNICORN_BIND=127.0.0.1:8000",
            "",
            "# ── Безпека ─────────────────────────────",
            f"ENVIRONMENT={body.site.environment}",
            f"SECRET_KEY={secret_key}",
            "",
            "# ── Redis (опціонально) ─────────────────",
            "# REDIS_URL=redis://127.0.0.1:6379/0",
            "",
            "# ── Google OAuth ────────────────────────",
            "GOOGLE_CLIENT_ID=",
            "GOOGLE_CLIENT_SECRET=",
            "",
            "# ── SMTP ────────────────────────────────",
            f"SMTP_HOST={body.smtp.host}",
            f"SMTP_PORT={body.smtp.port}",
            f"SMTP_USER={body.smtp.user}",
            f"SMTP_PASS={body.smtp.password}",
            f"SMTP_FROM={body.smtp.from_}",
            f"SMTP_ENABLED={smtp_enabled}",
        ]
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(env_lines) + "\n")

        # 6. Видалення інсталятора
        progress.append("Видалення інсталятора...")
        try:
            os.remove(_INSTALL_FILE)
        except Exception as e:
            raise HTTPException(500, f"Не вдалось видалити install.html: {e}")

        return {
            "ok": True,
            "progress": progress,
            "message": (
                "Встановлення успішне! "
                f"Адмін: {body.admin.email}. "
                "Перезапустіть сервер для застосування налаштувань."
            ),
            "restart_cmd": "sudo systemctl restart zoryna",
        }

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try: conn.close()
            except: pass
        raise HTTPException(500, f"Помилка встановлення ({progress[-1] if progress else ''}): {e}")

@app.post("/api/admin/sea-svg")
async def upload_sea_svg(
    request: Request,
    file: UploadFile = File(...)
):
    require_admin(request)
    raw = await file.read()
    if len(raw) > 500_000:
        raise HTTPException(400, "SVG файл занадто великий (макс 500 КБ)")
    try:
        svg_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "Файл не є валідним UTF-8 SVG")
    if "<svg" not in svg_text.lower():
        raise HTTPException(400, "Файл не є SVG")
    svg_text = _sanitize_svg(svg_text)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'SVG карта морів') "
            "ON DUPLICATE KEY UPDATE value=%s",
            ("sea_svg_content", svg_text, svg_text)
        )
    db.commit()
    db.close()
    cache_delete("colors")
    return {"ok": True, "bytes": len(raw)}

@app.delete("/api/admin/sea-svg")
def delete_sea_svg(request: Request):
    require_admin(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("DELETE FROM colors WHERE `key`='sea_svg_content'")
    db.commit()
    db.close()
    cache_delete("colors")
    return {"ok": True}

@app.put("/api/admin/label/{lid}")
def update_label(lid: int, lbl: LabelUpdate, request: Request):
    require_admin(request)
    db = get_db()
    fields, vals = ["x=%s", "y=%s"], [lbl.x, lbl.y]
    if lbl.name  is not None: fields.append("name=%s");  vals.append(lbl.name)
    if lbl.color is not None: fields.append("color=%s"); vals.append(lbl.color)
    if lbl.size  is not None: fields.append("size=%s");  vals.append(lbl.size)
    vals.append(lid)
    with db.cursor() as c:
        c.execute("UPDATE map_labels SET " + ",".join(fields) + " WHERE id=%s", vals)
    db.commit()
    db.close()
    cache_delete("labels")
    return {"ok": True}

@app.get("/api/admin/stats")
def admin_stats(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        # 5 запитів → 3 (оптимізація)
        c.execute(
            "SELECT COUNT(*) AS cnt FROM memorials"
        )
        total = c.fetchone()["cnt"]
        c.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(likes),0) AS likes FROM memorials WHERE approved=1"
        )
        row1 = c.fetchone()
        approved, likes = row1["cnt"], row1["likes"]
        c.execute(
            "SELECT COUNT(*) AS cnt FROM memorials WHERE approved=0"
        )
        pend = c.fetchone()["cnt"]
        c.execute(
            "SELECT COUNT(*) AS cnt FROM users"
        )
        users = c.fetchone()["cnt"]
    db.close()
    online_real = len(connected) + len(_online_pings)
    with _bot_lock:
        online_bots = _bot_online_count
    now_hour = int(time.time() // 3600) * 3600
    # visitors_24h: з БД (переживає рестарт) + поточна година з пам'яті
    try:
        db2 = get_db()
        with db2.cursor() as c2:
            cutoff = now_hour - 23 * 3600
            c2.execute(
                "SELECT COALESCE(SUM(human_views),0) AS v FROM hourly_stats WHERE hour_ts >= %s AND hour_ts < %s",
                (cutoff, now_hour)
            )
            db_visitors = int(c2.fetchone()["v"])
        db2.close()
    except Exception:
        db_visitors = 0
    visitors_24h = db_visitors + _human_pv_hourly.get(now_hour, 0)
    return {
        "total": total, "approved": approved, "pending": pend,
        "users": users, "likes": likes,
        "online": online_real + online_bots,
        "online_real": online_real,
        "online_bots": online_bots,
        "online_users": _online_users_list(),
        "visitors_24h": visitors_24h,
    }


@app.get("/api/admin/server-stats")
def server_stats(request: Request):
    require_moder(request)
    # CPU / RAM
    if _HAS_PSUTIL:
        cpu   = round(_psutil.cpu_percent(interval=0.2), 1)
        mem   = _psutil.virtual_memory()
        ram_p = round(mem.percent, 1)
        ram_gb_used  = round(mem.used  / 1024**3, 2)
        ram_gb_total = round(mem.total / 1024**3, 1)
    else:
        cpu = ram_p = ram_gb_used = ram_gb_total = None

    # Uptime
    uptime_sec = int(time.time() - _server_start)
    h, r = divmod(uptime_sec, 3600)
    m, s = divmod(r, 60)
    uptime_str = f"{h}г {m:02d}х {s:02d}с"

    # Visits last 24h (per hour)
    now_hour = int(time.time() // 3600) * 3600
    visits_24h = []
    for i in range(23, -1, -1):
        ts = now_hour - i * 3600
        visits_24h.append({"ts": ts, "count": _visits_hourly.get(ts, 0)})

    return {
        "cpu":          cpu,
        "ram_percent":  ram_p,
        "ram_used_gb":  ram_gb_used,
        "ram_total_gb": ram_gb_total,
        "online":       len(connected),
        "uptime":       uptime_str,
        "total_requests": _request_count,
        "visits_24h":   visits_24h,
    }


@app.get("/api/admin/realtime-12h")
def realtime_12h(request: Request):
    require_moder(request)
    now_h = int(time.time() // 3600) * 3600
    hours = [now_h - i * 3600 for i in range(11, -1, -1)]

    visits = [_pageviews_hourly.get(h, 0) for h in hours]
    db_queries = [_db_queries_hourly.get(h, 0) for h in hours]

    # Боти з bot_visits за останні 12 годин
    cutoff = hours[0]
    bots_total = [0] * 12
    bots_by_name: dict = {}
    try:
        db = get_db()
        with db.cursor() as c:
            c.execute(
                "SELECT FLOOR(created_at/3600)*3600 AS h, bot_name, COUNT(*) AS cnt"
                " FROM bot_visits WHERE created_at >= %s GROUP BY h, bot_name",
                (cutoff,)
            )
            rows = c.fetchall()
        db.close()
        bots_map: dict = {}
        for row in rows:
            h_val = int(row["h"])
            name  = row["bot_name"]
            cnt   = int(row["cnt"])
            bots_map.setdefault(h_val, {})
            bots_map[h_val][name] = cnt
            bots_by_name[name] = bots_by_name.get(name, 0) + cnt
        bots_total = [sum(bots_map.get(h, {}).values()) for h in hours]
    except Exception:
        pass

    # CPU/RAM — середнє за кожну годину
    cpu_avg, ram_avg = [], []
    for h in hours:
        snaps = [s for s in _cpu_ram_snapshots if h <= s["ts"] < h + 3600]
        cpu_avg.append(round(sum(s["cpu"] for s in snaps) / len(snaps), 1) if snaps else None)
        ram_avg.append(round(sum(s["ram"] for s in snaps) / len(snaps), 1) if snaps else None)

    labels = [time.strftime("%H:00", time.localtime(h)) for h in hours]
    return {
        "labels":      labels,
        "visits":      visits,
        "bots_total":  bots_total,
        "bots_by_name": sorted(bots_by_name.items(), key=lambda x: -x[1])[:5],
        "db_queries":  db_queries,
        "cpu":         cpu_avg,
        "ram":         ram_avg,
    }


# ── Хвилина мовчання ─────────────────────────────────────

@app.get("/api/minute-silence/settings")
def get_silence_settings():
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT `key`, `value` FROM minute_silence_settings")
        rows = c.fetchall()
    db.close()
    return {r["key"]: r["value"] for r in rows}


@app.post("/api/admin/minute-silence/settings")
async def save_silence_settings(request: Request):
    require_moder(request)
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "Очікується dict")
    _allowed = {
        "enabled", "time_hhmm", "duration_sec",
        "overlay_text", "overlay_subtext", "overlay_height", "overlay_bg_color", "overlay_text_color",
        "clock_enabled", "clock_x", "clock_y", "clock_font", "clock_font_size", "clock_opacity", "clock_color", "clock_bg",
        "audio_volume",
    }
    db = get_db()
    with db.cursor() as c:
        for k, v in data.items():
            if k not in _allowed:
                continue
            v = _sanitize_text(str(v))[:500]
            c.execute(
                "INSERT INTO minute_silence_settings (`key`,`value`) VALUES (%s,%s) "
                "ON DUPLICATE KEY UPDATE `value`=%s",
                (k, v, v)
            )
    db.commit()
    db.close()
    return {"ok": True}


@app.post("/api/admin/minute-silence/audio")
async def upload_silence_audio(request: Request, file: UploadFile = File(...)):
    require_moder(request)
    raw = await file.read()
    if len(raw) > 10_000_000:
        raise HTTPException(400, "Аудіо файл занадто великий (макс 10 МБ)")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".mp3", ".wav", ".ogg", ".m4a"):
        raise HTTPException(400, "Дозволені формати: mp3, wav, ogg, m4a")
    if not _check_audio_magic(raw):
        raise HTTPException(400, "Невалідний формат аудіо файлу")
    fname = "silence_audio" + ext
    fpath = os.path.join("img", "audio", fname)
    with open(fpath, "wb") as fh:
        fh.write(raw)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO minute_silence_settings (`key`,`value`) VALUES ('audio_file',%s) "
            "ON DUPLICATE KEY UPDATE `value`=%s",
            (fname, fname)
        )
    db.commit()
    db.close()
    return {"ok": True, "audio_file": fname}


@app.post("/api/admin/upload/logo")
async def upload_logo(request: Request, file: UploadFile = File(...)):
    require_moder(request)
    _ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED:
        raise HTTPException(400, f"Дозволені формати: {', '.join(_ALLOWED)}")
    raw = await file.read()
    if len(raw) > 2_000_000:
        raise HTTPException(400, "Файл завеликий (макс 2 МБ)")
    if not _check_image_magic(raw, ext):
        raise HTTPException(400, "Невалідний формат файлу")
    safe_name = f"logo_{int(time.time())}{ext}"
    with open(os.path.join("img", safe_name), "wb") as fh:
        fh.write(raw)
    return {"url": f"/img/{safe_name}"}


@app.post("/api/admin/minute-silence/test-start")
def silence_test_start(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO minute_silence_settings (`key`,`value`) VALUES ('force_active','1') "
            "ON DUPLICATE KEY UPDATE `value`='1'"
        )
    db.commit()
    db.close()
    return {"ok": True}


@app.post("/api/admin/minute-silence/test-stop")
def silence_test_stop(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "INSERT INTO minute_silence_settings (`key`,`value`) VALUES ('force_active','0') "
            "ON DUPLICATE KEY UPDATE `value`='0'"
        )
    db.commit()
    db.close()
    return {"ok": True}


# ── Дашборд статистики ────────────────────────────────────

@app.get("/api/admin/dashboard")
def admin_dashboard(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        # Топ-5 за лайками
        c.execute(
            "SELECT id, CONCAT(last,' ',first,IF(mid<>'' AND mid IS NOT NULL,CONCAT(' ',mid),'')) AS name,"
            " likes FROM memorials WHERE approved=1 ORDER BY likes DESC LIMIT 5"
        )
        top_liked = c.fetchall()

        # Пошуки за останні 7 днів
        c.execute(
            "SELECT DATE(FROM_UNIXTIME(created_at)) AS day, COUNT(*) AS cnt"
            " FROM search_logs"
            " WHERE created_at >= UNIX_TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY))"
            " GROUP BY day ORDER BY day ASC"
        )
        searches_7d = c.fetchall()

        # Топ-10 запитів за 30 днів
        c.execute(
            "SELECT query, COUNT(*) AS cnt FROM search_logs"
            " WHERE created_at >= UNIX_TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 30 DAY))"
            " GROUP BY LOWER(TRIM(query)) ORDER BY cnt DESC LIMIT 10"
        )
        top_queries = c.fetchall()

        # Останні 20 пошуків
        c.execute(
            "SELECT query, results_count, created_at FROM search_logs ORDER BY id DESC LIMIT 20"
        )
        recent_searches = c.fetchall()

        # Користувачі за роллю
        c.execute("SELECT role, COUNT(*) AS cnt FROM users GROUP BY role")
        users_by_role = c.fetchall()

        # Лайки за останні 7 днів
        c.execute(
            "SELECT DATE(FROM_UNIXTIME(ts)) AS day, COUNT(*) AS cnt"
            " FROM likes_log"
            " WHERE ts >= UNIX_TIMESTAMP(DATE_SUB(CURDATE(), INTERVAL 6 DAY))"
            " GROUP BY day ORDER BY day ASC"
        )
        likes_7d = c.fetchall()

        # Кількість записів за статусом
        c.execute("SELECT approved, COUNT(*) AS cnt FROM memorials GROUP BY approved")
        mem_status_rows = c.fetchall()

        # Відвідування за останні 30 днів (з daily_stats)
        c.execute(
            "SELECT date, views FROM daily_stats"
            " WHERE date >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)"
            " ORDER BY date ASC"
        )
        daily_30d_rows = c.fetchall()

    db.close()

    # Merge today's in-memory count into daily_30d
    today_str = time.strftime("%Y-%m-%d")
    today_mem = _visits_daily.get(today_str, 0)
    daily_map = {str(r["date"]): r["views"] for r in daily_30d_rows}
    if today_str in daily_map:
        daily_map[today_str] = max(daily_map[today_str], today_mem)
    else:
        daily_map[today_str] = today_mem

    mem_status = {"approved": 0, "pending": 0}
    for r in mem_status_rows:
        if r["approved"] == 1:
            mem_status["approved"] = r["cnt"]
        else:
            mem_status["pending"] = r["cnt"]

    daily_30d = [{"day": k, "cnt": v} for k, v in sorted(daily_map.items())]

    return {
        "top_liked":       [{"id": r["id"], "name": r["name"], "likes": r["likes"]} for r in top_liked],
        "searches_7d":     [{"day": str(r["day"]), "cnt": r["cnt"]} for r in searches_7d],
        "top_queries":     [{"query": r["query"], "cnt": r["cnt"]} for r in top_queries],
        "recent_searches": [{"query": r["query"], "results": r["results_count"], "ts": r["created_at"]} for r in recent_searches],
        "users_by_role":   [{"role": r["role"] or "user", "cnt": r["cnt"]} for r in users_by_role],
        "likes_7d":        [{"day": str(r["day"]), "cnt": r["cnt"]} for r in likes_7d],
        "mem_status":      mem_status,
        "daily_30d":       daily_30d,
    }


# ── SEO / Пошукові боти ──────────────────────────────────

@app.get("/api/admin/seo-stats")
def seo_stats(request: Request):
    require_moder(request)
    # Flush pending queue so data is fresh
    _flush_bot_queue()
    now = int(time.time())
    ts_30d = now - 30 * 86400
    ts_7d  = now - 7  * 86400
    db = get_db()
    with db.cursor() as c:
        # Загальна кількість візитів ботів (30 днів)
        c.execute(
            "SELECT COUNT(*) AS cnt FROM bot_visits WHERE created_at >= %s", (ts_30d,)
        )
        total_30d = c.fetchone()["cnt"]

        # Унікальних ботів (30 днів)
        c.execute(
            "SELECT COUNT(DISTINCT bot_name) AS cnt FROM bot_visits WHERE created_at >= %s", (ts_30d,)
        )
        unique_bots = c.fetchone()["cnt"]

        # Візити по ботах (30 днів)
        c.execute(
            "SELECT bot_name, COUNT(*) AS cnt FROM bot_visits"
            " WHERE created_at >= %s GROUP BY bot_name ORDER BY cnt DESC",
            (ts_30d,)
        )
        by_bot = c.fetchall()

        # Візити по днях і ботах (7 днів) — для графіка
        c.execute(
            "SELECT DATE(FROM_UNIXTIME(created_at)) AS day, bot_name, COUNT(*) AS cnt"
            " FROM bot_visits WHERE created_at >= %s"
            " GROUP BY day, bot_name ORDER BY day ASC",
            (ts_7d,)
        )
        daily_by_bot = c.fetchall()

        # Топ-15 сторінок (30 днів)
        c.execute(
            "SELECT path, COUNT(*) AS cnt, COUNT(DISTINCT bot_name) AS bots"
            " FROM bot_visits WHERE created_at >= %s"
            " GROUP BY path ORDER BY cnt DESC LIMIT 15",
            (ts_30d,)
        )
        top_pages = c.fetchall()

        # Останні 30 візитів
        c.execute(
            "SELECT bot_name, path, created_at FROM bot_visits ORDER BY id DESC LIMIT 30"
        )
        recent = c.fetchall()

    db.close()
    return {
        "total_30d":    total_30d,
        "unique_bots":  unique_bots,
        "by_bot":       [{"bot": r["bot_name"], "cnt": r["cnt"]} for r in by_bot],
        "daily_by_bot": [{"day": str(r["day"]), "bot": r["bot_name"], "cnt": r["cnt"]} for r in daily_by_bot],
        "top_pages":    [{"path": r["path"], "cnt": r["cnt"], "bots": r["bots"]} for r in top_pages],
        "recent":       [{"bot": r["bot_name"], "path": r["path"], "ts": r["created_at"]} for r in recent],
    }


# ── SEO ───────────────────────────────────────────────────

def _google_index_notify(url: str, notification_type: str = "URL_UPDATED"):
    """Send URL to Google Indexing API. No-op if not configured."""
    key_file = os.getenv("GOOGLE_INDEXING_KEY_FILE")
    if not key_file or not os.path.exists(key_file):
        return {"ok": False, "reason": "not configured"}
    try:
        import google.auth.crypt
        import google.auth.jwt

        with open(key_file) as _f:
            _sa = json.load(_f)

        _now = int(time.time())
        _payload = {
            "iss": _sa["client_email"],
            "sub": _sa["client_email"],
            "aud": "https://oauth2.googleapis.com/token",
            "iat": _now,
            "exp": _now + 3600,
            "scope": "https://www.googleapis.com/auth/indexing",
        }
        _signer = google.auth.crypt.RSASigner.from_service_account_info(_sa)
        _jwt = google.auth.jwt.encode(_signer, _payload)
        if isinstance(_jwt, bytes):
            _jwt = _jwt.decode()

        _token_body = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": _jwt,
        }).encode()
        _token_req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=_token_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(_token_req, timeout=10) as _r:
            _access_token = json.loads(_r.read())["access_token"]

        body = json.dumps({"url": url, "type": notification_type}).encode()
        req = urllib.request.Request(
            "https://indexing.googleapis.com/v3/urlNotifications:publish",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_access_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = resp.read().decode()
        try:
            db2 = get_db()
            with db2.cursor() as c2:
                c2.execute(
                    "INSERT INTO seo_index_log (url,notification_type,status,response,created_at)"
                    " VALUES (%s,%s,'sent',%s,%s)",
                    (url, notification_type, resp_body[:2000], int(time.time()))
                )
            db2.commit(); db2.close()
        except Exception:
            pass
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _build_memorial_seo(row: dict) -> dict:
    """Build full SEO context dict from a memorial row."""
    full_name = ' '.join(filter(None, [row.get('last'), row.get('first'), row.get('mid')])).strip() or 'Захисник'
    slug      = row.get('slug') or str(row['id'])
    canonical_url = f"{_SITE_BASE_URL}/memorial/{slug}"

    # ── Photo: real vs placeholder ────────────────────────
    photo = (row.get('photo') or '').strip()
    has_real_photo = bool(photo and len(photo) > 5 and '/foto_false' not in photo)
    if has_real_photo:
        photo_abs = photo if photo.startswith('http') else f"{_SITE_BASE_URL}{photo}"
    else:
        photo_abs = ''

    title       = gen_seo_title(row)
    description = gen_seo_description(row)
    keywords    = gen_seo_keywords(row)

    # ── ImageObject (only when real photo exists) ─────────
    image_obj = None
    if has_real_photo:
        image_obj = {
            "@type":       "ImageObject",
            "url":         photo_abs,
            "contentUrl":  photo_abs,
            "description": f"{full_name} — фото захисника України",
        }

    # ── Person JSON-LD ────────────────────────────────────
    person_ld: dict = {
        "@context":    "https://schema.org",
        "@type":       "Person",
        "@id":         canonical_url + "#person",
        "name":        full_name,
        "url":         canonical_url,
        "description": description,
    }
    if image_obj:
        person_ld["image"] = image_obj
    if row.get('first'):
        person_ld["givenName"]  = row['first']
    if row.get('last'):
        person_ld["familyName"] = row['last']
    if row.get('rank'):
        person_ld["jobTitle"] = row['rank']
    if row.get('grp'):
        person_ld["alternateName"] = row['grp']
    if row.get('birth'):
        person_ld["birthDate"] = row['birth']
    if row.get('death'):
        person_ld["deathDate"] = row['death']
    if row.get('loc'):
        person_ld["deathPlace"] = {"@type": "Place", "name": row['loc']}
    if row.get('unit'):
        person_ld["memberOf"] = {"@type": "MilitaryOrganization", "name": row['unit']}
    person_ld["nationality"] = {"@type": "Country", "name": "Україна"}

    # ── Article JSON-LD ───────────────────────────────────
    article_ld: dict = {
        "@context":    "https://schema.org",
        "@type":       "Article",
        "headline":    title,
        "description": description,
        "url":         canonical_url,
        "mainEntity":  {"@id": canonical_url + "#person"},
        "about":       {"@id": canonical_url + "#person"},
        "publisher": {
            "@type": "Organization",
            "name":  "Зоряна Пам'ять",
            "url":   _SITE_BASE_URL,
        },
        "inLanguage": "uk",
    }
    if image_obj:
        article_ld["image"] = image_obj
    if row.get('death'):
        _death_date = str(row['death'])[:10]
        article_ld["datePublished"] = _death_date
        article_ld["dateModified"]  = _death_date

    # ── BreadcrumbList JSON-LD (2 рівні, без фейкового середнього) ────
    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type":    "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Головна", "item": _SITE_BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": full_name,  "item": canonical_url},
        ]
    }

    return {
        "title":         title,
        "description":   description,
        "keywords":      keywords,
        "full_name":     full_name,
        "first_name":    row.get('first') or '',
        "last_name":     row.get('last')  or '',
        "slug":          slug,
        "canonical_url": canonical_url,
        "og_image":      photo_abs,
        "photo_url":     (photo if has_real_photo else '/img/foto_false.png'),
        "json_ld":       json.dumps(person_ld,   ensure_ascii=False),
        "article_ld":    json.dumps(article_ld,  ensure_ascii=False),
        "breadcrumb_ld": json.dumps(breadcrumb_ld, ensure_ascii=False),
        "rank":          row.get('rank')     or '',
        "unit":          row.get('unit')     or '',
        "position":      row.get('position') or '',
        "grp":           row.get('grp')      or '',
        "birth":         row.get('birth')    or '',
        "death":         row.get('death')    or '',
        "loc":           row.get('loc')      or '',
        "bury":          row.get('bury')     or '',
        "descr":         row.get('descr')    or '',
    }


@app.get("/memorial/{slug}")
def memorial_seo_page(slug: str, request: Request):
    cache_key = f"seo:{slug}"
    cached_html = cache_get(cache_key)
    if cached_html:
        return HTMLResponse(content=cached_html, headers={"Cache-Control": "public, max-age=300"})

    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT * FROM memorials WHERE slug=%s AND approved=1",
            (slug,)
        )
        row = c.fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Меморіал не знайдено")

    ctx = _build_memorial_seo(row)
    try:
        tmpl = _TEMPLATES.env.get_template("memorial.html")
        html_str = tmpl.render(**ctx)
    except Exception as e:
        raise HTTPException(500, f"Template error: {e}")
    cache_set(cache_key, html_str, ttl=300)
    return HTMLResponse(content=html_str, headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/memorial/by-slug/{slug}")
def get_memorial_by_slug(slug: str):
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id,last,first,mid,birth,death,bury,loc,circ,descr,photo,color,pos_x,pos_y,"
            "grp,`rank`,`position`,unit,likes,rating,video_url,slug "
            "FROM memorials WHERE slug=%s AND approved=1",
            (slug,)
        )
        row = c.fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Не знайдено")
    return row


@app.get("/sitemap.xml")
def sitemap():
    cached = cache_get("sitemap")
    if cached:
        return StreamingResponse(io.StringIO(cached), media_type="application/xml")

    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT slug, last, first, death, photo, video_url, descr FROM memorials "
            "WHERE approved=1 AND slug IS NOT NULL AND slug!='' ORDER BY id"
        )
        rows = c.fetchall()
    db.close()

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"',
        '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
    ]
    lines.append(
        f'  <url><loc>{_SITE_BASE_URL}/</loc>'
        f'<priority>1.0</priority><changefreq>daily</changefreq></url>'
    )
    for r in rows:
        loc  = f"{_SITE_BASE_URL}/memorial/{r['slug']}"
        name = f"{r.get('last','')} {r.get('first','')}".strip()
        lastmod = ""
        if r.get('death'):
            try:
                d = str(r['death'])[:10]
                if len(d) == 10:
                    lastmod = f"\n    <lastmod>{d}</lastmod>"
            except Exception:
                pass
        # Image tag if photo exists
        img_block = ""
        photo = (r.get('photo') or '').strip()
        if photo and len(photo) > 5:
            photo_abs = photo if photo.startswith('http') else f"{_SITE_BASE_URL}{photo}"
            img_block = (
                f"\n    <image:image>"
                f"<image:loc>{photo_abs}</image:loc>"
                f"<image:title>{name} — фото захисника України</image:title>"
                f"<image:caption>{name}, Захисник України</image:caption>"
                f"</image:image>"
            )
        # Video tag if YouTube URL
        vid_block = ""
        video_url = (r.get('video_url') or '').strip()
        if video_url:
            import re as _re
            _vm = _re.search(r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})', video_url)
            if _vm:
                _vid_id = _vm.group(1)
                _vdesc = (r.get('descr') or '')[:100].replace('&', '&amp;').replace('<', '').replace('>', '')
                _vtitle = f"{name} — відео спогад"
                vid_block = (
                    f"\n    <video:video>"
                    f"<video:thumbnail_loc>https://img.youtube.com/vi/{_vid_id}/hqdefault.jpg</video:thumbnail_loc>"
                    f"<video:title>{_vtitle}</video:title>"
                    f"<video:description>{_vdesc}</video:description>"
                    f"<video:player_loc>https://www.youtube.com/embed/{_vid_id}</video:player_loc>"
                    f"<video:family_friendly>yes</video:family_friendly>"
                    f"</video:video>"
                )
        lines.append(
            f"  <url>\n    <loc>{loc}</loc>{lastmod}"
            f"\n    <priority>0.8</priority><changefreq>monthly</changefreq>"
            f"{img_block}{vid_block}\n  </url>"
        )
    lines.append('</urlset>')
    xml = "\n".join(lines)
    cache_set("sitemap", xml, ttl=600)
    return StreamingResponse(io.StringIO(xml), media_type="application/xml")


@app.get("/robots.txt")
def robots():
    content = (
        f"User-agent: *\n"
        f"Allow: /\n"
        f"Allow: /memorial/\n"
        f"Allow: /sitemap.xml\n"
        f"Disallow: /admin\n"
        f"Disallow: /api/\n\n"
        f"User-agent: Googlebot\n"
        f"Allow: /\n"
        f"Allow: /memorial/\n"
        f"Crawl-delay: 1\n\n"
        f"Sitemap: {_SITE_BASE_URL}/sitemap.xml\n"
    )
    return StreamingResponse(io.StringIO(content), media_type="text/plain")


@app.get("/api/admin/seo-dashboard")
def admin_seo_dashboard(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1")
        total = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1 AND slug IS NOT NULL AND slug!=''")
        with_slug = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1 AND (slug IS NULL OR slug='')")
        without_slug = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1 AND video_url IS NOT NULL AND video_url!=''")
        with_video = c.fetchone()["cnt"]
        c.execute("SELECT id,last,first,slug FROM memorials WHERE approved=1 AND slug IS NOT NULL AND slug!='' ORDER BY id LIMIT 20")
        sample_urls = c.fetchall()
        c.execute("SELECT url,notification_type,status,created_at FROM seo_index_log ORDER BY id DESC LIMIT 20")
        index_log = c.fetchall()
        # Per-field fill rates
        _t = total or 1
        _field_conditions = {
            'photo':      "photo IS NOT NULL AND photo!='' AND photo NOT LIKE '/img/foto_false%' AND LENGTH(photo)>5",
            'descr_full': "descr IS NOT NULL AND LENGTH(TRIM(descr))>=150",
            'descr_any':  "descr IS NOT NULL AND LENGTH(TRIM(descr))>0",
            'unit':       "unit IS NOT NULL AND unit!=''",
            'rank':       "`rank` IS NOT NULL AND `rank`!=''",
            'position':   "`position` IS NOT NULL AND `position`!=''",
            'death':      "death IS NOT NULL AND death!=''",
            'birth':      "birth IS NOT NULL AND birth!=''",
            'loc':        "loc IS NOT NULL AND loc!=''",
            'grp':        "grp IS NOT NULL AND grp!=''",
            'video':      "video_url IS NOT NULL AND video_url!=''",
        }
        field_stats = {}
        for key, cond in _field_conditions.items():
            c.execute(f"SELECT COUNT(*) AS n FROM memorials WHERE approved=1 AND {cond}")
            cnt = (c.fetchone() or {}).get('n', 0)
            field_stats[key] = {"count": cnt, "pct": round(cnt * 100 / _t)}
        # Fetch all rows for score analysis
        c.execute(
            "SELECT id, photo, descr, unit, `rank`, `position`, death, birth, loc, grp, last, first, mid "
            "FROM memorials WHERE approved=1"
        )
        all_rows = c.fetchall()
    db.close()

    # Score distribution + issue frequency aggregation
    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    scores = []
    worst_10 = []
    issue_freq: dict = {}
    for r in all_rows:
        s = calc_seo_score(r)
        grade_dist[s['grade']] = grade_dist.get(s['grade'], 0) + 1
        scores.append(s['score'])
        worst_10.append({
            "id":     r['id'],
            "name":   f"{r.get('last','')} {r.get('first','')}".strip(),
            "score":  s['score'],
            "grade":  s['grade'],
            "issues": s['issues'][:2],
        })
        for issue in s['issues']:
            issue_freq[issue] = issue_freq.get(issue, 0) + 1
    worst_10.sort(key=lambda x: x['score'])
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    top_issues = sorted(issue_freq.items(), key=lambda x: -x[1])[:6]

    google_configured = bool(
        os.getenv("GOOGLE_INDEXING_KEY_FILE") and
        os.path.exists(os.getenv("GOOGLE_INDEXING_KEY_FILE", ""))
    )
    return {
        "total":        total,
        "with_slug":    with_slug,
        "without_slug": without_slug,
        "with_video":   with_video,
        "sitemap_url":  f"{_SITE_BASE_URL}/sitemap.xml",
        "sitemap_count": with_slug,
        "avg_score":    avg_score,
        "grade_dist":   grade_dist,
        "worst_10":     worst_10[:10],
        "field_stats":  field_stats,
        "top_issues":   [{"text": t, "count": c} for t, c in top_issues],
        "sample_urls": [
            {"id": r["id"], "name": f"{r['last']} {r['first']}", "slug": r["slug"],
             "url": f"{_SITE_BASE_URL}/memorial/{r['slug']}"}
            for r in sample_urls
        ],
        "google_configured": google_configured,
        "index_log": [
            {"url": r["url"], "type": r["notification_type"], "status": r["status"], "ts": r["created_at"]}
            for r in index_log
        ],
    }


@app.post("/api/admin/seo/regenerate-slugs")
def regenerate_slugs(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT id, first, last FROM memorials WHERE slug IS NULL OR slug=''")
        rows = c.fetchall()
    updated = 0
    with db.cursor() as c:
        for r in rows:
            sl = make_slug(r['first'], r['last'], r['id'])
            try:
                c.execute("UPDATE memorials SET slug=%s WHERE id=%s", (sl, r['id']))
                updated += 1
            except Exception:
                pass
    db.commit()
    db.close()
    cache_delete("sitemap")
    return {"ok": True, "updated": updated}


@app.post("/api/admin/seo/ping-google")
def ping_google_indexing(request: Request):
    require_moder(request)
    key_file = os.getenv("GOOGLE_INDEXING_KEY_FILE")
    if not key_file or not os.path.exists(key_file or ""):
        return {"ok": False, "reason": "not configured"}
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT slug FROM memorials WHERE approved=1 AND slug IS NOT NULL AND slug!='' ORDER BY id DESC LIMIT 10"
        )
        rows = c.fetchall()
    db.close()
    results = []
    for r in rows:
        url = f"{_SITE_BASE_URL}/memorial/{r['slug']}"
        res = _google_index_notify(url)
        results.append({"url": url, **res})
    return {"ok": True, "results": results}


@app.get("/api/admin/seo/analyze/{mid}")
def seo_analyze_memorial(mid: int, request: Request):
    """Return SEO score + recommendations for a single memorial."""
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute("SELECT * FROM memorials WHERE id=%s", (mid,))
        row = c.fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Не знайдено")
    result = calc_seo_score(row)
    result["id"]       = mid
    result["name"]     = f"{row.get('last','')} {row.get('first','')}".strip()
    result["slug"]     = row.get('slug') or ''
    result["url"]      = f"{_SITE_BASE_URL}/memorial/{row['slug']}" if row.get('slug') else ''
    result["title"]    = gen_seo_title(row)
    result["descr_len"] = len((row.get('descr') or ''))
    return result


@app.get("/api/admin/seo/scores")
def seo_scores_all(request: Request, limit: int = Query(default=50, le=500), grade: str = ""):
    """Return memorials sorted by SEO score ascending (worst first)."""
    require_moder(request)
    ip = _get_ip(request)
    if not _rl.check(f"adm_seo_scores:{ip}", 10, 60):
        raise HTTPException(429, "Занадто багато запитів")
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id, last, first, mid, photo, descr, unit, `rank`, death, birth, loc, grp, slug "
            "FROM memorials WHERE approved=1 ORDER BY id"
        )
        rows = c.fetchall()
    db.close()

    scored = []
    for r in rows:
        s = calc_seo_score(r)
        if grade and s['grade'] != grade.upper():
            continue
        scored.append({
            "id":    r['id'],
            "name":  f"{r.get('last','')} {r.get('first','')}".strip(),
            "slug":  r.get('slug') or '',
            "score": s['score'],
            "grade": s['grade'],
            "issues": s['issues'],
            "tips":   s['tips'],
        })

    scored.sort(key=lambda x: x['score'])
    total = len(scored)
    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    all_scored = []
    for r in rows:
        s = calc_seo_score(r)
        grade_dist[s['grade']] = grade_dist.get(s['grade'], 0) + 1
        all_scored.append(s['score'])
    avg = round(sum(all_scored) / len(all_scored), 1) if all_scored else 0

    return {
        "total":      total,
        "avg_score":  avg,
        "grade_dist": grade_dist,
        "items":      scored[:limit],
    }


# ── Broken Links Checker ─────────────────────────────────────────────────────

def _check_links_bg():
    import urllib.request as _urlreq
    import time as _time
    db2 = get_db()
    with db2.cursor() as c2:
        c2.execute(
            "SELECT id, photo FROM memorials "
            "WHERE approved=1 AND photo IS NOT NULL AND photo!='' AND photo NOT LIKE '/%%'"
        )
        photo_rows = c2.fetchall()
    db2.close()
    results = []
    ts = int(_time.time())
    for row in photo_rows:
        url = (row.get('photo') or '').strip()
        if not url or url.startswith('/'):
            continue
        try:
            req = _urlreq.Request(url, method='HEAD')
            req.add_header('User-Agent', 'ZoryanaPamyat-SEO/1.0')
            resp = _urlreq.urlopen(req, timeout=5)
            code = resp.status
        except Exception:
            code = 0
        is_broken = 1 if (code == 0 or code >= 400) else 0
        results.append((row['id'], url, code, ts, is_broken, code, ts, is_broken))
    if not results:
        return
    try:
        db3 = get_db()
        with db3.cursor() as c3:
            c3.executemany(
                "INSERT INTO seo_broken_links "
                "(memorial_id, url, link_type, status_code, last_checked, is_broken) "
                "VALUES (%s, %s, 'photo', %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE status_code=%s, last_checked=%s, is_broken=%s",
                results
            )
        db3.commit()
        db3.close()
    except Exception:
        pass


@app.post("/api/admin/seo/check-broken-links")
def check_broken_links(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT COUNT(*) as n FROM memorials "
            "WHERE approved=1 AND photo IS NOT NULL AND photo!='' AND photo NOT LIKE '/%%'"
        )
        total = (c.fetchone() or {}).get('n', 0)
    db.close()
    import threading as _thr
    t = _thr.Thread(target=_check_links_bg, daemon=True)
    t.start()
    return {"started": True, "total": total}


@app.get("/api/admin/seo/broken-links")
def get_broken_links(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT bl.id, bl.memorial_id, bl.url, bl.status_code, bl.last_checked, bl.is_broken, "
            "       m.last, m.first, m.slug "
            "FROM seo_broken_links bl "
            "LEFT JOIN memorials m ON m.id = bl.memorial_id "
            "WHERE bl.is_broken = 1 "
            "ORDER BY bl.last_checked DESC LIMIT 200"
        )
        broken = c.fetchall()
        c.execute("SELECT COUNT(*) as n FROM seo_broken_links WHERE is_broken=1")
        total = (c.fetchone() or {}).get('n', 0)
        c.execute("SELECT MAX(last_checked) as ts FROM seo_broken_links")
        last_ts = (c.fetchone() or {}).get('ts') or 0
    db.close()
    return {
        "total": total,
        "last_checked": last_ts,
        "broken": [
            {
                "id":          r['memorial_id'],
                "slug":        r.get('slug') or '',
                "name":        f"{r.get('last','')} {r.get('first','')}".strip(),
                "url":         r['url'],
                "status_code": r.get('status_code'),
                "last_checked": r.get('last_checked'),
            }
            for r in broken
        ],
    }


# ── Duplicate Detection ───────────────────────────────────────────────────────

@app.get("/api/admin/seo/duplicates")
def seo_duplicates(request: Request):
    require_moder(request)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT last, first, COUNT(*) as cnt, "
            "GROUP_CONCAT(id ORDER BY id SEPARATOR ',') as ids, "
            "GROUP_CONCAT(IFNULL(death,'') ORDER BY id SEPARATOR '|') as deaths "
            "FROM memorials "
            "WHERE approved=1 "
            "GROUP BY LOWER(TRIM(last)), LOWER(TRIM(first)) "
            "HAVING cnt > 1 "
            "ORDER BY cnt DESC "
            "LIMIT 100"
        )
        rows = c.fetchall()
    db.close()
    groups = []
    for r in rows:
        ids = [int(x) for x in (r['ids'] or '').split(',') if x.strip().isdigit()]
        deaths = (r['deaths'] or '').split('|')
        groups.append({
            "last":   r.get('last') or '',
            "first":  r.get('first') or '',
            "cnt":    r['cnt'],
            "ids":    ids,
            "deaths": deaths,
        })
    return {"total_groups": len(groups), "groups": groups}


# ── SEO Score History ─────────────────────────────────────────────────────────

@app.post("/api/admin/seo/snapshot")
def seo_snapshot(request: Request):
    require_moder(request)
    import datetime as _dt
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT id, last, first, mid, photo, descr, unit, `rank`, death, birth, loc, grp "
            "FROM memorials WHERE approved=1"
        )
        all_rows = c.fetchall()
    if not all_rows:
        db.close()
        return {"ok": False, "reason": "no approved memorials"}

    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0}
    scores = []
    for r in all_rows:
        s = calc_seo_score(r)
        grade_dist[s['grade']] = grade_dist.get(s['grade'], 0) + 1
        scores.append(s['score'])
    avg = round(sum(scores) / len(scores), 2) if scores else 0
    today = _dt.date.today().isoformat()

    with db.cursor() as c:
        c.execute(
            "INSERT INTO seo_score_history "
            "(snapshot_date, total_count, avg_score, count_a, count_b, count_c, count_d) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "total_count=%s, avg_score=%s, count_a=%s, count_b=%s, count_c=%s, count_d=%s",
            (today, len(scores), avg,
             grade_dist['A'], grade_dist['B'], grade_dist['C'], grade_dist['D'],
             len(scores), avg,
             grade_dist['A'], grade_dist['B'], grade_dist['C'], grade_dist['D'])
        )
    db.commit()
    db.close()
    return {
        "ok":          True,
        "date":        today,
        "total":       len(scores),
        "avg_score":   avg,
        "count_a":     grade_dist['A'],
        "count_b":     grade_dist['B'],
        "count_c":     grade_dist['C'],
        "count_d":     grade_dist['D'],
    }


@app.get("/api/admin/project-cost")
def get_project_cost(request: Request):
    require_admin(request)
    keys = ["proj_cost_server_usd","proj_cost_domains_usd","proj_cost_ai_usd",
            "proj_cost_other_usd","proj_cost_months","proj_usd_rate","proj_usd_rate_updated",
            "proj_cost_per_user_usd"]
    now = int(time.time())
    today_str = time.strftime("%Y-%m-%d")
    ts_24h = now - 86400
    db = get_db()
    with db.cursor() as c:
        ph = ",".join(["%s"] * len(keys))
        c.execute(f"SELECT `key`,value FROM colors WHERE `key` IN ({ph})", keys)
        rows = {r["key"]: r["value"] for r in c.fetchall()}
        # Зареєстровані користувачі (активні, не забанені)
        c.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_banned=0")
        users_total = c.fetchone()["cnt"]
        # Нові користувачі за добу
        c.execute("SELECT COUNT(*) AS cnt FROM users WHERE created_at >= %s AND is_banned=0",
                  (ts_24h,))
        users_24h = c.fetchone()["cnt"]
        # Переглядів за сьогодні (daily_stats + in-memory)
        c.execute("SELECT views FROM daily_stats WHERE date=%s", (today_str,))
        r = c.fetchone()
        views_today_db = r["views"] if r else 0
        views_today = max(views_today_db, _visits_daily.get(today_str, 0))
        # Переглядів за вчора
        yesterday = time.strftime("%Y-%m-%d", time.localtime(now - 86400))
        c.execute("SELECT views FROM daily_stats WHERE date=%s", (yesterday,))
        r = c.fetchone()
        views_yesterday = r["views"] if r else 0
        # Боти за добу (пошукові павуки)
        c.execute("SELECT COUNT(*) AS cnt, COUNT(DISTINCT bot_name) AS bots"
                  " FROM bot_visits WHERE created_at >= %s", (ts_24h,))
        bot_row = c.fetchone()
        bots_24h       = bot_row["cnt"]
        bots_24h_uniq  = bot_row["bots"]
        # Топ-боти за добу
        c.execute("SELECT bot_name, COUNT(*) AS cnt FROM bot_visits"
                  " WHERE created_at >= %s GROUP BY bot_name ORDER BY cnt DESC LIMIT 5",
                  (ts_24h,))
        top_bots = [{"bot": r["bot_name"], "cnt": r["cnt"]} for r in c.fetchall()]
        # Схвалених меморіалів
        c.execute("SELECT COUNT(*) AS cnt FROM memorials WHERE approved=1")
        mem_approved = c.fetchone()["cnt"]
    db.close()
    result = {k: rows.get(k, "0") for k in keys}
    result.update({
        "users_total":    users_total,
        "users_24h":      users_24h,
        "views_today":    views_today,
        "views_yesterday":views_yesterday,
        "bots_24h":       bots_24h,
        "bots_24h_uniq":  bots_24h_uniq,
        "top_bots":       top_bots,
        "mem_approved":   mem_approved,
    })
    return result


@app.post("/api/admin/project-cost/refresh-rate")
def refresh_usd_rate(request: Request):
    require_admin(request)
    try:
        url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        rate = str(round(float(data[0]["rate"]), 2))
        now = str(int(time.time()))
        db = get_db()
        with db.cursor() as c:
            for k, v in [("proj_usd_rate", rate), ("proj_usd_rate_updated", now)]:
                c.execute("INSERT INTO colors (`key`,value,label) VALUES (%s,%s,'') ON DUPLICATE KEY UPDATE value=%s", (k, v, v))
        db.commit()
        db.close()
        return {"ok": True, "rate": rate}
    except Exception as e:
        raise HTTPException(500, f"Помилка отримання курсу НБУ: {str(e)[:120]}")


@app.get("/api/admin/seo/score-history")
def seo_score_history(request: Request, days: int = 30):
    require_moder(request)
    days = min(max(days, 1), 365)
    db = get_db()
    with db.cursor() as c:
        c.execute(
            "SELECT snapshot_date, total_count, avg_score, count_a, count_b, count_c, count_d "
            "FROM seo_score_history "
            "ORDER BY snapshot_date DESC LIMIT %s",
            (days,)
        )
        rows = c.fetchall()
    db.close()
    return {
        "days": days,
        "history": [
            {
                "date":        str(r['snapshot_date']),
                "total":       r['total_count'],
                "avg_score":   float(r['avg_score']),
                "count_a":     r['count_a'],
                "count_b":     r['count_b'],
                "count_c":     r['count_c'],
                "count_d":     r['count_d'],
            }
            for r in rows
        ],
    }
