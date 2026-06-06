# Setting Up Football-Data.org API

## Overview

We use [football-data.org](https://www.football-data.org) as the primary data source for live match scores. Their free tier is sufficient for this project.

**Free Tier Limits:**
- 10 requests per minute
- All major competitions (including FIFA World Cup)
- No credit card required

---

## Step 1: Create an Account

1. Go to **https://www.football-data.org/client/register**
2. Fill in:
   - **Name**: Your name
   - **Email**: Your email address
   - **Password**: Choose a password
3. Click **Register**
4. Check your email and **verify your account** by clicking the confirmation link

---

## Step 2: Get Your API Key

1. Log in at **https://www.football-data.org/client/login**
2. Once logged in, you'll see your **Dashboard**
3. Your API token is displayed right on the dashboard page
4. It looks something like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
5. **Copy this token** — this is your `FOOTBALL_API_KEY`

---

## Step 3: Add to Your .env File

Open your `.env` file in the project root and set:

```bash
FOOTBALL_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

Replace the value with your actual API token.

---

## Step 4: Verify It Works

Run this quick test from the project directory:

```bash
source .venv/bin/activate
python -c "
import requests
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('FOOTBALL_API_KEY')
resp = requests.get(
    'https://api.football-data.org/v4/competitions/WC',
    headers={'X-Auth-Token': key}
)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    print(f'Competition: {data[\"name\"]}')
    print(f'Season: {data.get(\"currentSeason\", {}).get(\"startDate\", \"N/A\")}')
    print('✅ API key is working!')
else:
    print(f'❌ Error: {resp.text}')
"
```

You should see:
```
Status: 200
Competition: FIFA World Cup
✅ API key is working!
```

---

## API Endpoints We Use

| Endpoint | Purpose |
|----------|---------|
| `GET /v4/competitions/WC/matches` | All World Cup matches |
| `GET /v4/competitions/WC/matches?status=FINISHED` | Only completed matches |
| `GET /v4/competitions/WC/matches?dateFrom=X&dateTo=Y` | Matches on a specific date |

---

## Rate Limiting

- **Free tier**: 10 requests per minute
- If you exceed the limit, the API returns HTTP `429 Too Many Requests`
- Our app has built-in retry logic with exponential backoff, so this is handled automatically
- The daily sync only makes 1-2 API calls, well within limits

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `403 Forbidden` | Your API key is invalid or not set. Double-check `.env` |
| `429 Too Many Requests` | You've hit the rate limit. Wait 60 seconds |
| `404 Not Found` | Competition code might be wrong. We use `WC` for World Cup |
| Empty match list | The tournament may not have started yet, or the API hasn't published the draw |

---

## Useful Links

- **API Documentation**: https://www.football-data.org/documentation/api
- **Free tier info**: https://www.football-data.org/coverage
- **Status page**: Check if the API is down
- **Competitions list**: `GET /v4/competitions` — shows all available competitions

---

## Notes

- The API uses team names in English (e.g., "Germany" not "Deutschland")
- Match times are in UTC
- The `score.fullTime` field gives regular time + extra time goals
- Penalty shootout scores are separate in `score.penalties`
- This aligns perfectly with our scoring system (penalties don't count)
