@echo off
REM Build Lead Extractor Pro for Windows
REM Run this script ON A WINDOWS MACHINE (PyInstaller cannot cross-compile)
REM Prerequisites: Python 3.9+ with pip, all requirements installed

echo ============================================
echo  Lead Extractor Pro - Windows Build
echo ============================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.9+ from python.org
    pause
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

REM Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller --quiet

REM Install Playwright Chromium to LOCAL folder (bundled with exe)
echo Installing Playwright Chromium to playwright_browsers...
if not exist "playwright_browsers" mkdir playwright_browsers
set PLAYWRIGHT_BROWSERS_PATH=%CD%\playwright_browsers
python -m playwright install chromium
if errorlevel 1 (
    echo WARNING: Playwright install may have failed. The .exe will still build,
    echo but automation may not work until you run: python -m playwright install chromium
)

REM Clean previous build
echo Cleaning previous build...
if exist "dist\LeadExtractorPro.exe" del /q "dist\LeadExtractorPro.exe"
if exist "build" rmdir /s /q build 2>nul

REM Build with PyInstaller
echo.
echo Building LeadExtractorPro.exe...
echo This may take 5-15 minutes...
echo.
pyinstaller --clean --noconfirm LeadExtractorPro_windows.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESSFUL
echo ============================================
echo.
echo Output: dist\LeadExtractorPro.exe
echo.
echo Next steps:
echo   1. Copy the entire "dist" folder to the target Windows PC
echo   2. Run dist\LeadExtractorPro.exe
echo   3. On first run, if automation fails, run: python -m playwright install chromium
echo      from the same folder (or install Python + run that in the project folder)
echo.
pause
