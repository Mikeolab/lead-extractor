# RDP: Fix pip and build – exact commands

On your RDP Windows machine, run these in **Command Prompt as Administrator**.

---

## 1. Fix pip (if "No module named pip")

Run these **one at a time**:

```cmd
cd C:\Users\Administrator\Downloads\lead-extractor-for-windows\lead-extractor
```

```cmd
powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'get-pip.py' -UseBasicParsing"
```

```cmd
python get-pip.py
```

```cmd
python -m pip --version
```

You should see a pip version. Then continue to step 2.

---

## 2. Install PyInstaller and build

Still in the same folder:

```cmd
python -m pip install pyinstaller
```

```cmd
python -m pip install -r requirements.txt
```

```cmd
build_windows.bat
```

When the build finishes, the app is at: **`dist\LeadExtractorPro.exe`**

---

## 3. Run the app

```cmd
dist\LeadExtractorPro.exe
```

---

## If you have the updated zip (with fixed build_windows.bat)

The updated `build_windows.bat` now:

- Uses **`python -m pip`** and **`python -m PyInstaller`** (so it works even when `pip`/`pyinstaller` are not on PATH).
- Tries to install pip automatically if it’s missing (using get-pip.py).

So you can:

1. On your **Mac**: create a new zip (the project now has the updated `build_windows.bat`).
2. Upload to WeTransfer again and download on RDP.
3. Extract and run **`build_windows.bat`** from the `lead-extractor` folder.

If pip is missing, the script will try to install it; then it will install PyInstaller and run the build.
