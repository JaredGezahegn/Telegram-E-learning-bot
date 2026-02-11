@echo off
chcp 65001 >nul
echo ============================================================
echo Starting Telegram English Bot
echo ============================================================
echo.
echo Current time: %date% %time%
echo The bot will post lessons daily at 21:00 Africa/Nairobi time
echo Press Ctrl+C to stop the bot
echo ============================================================
echo.

python src/main.py

if errorlevel 1 (
    echo.
    echo ERROR: Bot exited with error code %errorlevel%
    pause
)
