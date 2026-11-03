@echo off
chcp 65001 > nul
title AI-Based Anti-Spoofing Online Exam Proctoring System
echo =====================================================================
echo   🎓 AI-Based Anti-Spoofing Online Exam Proctoring System
echo   Developer: Avijit Pal (@AVijit005)
echo =====================================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please download and install Python 3.10 from: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check and create virtual environment if not present
if not exist "venv\Scripts\activate.bat" (
    echo [*] Step 1/3: Creating virtual environment 'venv'...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created successfully.
) else (
    echo [OK] Existing virtual environment found.
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Check if dependencies need installation
if not exist "venv\.installed" (
    echo.
    echo [*] Step 2/3: Installing required dependencies from requirements.txt...
    echo (This only happens on the first run. Please wait...)
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [WARNING] Some optional packages might have had issues, continuing...
    )
    echo 1 > venv\.installed
    echo [OK] Dependencies installed successfully.
) else (
    echo [OK] Dependencies already installed.
)

:: Start application and open browser
echo.
echo [*] Step 3/3: Launching AI Proctoring Server...
echo.
echo ---------------------------------------------------------------------
echo   Server running at: http://localhost:5000
echo   Default Student:   student@test.com  /  123456
echo   Default Admin:     admin@test.com    /  admin123
echo ---------------------------------------------------------------------
echo.

:: Launch browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: Run Flask app
python app.py

pause
