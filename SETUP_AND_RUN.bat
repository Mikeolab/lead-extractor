@echo off
REM One-click setup and run for Lead Extractor Pro on Windows
REM First run: installs all dependencies + Chromium (~2-5 min)
REM Later runs: starts the app (no install needed)

cd /d "%~dp0"

echo ============================================
echo  Lead Extractor Pro - Setup and Run
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found.
    echo.
    echo Install Python 3.9+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Installing Python packages...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Failed to install packages. Run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [2/3] Installing Chromium for automation...
python -m playwright install chromium
if errorlevel 1 (
    echo WARNING: Playwright Chromium install failed.
    echo If you have Google Chrome installed, the app may still work.
    echo.
)

echo [3/3] Starting Lead Extractor Pro...
echo.
python launch_app_windows.py

pause
