# 📋 Session-Based Campaign Creation

## ✅ What's New

The email campaign creator now supports **session-based lead selection** - just like how the extractor works!

---

## 🎯 Key Features

### 1. **Select Leads by Session**
- View all extraction sessions (from Live Extractor)
- See session details: query, lead count, date
- Select one or multiple sessions to merge

### 2. **Merge Multiple Sessions**
- Combine leads from multiple extraction sessions
- Perfect for creating larger campaigns
- See which session each lead came from

### 3. **Smart Campaign Planning**
- **Target Send Count**: Limit campaign to specific number of emails
- **Deduplication**: Remove duplicate emails across sessions
- **Session Summary**: See which sessions are included

### 4. **Quick Selection Tools**
- **Select All Sessions**: One-click to select everything
- **Clear Selection**: Reset selection
- **Select Today's Sessions**: Quick filter for recent extractions

---

## 📊 How It Works

### Step 1: Select Sessions

1. Go to **📧 Sender** → **📨 Create Campaign**
2. Choose **"From Sessions (Extractor)"** as lead source
3. Browse sessions grouped by date
4. Check boxes to select sessions you want to merge
5. See total leads count update in real-time

### Step 2: Plan Your Campaign

- **Target Emails to Send**: Set how many emails you want to send
  - Useful for testing (start with 100)
  - Or capacity planning (match your mailbox limits)
  
- **Remove Duplicate Emails**: 
  - If same email appears in multiple sessions
  - System keeps only one copy
  - Shows deduplicated count

### Step 3: Preview & Create

- See preview of leads with session info
- Campaign name auto-generates with session info
- Create campaign as usual

---

## 🎨 UI Features

### Session Display

Each session shows:
- **Session ID**: Unique identifier (#123)
- **Query**: The search query used
- **Lead Count**: How many leads extracted
- **Date/Time**: When extraction ran

### Grouped by Date

Sessions are grouped by date for easy browsing:
```
📅 2026-02-18 (5 sessions)
  ☑ Session #123: "digital twin engineers" (45 leads)
  ☐ Session #124: "AI consultants" (32 leads)
  ...
```

### Quick Actions

Three buttons for fast selection:
- **✅ Select All Sessions** - Select everything
- **❌ Clear Selection** - Deselect all
- **📅 Select Today's Sessions** - Only today's extractions

---

## 📈 Use Cases

### Use Case 1: Single Session Campaign
**Scenario:** You extracted 500 leads from one search query

**Steps:**
1. Select that one session
2. Set target sends to 500 (or less for testing)
3. Create campaign

**Result:** Campaign with leads from that specific extraction

---

### Use Case 2: Merge Multiple Sessions
**Scenario:** You ran 5 different searches, each got 100 leads. You want one campaign with all 500.

**Steps:**
1. Select all 5 sessions
2. Enable "Remove Duplicate Emails" (in case of overlap)
3. Set target sends to 500
4. Create campaign

**Result:** One campaign merging all 5 sessions

---

### Use Case 3: Capacity-Based Planning
**Scenario:** You have 3 Gmail accounts (1,500 emails/day capacity). You want to plan campaigns accordingly.

**Steps:**
1. Select sessions with total 2,000 leads
2. Set target sends to 1,500 (match your capacity)
3. Create campaign
4. Remaining 500 leads can be in next campaign

**Result:** Campaign sized to your sending capacity

---

### Use Case 4: Test Campaign
**Scenario:** You want to test email template before sending to all leads.

**Steps:**
1. Select one session with 1,000 leads
2. Set target sends to 50 (small test)
3. Create test campaign
4. If successful, create full campaign with all 1,000

**Result:** Test campaign with small sample

---

## 🔍 Preview Features

### Session Info in Preview

Preview table shows:
- **Session**: Which session the lead came from (#123)
- **Query**: The search query used
- **Name**: Contact name
- **Email**: Email address
- **Phone**: Phone number

This helps you see which sessions contributed which leads.

---

## 🎯 Campaign Naming

Campaign names auto-generate based on selection:

- **Single session**: `Session #123 - 2026-02-18`
- **Multiple sessions**: `Merged 5 Sessions - 2026-02-18`
- **All leads**: `Campaign 2026-02-18 14:30`

Session IDs are also stored in campaign name for tracking:
`Merged 3 Sessions - 2026-02-18 [Sessions: 123,124,125]`

---

## 📊 Lead Source Options

### Option 1: From Sessions (Extractor) ⭐ NEW!
- Select by extraction session
- Merge multiple sessions
- See session context
- Best for organized campaigns

### Option 2: All Leads
- All leads from database (regardless of session)
- Quick selection
- Good for one-off campaigns

### Option 3: Import CSV
- Upload external CSV file
- Map columns
- Good for importing external lists

---

## 💡 Best Practices

### 1. **Organize by Session**
- Keep related searches together
- Name sessions descriptively (if possible)
- Use date grouping to find recent extractions

### 2. **Plan Campaign Size**
- Match campaign size to mailbox capacity
- Start small for testing (50-100 emails)
- Scale up once template is proven

### 3. **Deduplicate**
- Always enable deduplication when merging sessions
- Prevents sending multiple emails to same address
- Improves sender reputation

### 4. **Track Sessions**
- Campaign name includes session IDs
- Easy to trace which extractions were used
- Helps with reporting and analysis

---

## 🔧 Technical Details

### Database Structure

**Sessions Table (`searches`):**
- `id`: Session ID
- `query`: Search query
- `num_leads`: Lead count
- `created_at`: Timestamp

**Leads Table (`leads`):**
- `search_id`: Links to session
- `email`, `contact_name`, `phone`, etc.

**Campaigns Table (`email_campaigns`):**
- `name`: Includes session IDs for tracking
- `total_recipients`: Total leads selected

### Session Selection Logic

1. Load all sessions from `searches` table
2. Group by date for UI display
3. User selects sessions via checkboxes
4. Load leads from selected sessions
5. Filter for emails, deduplicate, limit to target
6. Create campaign with merged leads

---

## ✅ Summary

**Before:** Just "all leads from database" - no organization

**Now:** 
- ✅ Session-based selection
- ✅ Merge multiple sessions
- ✅ Campaign planning tools
- ✅ Deduplication
- ✅ Session tracking
- ✅ Smart campaign naming

**Result:** Professional campaign management that matches how the extractor works! 🎉
