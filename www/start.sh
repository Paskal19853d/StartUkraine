#!/usr/bin/env bash
# Зоряна Пам'ять — Production launcher (Linux)
# Вимоги: Python 3.9+, MySQL/MariaDB, pip
# Встановлення залежностей: pip install -r requirements.txt

set -e

cd "$(dirname "$0")"

# ── Перевірка віртуального середовища ──────────────────
if [ ! -d "venv" ]; then
    echo "[1/4] Створюю віртуальне середовище..."
    python3 -m venv venv
fi

source venv/bin/activate

# ── Встановлення залежностей ───────────────────────────
echo "[2/4] Встановлюю залежності..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt 2>/dev/null || {
    echo "[WARN] requirements.txt не знайдено, встановлюю базові пакети..."
    pip install --quiet fastapi uvicorn[standard] pymysql python-dotenv dbutils pydantic python-multipart
}

# ── Перевірка .env ─────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "[3/4] УВАГА: файл .env відсутній! Створіть його з .env.example"
    echo "     cp .env.example .env  # і заповніть дані БД"
    exit 1
fi

# ── Запуск ──────────────────────────────────────────────
echo "[4/4] Запускаю сервер..."
echo "=========================================="
echo "  Зоряна Пам'ять — Production Mode"
echo "  Workers: 4 (Uvicorn via Gunicorn)"
echo "  URL: http://0.0.0.0:8000"
echo "=========================================="

# Перевірка чи встановлено gunicorn
if python -c "import gunicorn" 2>/dev/null; then
    echo "[INFO] Запуск через Gunicorn (4 workers)..."
    exec gunicorn Paskal:app \
        -w 4 \
        -k uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --timeout 30 \
        --limit-concurrency 200 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile -
else
    echo "[WARN] Gunicorn не встановлено. Запуск через Uvicorn (1 worker)."
    echo "       Для production встановіть: pip install gunicorn"
    exec uvicorn Paskal:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --timeout-keep-alive 30 \
        --log-level info
fi
