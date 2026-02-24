@echo off
echo ===================================
echo Contest Reminder Bot - Quick Start
echo ===================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python is not installed. Please install Python 3.9 or higher.
    pause
    exit /b 1
)

echo + Python found
echo.

REM Check if BOT_TOKEN is set
if "%BOT_TOKEN%"=="" (
    echo ! BOT_TOKEN environment variable is not set!
    echo.
    echo Please get your bot token from @BotFather on Telegram and set it:
    echo   set BOT_TOKEN=your_token_here
    echo.
    echo Or create a .env file with:
    echo   BOT_TOKEN=your_token_here
    echo.
    pause
    exit /b 1
)

echo + BOT_TOKEN is set
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo + Setup complete!
echo.
echo Starting bot...
echo.

REM Run the bot
python bot.py

pause
