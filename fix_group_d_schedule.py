"""One-off fix: Correct the duplicate Paraguay vs Australia match on June 25.

The Group D schedule had:
  June 25: Turkey vs USA        → should be: Australia vs USA
  June 25: Paraguay vs Australia → should be: Turkey vs Paraguay

Run:
    python fix_group_d_schedule.py
"""

import logging
from src.config import Config
from src.sheets.client import SheetsClient
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def fix_group_d():
    errors = Config.validate()
    if errors:
        for err in errors:
            logger.error(f"Config error: {err}")
        return

    client = SheetsClient()
    data = client.read_all_values("Match Schedule")

    if not data:
        logger.error("No data found in Match Schedule tab")
        return

    fixes_applied = 0

    for i, row in enumerate(data[1:], start=2):  # skip header, 1-indexed in sheet
        if len(row) < 5:
            continue
        match_date = row[0]
        home_team = row[3]
        away_team = row[4]

        # Fix 1: "Turkey vs USA" on June 25 → "Australia vs USA"
        if match_date == "2026-06-25" and home_team == "Turkey" and away_team == "USA":
            client.update_range("Match Schedule", f"D{i}:E{i}", [["Australia", "USA"]])
            logger.info(f"Row {i}: Fixed 'Turkey vs USA' → 'Australia vs USA'")
            fixes_applied += 1

        # Fix 2: "Paraguay vs Australia" on June 25 → "Turkey vs Paraguay"
        if match_date == "2026-06-25" and home_team == "Paraguay" and away_team == "Australia":
            client.update_range("Match Schedule", f"D{i}:E{i}", [["Turkey", "Paraguay"]])
            logger.info(f"Row {i}: Fixed 'Paraguay vs Australia' → 'Turkey vs Paraguay'")
            fixes_applied += 1

    if fixes_applied == 2:
        logger.info("✅ Group D schedule fixed successfully!")
    elif fixes_applied == 0:
        logger.warning("⚠️  No matching rows found — schedule may already be fixed")
    else:
        logger.warning(f"⚠️  Only {fixes_applied}/2 fixes applied — check manually")


if __name__ == "__main__":
    fix_group_d()
