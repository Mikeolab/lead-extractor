# Send Lead Extractor to RDP Windows and Test

## Where things are on your Mac

| What | Location on Mac |
|------|------------------|
| **Project folder** | `/Users/mikeolab/lead-extractor` |
| **Windows build script** | `lead-extractor/build_windows.bat` |
| **After you build on Windows** | The app will be at `dist\LeadExtractorPro.exe` on the Windows machine |

There is **no pre-built .exe on your Mac**. The Windows .exe is created **on the Windows (RDP) machine** when you run the build script there.

---

## Easiest way: send project to RDP, then build on RDP

### Step 1: Zip the project on your Mac

In Terminal on your Mac:

```bash
cd /Users/mikeolab
zip -r lead-extractor-for-windows.zip lead-extractor -x "lead-extractor/__pycache__/*" -x "lead-extractor/.git/*" -x "lead-extractor/build/*" -x "lead-extractor/dist/*" -x "*.pyc"
```

This creates **`/Users/mikeolab/lead-extractor-for-windows.zip`** (you can use Finder to find it in your home folder).

---

### Step 2: Get the zip onto the RDP Windows machine

**Option A – RDP drive mapping (no cloud)**

1. Open **Microsoft Remote Desktop** on your Mac.
2. Edit your RDP connection → **“Local Resources”** tab.
3. Click **“More…”** under “Local devices and resources”.
4. Check **“Drives”** and select your Mac disk (e.g. “Macintosh HD” or your user volume).
5. Save and connect to the RDP.

On the Windows RDP session:

1. Open **File Explorer**.
2. In the left pane, under **“This PC”**, look for something like **“Macintosh HD”** or your Mac’s name (it’s the RDP “tsclient” share).
3. Open it and go to `Users\mikeolab`.
4. Copy **`lead-extractor-for-windows.zip`** to the Windows Desktop (or any folder, e.g. `C:\Users\YourUser\Desktop`).
5. Right‑click the zip → **Extract All** → choose a folder (e.g. Desktop). You’ll get a folder like `lead-extractor`.

**Option B – Google Drive (or OneDrive / Dropbox)**

1. On your Mac: upload **`lead-extractor-for-windows.zip`** to Google Drive (from Finder or drive.google.com).
2. On the RDP Windows machine: open a browser, go to drive.google.com, download the zip.
3. Right‑click the zip → **Extract All** (e.g. to Desktop). You’ll get a folder `lead-extractor`.

---

### Step 3: On RDP Windows – install Python (one-time)

The build script needs Python on the Windows machine:

1. In the RDP session, open a browser and go to **https://www.python.org/downloads/**.
2. Download **Python 3.9 or newer** for Windows.
3. Run the installer.
4. **Important:** check **“Add Python to PATH”**, then finish the install.
5. Close any open Command Prompt windows, then open a **new** Command Prompt.

---

### Step 4: Build the app on RDP (creates the “installer” .exe)

1. On the RDP Windows machine, open **Command Prompt** (or PowerShell).
2. Go to the folder where you extracted the project (e.g. Desktop):

   ```cmd
   cd Desktop\lead-extractor
   ```
   (If you put it somewhere else, use that path, e.g. `cd C:\Users\YourUser\Downloads\lead-extractor`.)

3. Run the Windows build script:

   ```cmd
   build_windows.bat
   ```

4. Wait for the build to finish (several minutes). When it’s done you’ll see:
   - **`dist\LeadExtractorPro.exe`** — this is your app.

So: **the “installer” / app is just that one file:**  
`dist\LeadExtractorPro.exe` (created on the Windows machine when you run `build_windows.bat`).

---

### Step 5: “Install” and test (no real installer)

There is no separate installer. You just run the .exe:

1. In File Explorer, go to the project folder, then into **`dist`**.
2. Double‑click **`LeadExtractorPro.exe`**.
3. The app will start and should open in your browser. You can test from there.

To “uninstall”, just delete the folder and the .exe; no Windows “Add/Remove Programs” step.

---

## Quick reference

| Step | Where | What to do |
|------|--------|------------|
| 1 | Mac | Create `lead-extractor-for-windows.zip` (command above). |
| 2 | Mac → RDP | Copy zip to RDP via drive mapping or Google Drive, then extract. |
| 3 | RDP | Install Python (add to PATH) if not already. |
| 4 | RDP | `cd` to `lead-extractor` folder, run `build_windows.bat`. |
| 5 | RDP | Run `dist\LeadExtractorPro.exe` to test. |

**Where is the “installer”?**  
On the **Windows (RDP) machine**, after building: **`dist\LeadExtractorPro.exe`** inside the project folder. There is no installer to run; that .exe is the app.
