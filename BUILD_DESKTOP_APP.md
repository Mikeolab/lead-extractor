# 🚀 Building Desktop App (.exe for Windows, .app for Mac)

## 📋 Overview

Convert your Streamlit app into a standalone executable that users can download and run without installing Python.

---

## 🎯 What Users See vs Admin

### Current System:
- **"Admin"** is just the **licensee name** (what you entered when generating the license)
- **No special privileges** - everyone sees the same features
- **Same UI** for all users
- **Same functionality** for all users

### What Users Will See:
- ✅ Same interface as you see
- ✅ Same features (Live Extractor, Saved Leads)
- ✅ Same license status display
- ✅ Their own name (from license) instead of "Admin"

**The "Admin" label is just metadata** - it doesn't grant special access.

---

## 🔧 Building Desktop App

### Prerequisites:

```bash
# Install PyInstaller
pip install pyinstaller

# Make sure all dependencies are installed
pip install -r requirements.txt
```

---

## 🍎 For Mac (.app bundle)

### Build Script: `build_macos.sh`

```bash
#!/bin/bash
# Build macOS .app bundle

echo "🔨 Building macOS app..."

pyinstaller --name=LeadExtractorPro \
    --onefile \
    --windowed \
    --icon=assets/icon.icns \
    --add-data="app:app" \
    --hidden-import=streamlit \
    --hidden-import=playwright \
    --hidden-import=fastapi \
    --hidden-import=uvicorn \
    --hidden-import=websocket \
    --hidden-import=sqlite3 \
    --hidden-import=pdfplumber \
    --collect-all streamlit \
    --collect-all playwright \
    app/main.py

echo "✅ Build complete! Check dist/LeadExtractorPro.app"
```

### Create Icon (Optional):
- Create `assets/icon.icns` for Mac app icon
- Or remove `--icon` flag if no icon

---

## 🪟 For Windows (.exe)

### Build Script: `build_windows.bat`

```batch
@echo off
echo Building Windows .exe...

pyinstaller --name=LeadExtractorPro ^
    --onefile ^
    --windowed ^
    --icon=assets/icon.ico ^
    --add-data="app;app" ^
    --hidden-import=streamlit ^
    --hidden-import=playwright ^
    --hidden-import=fastapi ^
    --hidden-import=uvicorn ^
    --hidden-import=websocket ^
    --hidden-import=sqlite3 ^
    --hidden-import=pdfplumber ^
    --collect-all streamlit ^
    --collect-all playwright ^
    app/main.py

echo Build complete! Check dist\LeadExtractorPro.exe
```

### Create Icon (Optional):
- Create `assets/icon.ico` for Windows app icon
- Or remove `--icon` flag if no icon

---

## 📦 Complete Build Process

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Build for Your Platform

**Mac:**
```bash
chmod +x build_macos.sh
./build_macos.sh
```

**Windows:**
```bash
build_windows.bat
```

### Step 3: Test the Executable
- Run the generated `.app` (Mac) or `.exe` (Windows)
- Test license activation
- Test all features

### Step 4: Create Installer (Optional)

**Mac (DMG):**
```bash
# Create DMG installer
hdiutil create -volname "Lead Extractor Pro" \
    -srcfolder dist/LeadExtractorPro.app \
    -ov -format UDZO dist/LeadExtractorPro.dmg
```

**Windows (NSIS/Inno Setup):**
- Use NSIS or Inno Setup to create installer
- Or just distribute the .exe file

---

## 🎯 Distribution

### Option 1: Direct Download
- Host `.app` or `.exe` on your website
- Users download and run
- Simple, no installer needed

### Option 2: Installer Package
- Create DMG (Mac) or installer (Windows)
- More professional
- Can add shortcuts, etc.

### Option 3: GitHub Releases
- Free hosting
- Version management
- Download tracking

---

## ⚠️ Important Notes

### 1. File Size
- Expect **50-150 MB** for the executable
- Includes Python, Streamlit, Playwright, etc.
- This is normal for desktop apps

### 2. First Run
- First launch may be slower (extracting files)
- Subsequent launches are faster

### 3. Dependencies
- All dependencies bundled in executable
- No need to install Python
- Works on clean machines

### 4. Playwright Browsers
- Playwright browsers need to be included
- May need to run `playwright install` after build
- Or bundle browsers in the app

---

## 🔧 Advanced: Include Playwright Browsers

Playwright needs browsers. Options:

### Option A: Bundle Browsers (Larger file)
```bash
# Include browsers in build
--add-data="~/.cache/ms-playwright:playwright"
```

### Option B: Download on First Run
- App downloads browsers on first launch
- Smaller initial file size
- Requires internet on first run

### Option C: Separate Browser Installer
- Distribute browsers separately
- Users install browsers first
- Then run app

---

## 📋 Build Checklist

- [ ] Install PyInstaller
- [ ] Test build on your machine
- [ ] Test on clean machine (no Python)
- [ ] Test license activation
- [ ] Test all features
- [ ] Create installer (optional)
- [ ] Test installer
- [ ] Distribute to users

---

## 🚀 Quick Start

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Build (Mac)
./build_macos.sh

# 3. Test
open dist/LeadExtractorPro.app

# 4. Distribute
# Upload to your website or GitHub
```

---

**Ready to build!** 🎯

