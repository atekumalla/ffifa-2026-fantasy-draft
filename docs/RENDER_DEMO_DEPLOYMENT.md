# Deploying Enhanced Demo Mode to Render

## Overview

This guide shows you how to deploy the **enhanced demo mode** (with Google Sheets integration) to Render. This is perfect for:
- Live demo for friends without running locally
- Testing in a production-like environment
- Showcasing the app with real Google Sheets integration

---

## Prerequisites

Before you start, make sure you have:

1. ✅ **Render Account** - Sign up at https://render.com (free tier available)
2. ✅ **GitHub Repository** - Your code is pushed to GitHub
3. ✅ **Google Service Account** - With Sheets API enabled
4. ✅ **Google Sheet ID** - Either production or demo-specific sheet
5. ✅ **OpenAI API Key** (Optional) - For validation testing

---

## Step-by-Step Deployment

### Step 1: Create a New Web Service on Render

1. **Go to Render Dashboard**
   - Visit https://dashboard.render.com

2. **Click "New +"** → **"Web Service"**

3. **Connect Your GitHub Repository**
   - Select your repository: `atekumalla/ffifa-2026-fantasy-draft`
   - Grant Render access if prompted

4. **Configure the Service**

   | Setting | Value |
   |---------|-------|
   | **Name** | `fifa-2026-demo` (or any name you like) |
   | **Region** | Choose closest to you |
   | **Branch** | `main` |
   | **Root Directory** | Leave empty |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | See below 👇 |
   | **Instance Type** | `Free` (or paid if you need more resources) |

---

### Step 2: Set the Start Command

This is the most important part! Use this command to run demo mode:

```bash
python -m src.server --demo
```

**Or with custom port** (Render provides $PORT):
```bash
python -m src.server --demo --port $PORT
```

**Why `--demo` flag?**
- Activates demo mode with pre-seeded data
- Uses Google Sheets if credentials are configured
- Stubs the Football API (no real API calls)
- 5-second cooldowns instead of 10 minutes

---

### Step 3: Configure Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add these:

#### Required Variables:

**1. Google Sheets Credentials**
```
Key: GOOGLE_SHEETS_CREDENTIALS_JSON
Value: {"type":"service_account","project_id":"fifa-2026-fantasy-draft",...}
```

> **How to get this:**
> - Open your `credentials.json` file locally
> - Copy the ENTIRE contents
> - Convert to single line: `cat credentials.json | jq -c .`
> - Paste the output as the value

**2. Google Sheet ID**
```
Key: GOOGLE_SHEETS_ID
Value: 1bLBgE5LnxNwg1B1zaTYhPqIRuPzBUpmkROPQSJ_C4I4
```

> **Or use a separate demo sheet:**
> ```
> Key: DEMO_GOOGLE_SHEETS_ID
> Value: your_demo_sheet_id_here
> ```

#### Optional but Recommended:

**3. OpenAI API Key** (for validation testing)
```
Key: OPENAI_API_KEY
Value: sk-...your-key...
```

**4. Other Configuration**
```
Key: OPENAI_MODEL
Value: gpt-4o-mini

Key: LOG_LEVEL
Value: INFO

Key: PORT
Value: 8000
```

> **Note:** Render automatically sets `PORT`, so this is optional

---

### Step 4: Deploy!

1. **Click "Create Web Service"**
2. **Wait for Build** - Takes ~2-3 minutes
3. **Check Logs** - Should see:
   ```
   🎮 DEMO MODE
      ✅ Using REAL Google Sheets with pre-seeded data
      ✅ Using STUBBED Football API (no real API calls)
      ✅ Using REAL OpenAI API for validation
      📊 Sheet ID: ...
   
   Demo sheet initialized successfully!
   Demo server ready! Open http://...
   ```

4. **Access Your App**
   - Render will provide a URL like: `https://fifa-2026-demo.onrender.com`
   - Open it and test!

---

## Complete Environment Variables Reference

Here's a complete list of all environment variables you can set:

### Required
```bash
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}
GOOGLE_SHEETS_ID=your_sheet_id
```

### Optional
```bash
# Use separate demo sheet (recommended)
DEMO_GOOGLE_SHEETS_ID=your_demo_sheet_id

# OpenAI for validation
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=INFO

# Server (usually auto-set by Render)
PORT=8000
```

### NOT Needed for Demo Mode
```bash
# These are NOT needed since Football API is stubbed
FOOTBALL_API_KEY=not_needed_in_demo

# These are NOT needed since scheduler is disabled
SYNC_HOUR=not_needed_in_demo
SYNC_MINUTE=not_needed_in_demo
SYNC_TIMEZONE=not_needed_in_demo
```

---

## Verifying Deployment

### 1. Check Deployment Logs

In Render dashboard, go to **Logs** tab. You should see:

✅ **Successful startup:**
```
🎮 DEMO MODE
   ✅ Using REAL Google Sheets with pre-seeded data
   ✅ Using STUBBED Football API (no real API calls)
   ✅ Using REAL OpenAI API for validation

Initializing Google Sheet with demo data...
Demo initialized: 18 played, 54 group matches pending, 104 total
Writing draft picks to sheet...
Wrote 4 players to 'Draft Picks'
Writing full schedule with pre-scored matches...
Wrote 104 matches to 'Match Schedule'

✅ Demo sheet initialized successfully!
   - 4 players with draft picks
   - 104 matches in schedule
   - 18 matches pre-scored

✅ Loaded 4 players, 104 matches from sheet
Demo server ready! Open http://...
```

❌ **If you see errors:**
- Check that credentials JSON is properly formatted (single line, no line breaks)
- Verify Sheet ID is correct
- Ensure service account has edit access to the sheet

### 2. Test the Dashboard

1. **Open the Render URL** (e.g., `https://fifa-2026-demo.onrender.com`)
2. **Check the UI:**
   - Leaderboard displays with 4 players
   - Charts render correctly
   - Recent/upcoming matches show

3. **Test Sync:**
   - Click "Sync Scores" button
   - Should add one match result
   - Wait 5 seconds, click again
   - Leaderboard should update

4. **Test Validation:**
   - Click "Validate" button
   - Should run structural checks
   - If OpenAI configured, runs LLM validation too

5. **Check Google Sheet:**
   - Open your Google Sheet directly
   - Verify data is being written
   - Check that scores update after sync

---

## Troubleshooting

### Issue: "Application failed to start"

**Check:**
1. Build logs for Python dependency errors
2. Start command is correct: `python -m src.server --demo`
3. Python version matches (Render uses Python 3.11+ by default)

### Issue: "No module named 'src'"

**Solution:**
- Make sure `Root Directory` is empty (not set to a subdirectory)
- The app should run from the repository root

### Issue: "Unable to find credentials"

**Check:**
1. `GOOGLE_SHEETS_CREDENTIALS_JSON` is set correctly
2. JSON is single-line (no newlines/line breaks)
3. All quotes and braces are properly escaped

**Test locally first:**
```bash
# Set env var and test
export GOOGLE_SHEETS_CREDENTIALS_JSON='{"type":"service_account",...}'
python -m src.server --demo
```

### Issue: "Permission denied" when writing to sheet

**Check:**
1. Service account email has **Editor** access to the sheet
2. Sheet ID is correct
3. Sheets API is enabled in Google Cloud Console

**Find service account email:**
```bash
# It's in your credentials JSON
cat credentials.json | jq -r '.client_email'
# Example: fifa-draft-sheets@fifa-2026-fantasy-draft.iam.gserviceaccount.com
```

### Issue: App works but data doesn't persist

**This is expected!** 
- Demo mode reinitializes the sheet on every deployment/restart
- Each time the server restarts, it creates fresh demo data
- This is by design for demo purposes

**To persist data:**
- Switch to production mode (remove `--demo` flag)
- Use real Football API instead of stub

### Issue: Render free tier sleeps after inactivity

**Behavior:**
- Free tier apps sleep after 15 minutes of inactivity
- First request after sleep takes ~30 seconds to wake up
- Subsequent requests are fast

**Solutions:**
1. Upgrade to paid tier ($7/month for always-on)
2. Use a service like UptimeRobot to ping every 10 minutes
3. Accept the sleep behavior for demo purposes

---

## Cost Breakdown

### Render Hosting
- **Free Tier**: $0/month
  - 750 hours/month
  - Sleeps after 15 min inactivity
  - Perfect for demos

- **Paid Tier**: $7/month
  - Always-on
  - No sleep
  - Better for production

### Google Sheets API
- **Free**: No cost
- Service account usage has no quota

### OpenAI API (Optional)
- **Cost**: ~$0.01-0.02 per validation
- Demo mode: Minimal usage (only if you click Validate)

---

## Alternative: Deploy Without Google Sheets

If you just want to test the UI without Google Sheets:

**Start Command:**
```bash
python -m src.server --demo
```

**Environment Variables:**
```bash
# None required! Will run in-memory mode
```

**What you get:**
- ✅ Full UI with pre-seeded data
- ✅ Sync button works (in-memory only)
- ❌ No Google Sheets integration
- ❌ No validation

**Use case:** Quick demo without any setup

---

## Updating Your Deployment

When you push new code to GitHub:

1. **Automatic Deployment** (if auto-deploy is enabled)
   - Push to `main` branch
   - Render automatically rebuilds and deploys

2. **Manual Deployment**
   - Go to Render dashboard
   - Click **"Manual Deploy"** → **"Deploy latest commit"**

3. **Check Logs**
   - Verify new version deployed successfully
   - Demo mode reinitializes sheet with fresh data

---

## Sharing Your Demo

Once deployed, share your demo with:

### Option 1: Direct URL
```
https://fifa-2026-demo.onrender.com
```

### Option 2: Custom Domain (Paid Tier)
- Add a custom domain in Render settings
- Example: `demo.yoursite.com`

### Option 3: Google Sheet Link
Share the Google Sheet directly so people can see real-time updates:
```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID
```

---

## Production vs Demo Mode

| Feature | Demo Mode | Production Mode |
|---------|-----------|-----------------|
| **Start Command** | `--demo` flag | No flag |
| **Data Source** | Pre-seeded | Football API |
| **Google Sheets** | Optional | Required |
| **Sync Cooldown** | 5 seconds | 10 minutes |
| **Scheduler** | Disabled | Enabled (daily) |
| **Data Persistence** | Reinit on restart | Persistent |

**To switch to production:**
1. Remove `--demo` from start command
2. Add `FOOTBALL_API_KEY` to env vars
3. Configure sync schedule (SYNC_HOUR, etc.)

---

## Quick Reference: Render Configuration

**Copy-paste this into Render:**

**Start Command:**
```
python -m src.server --demo
```

**Environment Variables (minimum):**
```
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account"...}
GOOGLE_SHEETS_ID=your_sheet_id
```

**Environment Variables (recommended):**
```
GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account"...}
DEMO_GOOGLE_SHEETS_ID=your_demo_sheet_id
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

---

## Success Checklist

Before going live, verify:

- [ ] App deploys successfully (check build logs)
- [ ] Demo mode activates (check runtime logs)
- [ ] Google Sheet initializes with demo data
- [ ] UI loads at your Render URL
- [ ] Leaderboard displays correctly
- [ ] Sync button works (adds match results)
- [ ] Validate button works (if OpenAI configured)
- [ ] Google Sheet updates when you click Sync
- [ ] No errors in logs

---

## Next Steps

After successful deployment:

1. **Test thoroughly** - Click around, test all features
2. **Share with friends** - Get feedback on the demo
3. **Monitor logs** - Watch for any errors
4. **Consider paid tier** - If you want always-on availability
5. **Switch to production** - When ready for real data

---

## Support

**Issues with Render:**
- Check Render status: https://status.render.com
- Render docs: https://render.com/docs

**Issues with the app:**
- Check logs in Render dashboard
- Review `docs/DEMO_MODE.md` for troubleshooting
- Verify environment variables are set correctly

**Need help?**
- GitHub Issues: https://github.com/atekumalla/ffifa-2026-fantasy-draft/issues
- Check existing documentation in `docs/` folder

---

## 🎉 You're Ready!

Your enhanced demo mode is ready to deploy to Render! Follow the steps above and you'll have a live demo running in minutes.

**Key takeaway:** Just use `python -m src.server --demo` as your start command and set your Google Sheets credentials. Everything else is optional!

Good luck with your deployment! 🚀
