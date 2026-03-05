# 🧪 Testing Standalone App on Your Mac

## 🎯 Goal: Test the app as end users will experience it

Test the app as a standalone `.app` bundle, not from localhost/development mode.

---

## 📋 Step-by-Step Testing Process

### Step 1: Build the Standalone App

```bash
cd /Users/mikeolab/lead-extractor

# Make sure PyInstaller is installed
pip install pyinstaller

# Build the app
./build_macos.sh
```

**Result**: `dist/LeadExtractorPro.app`

---

### Step 2: Test on Clean Environment

#### Option A: Test in Different Location (Recommended)

**Move app to a test location:**
```bash
# Create test directory
mkdir -p ~/Desktop/LeadExtractorTest
cp -r dist/LeadExtractorPro.app ~/Desktop/LeadExtractorTest/

# Test from there
cd ~/Desktop/LeadExtractorTest
open LeadExtractorPro.app
```

#### Option B: Test with Clean User Account (Most Realistic)

**Create a test user account:**
1. System Preferences → Users & Groups
2. Create new test user
3. Log in as test user
4. Copy app to test user's Desktop
5. Run and test

**This simulates a completely fresh installation!**

---

### Step 3: Test Checklist

#### ✅ Basic Functionality:
- [ ] App launches without errors
- [ ] No Python/import errors
- [ ] UI loads correctly
- [ ] All pages accessible

#### ✅ License Activation:
- [ ] Activation dialog appears (if no license)
- [ ] Hardware ID displays correctly
- [ ] Copy button works
- [ ] License key input works
- [ ] Activation succeeds with valid license
- [ ] License status shows in sidebar

#### ✅ Core Features:
- [ ] Live Extractor page loads
- [ ] Server connection works (if server embedded)
- [ ] Search queries work
- [ ] Automation runs
- [ ] Leads are extracted
- [ ] Saved Leads page works
- [ ] Exports work (CSV, Excel, PDF)

#### ✅ Data Persistence:
- [ ] Database created in app directory
- [ ] Leads saved correctly
- [ ] Searches saved correctly
- [ ] Data persists after app restart

#### ✅ File Paths:
- [ ] Exports saved to correct location
- [ ] Database in correct location
- [ ] No absolute path errors

---

### Step 4: Test License Activation Flow

**1. First Run (No License):**
```bash
# Delete any existing license
rm -rf ~/Library/Application\ Support/LeadExtractorPro
# Or wherever the app stores data

# Run app
open dist/LeadExtractorPro.app
```

**Expected:**
- ✅ Activation dialog appears
- ✅ Hardware ID shown
- ✅ Can copy Hardware ID

**2. Generate Test License:**
```bash
# Get Hardware ID from app
# Then generate license
python3 generate_license_admin.py \
    --name "Test User" \
    --machine-id "YOUR_HARDWARE_ID" \
    --plan enterprise \
    --type lifetime
```

**3. Activate License:**
- Enter license key in app
- Should activate successfully
- App should work normally

**4. Test License Persistence:**
- Close app
- Reopen app
- License should still be active
- No need to re-enter license

---

### Step 5: Test Server Integration

**Check if server is embedded:**
- App should auto-start FastAPI server
- Or provide instructions if server needs to run separately

**Test automation:**
- Run a test search
- Verify browser automation works
- Verify leads are extracted

---

## 🔧 Troubleshooting

### Issue: App won't launch
**Check:**
```bash
# Check console logs
Console.app → Look for errors

# Or run from terminal
open -a Console
```

### Issue: Import errors
**Fix:**
- Rebuild with all hidden imports
- Check `build_macos.sh` includes all dependencies

### Issue: Path errors
**Fix:**
- Ensure app uses relative paths
- Check data directory creation

### Issue: License not persisting
**Fix:**
- Check database location
- Ensure app has write permissions

---

## 📋 Quick Test Script

```bash
#!/bin/bash
# Quick test script

echo "🧪 Testing Lead Extractor Pro..."

# Build
echo "1. Building app..."
./build_macos.sh

# Test launch
echo "2. Testing launch..."
open dist/LeadExtractorPro.app

echo "3. App launched! Test manually:"
echo "   - Check activation dialog"
echo "   - Test license activation"
echo "   - Test all features"
echo ""
echo "✅ Testing complete!"
```

---

## 🎯 What to Look For

### ✅ Success Indicators:
- App launches without errors
- No console errors
- All features work
- License activates correctly
- Data persists
- Exports work

### ❌ Failure Indicators:
- Import errors
- Path errors
- Missing dependencies
- License not working
- Data not saving
- Server not starting

---

## 🔍 Detailed Testing

### Test 1: Fresh Installation
```bash
# Clean test
rm -rf ~/Library/Application\ Support/LeadExtractorPro
open dist/LeadExtractorPro.app
```
**Verify:** Activation dialog appears

### Test 2: License Activation
**Verify:**
- License key accepted
- License status shows
- App works after activation

### Test 3: Feature Testing
**Verify:**
- All pages load
- Automation works
- Leads extracted
- Exports work

### Test 4: Persistence
**Verify:**
- Close and reopen app
- License still active
- Data still there

---

## 📦 Distribution Readiness Checklist

Before sending to users:
- [ ] App builds successfully
- [ ] App launches on clean system
- [ ] License activation works
- [ ] All features tested
- [ ] No console errors
- [ ] Data persists correctly
- [ ] Exports work
- [ ] Server integration works (if applicable)
- [ ] Tested on different Mac (if possible)

---

## 🚀 Quick Start Testing

```bash
# 1. Build
./build_macos.sh

# 2. Test
open dist/LeadExtractorPro.app

# 3. Test activation
# - Copy Hardware ID
# - Generate license
# - Activate in app

# 4. Test features
# - Run automation
# - Check exports
# - Verify data saves
```

---

**Ready to test! Build and run the app to ensure everything works!** 🧪

