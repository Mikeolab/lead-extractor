# 🖥️ Testing on Windows RDP - Complete Guide

## 📋 Overview

Testing Lead Extractor Pro on Windows via RDP (Remote Desktop Protocol) from your Mac. This guide covers file transfer, Playwright considerations, and potential issues.

---

## 📦 File Transfer Options

### Option 1: RDP Clipboard (Easiest for Small Files)

**For the build script and source files:**

1. **Copy files on Mac:**
   ```bash
   # Copy these files to clipboard or create a zip
   zip -r windows_build_files.zip \
     launch_app_windows.py \
     LeadExtractorPro_windows.spec \
     build_windows.bat \
     package_windows.bat \
     app/ \
     requirements.txt
   ```

2. **In RDP session:**
   - Paste files directly (RDP supports clipboard)
   - Or use RDP's "Local Resources" → "Drives" to mount your Mac drive

### Option 2: RDP Drive Mapping (Recommended)

**Mount your Mac drive in RDP:**

1. **Before connecting to RDP:**
   - Open RDP client settings
   - Go to "Local Resources" tab
   - Check "Drives" → Select your Mac drive
   - Connect to RDP

2. **In RDP session:**
   - Open File Explorer
   - Look for "\\tsclient\MacDriveName" or similar
   - Copy files directly from your Mac

### Option 3: Google Drive / Cloud Storage

**If RDP file sharing doesn't work:**

1. **Upload to Google Drive from Mac:**
   ```bash
   # Create zip of build files
   zip -r LeadExtractorPro_Windows_Build.zip \
     launch_app_windows.py \
     LeadExtractorPro_windows.spec \
     build_windows.bat \
     package_windows.bat \
     app/ \
     requirements.txt
   ```

2. **Download in RDP:**
   - Open browser in RDP session
   - Download from Google Drive
   - Extract and build

### Option 4: Network Share / SMB

**If both machines are on same network:**

```bash
# On Mac, share folder
# Then in RDP Windows, map network drive:
net use Z: \\MacIP\SharedFolder
```

---

## ⚠️ Playwright in RDP - Important Considerations

### The Problem

**Playwright may have issues in RDP sessions because:**

1. **No GPU Acceleration:** RDP sessions often lack GPU access
2. **Display Limitations:** RDP uses virtual display drivers
3. **Browser Rendering:** Chromium may not render properly in RDP
4. **Headless Mode:** May not work as expected in RDP

### Current Configuration

Looking at `automation_server.py`, browsers are launched with:
```python
self.browser = await self.playwright.chromium.launch(
    headless=False,  # Visible browser
    ...
)
```

**This means:** The browser will try to open visibly, which may not work well in RDP.

---

## 🔧 Solutions for RDP Testing

### Solution 1: Force Headless Mode for RDP (Recommended)

**Modify the browser launch to detect RDP and use headless:**

Update `automation_server.py`:

```python
import os

# Detect if running in RDP session
def is_rdp_session():
    """Detect if running in RDP session"""
    if sys.platform == 'win32':
        # Check for RDP session indicators
        return (
            os.environ.get('SESSIONNAME', '').startswith('RDP') or
            os.environ.get('CLIENTNAME', '') != '' or
            os.environ.get('REMOTE_SESSION', '0') == '1'
        )
    return False

# In run_automation method:
headless_mode = is_rdp_session()  # Use headless in RDP
self.browser = await self.playwright.chromium.launch(
    headless=headless_mode,
    ...
)
```

### Solution 2: Use Virtual Display (Advanced)

**Install virtual display driver on Windows RDP:**

1. **Install Xvfb or similar** (if available for Windows)
2. **Or use VNC** instead of RDP for better display support

### Solution 3: Test Locally First

**Build on RDP, test locally:**

1. Build the `.exe` on RDP Windows machine
2. Transfer `.exe` back to Mac
3. Test in local Windows VM or actual Windows machine

---

## 🚀 Recommended Testing Workflow

### Step 1: Transfer Files to RDP

**Use RDP drive mapping (easiest):**

1. Connect to RDP with drive mapping enabled
2. Copy entire project folder to Windows desktop
3. Or copy just build files if you'll build on RDP

### Step 2: Build on RDP

```cmd
REM In RDP Windows session
cd C:\Users\YourUser\Desktop\lead-extractor
build_windows.bat
```

### Step 3: Test Considerations

**For RDP testing, you have two options:**

#### Option A: Test UI Only (No Browser Automation)

- Test Streamlit UI
- Test database operations
- Test PDF export
- **Skip browser automation tests** (Playwright issues)

#### Option B: Modify for RDP

- Add RDP detection
- Force headless mode
- Test browser automation

### Step 4: Transfer Built Executable Back

**After building:**

1. Copy `dist\LeadExtractorPro.exe` back to Mac
2. Test on local Windows VM/machine
3. Or distribute to actual Windows users

---

## 🛠️ Quick Fix: Add RDP Detection

I can add RDP detection to automatically use headless mode. Would you like me to:

1. **Add RDP detection** to `automation_server.py`
2. **Auto-switch to headless** when RDP detected
3. **Add environment variable override** for manual control

---

## 📝 Testing Checklist for RDP

- [ ] Files transferred to RDP Windows machine
- [ ] Python installed on RDP Windows
- [ ] Build script runs successfully
- [ ] Executable created (`dist\LeadExtractorPro.exe`)
- [ ] Streamlit UI opens in browser (in RDP)
- [ ] FastAPI server starts
- [ ] Database operations work
- [ ] PDF export works
- [ ] **Browser automation** (may need headless mode)
- [ ] Transfer `.exe` back to Mac for local testing

---

## 🎯 Best Practice Recommendation

**For RDP testing:**

1. **Build on RDP** (Windows environment)
2. **Test UI/backend** on RDP (Streamlit, database, etc.)
3. **Transfer `.exe` to local Windows** for full browser automation testing
4. **Or use headless mode** for RDP browser automation tests

---

## 🔍 Troubleshooting RDP Issues

### Browser Won't Open

**Problem:** Playwright browser doesn't open in RDP

**Solution:**
- Use headless mode
- Or test browser automation locally

### Display Errors

**Problem:** "Display not found" or rendering errors

**Solution:**
- Force headless mode
- Check RDP display settings
- Use VNC instead of RDP

### Performance Issues

**Problem:** App runs slowly in RDP

**Solution:**
- Normal for RDP (network latency)
- Test locally for real performance
- RDP is fine for build verification

---

## 💡 Quick Answer to Your Questions

**Q: Must I use Google Drive?**  
A: No! Use RDP drive mapping (easiest) or clipboard transfer.

**Q: Will Playwright affect anything?**  
A: Yes! Playwright may not work well in RDP. Use headless mode or test locally.

**Q: Why?**  
A: RDP lacks GPU acceleration and proper display drivers that browsers need.

---

**Would you like me to add RDP detection and auto-headless mode to the code?**
