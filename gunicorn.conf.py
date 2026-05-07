# ── Gunicorn Production Configuration ──
# Використовується замість Uvicorn для production
# Запуск: gunicorn -c gunicorn.conf.py Paskal:app

import multiprocessing
import os

# ── Workers ──
# Формула: (2 × CPU) + 1, але не більше 8 для I/O-bound
cpu_count = multiprocessing.cpu_count()
workers = min((2 * cpu_count) + 1, 8)

# ── Worker Class ──
# UvicornWorker для async/await підтримки
worker_class = "uvicorn.workers.UvicornWorker"

# ── Timeout ──
# 30 секунд — достатньо для довгих запитів
timeout = 30
graceful_timeout = 15

# ── Binding ──
bind = "127.0.0.1:8000"

# ── Logging ──
accesslog = "/var/log/zoryna/access.log"
errorlog = "/var/log/zoryna/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ── Process Naming ──
proc_name = "zoryna_pamyat"

# ── Preload ──
# Preload app для швидшого restart
preload_app = True

# ── Max Requests ──
# Перезапуск worker після 1000 запитів (проти memory leaks)
max_requests = 1000
max_requests_jitter = 50

# ── Keep-Alive ──
keepalive = 5

# ── Hooks ──
def on_starting(server):
    server.log.info("Зоряна Пам'ять starting with %d workers", workers)

def post_fork(server, worker):
    server.log.info("Worker %d spawned", worker.pid)

def worker_exit(server, worker):
    server.log.info("Worker %d exiting", worker.pid)
