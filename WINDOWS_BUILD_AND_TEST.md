# Lead Extractor Pro - Windows Build & Test Guide

This guide covers how to build the Windows `.exe` and test the app on Windows.

---

## ⚠️ Critical: You Must Build on Windows

**PyInstaller cannot cross-compile.** You cannot build a Windows `.exe` on a Mac. You must:

1. Use a Windows PC (physical or VM), or
2. Use GitHub Actions / CI to build on Windows and download the artifact

---

## Option A: Quick Test (No Build) – Run from Source on Windows

**Best for immediate testing.** Install Python and run directly.

### 1. Prerequisites on Windows

- **Python 3.9 or 3.10** – [python.org/downloads](https://www.python.org/downloads/)
  - During install, check **"Add Python to PATH"**
- **Git** (optional) – to clone the repo, or copy the project folder

### 2. Setup

```cmd
cd C:\path\to\lead-extractor

REM Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

REM Install dependencies
pip install -r requirements.txt

REM Install Playwright browser (REQUIRED for automation)
python -m playwright install chromium
```

### 3. Run the App

```cmd
python launch_app_windows.py
```

- A browser window opens at `http://localhost:8501`
- Click **Start** and enter a search query
- Watch the Live Browser View and Activity Log

### 4. Quick Sanity Checks

| Test | Expected |
|------|----------|
| App opens in browser | Streamlit UI at localhost:8501 |
| "Check Server" | ✅ Server is running |
| Click Start | Activity log shows "Connected", "Automation starting..." |
| DuckDuckGo search | Browser automation runs, leads extracted |
| Headless mode | Runs without visible browser window |

---

## Option B: Build the Windows .exe

### 1. Prerequisites

- Python 3.9 or 3.10
- All dependencies installed (`pip install -r requirements.txt`)
- Playwright browser: `python -m playwright install chromium`

### 2. Build

```cmd
cd C:\path\to\lead-extractor
build_windows.bat
```

Or manually:

```cmd
pip install pyinstaller
pyinstaller --clean --noconfirm LeadExtractorPro_windows.spec
```

### 3. Output

- **Executable:** `dist\LeadExtractorPro.exe`
- The `.exe` is **one-file** (PyInstaller bundles everything)

### 4. Run the .exe

```cmd
dist\LeadExtractorPro.exe
```

- A console window appears (for logs)
- A browser tab opens with the app
- Click Start to run automation

### 5. If Automation Fails After Build

Playwright browsers are not always bundled. If the automation/browser does not launch:

1. Install Python on the target PC
2. Unzip or copy the project
3. Run: `python -m playwright install chromium`
4. Run the app again (from source or `.exe`)

---

## Platform-Specific Differences (Mac vs Windows)

| Feature | macOS | Windows |
|---------|-------|---------|
| Launcher | `launch_app_simple.py` | `launch_app_windows.py` |
| "Launch in Terminal" | Opens Terminal.app | "Launch in CMD" opens Command Prompt |
| Browser activation | Uses osascript | Not used |
| Data folder | `~/Library/Application Support/LeadExtractorPro` | `%APPDATA%\LeadExtractorPro` |
| Port cleanup | pkill, lsof | taskkill |
| Subprocess flag | None | `CREATE_NO_WINDOW` for Streamlit |

---

## Troubleshooting

### "Server not connected"

- FastAPI may not have started. Check the console window for errors.
- Try running from source: `python launch_app_windows.py` and watch the console.

### "Browser doesn't appear"

- Enable **Run headless** in Settings – extraction still works; logs update.
- Use **Launch in CMD** – runs from Command Prompt, often fixes visibility.
- Ensure Chromium is installed: `python -m playwright install chromium`

### "Import error" or "Module not found"

- Activate the venv: `venv\Scripts\activate`
- Reinstall: `pip install -r requirements.txt`

### Build fails with PyInstaller

- Try: `pip install --upgrade pyinstaller`
- Use Python 3.9 or 3.10 (3.11/3.12 may have compatibility issues)
- Check: `LeadExtractorPro_windows.spec` for hidden imports

---

## File Layout for Distribution

To distribute to a Windows user:

1. **Source run:** zip the project and send; user runs `python launch_app_windows.py`
2. **Built .exe:** send `dist\LeadExtractorPro.exe`; user runs it
3. **Full package:** send the whole `dist` folder if the spec uses `--onedir`

---

## Testing Checklist

- [ ] App starts (browser opens)
- [ ] License activation works
- [ ] Click Start – activity log updates
- [ ] DuckDuckGo search runs
- [ ] Leads are extracted
- [ ] PDF export works
- [ ] Headless mode works
- [ ] "Launch in CMD" opens a new Command Prompt and runs the app
