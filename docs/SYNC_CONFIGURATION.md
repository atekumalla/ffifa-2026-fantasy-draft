# Sync Configuration Guide

## Overview

The FIFA 2026 Fantasy Draft app syncs match scores and updates the leaderboard automatically. This guide explains how sync works and how to configure it.

---

## Sync Schedule (Automatic Interval Sync)

The app automatically syncs at regular intervals and switches to aggressive mode when live matches are detected.

### Environment Variables

```bash
# Regular sync interval in minutes (default: 60 = once per hour)
SYNC_INTERVAL_MINUTES=60

# Live match sync interval in seconds (default: 120 = every 2 minutes)
SYNC_LIVE_INTERVAL_SECONDS=120

# Timezone for scheduler
SYNC_TIMEZONE=Asia/Kolkata
```

### How It Works

- **Regular mode**: Syncs every `SYNC_INTERVAL_MINUTES` minutes (default: hourly)
- **Live mode**: When a match is `IN_PLAY`, automatically switches to syncing every `SYNC_LIVE_INTERVAL_SECONDS` seconds (default: every 2 minutes)
- **Auto-switch back**: Once no live matches are detected, reverts to regular interval

### Recommended Values

| Scenario | `SYNC_INTERVAL_MINUTES` | `SYNC_LIVE_INTERVAL_SECONDS` |
|----------|------------------------|------------------------------|
| **Default** | `60` | `120` |
| **Aggressive** | `30` | `60` |
| **Conservative** (free API tier) | `120` | `300` |
| **Testing** | `5` | `30` |

### Legacy Config (still supported)

```bash
SYNC_HOUR=6          # Legacy: used with timezone only
SYNC_MINUTE=0
```

---

## Manual Sync Cooldown

### What It Does
Prevents users from hammering the sync button and overwhelming the APIs.

### Environment Variable

```bash
SYNC_COOLDOWN_SECONDS=600   # Default: 10 minutes
```

### Recommended Values

| Use Case | Value | Description |
|----------|-------|-------------|
| **Tournament Days** | `60` | Sync every minute during live matches |
| **Heavy Match Days** | `300` | Sync every 5 minutes |
| **Normal Days** | `600` | Default - every 10 minutes |
| **Testing/Development** | `0` | No cooldown (use carefully!) |

### How to Change

1. Edit `.env` file:
   ```bash
   SYNC_COOLDOWN_SECONDS=60
   ```

2. Restart the server:
   ```bash
   python -m src.server
   ```

---

## Live Match Support

### Backend Support: ✅ YES

The system **fully supports** live matches with dynamic score updates:

1. **Live Match Detection**
   - API returns `IN_PLAY` status for live matches
   - Backend maps `IN_PLAY` and `PAUSED` to `MatchStatus.IN_PLAY`
   - Recent results now include live matches

2. **Dynamic Score Updates**
   - Scores update automatically on each sync
   - Points recalculate for all players
   - Leaderboard updates in real-time
   - Score worm chart adjusts dynamically

3. **Live Match Indicator**
   - Red pulsing "LIVE" badge in recent results table
   - Shows current score even as it changes

### How It Works

```
Match Lifecycle:
SCHEDULED → IN_PLAY (scores update) → FINISHED (final scores)
           ↑ Live updates happen here ↑
```

When a match is `IN_PLAY`:
- Shows in "Recent Results" with LIVE indicator
- Scores can change with each sync
- Player points update dynamically
- **Points can go up or down** as the match progresses

### Example Scenario

```
Match: Mexico vs South Africa
12:00 PM - Status: IN_PLAY, Score: 0-0
12:30 PM - Status: IN_PLAY, Score: 1-0  (Mexico player gains points)
1:00 PM  - Status: IN_PLAY, Score: 1-1  (South Africa player gains points)
1:45 PM  - Status: IN_PLAY, Score: 2-1  (Mexico player gains more)
2:00 PM  - Status: FINISHED, Score: 2-1 (Final)
```

Each sync updates the leaderboard with current scores.

---

## API Rate Limits

### football-data.org
- **Free Tier**: 10 requests per minute
- **Recommendation**: Sync every 1-5 minutes during matches

### API-Football (if configured)
- **Free Tier**: 100 requests per day
- **Recommendation**: Sync every 10-15 minutes

---

## Best Practices

### During Tournament

**Heavy Match Days** (3+ matches):
```bash
SYNC_COOLDOWN_SECONDS=60     # Every minute
SYNC_HOUR=6                  # Once daily at 6 AM
```

**Light Match Days** (1-2 matches):
```bash
SYNC_COOLDOWN_SECONDS=300    # Every 5 minutes
```

**Off Days** (no matches):
```bash
SYNC_COOLDOWN_SECONDS=600    # Every 10 minutes (default)
```

### For Live Match Tracking

1. **Set aggressive cooldown**:
   ```bash
   SYNC_COOLDOWN_SECONDS=60
   ```

2. **Manually trigger sync** during matches:
   - Click "Sync Scores" button in dashboard
   - Or call API: `POST /api/sync`

3. **Watch live updates**:
   - Scores update in real-time
   - LIVE indicator shows active matches
   - Leaderboard recalculates automatically

---

## Deployment Recommendations

### Local Development
```bash
SYNC_COOLDOWN_SECONDS=0      # No cooldown for testing
SYNC_HOUR=6
```

### Render/Production (Normal)
```bash
SYNC_COOLDOWN_SECONDS=600    # 10 minutes
SYNC_HOUR=6
```

### Render/Production (Tournament Days)
```bash
SYNC_COOLDOWN_SECONDS=60     # 1 minute for live tracking
SYNC_HOUR=6
```

---

## Troubleshooting

### "Sync available in X seconds"
- Cooldown is active
- Wait or reduce `SYNC_COOLDOWN_SECONDS`

### Live matches not showing
- Check if API returns `IN_PLAY` status
- Verify match has scores (not null)
- Trigger manual sync

### Scores not updating during live match
- Reduce `SYNC_COOLDOWN_SECONDS` to 60
- Manually trigger sync more frequently
- Check API rate limits

---

## Summary

✅ **Live matches are fully supported**  
✅ **Scores update dynamically**  
✅ **Points recalculate automatically**  
✅ **Live indicator shows active matches**  

**To make sync more aggressive:**
Set `SYNC_COOLDOWN_SECONDS=60` in your `.env` file and restart the server.
