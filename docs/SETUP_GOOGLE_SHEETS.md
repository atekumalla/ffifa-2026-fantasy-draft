# Setting Up Google Sheets API (Service Account)

## Overview

This app uses a **Google Service Account** to read/write a Google Spreadsheet programmatically. A service account is like a robot Google account — it has its own email address and can be granted access to your spreadsheet.

**Cost:** Completely free (Google Cloud free tier).

---

## Step 1: Create a Google Cloud Project

1. Go to the **Google Cloud Console**: https://console.cloud.google.com/
2. If you've never used Google Cloud, you'll need to agree to the Terms of Service
3. Click the project dropdown at the top of the page (it may say "Select a project" or show an existing project name)
4. Click **"New Project"** in the top-right of the popup
5. Fill in:
   - **Project name**: `fifa-2026-fantasy-draft` (or anything you like)
   - **Organization**: Leave as "No organization" (or select yours if applicable)
6. Click **Create**
7. Wait a few seconds, then make sure this new project is selected in the dropdown at the top

---

## Step 2: Enable the Google Sheets API

1. In the Google Cloud Console, go to **APIs & Services > Library**
   - Direct link: https://console.cloud.google.com/apis/library
2. Search for **"Google Sheets API"**
3. Click on **Google Sheets API** in the results
4. Click the blue **"Enable"** button
5. Wait for it to enable (takes a few seconds)

---

## Step 3: Enable the Google Drive API

We also need Drive API access so the service account can access spreadsheets shared with it.

1. Go back to **APIs & Services > Library**
2. Search for **"Google Drive API"**
3. Click on **Google Drive API** in the results
4. Click the blue **"Enable"** button

---

## Step 4: Create a Service Account

1. Go to **APIs & Services > Credentials**
   - Direct link: https://console.cloud.google.com/apis/credentials
2. Click **"+ Create Credentials"** at the top
3. Select **"Service account"**
4. Fill in:
   - **Service account name**: `fifa-draft-sheets` (or anything descriptive)
   - **Service account ID**: This auto-fills (e.g., `fifa-draft-sheets@your-project.iam.gserviceaccount.com`)
   - **Description**: Optional — e.g., "Reads/writes FIFA draft spreadsheet"
5. Click **"Create and Continue"**
6. **Grant this service account access to project** (Role):
   - You can skip this — click **"Continue"**
7. **Grant users access to this service account**:
   - You can skip this — click **"Done"**

---

## Step 5: Create and Download the JSON Key

1. You should now see your service account in the credentials list
2. Click on the **service account email** you just created
3. Go to the **"Keys"** tab at the top
4. Click **"Add Key" > "Create new key"**
5. Select **JSON** format
6. Click **"Create"**
7. A `.json` file will be **automatically downloaded** to your computer
   - It will have a name like `your-project-abc123.json`

---

## Step 6: Add the Key to Your Project

1. **Rename** the downloaded file to `credentials.json`
2. **Move** it to the project root:
   ```
   fifa-2026-fantasy-draft/
   ├── credentials.json    ← PUT IT HERE
   ├── .env
   ├── src/
   └── ...
   ```
3. **IMPORTANT**: This file contains a private key. **Never commit it to git!**
   - It's already in `.gitignore` but double-check

The JSON file looks something like this:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "fifa-draft-sheets@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  ...
}
```

---

## Step 7: Create a Google Spreadsheet

1. Go to **Google Sheets**: https://sheets.google.com
2. Create a **new blank spreadsheet**
3. Name it something like **"FIFA 2026 Fantasy Draft"**
4. Copy the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_SPREADSHEET_ID/edit
   ```
   - The ID is the long alphanumeric string between `/d/` and `/edit`
   - Example: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`

---

## Step 8: Share the Spreadsheet with the Service Account

This is the most commonly missed step! The service account is like a separate Google user — you need to explicitly give it access to your spreadsheet.

1. Open your spreadsheet in Google Sheets
2. Click the **"Share"** button (top-right, green button)
3. In the "Add people and groups" field, paste the **service account email**
   - Find it in your `credentials.json` under `"client_email"`
   - It looks like: `fifa-draft-sheets@your-project.iam.gserviceaccount.com`
4. Set the permission to **"Editor"** (not Viewer — we need write access)
5. **Uncheck** "Notify people" (the service account can't receive emails)
6. Click **"Share"**

---

## Step 9: Configure Your .env File

Open the `.env` file in your project root and set:

```bash
# Path to the credentials JSON file (relative to project root)
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json

# The spreadsheet ID from Step 7
GOOGLE_SHEETS_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
```

Replace the spreadsheet ID with your actual one.

---

## Step 10: Verify It Works

Run this quick test from the project directory:

```bash
source .venv/bin/activate
python -c "
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv

load_dotenv()

creds_file = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'credentials.json')
sheet_id = os.getenv('GOOGLE_SHEETS_ID')

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
gc = gspread.authorize(creds)

spreadsheet = gc.open_by_key(sheet_id)
print(f'✅ Connected to: \"{spreadsheet.title}\"')
print(f'   Sheets: {[ws.title for ws in spreadsheet.worksheets()]}')
print(f'   URL: https://docs.google.com/spreadsheets/d/{sheet_id}')
"
```

You should see:
```
✅ Connected to: "FIFA 2026 Fantasy Draft"
   Sheets: ['Sheet1']
   URL: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBd...
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `FileNotFoundError: credentials.json` | Make sure the file is in the project root and the path in `.env` is correct |
| `gspread.exceptions.SpreadsheetNotFound` | The spreadsheet ID is wrong, or you haven't shared the sheet with the service account email |
| `403 PERMISSION_DENIED` | The Sheets API or Drive API isn't enabled in your Google Cloud project |
| `google.auth.exceptions.DefaultCredentialsError` | The `credentials.json` file is malformed or corrupted. Re-download it |
| `gspread.exceptions.APIError: 429` | Too many requests. Google Sheets API allows 60 requests/minute per user |
| `Quota exceeded` | Free tier allows 300 requests per minute per project. You shouldn't hit this |

---

## Common Mistakes

1. **Forgetting to share the spreadsheet** with the service account email — this is the #1 issue
2. **Using the wrong spreadsheet ID** — make sure you copy only the ID part from the URL, not the full URL
3. **Not enabling both APIs** — you need both Google Sheets API AND Google Drive API
4. **Committing credentials.json to git** — this is a security risk! Keep it out of version control

---

## Security Notes

- The `credentials.json` file contains a **private key**. Treat it like a password.
- Add it to `.gitignore` (already done in this project)
- If you accidentally expose it, go to Google Cloud Console > Service Accounts > Keys, and **delete the key** immediately, then create a new one
- The service account only has access to spreadsheets explicitly shared with it — it cannot access your personal Google Drive files

---

## Deploying to Render (or any hosted service)

On hosted platforms you **cannot** put a `credentials.json` file in the repo. Instead, pass the entire JSON as an environment variable.

### Convert credentials.json to a single-line string

```bash
# Using jq (install with: brew install jq)
cat credentials.json | jq -c .

# Or using Python
python -c "import json; print(json.dumps(json.load(open('credentials.json'))))"
```

This outputs the entire JSON on one line, e.g.:
```
{"type":"service_account","project_id":"my-project","private_key_id":"abc...","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"fifa-draft@my-project.iam.gserviceaccount.com",...}
```

### Set it as an environment variable on Render

1. Go to your Render service dashboard
2. Click **Environment** in the left sidebar
3. Add these environment variables:

| Key | Value |
|-----|-------|
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | *(paste the single-line JSON from above)* |
| `GOOGLE_SHEETS_ID` | Your spreadsheet ID |
| `FOOTBALL_API_KEY` | Your football-data.org API key |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` |
| `SYNC_HOUR` | `6` |
| `SYNC_MINUTE` | `0` |
| `SYNC_TIMEZONE` | `Asia/Kolkata` |
| `STATE_FILE` | `/tmp/last_sync.json` |
| `LOG_LEVEL` | `INFO` |

### How it works

The app checks for credentials in this priority order:
1. **`GOOGLE_SHEETS_CREDENTIALS_JSON`** env var (full JSON string) — used on Render
2. **`GOOGLE_SHEETS_CREDENTIALS_FILE`** file path — used for local development

No credentials files are ever needed in the repository.

---

## Summary Checklist

### For local development:
- [ ] Created Google Cloud project
- [ ] Enabled Google Sheets API
- [ ] Enabled Google Drive API
- [ ] Created a service account
- [ ] Downloaded the JSON key as `credentials.json`
- [ ] Placed `credentials.json` in the project root (NOT committed to git)
- [ ] Created a Google Spreadsheet
- [ ] Copied the Spreadsheet ID to `.env`
- [ ] Shared the spreadsheet with the service account email (as Editor)
- [ ] Ran the verification script successfully

### For hosted deployment (Render):
- [ ] All of the above, except placing the file in the repo
- [ ] Converted `credentials.json` to single-line JSON
- [ ] Set `GOOGLE_SHEETS_CREDENTIALS_JSON` env var on Render
- [ ] Set all other env vars on Render (`GOOGLE_SHEETS_ID`, `FOOTBALL_API_KEY`, etc.)
- [ ] Verified the deployed service can connect to the spreadsheet

