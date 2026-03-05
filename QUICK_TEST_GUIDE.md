# ⚡ Quick Test Guide: Standalone App

## 🚀 Fastest Way to Test

### Option 1: Quick Test Script (Easiest)
```bash
./test_standalone.sh
```

This will:
- Build the app (if needed)
- Copy to test location
- Clean previous data
- Launch the app
- Show test checklist

---

### Option 2: Manual Test

**Step 1: Build**
```bash
./build_macos.sh
```

**Step 2: Test**
```bash
# Clean any existing data
rm -rf ~/Library/Application\ Support/LeadExtractorPro

# Launch app
open dist/LeadExtractorPro.app
```

**Step 3: Test Activation**
1. App should show activation dialog
2. Copy Hardware ID
3. Generate license:
   ```bash
   python3 generate_license_admin.py \
       --name "Test User" \
       --machine-id "YOUR_HARDWARE_ID" \
       --plan enterprise \
       --type lifetime
   ```
4. Enter license key in app
5. Should activate ✅

---

## ✅ What to Verify

### Basic:
- [ ] App launches
- [ ] No errors in Console
- [ ] UI loads correctly

### License:
- [ ] Activation dialog appears
- [ ] Hardware ID shows
- [ ] License activates
- [ ] License persists after restart

### Features:
- [ ] All pages work
- [ ] Automation runs
- [ ] Leads extracted
- [ ] Exports work

---

## 🔍 Check for Errors

**Open Console.app:**
1. Open Console.app (Applications → Utilities)
2. Filter for "LeadExtractorPro"
3. Look for errors (red text)

**Or from terminal:**
```bash
# Watch logs
log stream --predicate 'process == "LeadExtractorPro"' --level debug
```

---

## 📋 Test Checklist

**First Run:**
- ✅ Activation dialog appears
- ✅ Hardware ID displays
- ✅ Copy button works

**After Activation:**
- ✅ License status shows
- ✅ App works normally
- ✅ All features accessible

**After Restart:**
- ✅ License still active
- ✅ No need to re-enter license
- ✅ Data persists

---

**Run `./test_standalone.sh` to start testing!** 🧪

