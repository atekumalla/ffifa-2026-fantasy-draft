# How Validation Works - Complete Explanation

## Overview

The validation system has **TWO layers** that run when you click the "Validate" button:

### Layer 1: Structural & Math Validation (Always Runs)
**No API calls needed** - All checks are deterministic

### Layer 2: Factual Validation with OpenAI (Optional)
**Requires OpenAI API** - Uses LLM to verify match results are actually correct

---

## Layer 1: Structural & Math Validation

These checks run **locally** without any API calls:

### 1. Match Count Check
- Expected: 104 matches (FIFA 2026 format)
- Validates you have all matches in the schedule

### 2. No Duplicate Matches
- Checks for duplicate match IDs
- Ensures no match appears twice

### 3. Score Consistency
- Validates played matches have scores
- Ensures scheduled matches don't have scores yet
- Checks for data corruption

### 4. Points Calculations
- Recalculates all points using the scoring rules
- Verifies spreadsheet calculations are correct
- Formula: Win=3pts, Draw=1.5pts, Goal=0.5pts (group) or 0.75pts (knockout)

### 5. Draft Picks Integrity
- Validates each player has exactly 10 teams
- Checks for duplicate team picks
- Ensures all 40 drafted teams are assigned

### 6. Reasonable Scores
- Flags matches with >10 total goals (extremely rare)
- Flags negative goals (data corruption)
- Examples: 
  - ❌ Brazil 50-0 Fiji (unreasonable)
  - ❌ Argentina -1-2 France (negative goals = bug)

**Cost:** Free, runs instantly

---

## Layer 2: Factual Validation with OpenAI

This is where **OpenAI API** comes in!

### When Does It Run?

✅ **YES** if:
- `OPENAI_API_KEY` is set in `.env`
- `use_llm=True` parameter is passed
- There are finished matches from the **last 3 days**

❌ **NO** if:
- No OpenAI API key configured
- No recent matches (last 3 days)
- API call fails

### What Does It Do?

1. **Filters Recent Matches**
   - Only checks matches from last 3 days
   - Keeps token usage low (~$0.01 per validation)
   - Example: If today is June 6, only checks matches from June 3-6

2. **Sends to OpenAI**
   - Model: `gpt-4o-mini` (default)
   - Temperature: 0.1 (low randomness for accuracy)
   - Prompt: "Verify if these World Cup results are correct"

3. **Gets Response**
   - OpenAI returns JSON with verification results
   - For each match: `recorded_correct: true/false`
   - Includes confidence level: high/medium/low
   - Provides correct score if wrong

4. **Parses Results**
   - High confidence wrong scores → **ERROR**
   - Low confidence wrong scores → **WARNING**
   - Correct matches → **PASSED**

### Example OpenAI Interaction

**Sent to OpenAI:**
```
My recorded results:
- 2026-06-05: France 3-1 Belgium (group)
- 2026-06-05: Argentina 2-0 Chile (group)
- 2026-06-06: Brazil 4-2 Germany (group)

Verify if these are correct...
```

**Response from OpenAI:**
```json
[
  {
    "home_team": "France",
    "away_team": "Belgium",
    "recorded_correct": true,
    "confidence": "high",
    "note": "Score verified from official FIFA records"
  },
  {
    "home_team": "Argentina",
    "away_team": "Chile",
    "recorded_correct": false,
    "correct_score": "1-1",
    "confidence": "medium",
    "note": "Match ended 1-1, not 2-0"
  }
]
```

**Cost:** ~$0.01-0.02 per validation (depends on number of matches)

---

## How Validation Works in Demo Mode

### Your Current Demo State

Based on the logs, here's what happened when you clicked "Validate":

```
2026-06-06 22:29:07 | 🎮 Demo mode: Running REAL validation with OpenAI...
2026-06-06 22:29:07 | Running daily validation...
2026-06-06 22:29:07 | No recent matches to validate with LLM
2026-06-06 22:29:07 | Validation complete: ✅ HEALTHY | 7 passed, 0 failed
```

### Why "No recent matches to validate with LLM"?

**Reason:** Your demo matches are dated in the past!

The demo generates matches starting **6 days before today** (June 6, 2026), so:
- Demo tournament started: ~May 31, 2026
- 18 pre-scored matches: May 31 - June 5
- **None are within the last 3 days** (June 3-6)

### The 7 Checks That Passed

Layer 1 ran successfully:
1. ✅ Match count (104 matches)
2. ✅ No duplicates
3. ✅ Score consistency
4. ✅ Points calculations
5. ✅ Draft picks integrity (4 players, 40 teams)
6. ✅ Reasonable scores (no 50-0 results)
7. ✅ LLM validation check (skipped, no recent matches)

---

## How to Test OpenAI Integration

To actually test the OpenAI API call, you need **recent match data**. Here are your options:

### Option 1: Wait for Recent Demo Matches

Keep clicking "Sync" until you have matches from the **last 3 days**:

```bash
# Current date: June 6, 2026
# Need matches from: June 3-6

# Keep syncing until match dates reach June 3+
# The demo generates matches chronologically
```

### Option 2: Modify Demo Date Logic

Temporarily change the demo to generate recent matches:

```python
# In src/demo.py, line ~103
tournament_start = today - timedelta(days=6)  # Current

# Change to:
tournament_start = today - timedelta(days=2)  # Recent matches!
```

This will make all demo matches recent, triggering LLM validation.

### Option 3: Test in Production Mode

Use real match data from an actual API:

```bash
# Stop demo, run production mode
python -m src.server  # (without --demo)
```

Production mode fetches real match data from football-data.org, which will have actual dates.

---

## Validation API Response

When validation runs, you get a JSON response like:

```json
{
  "status": "ok",
  "healthy": true,
  "summary": "✅ HEALTHY | 7 passed, 0 failed | 0 errors, 0 warnings",
  "issues": [],
  "checks_passed": 7,
  "checks_failed": 0
}
```

If issues are found:

```json
{
  "status": "ok",
  "healthy": false,
  "summary": "❌ ISSUES FOUND | 5 passed, 2 failed | 1 errors, 1 warnings",
  "issues": [
    {
      "severity": "error",
      "message": "Possibly wrong score: France vs Belgium — correct score may be 2-1 (confidence: high)",
      "details": "Official FIFA records show France won 2-1, not 3-1"
    },
    {
      "severity": "warning",
      "message": "Unusual score: 2026-06-05 Brazil 8-0 Peru (total 8 goals — verify!)",
      "details": null
    }
  ],
  "checks_passed": 5,
  "checks_failed": 2
}
```

---

## Cost Breakdown

### Free Components
- ✅ Structural validation (Layer 1)
- ✅ Google Sheets API calls
- ✅ Server hosting (until usage grows)

### Paid Components
- 💰 OpenAI API calls: ~$0.01-0.02 per validation
  - gpt-4o-mini: $0.15 per 1M input tokens
  - Typical validation: ~1000 tokens = $0.00015
  - With 10 matches: ~5000 tokens = $0.00075
  - Negligible cost unless running 1000s of validations

---

## Summary

### Is Validation Hitting OpenAI?

**Currently: NO** ❌
- Reason: No matches in the last 3 days
- Your demo matches are dated May 31 - June 5
- Today is June 6, so the newest match is 1+ days old
- LLM validation only checks matches from last 3 days

### Will It Hit OpenAI Eventually?

**YES** ✅ when:
- You sync enough matches to reach June 4-6 dates
- OR you modify demo dates
- OR you run production mode with real data

### What Ran Today?

**Layer 1 only:**
- 7 structural/math checks
- All passed ✅
- No OpenAI API calls made
- Cost: $0.00

### To Test OpenAI:

1. Keep clicking "Sync" to advance match dates
2. Wait until matches reach June 4+ dates
3. Click "Validate" again
4. Watch logs for: `"Asking LLM to verify X matches"`
5. OpenAI API will be called!

---

## Logs to Watch For

### When OpenAI IS called:
```
Running daily validation...
Asking LLM to verify 5 recent matches
[API call to OpenAI happens here]
Validation complete: ✅ HEALTHY | 12 passed, 0 failed
```

### When OpenAI is NOT called:
```
Running daily validation...
No recent matches to validate with LLM  ← This is you now!
Validation complete: ✅ HEALTHY | 7 passed, 0 failed
```

The difference? **7 passed** (no LLM) vs **12+ passed** (with LLM)
