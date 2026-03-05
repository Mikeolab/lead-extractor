# 🔐 License System: How It Works (Simple & Secure)

## 🎯 The Simple Flow

### For You (Admin):
1. User pays on your website/platform (external)
2. User sends you their Hardware ID
3. You run license generator: `python generate_license.py`
4. You send license key to user (email)
5. Done! ✅

### For User:
1. User opens app → Sees "License Activation Required"
2. User copies Hardware ID (shown in dialog)
3. User sends Hardware ID to you
4. User receives license key (from you)
5. User enters license key in app
6. App validates → Activated! ✅

---

## 🛡️ Security: Why Users Can't Bypass

### 1. **HMAC Signature** (Cryptographic Lock)
```
License Key = PAYLOAD + SIGNATURE
             (data)    (cryptographic proof)
```

**What it means**:
- Signature is created with a **secret key** (only you have it)
- **Cannot be forged** - user can't create valid signature
- **Cannot be modified** - any change breaks signature
- **Mathematically secure** - HMAC-SHA256 is unbreakable

**User tries to modify license**:
- Changes expiry date → Signature invalid → ❌ Rejected
- Changes plan → Signature invalid → ❌ Rejected
- Creates fake license → No valid signature → ❌ Rejected

### 2. **Machine ID Binding** (Hardware Lock)
```
License contains: machine_id = "70998ed59f0f1577"
App checks: current_machine_id = "70998ed59f0f1577"
Must match → ✅ Valid
```

**What it means**:
- License is **tied to specific computer**
- **Cannot be shared** - won't work on different machine
- **Cannot be copied** - machine ID is unique

**User tries to share license**:
- Copies license to another computer → Machine ID mismatch → ❌ Rejected
- Tries to change machine ID → Can't (it's hardware-based) → ❌ Rejected

### 3. **Offline Validation** (No Network Bypass)
```
Validation happens: Locally in app
No server calls: Cannot bypass server
No network: Cannot bypass network
```

**What it means**:
- All validation happens **inside the app**
- **No external dependencies** - can't bypass by blocking network
- **No server to hack** - validation is in compiled code

**User tries to bypass**:
- Blocks network → Still validates (offline) → ❌ Can't bypass
- Modifies code → App breaks (compiled) → ❌ Can't bypass

### 4. **Expiry Date** (Time Lock)
```
License contains: expires_at = "2027-02-13"
App checks: current_date = "2026-02-13"
Not expired → ✅ Valid
```

**What it means**:
- License has **expiry date** in payload
- Checked on **every validation**
- **Cannot be extended** without new license

**User tries to extend**:
- Changes system date → Possible but rare → ⚠️ Minor risk
- Modifies expiry in license → Signature breaks → ❌ Rejected

---

## 📋 License Key Structure

### Current Format:
```
PAYLOAD.SIGNATURE
```

**Example**:
```
eyJsaWNlbnNlZSI6Ik1pa2UiLCJwbGFuIjoiZW50ZXJwcmlzZSIsImV4cGlyZXNfYXQiOiIyMDI3LTAyLTEzVDE4OjAwOjAwWiJ9.a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

### Enhanced Format (With Machine ID):
```
PAYLOAD.MACHINE_ID.SIGNATURE
```

**Example**:
```
eyJsaWNlbnNlZSI6Ik1pa2UiLCJwbGFuIjoiZW50ZXJwcmlzZSIsIm1hY2hpbmVfaWQiOiI3MDk5OGVkNTlmMGYxNTc3IiwiZXhwaXJlc19hdCI6IjIwMjctMDItMTNUMTg6MDA6MDBaIn0.70998ed59f0f1577.a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

**Parts**:
1. **PAYLOAD** (Base64): Licensee name, plan, machine_id, expiry
2. **MACHINE_ID** (16-char hex): Hardware identifier
3. **SIGNATURE** (64-char hex): HMAC-SHA256 signature

---

## 🔄 Complete Workflow

### Step 1: User Opens App (No License)
```
App starts → Checks for license → None found → Shows activation dialog
```

### Step 2: User Sees Hardware ID
```
Dialog shows:
┌─────────────────────────────┐
│ Your Hardware ID:           │
│ 7099-8ed5-9f0f-1577  [Copy] │
└─────────────────────────────┘
```

### Step 3: User Requests License
```
User copies Hardware ID → Sends to you → You process payment (external) → You generate license
```

### Step 4: You Generate License
```python
# You run this (admin tool)
from app.license.generator import generate_license_key
from app.config import LICENSE_SECRET

license_key = generate_license_key(
    secret=LICENSE_SECRET,
    licensee_name="Mike",
    machine_id="70998ed59f0f1577",  # From user
    plan="enterprise",
    days_valid=365
)

# Send to user: license_key
```

### Step 5: User Activates
```
User enters license key → App validates:
  1. Check HMAC signature ✅
  2. Check machine ID match ✅
  3. Check expiry date ✅
  → All valid → License activated! ✅
```

### Step 6: App Works
```
License valid → App features unlocked → User can use app
```

---

## 🚫 What Users CANNOT Do

### ❌ Cannot Create Fake License
- **Why**: Need secret key to create valid signature
- **Result**: Invalid signature → Rejected

### ❌ Cannot Modify License
- **Why**: Any change breaks HMAC signature
- **Result**: Invalid signature → Rejected

### ❌ Cannot Share License
- **Why**: License tied to specific machine ID
- **Result**: Machine ID mismatch → Rejected

### ❌ Cannot Bypass Validation
- **Why**: Validation happens in app code
- **Result**: App won't work without valid license

### ❌ Cannot Use Expired License
- **Why**: Expiry date checked on every validation
- **Result**: Expired → Rejected

---

## ✅ What Users CAN Do

### ✅ Use App on Licensed Machine
- License works on the computer it was issued for
- No internet required (offline validation)

### ✅ Reinstall App
- License stored in database
- Works after reinstall (same machine)

---

## 💼 Your Admin Workflow

### Generate License (After Payment)
```bash
# User sends: Hardware ID = "70998ed59f0f1577"
# User paid for: Enterprise plan, 1 year

python3 generate_license.py \
    --name "Mike" \
    --machine-id "70998ed59f0f1577" \
    --plan "enterprise" \
    --days 365

# Output: License key
# Send to user via email
```

### Track Licenses (Optional)
```sql
-- Store in your database
INSERT INTO licenses (
    licensee_name,
    machine_id,
    license_key,
    plan,
    issued_at,
    expires_at
) VALUES (
    'Mike',
    '70998ed59f0f1577',
    'eyJsaWNlbnNlZSI6...',
    'enterprise',
    '2026-02-13',
    '2027-02-13'
);
```

---

## 🎨 UI Implementation

### Activation Dialog (Like Screenshot)
- ✅ Shows Hardware ID with copy button
- ✅ License key input field
- ✅ Activate button
- ✅ Error messages (invalid, wrong machine, expired)
- ✅ Contact information

### License Status (Sidebar)
- ✅ Shows license status (Active/Expired)
- ✅ Shows plan (Free/Pro/Enterprise)
- ✅ Shows expiry date
- ✅ Shows user name

---

## 🔧 Technical Details

### Validation Process
```python
def validate_license(license_key, secret):
    # 1. Split license key
    payload, signature = license_key.split(".")
    
    # 2. Verify HMAC signature
    expected_sig = hmac.new(secret, payload, sha256).hexdigest()
    if signature != expected_sig:
        return False  # Invalid signature
    
    # 3. Decode payload
    payload_data = base64_decode(payload)
    
    # 4. Check machine ID
    if payload_data["machine_id"] != get_machine_id():
        return False  # Wrong machine
    
    # 5. Check expiry
    if datetime.now() > payload_data["expires_at"]:
        return False  # Expired
    
    return True  # Valid!
```

### Storage
```sql
-- License stored in local database
CREATE TABLE app_license (
    license_key TEXT UNIQUE,
    machine_id TEXT,
    activated_at TIMESTAMP,
    is_active BOOLEAN
);
```

---

## 📊 Summary

### ✅ Secure
- HMAC signature (cannot forge)
- Machine ID binding (cannot share)
- Offline validation (cannot bypass)
- Expiry date (time-limited)

### ✅ Simple
- No payment in app
- No server required
- User-friendly UI
- Clear workflow

### ✅ Flexible
- Easy to generate licenses
- Track licenses (optional)
- Upgrade/downgrade plans
- Revoke licenses (if needed)

**Ready to implement!** 🚀

