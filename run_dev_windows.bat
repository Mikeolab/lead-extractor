@echo off
REM Quick run for development - installs deps and starts app
cd /d "%~dp0"

echo Installing dependencies...
python -m pip install -q -r requirements.txt 2>nul
if errorlevel 1 (
    echo Failed to install. Run: python -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting Lead Extractor Pro...
python launch_app_windows.py

pause
