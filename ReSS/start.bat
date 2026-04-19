@echo off
cd /d "%~dp0"
echo ================================================
echo  Зоряна Пам'ять — ReSS Secure Server
echo  http://127.0.0.1:8000
echo  Адмін: http://127.0.0.1:8000/admin
echo  Логін: admin@admin.com / Admin
echo ================================================
echo.
..\venv\Scripts\python -m uvicorn app:app --reload --port 8000
pause
