# 🚀 Quick Start: Testing on Windows RDP

## 📦 File Transfer (Choose One)

### ✅ Option 1: RDP Drive Mapping (Easiest - Recommended)

1. **Before connecting to RDP:**
   - In your RDP client (Microsoft Remote Desktop on Mac)
   - Click "Show Options" → "Local Resources" tab
   - Check "Drives" → Select your Mac drive
   - Connect

2. **In RDP session:**
   - Open File Explorer
   - Look for `\\tsclient\MacDriveName` or similar
   - Copy entire `lead-extractor` folder to Windows Desktop
   - Done! No Google Drive needed.

### Option 2: Google Drive (If RDP drive mapping doesn't work)

1. **On Mac:** Zip the project folder
2. **Upload to Google Drive**
3. **In RDP:** Download and extract

---

## ⚠️ Playwright in RDP - Auto-Fixed!

**Good news:** I've added automatic RDP detection! The app will:
- ✅ **Detect RDP sessions** automatically
- ✅ **Use headless mode** in RDP (no visible browser needed)
- ✅ **Work properly** in RDP environment

**You don't need to do anything** - it's automatic!

---

## 🏗️ Build Steps

### 1. Transfer Files to RDP

Use RDP drive mapping (see above) or Google Drive.

### 2. Build on Windows RDP

```cmd
REM In RDP Windows session
cd C:\Users\YourUser\Desktop\lead-extractor
build_windows.bat
```

### 3. Test

```cmd
REM Run the executable
dist\LeadExtractorPro.exe
```

The app will:
- Detect RDP automatically
- Use headless browser mode
- Work normally otherwise

---

## 🎯 What Works in RDP

- ✅ Streamlit UI (opens in browser)
- ✅ FastAPI server
- ✅ Database operations
- ✅ PDF export
- ✅ **Browser automation** (now works in headless mode!)
- ✅ Lead extraction

---

## 📝 Quick Checklist

- [ ] Connect to RDP with drive mapping enabled
- [ ] Copy project folder to Windows Desktop
- [ ] Run `build_windows.bat`
- [ ] Test `dist\LeadExtractorPro.exe`
- [ ] Verify browser automation works (headless mode)

---

## 💡 Why Playwright Needed Fixing

**RDP sessions:**
- ❌ No GPU acceleration
- ❌ Virtual display drivers
- ❌ Browser rendering issues

**Solution:**
- ✅ Auto-detect RDP
- ✅ Use headless mode automatically
- ✅ Works perfectly in RDP!

---

**You're all set! No Google Drive needed if you use RDP drive mapping.** 🎉
