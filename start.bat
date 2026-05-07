@echo off
cd /d "%~dp0"
echo ================================================
echo  Зоряна Пам'ять — Development Server (Windows)
echo  URL: http://127.0.0.1:8000
echo  Адмн: http://127.0.0.1:8000/admin
echo ================================================
echo.

REM Переврка вiртуального середовища
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Створю вiртуальне середовище...
    python -m venv venv
)

REM Активацiя
call venv\Scripts\activate.bat

REM Встановлення залежностей
echo [2/3] Перевiряю залежностi...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
) else (
    pip install fastapi uvicorn[standard] pymysql python-dotenv dbutils pydantic python-multipart --quiet
)

REM Запуск
echo [3/3] Запускаю Uvicorn (1 worker, dev mode)...
echo.
uvicorn Paskal:app --reload --host 127.0.0.1 --port 8000 --log-level info
pause
