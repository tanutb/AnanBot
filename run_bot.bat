@echo off
echo ==========================================
echo Starting AnanBot System
echo ==========================================

:: Attempt to activate the conda environment 'ws'
:: Note: This assumes 'conda' is in your PATH. 
:: If this fails, you might need to use the full path to activate.bat
call conda activate ws
if %errorlevel% neq 0 (
    echo Failed to activate conda environment 'ws'.
    echo Please ensure conda is in your PATH or the environment exists.
    pause
    exit /b
)

echo Environment 'ws' activated.

:: 1. Start FastAPI Backend (api.py)
echo Starting FastAPI Backend (Port 8119)...
:: Using 'api.py' instead of 'app.py' as found in the directory.
start "AnanBot Backend API" cmd /k "fastapi run api.py --port 8119"

:: Wait 5 seconds to let the API spin up
echo Waiting for API to initialize...
timeout /t 5 /nobreak >nul

:: 2. Start Discord Bot
echo Starting Discord Bot...
start "AnanBot Discord Client" cmd /k "python discord_bot.py"

echo ==========================================
echo All services launched!
echo Keep these windows open.
echo ==========================================
