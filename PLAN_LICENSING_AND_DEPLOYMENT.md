# 🎯 Plan: Licensing, User Management & Desktop App Conversion

## 📋 Overview

Transform Lead Extractor Pro into a licensed desktop application with:
- **Per-computer licensing** (machine ID based)
- **Dynamic user management** (per-user data isolation)
- **Desktop app** (standalone executable)
- **Hosting options** (local, cloud, or hybrid)

---

## 🔐 Part 1: Enhanced Licensing System

### Current State
- ✅ HMAC-signed license keys
- ✅ Expiry date support
- ✅ Basic validation

### Required Enhancements

#### 1.1 Machine ID Generation
**Purpose**: Bind license to specific computer

**Implementation**:
```python
# app/license/machine_id.py
import platform
import hashlib
import uuid

def get_machine_id() -> str:
    """Generate unique machine ID"""
    # Combine multiple hardware identifiers
    machine_info = {
        "hostname": platform.node(),
        "processor": platform.processor(),
        "system": platform.system(),
        "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                                  for i in range(0, 8*6, 8)][::-1]),
    }
    # Create hash
    machine_string = json.dumps(machine_info, sort_keys=True)
    return hashlib.sha256(machine_string.encode()).hexdigest()[:16]
```

#### 1.2 License Key Format (Enhanced)
**New Format**: `PAYLOAD.MACHINE_ID.SIGNATURE`

**Payload Structure**:
```json
{
    "licensee": "John Doe",
    "plan": "enterprise",
    "machine_id": "abc123...",  // NEW: Machine ID
    "issued_at": "2026-02-13T...",
    "expires_at": "2027-02-13T...",
    "max_activations": 1,  // NEW: Limit to 1 machine
    "features": ["pdf_extraction", "batch_processing"]  // NEW: Feature flags
}
```

#### 1.3 License Validation (Enhanced)
**Steps**:
1. Extract machine ID from license
2. Get current machine ID
3. Compare (must match)
4. Check expiry
5. Check activation count (if server-based)

#### 1.4 License Server (Optional)
**For online validation**:
- REST API endpoint: `POST /api/validate-license`
- Checks machine ID against database
- Tracks activations
- Supports license revocation

---

## 👥 Part 2: User Management System

### 2.1 Database Schema (Enhanced)

**Users Table**:
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    license_key TEXT,
    machine_id TEXT,
    plan TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

**User Sessions Table**:
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    session_token TEXT UNIQUE,
    machine_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**User-Specific Data**:
- Each search/lead linked to `user_id`
- Separate databases per user (optional)
- Or single DB with user_id foreign keys

### 2.2 User Authentication Flow

**Option A: Local Only (No Server)**
```
1. User enters license key
2. Validate license (offline)
3. Get/create user profile
4. Store in local database
5. All data isolated by user_id
```

**Option B: Hybrid (Local + Server)**
```
1. User enters license key
2. Validate locally (quick)
3. Sync with server (background)
4. Server validates and updates status
5. Local data synced to server (optional)
```

### 2.3 Dynamic User Interface

**Per-User Features**:
- User profile in sidebar
- User-specific settings
- User-specific data (searches, leads)
- Plan-based feature limits:
  - Free: 10 searches/day
  - Pro: 100 searches/day
  - Enterprise: Unlimited

---

## 💻 Part 3: Desktop App Conversion

### 3.1 Options Comparison

| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| **PyInstaller** | ✅ Native Python, small size, fast | ❌ Platform-specific builds | ✅ **RECOMMENDED** |
| **Electron** | ✅ Cross-platform, modern UI | ❌ Large size (~100MB+), slower | Web-first apps |
| **PyQt/Tkinter** | ✅ Native, lightweight | ❌ Different UI framework | Simple apps |
| **Streamlit Desktop** | ✅ Keep Streamlit UI | ❌ Limited customization | Quick conversion |

### 3.2 Recommended: PyInstaller + Streamlit

**Why**:
- Keep existing Streamlit UI
- Single executable per platform
- Fast startup
- Small file size (~50-80MB)

**Implementation**:
```python
# build_desktop.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    'app/main.py',
    '--name=LeadExtractorPro',
    '--onefile',
    '--windowed',  # No console window
    '--icon=assets/icon.ico',
    '--add-data=app:app',
    '--hidden-import=streamlit',
    '--hidden-import=playwright',
    # ... more imports
])
```

### 3.3 Desktop App Structure

```
LeadExtractorPro.app (macOS) / LeadExtractorPro.exe (Windows)
├── Main executable
├── Embedded Python
├── All dependencies
├── app/ (code)
├── data/ (user database)
└── exports/ (PDF exports)
```

### 3.4 Auto-Start Server

**Embedded Server**:
- FastAPI server runs automatically
- No separate server process needed
- Single executable handles everything

---

## 🌐 Part 4: Hosting Options

### 4.1 Option A: Fully Local (Recommended for MVP)

**Architecture**:
```
Desktop App (Standalone)
├── Streamlit UI (embedded)
├── FastAPI Server (embedded)
├── SQLite Database (local)
└── License Validation (offline)
```

**Pros**:
- ✅ No hosting costs
- ✅ Works offline
- ✅ Fast (no network latency)
- ✅ Privacy (data stays local)

**Cons**:
- ❌ No cloud sync
- ❌ Manual license management
- ❌ No usage analytics

### 4.2 Option B: Hybrid (Local + Cloud)

**Architecture**:
```
Desktop App (Local)
├── Streamlit UI
├── FastAPI Server
├── SQLite Database
└── License Server (Cloud)
    ├── License validation API
    ├── User management
    └── Usage analytics
```

**Cloud Components**:
- **FastAPI Backend** (PythonAnywhere, Heroku, AWS, DigitalOcean)
- **PostgreSQL Database** (for user/license data)
- **REST API** for license validation

**Pros**:
- ✅ License management
- ✅ Usage tracking
- ✅ Cloud sync (optional)
- ✅ License revocation

**Cons**:
- ❌ Requires internet for validation
- ❌ Hosting costs
- ❌ More complex

### 4.3 Option C: Fully Cloud (Web App)

**Not recommended** for desktop app, but possible:
- Deploy Streamlit to Streamlit Cloud
- Deploy FastAPI to cloud
- Users access via browser

---

## 🏗️ Part 5: Implementation Plan

### Phase 1: Enhanced Licensing (Week 1)
- [ ] Add machine ID generation
- [ ] Update license generator to include machine_id
- [ ] Update license validator to check machine_id
- [ ] Test license binding to machine

### Phase 2: User Management (Week 2)
- [ ] Create users table in database
- [ ] Add user authentication flow
- [ ] Implement user-specific data isolation
- [ ] Add user profile UI

### Phase 3: Desktop App (Week 3)
- [ ] Set up PyInstaller build
- [ ] Create build script
- [ ] Test standalone executable
- [ ] Create installer (DMG for macOS, EXE for Windows)

### Phase 4: Optional Cloud Backend (Week 4)
- [ ] Deploy license server API
- [ ] Set up PostgreSQL database
- [ ] Implement license validation endpoint
- [ ] Add usage tracking

---

## 📦 Part 6: Build & Distribution

### 6.1 Build Scripts

**macOS**:
```bash
# build_macos.sh
pyinstaller --name=LeadExtractorPro \
    --onefile \
    --windowed \
    --icon=assets/icon.icns \
    app/main.py
```

**Windows**:
```bash
# build_windows.bat
pyinstaller --name=LeadExtractorPro \
    --onefile \
    --windowed \
    --icon=assets/icon.ico \
    app/main.py
```

### 6.2 Distribution

**Options**:
1. **Direct Download** (Website)
   - Host on your website
   - License key sent via email

2. **GitHub Releases**
   - Free hosting
   - Version management
   - Download tracking

3. **App Stores** (Future)
   - Mac App Store
   - Microsoft Store
   - Requires code signing

---

## 🔧 Part 7: Technical Implementation

### 7.1 Enhanced License Generator

```python
# app/license/generator.py (enhanced)
def generate_license_key(
    secret: str,
    licensee_name: str,
    machine_id: str,  # NEW
    plan: str = "pro",
    days_valid: int = 365,
    max_activations: int = 1,  # NEW
) -> str:
    payload = {
        "licensee": licensee_name,
        "plan": plan,
        "machine_id": machine_id,  # NEW
        "max_activations": max_activations,  # NEW
        "issued_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=days_valid)).isoformat(),
    }
    # ... rest of generation
```

### 7.2 Enhanced License Validator

```python
# app/license/validator.py (enhanced)
def validate_license(license_key: str, secret: str) -> LicenseInfo:
    # ... existing validation ...
    
    # NEW: Check machine ID
    current_machine_id = get_machine_id()
    if payload.get("machine_id") != current_machine_id:
        return LicenseInfo(
            valid=False,
            error="License not valid for this computer"
        )
    
    # ... rest of validation
```

### 7.3 User Management Module

```python
# app/users/manager.py (new)
class UserManager:
    def create_user(self, username: str, license_key: str):
        """Create new user from license"""
        # Validate license
        # Create user record
        # Link to machine_id
        pass
    
    def get_current_user(self):
        """Get current logged-in user"""
        pass
    
    def get_user_data(self, user_id: int):
        """Get all data for specific user"""
        pass
```

### 7.4 Database Schema Updates

```python
# app/database/schema.py (new)
def create_tables():
    """Create all tables including users"""
    conn = get_connection()
    
    # Users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            license_key TEXT,
            machine_id TEXT,
            plan TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    # Update searches table
    conn.execute("""
        ALTER TABLE searches ADD COLUMN user_id INTEGER
    """)
    
    # Update leads table
    conn.execute("""
        ALTER TABLE leads ADD COLUMN user_id INTEGER
    """)
    
    conn.commit()
```

---

## 🎨 Part 8: UI Updates

### 8.1 User Profile Section

**Sidebar Updates**:
- User avatar/name
- Plan badge (Free/Pro/Enterprise)
- License status
- Usage stats (searches today, total leads)

### 8.2 User Settings

**New Settings Page**:
- Change username
- View license details
- Export user data
- Deactivate license (if server-based)

### 8.3 Data Isolation

**Per-User Views**:
- "My Searches" (only user's searches)
- "My Leads" (only user's leads)
- User-specific exports

---

## 📊 Part 9: Feature Matrix by Plan

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Searches/day | 10 | 100 | Unlimited |
| Leads extraction | ✅ | ✅ | ✅ |
| PDF extraction | ✅ | ✅ | ✅ |
| Batch processing | ❌ | ✅ | ✅ |
| Export formats | CSV | CSV, Excel | All formats |
| Cloud sync | ❌ | ❌ | ✅ |
| Priority support | ❌ | ❌ | ✅ |

---

## 🚀 Part 10: Deployment Checklist

### Pre-Launch
- [ ] Enhanced license system implemented
- [ ] Machine ID binding working
- [ ] User management system complete
- [ ] Desktop app builds successfully
- [ ] Installers created (DMG/EXE)
- [ ] License generator tool ready
- [ ] Documentation updated

### Launch
- [ ] Website/landing page
- [ ] License purchase flow (if applicable)
- [ ] Download page
- [ ] Support email/chat
- [ ] User documentation

### Post-Launch
- [ ] Usage analytics (if cloud)
- [ ] License management dashboard
- [ ] User support system
- [ ] Update mechanism (auto-update)

---

## 💡 Recommendations

### MVP Approach (Recommended)
1. **Start with Local-Only**
   - Machine ID-based licensing
   - Local user management
   - PyInstaller desktop app
   - No cloud dependency

2. **Add Cloud Later** (if needed)
   - License validation API
   - Usage tracking
   - Cloud sync

### Tech Stack
- **Desktop App**: PyInstaller + Streamlit
- **License**: HMAC + Machine ID
- **Database**: SQLite (local) + PostgreSQL (if cloud)
- **Backend**: FastAPI (embedded in app)
- **Hosting**: Local first, cloud optional

---

## 📝 Next Steps

1. **Implement machine ID generation**
2. **Update license system** (add machine_id)
3. **Create user management** (database + UI)
4. **Set up PyInstaller** build
5. **Test desktop app** on target platforms
6. **Create installers**
7. **Set up distribution** (website/GitHub)

---

**Status**: Ready to implement! 🎯

