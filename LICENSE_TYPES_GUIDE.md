# 📋 License Types & Validity Guide

## ✅ License Binding: ONE COMPUTER PER LICENSE

**Current System**: Machine-bound (restricted to one computer)
- ✅ License tied to specific Machine ID
- ✅ Cannot be used on different computer
- ✅ Already working as you want!

---

## 🎯 License Validity Types

### Available Types:

#### 1. **Lifetime License** (Permanent)
```bash
python3 generate_license_admin.py \
    --name "Mike" \
    --machine-id "70998ed59f0f1577" \
    --plan enterprise \
    --type lifetime
```
- **Duration**: 100 years (effectively permanent)
- **Use case**: One-time purchase, permanent access
- **Days**: 36,500 days

#### 2. **Monthly Subscription**
```bash
python3 generate_license_admin.py \
    --name "John" \
    --machine-id "abc123..." \
    --plan pro \
    --type monthly
```
- **Duration**: 30 days
- **Use case**: Monthly recurring subscription
- **Days**: 30 days

#### 3. **Quarterly Subscription** (3 Months)
```bash
python3 generate_license_admin.py \
    --name "Jane" \
    --machine-id "def456..." \
    --plan enterprise \
    --type quarterly
```
- **Duration**: 90 days
- **Use case**: 3-month subscription
- **Days**: 90 days

#### 4. **Semiannual Subscription** (6 Months)
```bash
python3 generate_license_admin.py \
    --name "Bob" \
    --machine-id "ghi789..." \
    --plan pro \
    --type semiannual
```
- **Duration**: 180 days
- **Use case**: 6-month subscription
- **Days**: 180 days

#### 5. **Yearly Subscription**
```bash
python3 generate_license_admin.py \
    --name "Alice" \
    --machine-id "jkl012..." \
    --plan enterprise \
    --type yearly
```
- **Duration**: 365 days
- **Use case**: Annual subscription
- **Days**: 365 days

#### 6. **Custom Period** (Any Number of Days)
```bash
python3 generate_license_admin.py \
    --name "Charlie" \
    --machine-id "mno345..." \
    --plan pro \
    --days 45  # Custom: 45 days
```
- **Duration**: Any number of days you specify
- **Use case**: Special promotions, trial periods, custom terms
- **Days**: Whatever you set

---

## 📊 Summary Table

| Type | Days | Use Case |
|------|------|----------|
| `lifetime` | 36,500 | One-time purchase, permanent |
| `monthly` | 30 | Monthly subscription |
| `quarterly` | 90 | 3-month subscription |
| `semiannual` | 180 | 6-month subscription |
| `yearly` | 365 | Annual subscription |
| `--days X` | Custom | Any custom period |

---

## 🔄 Workflow Examples

### Example 1: Customer Buys Lifetime License
```bash
# Customer sends Hardware ID: "70998ed59f0f1577"
# Customer paid for: Lifetime Enterprise

python3 generate_license_admin.py \
    --name "Customer Name" \
    --machine-id "70998ed59f0f1577" \
    --plan enterprise \
    --type lifetime

# Send license key to customer
```

### Example 2: Customer Subscribes Monthly
```bash
# Customer sends Hardware ID: "abc123def456"
# Customer paid for: Monthly Pro

python3 generate_license_admin.py \
    --name "Customer Name" \
    --machine-id "abc123def456" \
    --plan pro \
    --type monthly

# Send license key to customer
# Renew after 30 days (generate new license)
```

### Example 3: Customer Buys Yearly
```bash
# Customer sends Hardware ID: "def456ghi789"
# Customer paid for: Yearly Enterprise

python3 generate_license_admin.py \
    --name "Customer Name" \
    --machine-id "def456ghi789" \
    --plan enterprise \
    --type yearly

# Send license key to customer
# Renew after 365 days (generate new license)
```

---

## ✅ Key Points:

1. **One Computer Per License** ✅
   - License is machine-bound
   - Cannot be used on different computer
   - Already working correctly!

2. **Flexible Validity** ✅
   - Preset types: lifetime, monthly, yearly, etc.
   - Custom periods: use `--days` for any number of days
   - Easy to set different subscription models

3. **No Sharing Across Computers** ✅
   - Machine ID binding prevents this
   - Each computer needs its own license
   - Already enforced!

---

## 🎯 Your Admin License

Generate your own admin license (lifetime):
```bash
python3 generate_license_admin.py \
    --name "Admin" \
    --machine-id "70998ed59f0f1577" \
    --plan enterprise \
    --type lifetime
```

Or use the quick script:
```bash
./generate_admin_license.sh
```

---

**All set! You can now generate licenses with any validity period you want!** 🚀

