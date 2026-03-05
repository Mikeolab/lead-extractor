# 🔧 Fix: App Crashes on Launch

## 🐛 Problem
App shows in dock then disappears - crashes on startup.

## ✅ Fixes Applied:

### 1. Fixed Path Handling
- App detects if bundled (PyInstaller)
- Uses `sys._MEIPASS` for resources
- Uses user's Application Support for data files

### 2. Created Proper Launcher
- `launch_app_simple.py` - Properly runs Streamlit
- Handles both development and bundled modes
- Sets Streamlit configuration correctly

### 3. Changed Build Mode
- Changed from `--onefile` to `--onedir`
- Better for Streamlit apps
- More reliable

### 4. Fixed Data Paths
- Bundled app uses: `~/Library/Application Support/LeadExtractorPro/`
- Development uses: `project/data/` and `project/exports/`

---

## 🧪 Test the Fixed App

### Option 1: Double-Click
```bash
open dist/LeadExtractorPro.app
```

### Option 2: From Terminal (See Errors)
```bash
dist/LeadExtractorPro.app/Contents/MacOS/LeadExtractorPro
```

### Option 3: Check Console
1. Open Console.app
2. Filter for "LeadExtractorPro"
3. Look for errors

---

## 📋 If Still Crashes:

### Check for:
1. **Import errors** - Missing dependencies
2. **Path errors** - Can't find files
3. **Streamlit errors** - Streamlit not starting
4. **Permission errors** - Can't write to data directory

### Debug Steps:
```bash
# Run from terminal to see errors
dist/LeadExtractorPro.app/Contents/MacOS/LeadExtractorPro 2>&1 | head -50
```

---

## 🔄 Rebuild If Needed:

```bash
./build_macos.sh
```

---

**Try the app now - it should work!** 🚀

