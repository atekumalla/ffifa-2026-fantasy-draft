# Next Steps & Testing Guide

## 🎯 Immediate Testing Steps

### 1. Test Sync Functionality
The demo server is running. Now test the sync button:

1. **Open the Dashboard**
   - Already open at http://localhost:8000
   - Should see 4 players with current scores

2. **Click "Sync Scores" Button**
   - Wait 5 seconds between clicks (rate limit)
   - Each click should:
     - Score one more match
     - Update the leaderboard
     - Update the Google Sheet
   - Check the console logs for updates

3. **Verify Sheet Updates**
   - Open: https://docs.google.com/spreadsheets/d/1bLBgE5LnxNwg1B1zaTYhPqIRuPzBUpmkROPQSJ_C4I4
   - Go to "Match Schedule" tab
   - Watch for new scores appearing after sync
   - Go to "Leaderboard" tab
   - Verify rankings update

### 2. Test Validation (OpenAI)
Since OpenAI API key is configured, test validation:

1. **Click "Validate" Button** on the dashboard
2. **Expected behavior:**
   - Rate limit check (5 second cooldown)
   - Runs structural validation checks
   - Runs LLM-based validation (with OpenAI)
   - Returns summary and issues

3. **Check the logs** for validation output
4. **Verify in UI** - Should show validation results

### 3. Test Multiple Syncs
Test the full flow:

```bash
# Keep clicking Sync every 5 seconds
# Should score matches: 19, 20, 21, 22...
# Eventually all 72 group matches will be complete
```

Watch for:
- Match scores updating in UI
- Leaderboard rankings changing
- Sheet updates happening
- "All group stage matches complete!" message

---

## 🧪 Manual Verification Checklist

### Google Sheets
- [ ] Draft Picks sheet exists with 4 players
- [ ] Match Schedule shows 104 matches
- [ ] Leaderboard shows current rankings
- [ ] Scoring Rules sheet is populated
- [ ] After sync: new match scores appear
- [ ] After sync: leaderboard updates

### UI Dashboard
- [ ] Leaderboard displays correctly
- [ ] Points chart renders
- [ ] Recent matches show scores
- [ ] Upcoming matches listed
- [ ] Sync button works (5 sec cooldown)
- [ ] Validate button works (if OpenAI configured)
- [ ] Share to WhatsApp generates text

### Logs
- [ ] "Using REAL Google Sheets" message appears
- [ ] "Using STUBBED Football API" message appears
- [ ] "Using REAL OpenAI API" (if configured)
- [ ] Sheet initialization successful
- [ ] Players and matches loaded
- [ ] No errors or exceptions

---

## 🔍 Things to Verify

### 1. Data Integrity
- Match scores are realistic (0-5 goals typical)
- Points calculations are correct
- Leaderboard rankings make sense
- Team assignments match draft picks

### 2. Sheet Formatting
- Headers are bold/colored
- Data is aligned properly
- Formulas work (if any)
- All tabs are created

### 3. API Rate Limits
- Sync button shows cooldown timer
- Validate button shows cooldown timer
- Can't spam requests (429 error if too fast)

### 4. Error Handling
- Invalid operations show error messages
- Server doesn't crash on errors
- Logs show meaningful error info

---

## 🐛 Troubleshooting

### Issue: Sync doesn't update sheet
**Check:**
- Service account has edit access to sheet
- No permission errors in logs
- Sheet ID is correct in .env

### Issue: Validation fails or skipped
**Check:**
- OPENAI_API_KEY is set in .env
- API key is valid and has credits
- Check logs for OpenAI errors

### Issue: UI doesn't reflect changes
**Check:**
- Browser isn't caching old data (hard refresh)
- Server is actually running
- /api/status endpoint returns fresh data

### Issue: Rate limit issues
**Behavior:**
- This is expected! Demo has 5-second cooldown
- Production has 10-minute cooldown
- Wait for timer to reset

---

## 🎓 Advanced Testing

### Test In-Memory Demo (No Sheets)
To compare with sheets demo:

```bash
# 1. Stop current server (Ctrl+C)

# 2. Temporarily rename .env
mv .env .env.backup

# 3. Run in-memory demo
python -m src.server --demo

# 4. Should see: "In-memory only (no Google Sheets credentials)"

# 5. Restore .env
mv .env.backup .env
```

### Test Without OpenAI
```bash
# 1. Edit .env, comment out OPENAI_API_KEY
# 2. Restart server
# 3. Click Validate
# 4. Should see: "structural checks only"
```

### Test Production Mode
```bash
# 1. Stop demo server
# 2. Run without --demo flag
python -m src.server

# 3. Should load data from sheet
# 4. Should have 10-minute cooldowns
# 5. Would use real Football API (but nothing to sync yet)
```

---

## 📊 API Testing with curl

Test endpoints directly:

### Get Status
```bash
curl http://localhost:8000/api/status | jq .
```

### Trigger Sync
```bash
curl -X POST http://localhost:8000/api/sync
```

### Trigger Validation
```bash
curl -X POST http://localhost:8000/api/validate
```

### Get Share Text
```bash
curl http://localhost:8000/api/share-text
```

---

## 🎯 Success Criteria

After testing, you should have verified:

✅ **Sheet Creation:** All 4 sheets created correctly
✅ **Sheet Writing:** Data written with proper formatting
✅ **Sheet Reading:** UI displays sheet data correctly
✅ **Credentials:** Service account authentication works
✅ **Sync Flow:** Match updates propagate to sheet
✅ **UI Rendering:** Dashboard shows real-time data
✅ **OpenAI Integration:** Validation runs successfully
✅ **Stubbed Football API:** No unwanted API calls
✅ **Round-trip Integrity:** Write → Read cycle works

---

## 🚀 Production Readiness

Once demo testing is complete:

### Deploy to Production
1. Set up production Google Sheet
2. Configure all .env variables
3. Remove `--demo` flag
4. Enable real Football API
5. Set 10-minute cooldowns
6. Deploy to Render/Heroku

### Ongoing Monitoring
- Check daily sync logs
- Verify sheet updates
- Monitor API rate limits
- Review validation reports

---

## 📝 Notes

### Demo Sheet ID
Current: `1bLBgE5LnxNwg1B1zaTYhPqIRuPzBUpmkROPQSJ_C4I4`

This appears to be your production sheet. Consider:
- Creating a separate demo sheet
- Setting `DEMO_GOOGLE_SHEETS_ID` in .env
- Keeping production data safe

### API Keys Present
- ✅ Google Sheets credentials configured
- ✅ OpenAI API key configured
- ✅ Football API key configured (but stubbed in demo)

All APIs are ready for testing!

---

## 🎉 You're All Set!

The demo mode is now running with:
- Real Google Sheets ✅
- Stubbed Football API ✅
- Real OpenAI API ✅
- Pre-seeded data ✅

Start clicking around and test all the features! 🚀
