@echo off
REM Build Windows .exe for Lead Extractor Pro
REM This script creates a standalone Windows executable

echo ========================================
echo Lead Extractor Pro - Windows Build
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.9+ and add it to PATH.
    pause
    exit /b 1
)

REM Check if pip is available (fix broken Python installs)
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip not found. Installing pip...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"
    python get-pip.py
    del get-pip.py 2>nul
)

REM Check if PyInstaller is installed
echo Checking PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller!
        pause
        exit /b 1
    )
)

REM Always install/update dependencies before build
echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo WARNING: Some dependencies may have failed. Continuing anyway...
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "LeadExtractorPro_windows.spec" (
    echo Keeping spec file for reference...
)

REM Build the app using spec file
echo.
echo Building LeadExtractorPro.exe...
echo This may take several minutes...
echo.

python -m PyInstaller --clean --noconfirm LeadExtractorPro_windows.spec

REM Check if build succeeded
if exist "dist\LeadExtractorPro.exe" (
    echo.
    echo ========================================
    echo Build successful!
    echo ========================================
    echo.
    echo App location: dist\LeadExtractorPro.exe
    echo File size: 
    dir "dist\LeadExtractorPro.exe" | find "LeadExtractorPro.exe"
    echo.
    echo Next steps:
    echo 1. Test the app: Run dist\LeadExtractorPro.exe
    echo 2. Test on a clean Windows machine (no Python installed)
    echo 3. Create installer (optional, use NSIS or Inno Setup)
    echo 4. Distribute to users
    echo.
    echo NOTE: Playwright browsers may need to be installed separately
    echo       Run: playwright install chromium
    echo       Or bundle browsers in the installer
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    echo.
    echo Check the errors above for details.
    echo Common issues:
    echo - Missing dependencies (run: python -m pip install -r requirements.txt)
    echo - PyInstaller issues (try: python -m pip install --upgrade pyinstaller)
    echo - Path issues with app folder
    echo.
    pause
    exit /b 1
)

pause

