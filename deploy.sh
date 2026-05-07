#!/bin/bash
# ── Deploy Script для Зоряна Пам'ять ──
# Використання: bash deploy.sh [production|staging]
# Вимоги: sudo, git, python3, mysql, redis

set -e

# ── Налаштування ──
DEPLOY_DIR="/var/www/zoryna"
REPO_URL="git@your-repo.git"  # ← Замініть на свій репозиторій
BRANCH="main"
PYTHON="python3"
SERVICE_NAME="zoryna"

# ── Кольори ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Перевірка root ──
if [[ $EUID -ne 0 ]]; then
   err "Запустіть через sudo"
fi

log "=== Зоряна Пам'ять — Deploy ==="

# ── Крок 1: Системні залежності ──
log "Крок 1/7: Перевірка системних залежностей..."

command -v git >/dev/null 2>&1 || { apt-get update && apt-get install -y git; }
command -v $PYTHON >/dev/null 2>&1 || { apt-get update && apt-get install -y python3 python3-pip python3-venv; }
command -v nginx >/dev/null 2>&1 || { apt-get update && apt-get install -y nginx; }
command -v mysql >/dev/null 2>&1 || { warn "MySQL не знайдено — встановіть вручну"; }

# ── Крок 2: Користувач ──
log "Крок 2/7: Налаштування користувача..."
id zoryna &>/dev/null || useradd --system --no-create-home --shell /bin/false zoryna

# ── Крок 3: Код ──
log "Крок 3/7: Оновлення коду..."
if [ -d "$DEPLOY_DIR/.git" ]; then
    cd "$DEPLOY_DIR"
    git pull origin $BRANCH
else
    mkdir -p "$DEPLOY_DIR"
    git clone -b $BRANCH "$REPO_URL" "$DEPLOY_DIR"
fi
cd "$DEPLOY_DIR"

# ── Крок 4: Віртуальне середовище ──
log "Крок 4/7: Оновлення залежностей..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn uvicorn

# ── Крок 5: БД міграції ──
log "Крок 5/7: Перевірка БД..."
if [ -f ".env" ]; then
    # .env вже існує — пропускаємо
    warn ".env знайдено — пропускаємо налаштування БД"
else
    warn "Створіть .env файл з налаштуваннями БД"
    cp .env.example .env 2>/dev/null || true
fi

# ── Крок 6: Nginx ──
log "Крок 6/7: Налаштування Nginx..."
if [ -f "zoryna-nginx.conf" ]; then
    cp zoryna-nginx.conf /etc/nginx/sites-available/zoryna
    ln -sf /etc/nginx/sites-available/zoryna /etc/nginx/sites-enabled/zoryna
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
else
    warn "zoryna-nginx.conf не знайдено"
fi

# ── Крок 7: Systemd ──
log "Крок 7/7: Перезапуск сервісу..."
if [ -f "zoryna.service" ]; then
    cp zoryna.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl restart $SERVICE_NAME
    systemctl enable $SERVICE_NAME
fi

# ── Готово ──
log "=== Deploy завершено ==="
echo ""
echo "  URL:  http://$(curl -s ifconfig.me)"
echo "  Адмін: http://$(curl -s ifconfig.me)/admin"
echo "  Логи: journalctl -u $SERVICE_NAME -f"
echo ""
