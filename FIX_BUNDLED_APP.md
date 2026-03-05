# 🔧 Fix: App Crashes on Launch (Bundled App)

## 🐛 Problem
App shows in dock then disappears - it's crashing on startup.

## 🔍 Common Causes:
1. **Path issues** - App can't find its resources
2. **Missing imports** - Dependencies not bundled
3. **Server startup** - FastAPI server fails to start
4. **Data directory** - Can't create/write to data directory

## ✅ Fixes Applied:

### 1. Fixed Path Handling
- App now detects if it's bundled (PyInstaller)
- Uses `sys._MEIPASS` for resources
- Uses user's Application Support for data

### 2. Data Directory
- Bundled app uses: `~/Library/Application Support/LeadExtractorPro/`
- Development uses: `project/data/` and `project/exports/`

### 3. Next Steps:
- Rebuild the app
- Test again
- Check console logs if still crashes

---

## 🧪 Debug Steps:

### Check Console Logs:
```bash
# Open Console.app
open -a Console

# Filter for LeadExtractorPro
# Look for red errors
```

### Or from Terminal:
```bash
# Run app and capture output
/Users/mikeolab/lead-extractor/dist/LeadExtractorPro.app/Contents/MacOS/LeadExtractorPro 2>&1 | head -50
```

---

**Rebuild the app and test again!** 🔧

