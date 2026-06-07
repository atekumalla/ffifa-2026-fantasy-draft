# Demo Mode Guide

## Overview

The FIFA 2026 Fantasy Draft app now supports an **enhanced demo mode** that can run in two configurations:

### 1. In-Memory Demo (Original)
- No credentials required
- All data stored in memory
- Perfect for quick testing without setup

### 2. Google Sheets Demo (New)
- Uses **real Google Sheets** with pre-seeded data
- Uses **stubbed Football API** (no real API calls)
- Can test **OpenAI validation** if configured
- Tests the complete integration:
  - ✅ Google Sheets creation and updates
  - ✅ UI rendering from real sheet data
  - ✅ Sheets API credentials and access
  - ✅ OpenAI API for validation (optional)
  - ✅ Sync/update workflows

---

## When to Use Each Mode

### In-Memory Demo
Use when you want to:
- Quick demo without any setup
- No Google or OpenAI accounts needed
- Test UI and basic functionality

### Google Sheets Demo
Use when you want to:
- Test the complete system integration
- Verify Google Sheets API access
- Test OpenAI validation
- See how the UI renders real sheet data
- Debug sheet formatting and updates
- Validate credentials before production

---

## Setup Instructions

### In-Memory Demo (No Setup Required)

```bash
python -m src.server --demo
```

That's it! Open http://localhost:8000

### Google Sheets Demo

#### Step 1: Configure `.env` file

You need at least:
- `GOOGLE_SHEETS_ID` or `DEMO_GOOGLE_SHEETS_ID`
- `GOOGLE_SHEETS_CREDENTIALS_JSON` (or `GOOGLE_SHEETS_CREDENTIALS_FILE`)

Optionally add:
- `OPENAI_API_KEY` - To test validation feature

```bash
# .env file
GOOGLE_SHEETS_ID=your_main_sheet_id

# Optional: Use a separate sheet for demo/testing
DEMO_GOOGLE_SHEETS_ID=your_demo_sheet_id

# Service account credentials (JSON format)
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}

# Optional: Enable validation testing
OPENAI_API_KEY=sk-...
```

#### Step 2: Create/Prepare Google Sheet

1. **Option A**: Let the app create it
   - Create a blank Google Sheet
   - Share it with your service account email
   - Copy the Sheet ID to `.env`

2. **Option B**: Use existing sheet
   - The demo will overwrite existing data
   - Make sure you're using a test sheet!

#### Step 3: Run Demo

```bash
python -m src.server --demo
```

The demo will:
1. Initialize the Google Sheet with demo data
2. Create all necessary sheets (Schedule, Players, Scores, etc.)
3. Pre-fill 18 matches with results
4. Start the server

---

## Demo Features

### Pre-Seeded Data

The demo includes:
- **4 Players**: Prateik, Rohit, Anup, Abhinav
- **48 Teams**: All FIFA 2026 World Cup teams (including 8 neutral teams)
- **104 Matches**: Full tournament schedule
- **18 Pre-Scored Matches**: Group stage matches with realistic scores

### Demo Behaviors

#### Sync Button
- **In-Memory**: Reveals next match result instantly
- **With Sheets**: Updates the Google Sheet, then re-reads data
- **Cooldown**: 5 seconds (vs 10 minutes in production)

#### Validate Button
- **In-Memory**: Returns canned "validation skipped" response
- **With Sheets (no OpenAI)**: Returns "structural checks only"
- **With Sheets + OpenAI**: Runs REAL validation with LLM checks!
- **Cooldown**: 5 seconds (vs 10 minutes in production)

#### Football API
- **Always Stubbed**: Returns empty results
- No real API calls to football-data.org
- Prevents rate limit issues during testing

---

## What Gets Tested

### ✅ With Google Sheets Demo

| Component | Tested | Notes |
|-----------|--------|-------|
| Sheet Creation | ✅ | Creates all necessary sheets |
| Sheet Formatting | ✅ | Headers, colors, formulas |
| Write Operations | ✅ | Draft picks, schedule, scores |
| Read Operations | ✅ | UI reads from sheet |
| Credentials | ✅ | Service account access |
| Sync Flow | ✅ | Update workflow |
| OpenAI Validation | ✅ | If API key is configured |
| Football API | ❌ | Stubbed (intentional) |

### ⚠️ With In-Memory Demo

| Component | Tested | Notes |
|-----------|--------|-------|
| UI Rendering | ✅ | Basic UI functionality |
| Scoring Logic | ✅ | Point calculations |
| Match Generation | ✅ | Realistic schedules |
| Google Sheets | ❌ | Not used |
| OpenAI | ❌ | Not used |
| Football API | ❌ | Not used |

---

## Example Workflows

### Test Google Sheets Integration

```bash
# 1. Set up .env with credentials
export DEMO_GOOGLE_SHEETS_ID="your_test_sheet_id"

# 2. Run demo
python -m src.server --demo

# 3. Check the logs
# Should see:
# ✅ Using REAL Google Sheets with pre-seeded data
# ✅ Using STUBBED Football API
# ✅ Loaded X players, Y matches from sheet

# 4. Open browser and test
# - Click Sync → Should update sheet
# - Check Google Sheet → Should see new scores
# - Click Validate → Tests OpenAI if configured
```

### Test OpenAI Validation

```bash
# 1. Ensure OpenAI key is set
export OPENAI_API_KEY="sk-..."
export DEMO_GOOGLE_SHEETS_ID="your_test_sheet_id"

# 2. Run demo
python -m src.server --demo

# 3. Wait for startup, then click "Validate"
# Should see real validation results with LLM checks
```

### Quick UI Testing (No Setup)

```bash
# Just run in-memory demo
python -m src.server --demo

# Test UI without any credentials
```

---

## Troubleshooting

### "Demo mode (in-memory only)" instead of using sheets

**Problem**: Demo is running in-memory mode even though you have credentials.

**Solution**: Check that:
- `GOOGLE_SHEETS_ID` or `DEMO_GOOGLE_SHEETS_ID` is set
- `GOOGLE_SHEETS_CREDENTIALS_JSON` is set (or credentials.json file exists)
- Service account has access to the sheet

### Validation returns "validation skipped"

**Cause 1**: Running in-memory demo (no sheets)
- Validation is disabled without sheets

**Cause 2**: No OpenAI API key
- Set `OPENAI_API_KEY` in `.env`

### Sheet initialization fails

**Common causes**:
- Service account doesn't have edit access
- Sheet ID is incorrect
- Credentials are malformed

**Check**:
```bash
# Test credentials separately
python -m src.seed_data
```

---

## Environment Variables Reference

### Required for Google Sheets Demo

```bash
# Main or demo-specific sheet ID
GOOGLE_SHEETS_ID=xxx
# OR
DEMO_GOOGLE_SHEETS_ID=xxx

# Service account credentials
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}
# OR
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
```

### Optional for Enhanced Testing

```bash
# Enable OpenAI validation testing
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Adjust demo behavior
SYNC_HOUR=6
SYNC_MINUTE=0
LOG_LEVEL=DEBUG
```

---

## API Differences: Demo vs Production

### `/api/status`

**Demo (In-Memory)**:
```json
{
  "demo_mode": true,
  "spreadsheet_url": "#demo-mode",
  "validate_available": false,
  ...
}
```

**Demo (With Sheets)**:
```json
{
  "demo_mode": true,
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/...",
  "validate_available": true,  // if OpenAI configured
  ...
}
```

**Production**:
```json
{
  "demo_mode": false,
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/...",
  "validate_available": true,
  ...
}
```

### `/api/sync`

**Demo**: Scores next pre-generated match
**Production**: Fetches from Football API

### `/api/validate`

**Demo (In-Memory)**: Returns canned response
**Demo (With Sheets + OpenAI)**: Runs real validation!
**Production**: Runs real validation

---

## Best Practices

1. **Use a separate demo sheet**: Set `DEMO_GOOGLE_SHEETS_ID` to avoid overwriting production data

2. **Test incrementally**:
   - Start with in-memory demo
   - Add Google Sheets
   - Add OpenAI validation
   - Finally test production mode

3. **Check the logs**: Demo mode prints detailed status on startup

4. **Rate limits**: Demo has 5-second cooldown (production has 10 minutes)

5. **Clean slate**: Each demo run reinitializes the sheet with fresh data

---

## Migration Path

```
In-Memory Demo
    ↓
Google Sheets Demo (without OpenAI)
    ↓
Google Sheets Demo (with OpenAI)
    ↓
Production Mode (with Football API)
```

Each step adds one more component to test!
