@echo off
echo ================================================
echo  Redis Server — Запуск
echo ================================================
echo.

cd /d "D:\OSPanel\modules\Redis"

if exist "redis-server.exe" (
    echo [OK] Redis знайдено
    echo Запускаю Redis на 127.0.0.1:6379...
    echo.
    start "Redis Server" redis-server.exe --service-run
    echo.
    echo Redis запущено!
    echo Для перевірки: redis-cli ping
) else (
    echo [ERROR] Redis не знайдено в D:\OSPanel\modules\Redis
    echo Встановіть Redis через OSPanel
)
pause
