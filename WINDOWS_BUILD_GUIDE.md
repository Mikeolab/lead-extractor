# 🪟 Windows Build Guide

Complete guide for building Lead Extractor Pro for Windows.

## 📋 Prerequisites

1. **Windows 10/11** (64-bit)
2. **Python 3.9+** installed and added to PATH
3. **Git** (optional, for cloning the repository)

## 🚀 Quick Build

### Step 1: Install Dependencies

```cmd
pip install -r requirements.txt
pip install pyinstaller
```

### Step 2: Run Build Script

```cmd
build_windows.bat
```

The script will:
- Check for Python and PyInstaller
- Install missing dependencies
- Clean previous builds
- Build the executable using PyInstaller
- Create `dist\LeadExtractorPro.exe`

### Step 3: Test the Build

1. Navigate to `dist` folder
2. Double-click `LeadExtractorPro.exe`
3. The app should launch and open in your default browser

## 📦 What Gets Built

- **`dist\LeadExtractorPro.exe`** - Standalone executable (~50-150 MB)
  - Includes Python runtime
  - Includes all dependencies
  - Includes Streamlit and FastAPI servers
  - No Python installation needed on target machine

## 🎯 Distribution

### Option 1: Direct Distribution
- Zip the `LeadExtractorPro.exe` file
- Users extract and run
- Simple, no installer needed

### Option 2: Create Installer (Recommended)

Use **NSIS** or **Inno Setup** to create a professional installer:

**NSIS Example:**
```nsis
OutFile "LeadExtractorPro_Setup.exe"
InstallDir "$PROGRAMFILES\LeadExtractorPro"
Section "Install"
    SetOutPath $INSTDIR
    File "dist\LeadExtractorPro.exe"
    CreateShortcut "$DESKTOP\Lead Extractor Pro.lnk" "$INSTDIR\LeadExtractorPro.exe"
SectionEnd
```

**Inno Setup Example:**
```pascal
[Setup]
AppName=Lead Extractor Pro
AppVersion=1.0.0
DefaultDirName={pf}\LeadExtractorPro
DefaultGroupName=Lead Extractor Pro

[Files]
Source: "dist\LeadExtractorPro.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\Lead Extractor Pro"; Filename: "{app}\LeadExtractorPro.exe"
Name: "{commondesktop}\Lead Extractor Pro"; Filename: "{app}\LeadExtractorPro.exe"
```

### Option 3: GitHub Releases
- Upload `.exe` to GitHub Releases
- Free hosting with version management
- Download tracking

## ⚠️ Important Notes

### Playwright Browsers

Playwright requires browsers to be installed. Options:

**Option A: Bundle Browsers (Larger file, ~300-500 MB)**
- Include Playwright browsers in the build
- Users don't need to install anything
- Larger download size

**Option B: Download on First Run**
- App downloads browsers on first launch
- Smaller initial file size (~50-150 MB)
- Requires internet on first run
- Add to launcher:
```python
# In launch_app_windows.py, add after imports:
if getattr(sys, 'frozen', False):
    import subprocess
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                   capture_output=True)
```

**Option C: Separate Browser Installer**
- Distribute browsers separately
- Users install browsers first
- Then run app

### File Size

- Expect **50-150 MB** for the executable
- Includes Python, Streamlit, Playwright, FastAPI, etc.
- This is normal for desktop apps

### First Run

- First launch may be slower (extracting files)
- Subsequent launches are faster
- App creates data folder in `%APPDATA%\LeadExtractorPro`

### Testing Checklist

- [ ] Test on build machine
- [ ] Test on clean Windows machine (no Python)
- [ ] Test license activation
- [ ] Test lead extraction
- [ ] Test PDF export
- [ ] Test email sending
- [ ] Test browser automation
- [ ] Test WebSocket connection
- [ ] Test database operations

## 🔧 Troubleshooting

### Build Fails

1. **Missing dependencies:**
   ```cmd
   pip install -r requirements.txt
   ```

2. **PyInstaller issues:**
   ```cmd
   pip install --upgrade pyinstaller
   ```

3. **Path issues:**
   - Ensure you're running `build_windows.bat` from project root
   - Check that `app` folder exists

### App Won't Start

1. **Check error log:**
   - `%APPDATA%\LeadExtractorPro\error.log`

2. **Check Streamlit log:**
   - `%APPDATA%\LeadExtractorPro\streamlit_stderr.log`

3. **Port conflicts:**
   - Ensure ports 8501 and 8000 are free
   - Close any running instances

### Browser Won't Open

- Check firewall settings
- Ensure ports 8501 and 8000 are not blocked
- Try manually opening `http://localhost:8501`

## 📝 Build Script Details

The `build_windows.bat` script:
1. Checks Python installation
2. Installs PyInstaller if missing
3. Installs dependencies from `requirements.txt`
4. Cleans previous builds
5. Runs PyInstaller with `LeadExtractorPro_windows.spec`
6. Creates `dist\LeadExtractorPro.exe`

## 🎨 Customization

### Add Icon

1. Create `assets\icon.ico` (256x256 recommended)
2. Update `LeadExtractorPro_windows.spec`:
   ```python
   icon='assets/icon.ico'
   ```

### Change App Name

1. Update `LeadExtractorPro_windows.spec`:
   ```python
   name='YourAppName'
   ```

### Add Version Info

Create `version_info.txt`:
```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    ...
  ),
  ...
)
```

Then add to spec:
```python
version='version_info.txt'
```

## 🚀 Ready to Build!

Run `build_windows.bat` and you're good to go! 🎯
