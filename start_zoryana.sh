#!/bin/bash
set -a
source /var/www/treete07/data/www/xn----7sbbz2acglf0a4i2ag.xn--j1amh/.env
set +a
exec /var/www/treete07/data/www/xn----7sbbz2acglf0a4i2ag.xn--j1amh/venv/bin/python -m uvicorn Paskal:app --host 127.0.0.1 --port 8000
