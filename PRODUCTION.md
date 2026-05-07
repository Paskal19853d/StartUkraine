# Зоряна Пам'ять — Production Deployment

## Вимоги
- Ubuntu 20.04+ / Debian 11+
- Python 3.8+
- MySQL 8.0+ / MariaDB 10.5+
- Nginx 1.18+
- (опціонально) Redis 6.0+

## Швидкий deploy

```bash
# 1. Завантаження коду
git clone https://your-repo.git /var/www/zoryna
cd /var/www/zoryna

# 2. Налаштування БД
cp .env.example .env
nano .env  # заповніть DB_HOST, DB_USER, DB_PASS, DB_NAME

# 3. Встановлення залежностей
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Створення БД
mysql -u root -p < schema.sql  # або використовуйте наявну БД

# 5. Nginx
sudo cp zoryna-nginx.conf /etc/nginx/sites-available/zoryna
sudo ln -s /etc/nginx/sites-available/zoryna /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 6. Systemd
sudo cp zoryna.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zoryna
sudo systemctl start zoryna

# 7. SSL (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Автоматичний deploy

```bash
sudo bash deploy.sh
```

## Моніторинг

### Health Check
```bash
curl http://localhost:8000/health
# {"status":"ok","uptime":3600,"db":"connected","redis":"connected"}
```

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
# zoryna_memorials_total 12345
# zoryna_uptime_seconds 3600
# ...
```

### Логи
```bash
# Сервіс
journalctl -u zoryna -f --no-pager

# Nginx
tail -f /var/log/nginx/zoryna-access.log

# Gunicorn
tail -f /var/log/zoryna/error.log
```

## Конфігурація

### gunicorn.conf.py
| Параметр | Значення | Опис |
|----------|----------|------|
| workers | (2×CPU)+1 | Кількість воркерів |
| timeout | 30s | Таймаут запиту |
| max_requests | 1000 | Рестарт воркера після N запитів |
| keepalive | 5s | Keep-alive з'єднання |

### Redis кешування
| Ендпоінт | TTL |
|----------|-----|
| /api/people | 60с |
| /api/stats | 30с |
| /api/colors | 300с |
| /api/labels | 300с |
| /api/cities | 300с |

### Nginx
- Gzip стиснення для текст/JSON/CSS/JS/SVG
- HTTP/2 підтримка (після SSL)
- Кешування статичних файлів 30 днів
- WebSocket підтримка

## Безпека
- `.env` файл НЕ комітиться в git
- `logs/` директорія НЕ комітиться в git
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Rate limiting: 30/хв IP, 100/хв API

## Оновлення

```bash
# 1. Оновлення коду
cd /var/www/zoryna
git pull origin main

# 2. Оновлення залежностей
source venv/bin/activate
pip install -r requirements.txt

# 3. Рестарт
sudo systemctl restart zoryna
```
