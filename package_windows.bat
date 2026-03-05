@echo off
REM Package Windows build for distribution
REM Run this after build_windows.bat succeeds

echo ========================================
echo Lead Extractor Pro - Windows Packaging
echo ========================================
echo.

if not exist "dist\LeadExtractorPro.exe" (
    echo ERROR: LeadExtractorPro.exe not found!
    echo Please run build_windows.bat first.
    pause
    exit /b 1
)

REM Create package directory
set PACKAGE_DIR=package
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

REM Copy executable
echo Copying executable...
copy "dist\LeadExtractorPro.exe" "%PACKAGE_DIR%\"

REM Create README
echo Creating README...
(
echo Lead Extractor Pro - Windows
echo =============================
echo.
echo Installation:
echo 1. Extract this zip file
echo 2. Run LeadExtractorPro.exe
echo 3. The app will open in your default browser
echo.
echo Requirements:
echo - Windows 10/11 ^(64-bit^)
echo - Internet connection ^(for first-time browser download^)
echo.
echo First Run:
echo - The app may take a moment to start on first launch
echo - Playwright browsers will be downloaded automatically
echo - Your browser will open automatically
echo.
echo Troubleshooting:
echo - If the app won't start, check: %%APPDATA%%\LeadExtractorPro\error.log
echo - Ensure ports 8501 and 8000 are not blocked by firewall
echo - Close any existing instances before running
echo.
echo Support:
echo Contact support for license activation and technical issues.
) > "%PACKAGE_DIR%\README.txt"

REM Create zip file
echo Creating zip package...
set ZIP_NAME=LeadExtractorPro_Windows_v1.0.0.zip
if exist "%ZIP_NAME%" del "%ZIP_NAME%"

REM Use PowerShell to create zip (available on Windows 10+)
powershell -Command "Compress-Archive -Path '%PACKAGE_DIR%\*' -DestinationPath '%ZIP_NAME%' -Force"

if exist "%ZIP_NAME%" (
    echo.
    echo ========================================
    echo Package created successfully!
    echo ========================================
    echo.
    echo Package: %ZIP_NAME%
    echo Size:
    dir "%ZIP_NAME%" | find "%ZIP_NAME%"
    echo.
    echo Contents:
    echo - LeadExtractorPro.exe
    echo - README.txt
    echo.
    echo Ready for distribution!
) else (
    echo.
    echo ERROR: Failed to create zip file.
    echo You can manually zip the contents of: %PACKAGE_DIR%
    echo.
)

pause
