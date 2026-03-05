# 📦 Quick Build Instructions

## 🚀 Build Desktop App in 3 Steps

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Build for Your Platform

**Mac:**
```bash
./build_macos.sh
```

**Windows:**
```bash
build_windows.bat
```

### Step 3: Test & Distribute
- Test the generated `.app` (Mac) or `.exe` (Windows)
- Upload to your website or GitHub
- Users download and run!

---

## 📋 What Gets Built

### Mac:
- `dist/LeadExtractorPro.app` - Standalone app bundle
- Users double-click to run
- No Python installation needed

### Windows:
- `dist/LeadExtractorPro.exe` - Standalone executable
- Users double-click to run
- No Python installation needed

---

## ⚠️ Important Notes

1. **File Size**: Expect 50-150 MB (includes everything)
2. **First Run**: May be slower (extracting files)
3. **Playwright**: Browsers may need to be installed separately
4. **Testing**: Always test on a clean machine before distributing

---

## 🎯 Distribution Options

1. **Direct Download**: Upload `.app` or `.exe` to your website
2. **GitHub Releases**: Free hosting with version management
3. **Installer**: Create DMG (Mac) or installer (Windows) for professional distribution

---

**Ready to build!** 🚀

