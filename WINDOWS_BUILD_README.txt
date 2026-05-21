Lead Extractor Pro — Build the Windows .exe on your PC
======================================================

WHAT YOU NEED
  - Windows 10 or 11 (64-bit)
  - Python 3.10 or 3.11 from https://www.python.org/downloads/
    During install, enable: "Add python.exe to PATH"

BUILD STEPS
  1. Unzip this entire folder to a simple path, e.g. C:\dev\lead-extractor
     (Avoid very long paths; spaces are usually OK.)

  2. Open Command Prompt in that folder (Shift+Right-click folder → Open in Terminal,
     or:  cd C:\dev\lead-extractor)

  3. Run:
       build_windows.bat

     This will:
       - pip install -r requirements.txt
       - install PyInstaller
       - download Playwright Chromium into .\playwright_browsers (needed for the .exe)
       - run: pyinstaller LeadExtractorPro_windows.spec

     First time: about 5–15 minutes. Output:
       dist\LeadExtractorPro.exe

  4. Optional — customer zip:
       package_windows.bat
     (expects dist\LeadExtractorPro.exe to exist)

RUN FROM SOURCE (no .exe)
  Double-click SETUP_AND_RUN.bat — installs deps and starts the app with Python.

TROUBLESHOOTING
  - "Python not found" → Reinstall Python with PATH enabled, then open a NEW Command Prompt.
  - Playwright errors → In the project folder run:  python -m playwright install chromium
  - Antivirus may slow or block the first PyInstaller run; allow the folder if needed.

NOTES
  - This zip does not include your Mac database or exports; the app creates data\ on first run.
  - Copy .env from your Mac manually if you use environment variables (not required for build).
