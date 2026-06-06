# FIFA 2026 World Cup Fantasy Draft 🏆⚽

A complete fantasy draft system for the FIFA 2026 World Cup with a real-time web dashboard, automated score syncing, and Google Sheets integration. 4 friends each pick 10 national teams, earning points based on match results throughout the tournament.

**✨ Features:**
- 🎮 **Interactive Web Dashboard** — Real-time leaderboard with charts, match timeline, and share functionality
- 📊 **Google Sheets Backend** — All data lives in a shareable spreadsheet (works standalone)
- 🤖 **Automated Syncing** — Scheduled daily updates from football-data.org API + ChatGPT fallback
- 🚀 **Demo Mode** — Try it instantly with fake data, no credentials needed
- 💪 **Production Ready** — Deployable to Render/Heroku with full crash recovery
- ✅ **Validation System** — Daily integrity checks with detailed error reporting

## Scoring System

| Event | Group Stage | Knockout |
|-------|-------------|----------|
| Win | 3 pts | 3 pts |
| Draw | 1.5 pts | 1.5 pts |
| Goal Scored | 0.5 pts | 0.75 pts |
| Goal Conceded | -0.25 pts | -0.25 pts |
| Penalty Shootout Goals | ❌ Don't count | ❌ Don't count |

## Architecture

```
                   ┌─────────────────────────┐
                   │   Web Dashboard (UI)    │
                   │  FastAPI + Chart.js     │
                   └───────────┬─────────────┘
                               │
                   ┌───────────▼─────────────┐
                   │   Python Sync Engine    │
                   │  (State Manager + Jobs) │
                   └───────────┬─────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
        ┌───────▼───────┐ ┌───▼──────┐ ┌─────▼──────┐
        │ Football API  │ │ ChatGPT  │ │   Google   │
        │ (Primary)     │ │ Fallback │ │   Sheets   │
        └───────────────┘ └──────────┘ └────────────┘
```

**Components:**
- **Google Sheets** — 5 tabs: Draft Picks, Match Schedule, Leaderboard, Scoring Rules, Validation Log
- **FastAPI Server** — REST API + static dashboard UI at `http://localhost:8000`
- **Sync Engine** — APScheduler for daily updates, state file for crash recovery
- **Data Sources** — football-data.org (primary), OpenAI GPT-4o-mini (fallback)
- **Validation** — Daily integrity checks on scoring consistency

## Quick Start (Production Mode)

## Quick Start (Production Mode)

### 1. Prerequisites
- Python 3.11+
- Google Cloud service account with Sheets API enabled ([Setup Guide](docs/SETUP_GOOGLE_SHEETS.md))
- football-data.org API key ([Register Free](https://www.football-data.org/client/register))
- OpenAI API key (for fallback scoring)

### 2. Install Dependencies
```bash
cd fifa-2026-fantasy-draft
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your:
#   - GOOGLE_SHEETS_ID
#   - GOOGLE_SHEETS_CREDENTIALS_JSON (or _FILE for local dev)
#   - FOOTBALL_API_KEY
#   - OPENAI_API_KEY
```

### 4. Seed the Google Sheet (run once)
```bash
python -m src.seed_data
```
This creates 5 tabs and pre-fills the 104-match World Cup schedule.

### 5. Start the Dashboard
```bash
python -m src.server
```
Open **http://localhost:8000** to see the live dashboard!

The server will:
- ✅ Load draft picks and matches from Google Sheets
- ✅ Display real-time leaderboard with charts
- ✅ Auto-sync daily at 6:00 AM (configurable via `SYNC_HOUR`)
- ✅ Run daily validation checks
- ✅ Expose API endpoints for manual sync/validate

---

## Quick Start (Demo Mode) 🎮

**Try the app instantly without any credentials!**

```bash
# No setup needed, just run:
python -m src.server --demo
```

Then open **http://localhost:8000**

**Demo features:**
- Pre-filled with 18 completed group stage matches
- Click "Sync Scores" to reveal one more match result
- Click "Validate" to run integrity checks (validation disabled in demo)
- Fully interactive dashboard with fake but realistic data
- 5-second cooldown (instead of 10 min) for testing

Perfect for:
- Testing the UI without API keys
- Demoing the app to friends
- Development and iteration

---

## Dashboard Features

### Web UI (http://localhost:8000)
- 📈 **Live Leaderboard** — Current rankings with point breakdowns
- 📊 **Points Chart** — Visual comparison across all players
- 🎯 **Recent Matches** — Last 5 completed matches with scores
- ⚽ **Upcoming Matches** — Next 5 scheduled matches
- 🔄 **Manual Sync** — Trigger score updates on-demand (10 min cooldown)
- ✅ **Validation** — Run integrity checks manually (10 min cooldown)
- 📱 **Share to WhatsApp** — Generate shareable leaderboard text
- 🌓 **Dark/Light Theme** — Toggle via button in header

### API Endpoints
- `GET /` — Dashboard HTML
- `GET /api/status` — Current state (leaderboard, matches, sync time)
- `POST /api/sync` — Trigger score sync (rate limited)
- `POST /api/validate` — Trigger validation (rate limited)
- `GET /api/share-text` — Get WhatsApp-formatted standings

---

## CLI Mode (Alternative)

Run the orchestrator without the web UI:

```bash
python -m src.main
```

### Interactive Commands
```
> sync            # Trigger manual score update
> status          # Show current leaderboard in terminal
> reschedule 22:00  # Change daily sync time to 10 PM
> quit            # Exit gracefully
```

## Data Sources

| Source | Type | Usage | Rate Limit |
|--------|------|-------|------------|
| **football-data.org** | REST API | Primary match scores | 10 req/min (free tier) |
| **OpenAI GPT-4o-mini** | LLM | Fallback when API fails | ~$0.01/query |
| **Google Sheets** | Spreadsheet | Source of truth (backend) | No limit (service account) |

**Sync Flow:**
1. Check which matches need updating (based on date + state file)
2. Try football-data.org API first
3. If API fails → fall back to ChatGPT (structured prompt)
4. Reconcile and update Google Sheets
5. Persist state to `state/last_sync.json` for crash recovery

---

## Validation System

The app runs daily integrity checks after each sync to catch scoring bugs:

**Checks performed:**
- ✅ All draft picks exist in the Match Schedule tab
- ✅ Point calculations match the scoring rules
- ✅ Group stage vs knockout multipliers applied correctly
- ✅ No duplicate matches or missing match IDs
- ✅ All players have 10 teams drafted

Results are logged to the **Validation Log** tab in Google Sheets with:
- Timestamp
- Pass/Fail status
- Detailed error descriptions (if any)

**Trigger manually:**
```bash
# Via dashboard: Click "Validate" button
# Via CLI: type "validate" in the interactive prompt
```

---

## Deployment (Render / Heroku)

### Render (Recommended)

1. **Create a new Web Service** on [Render](https://render.com)
2. **Connect your GitHub repo**
3. **Set environment variables** in Render dashboard:
   ```
   GOOGLE_SHEETS_ID=your_spreadsheet_id
   GOOGLE_SHEETS_CREDENTIALS_JSON={"type":"service_account",...}
   FOOTBALL_API_KEY=your_key
   OPENAI_API_KEY=sk-...
   SYNC_HOUR=6
   SYNC_MINUTE=0
   ```
4. **Deploy!** Render will auto-detect `Procfile` and run:
   ```
   uvicorn src.server:app --host 0.0.0.0 --port $PORT
   ```

**Note:** The `Procfile` is configured for the web server mode (FastAPI), not CLI mode.

### Heroku

Same process as Render. Set environment variables in Heroku config vars.

---

## Resilience & Recovery

### Crash Recovery
- **State file** (`state/last_sync.json`) persists after every sync
- Contains: last sync timestamp, list of scored match IDs
- On restart, app checks this file to avoid re-scoring matches
- **Idempotent:** Running sync multiple times won't duplicate points

### Graceful Degradation
1. **API unavailable** → Falls back to ChatGPT
2. **ChatGPT fails** → Logs error, retries next cycle
3. **Sheets write fails** → Logs error, state not updated (safe to retry)
4. **Invalid config** → Logs warnings but starts anyway (some features disabled)

### Google Sheets is Standalone
Anyone can open the spreadsheet and see current standings, even if the Python app is down.

---

## Project Structure

```
src/
├── main.py              # CLI orchestrator (interactive mode)
├── server.py            # FastAPI web server (dashboard + API)
├── demo.py              # Demo mode with fake data generation
├── config.py            # Environment variable config (.env)
├── seed_data.py         # One-time spreadsheet setup script
├── validation.py        # Integrity check system
├── models/              # Pydantic data models
│   ├── match.py         # Match, MatchStatus, MatchStage
│   ├── team.py          # Team model
│   ├── player.py        # DraftPlayer model
│   └── draft_pick.py    # DraftPick model
├── scoring/             # Point calculation engine
│   ├── rules.py         # Scoring rule definitions
│   └── calculator.py    # Apply rules to matches
├── data_sources/        # External data fetching
│   ├── football_api.py  # football-data.org client
│   └── llm_fallback.py  # ChatGPT fallback client
├── sheets/              # Google Sheets read/write per tab
│   ├── client.py        # gspread wrapper
│   ├── players.py       # Draft Picks tab
│   ├── schedule.py      # Match Schedule tab
│   ├── scores.py        # Leaderboard tab
│   ├── scoring_rules.py # Scoring Rules tab
│   └── formatting.py    # Cell styling utilities
├── sync/                # Scheduler + state management
│   ├── scheduler.py     # APScheduler wrapper
│   ├── state_manager.py # Persist last sync to JSON
│   └── recovery.py      # Determine which matches to update
└── utils/               # Shared utilities
    ├── logger.py        # Colored console logging
    ├── retry.py         # Exponential backoff decorator
    └── rate_limiter.py  # API cooldown enforcement

static/
└── index.html           # Single-page dashboard UI (vanilla JS + Chart.js)

templates/
├── sheet_schema.json    # Google Sheets tab structure definition
└── scoring_rules.json   # Default scoring rules template

tests/
├── test_scoring.py      # Scoring calculator tests
├── test_sheets_client.py # Google Sheets integration tests
├── test_sync.py         # Sync logic tests
├── test_recovery.py     # Crash recovery tests
└── test_validation.py   # Validation system tests
```

---

## Configuration Reference

**Environment Variables** (`.env` file):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_SHEETS_ID` | ✅ Yes | — | Spreadsheet ID from URL |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | ✅ Yes* | — | Full JSON service account (Render/hosted) |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | ✅ Yes* | `credentials.json` | Path to credentials (local dev) |
| `FOOTBALL_API_KEY` | ✅ Yes | — | football-data.org API key |
| `OPENAI_API_KEY` | ✅ Yes | — | OpenAI API key for fallback |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | ChatGPT model to use |
| `SYNC_HOUR` | No | `6` | Daily sync time (0-23) |
| `SYNC_MINUTE` | No | `0` | Daily sync minute (0-59) |
| `SYNC_TIMEZONE` | No | `Asia/Kolkata` | Timezone for scheduler |
| `STATE_FILE` | No | `state/last_sync.json` | Path to state file |
| `PORT` | No | `8000` | Web server port |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

*Either `_JSON` or `_FILE` must be set for Google Sheets credentials.

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_scoring.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test coverage:**
- ✅ Scoring calculator (group stage + knockout multipliers)
- ✅ Google Sheets read/write operations
- ✅ Sync logic and match reconciliation
- ✅ Crash recovery state management
- ✅ Validation system integrity checks

---

## Troubleshooting

### "No module named 'src'"
Make sure you're running commands from the project root:
```bash
cd fifa-2026-fantasy-draft
python -m src.server  # ✅ Correct
```

### "Unable to find credentials"
**Local dev:** Make sure `credentials.json` exists in project root.
**Render/hosted:** Set `GOOGLE_SHEETS_CREDENTIALS_JSON` env var with full JSON content.

### "Rate limit exceeded" (football API)
Free tier allows 10 req/min. The app automatically falls back to ChatGPT.

### "Sync button disabled"
There's a 10-minute cooldown after each sync to avoid hammering APIs.
In demo mode, cooldown is only 5 seconds.

### Dashboard not loading
Check terminal logs for errors. Make sure port 8000 is not in use:
```bash
lsof -ti:8000 | xargs kill -9  # Kill process on port 8000
```

---

## Roadmap / Future Enhancements

- [ ] Telegram bot for score notifications
- [ ] Mobile-responsive improvements
- [ ] Historical match replays in dashboard
- [ ] Player-level stats (top scorers, assists)
- [ ] Bracket visualization for knockout stage
- [ ] Multi-tournament support (Euros, Copa América)
- [ ] Email digest for daily standings
- [ ] Webhooks for real-time match updates

---

## Documentation

- 📘 [Google Sheets Setup Guide](docs/SETUP_GOOGLE_SHEETS.md)
- 🔑 [Football API Setup Guide](docs/SETUP_FOOTBALL_API.md)
- 📊 [Spreadsheet Structure Preview](docs/SPREADSHEET_PREVIEW.md)

---

## License

MIT License — feel free to use this for your own fantasy draft!

---

## Credits

Built with ❤️ for FIFA 2026 World Cup

**Tech Stack:**
- Python 3.11+ (FastAPI, APScheduler, gspread)
- Google Sheets API (backend storage)
- football-data.org API (match data)
- OpenAI GPT-4o-mini (fallback scoring)
- Chart.js (dashboard visualizations)
- Vanilla JavaScript (no frontend frameworks!)

---

**Questions?** Open an issue or contact the maintainer.
