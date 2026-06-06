"""Google Sheets formatting — colors, headers, conditional formatting.

Makes the spreadsheet visually appealing and easy to read at a glance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gspread

logger = logging.getLogger(__name__)

# ============================================================================
# Color palette (RGB 0-1 scale for Google Sheets API)
# ============================================================================

COLORS = {
    # Headers
    "header_blue": {"red": 0.07, "green": 0.34, "blue": 0.65},         # Dark blue
    "header_green": {"red": 0.15, "green": 0.5, "blue": 0.25},         # Dark green
    "header_gold": {"red": 0.75, "green": 0.56, "blue": 0.0},          # Gold
    "header_purple": {"red": 0.4, "green": 0.2, "blue": 0.6},          # Purple

    # Tab colors
    "tab_blue": {"red": 0.2, "green": 0.5, "blue": 0.85},
    "tab_green": {"red": 0.2, "green": 0.7, "blue": 0.3},
    "tab_gold": {"red": 0.9, "green": 0.7, "blue": 0.1},
    "tab_purple": {"red": 0.6, "green": 0.3, "blue": 0.8},

    # Row colors
    "white": {"red": 1.0, "green": 1.0, "blue": 1.0},
    "light_blue": {"red": 0.85, "green": 0.92, "blue": 1.0},
    "light_green": {"red": 0.85, "green": 0.95, "blue": 0.85},
    "light_gold": {"red": 1.0, "green": 0.96, "blue": 0.8},
    "light_gray": {"red": 0.95, "green": 0.95, "blue": 0.95},
    "light_red": {"red": 1.0, "green": 0.9, "blue": 0.9},

    # Text
    "text_white": {"red": 1.0, "green": 1.0, "blue": 1.0},
    "text_dark": {"red": 0.1, "green": 0.1, "blue": 0.1},
}


def format_scoring_rules_tab(worksheet: gspread.Worksheet):
    """Format the Scoring Rules tab with colors and styling."""
    sheet_id = worksheet.id
    requests = []

    # Set tab color (gold)
    requests.append(_tab_color_request(sheet_id, COLORS["tab_gold"]))

    # Header row (row 1) — bold white text on gold background
    requests.append(_header_format_request(sheet_id, 0, 1, COLORS["header_gold"]))

    # "GROUP STAGE" section header (row 3)
    requests.append(_section_header_request(sheet_id, 2, 3, COLORS["light_green"]))

    # "KNOCKOUT ROUNDS" section header (row 9)
    requests.append(_section_header_request(sheet_id, 8, 9, COLORS["light_blue"]))

    # "IMPORTANT NOTES" section header (row 15)
    requests.append(_section_header_request(sheet_id, 14, 15, COLORS["light_gold"]))

    # Freeze first row
    requests.append(_freeze_rows_request(sheet_id, 1))

    # Column widths
    requests.append(_column_width_request(sheet_id, 0, 1, 180))   # Category
    requests.append(_column_width_request(sheet_id, 1, 2, 180))   # Event
    requests.append(_column_width_request(sheet_id, 2, 3, 100))   # Points
    requests.append(_column_width_request(sheet_id, 3, 4, 350))   # Notes

    _batch_update(worksheet, requests)


def format_draft_picks_tab(worksheet: gspread.Worksheet, num_players: int):
    """Format the Draft Picks tab."""
    sheet_id = worksheet.id
    requests = []

    # Tab color (purple)
    requests.append(_tab_color_request(sheet_id, COLORS["tab_purple"]))

    # Header row — white text on purple background
    requests.append(_header_format_request(sheet_id, 0, 1, COLORS["header_purple"]))

    # Alternating row colors for player rows
    for i in range(num_players):
        row = i + 1  # 0-indexed (row 1 = first data row after header)
        color = COLORS["white"] if i % 2 == 0 else COLORS["light_gray"]
        requests.append(_row_color_request(sheet_id, row, row + 1, color))

    # Freeze header row
    requests.append(_freeze_rows_request(sheet_id, 1))

    # Column widths
    requests.append(_column_width_request(sheet_id, 0, 1, 120))   # Player name
    for col in range(1, 11):
        requests.append(_column_width_request(sheet_id, col, col + 1, 140))  # Teams

    _batch_update(worksheet, requests)


def format_schedule_tab(worksheet: gspread.Worksheet, num_matches: int):
    """Format the Match Schedule tab with stage-based coloring."""
    sheet_id = worksheet.id
    requests = []

    # Tab color (blue)
    requests.append(_tab_color_request(sheet_id, COLORS["tab_blue"]))

    # Header row — white text on blue background
    requests.append(_header_format_request(sheet_id, 0, 1, COLORS["header_blue"]))

    # Freeze header row and first 2 columns (Date, Stage)
    requests.append(_freeze_rows_request(sheet_id, 1))
    requests.append(_freeze_cols_request(sheet_id, 2))

    # Column widths
    col_widths = [100, 110, 60, 150, 150, 85, 85, 100, 100, 80, 90, 90]
    for i, width in enumerate(col_widths):
        requests.append(_column_width_request(sheet_id, i, i + 1, width))

    # Alternating row colors
    for i in range(num_matches):
        row = i + 1
        color = COLORS["white"] if i % 2 == 0 else COLORS["light_blue"]
        requests.append(_row_color_request(sheet_id, row, row + 1, color))

    # Bold the points columns (K, L)
    requests.append(_bold_column_request(sheet_id, 10, 12, 1, num_matches + 1))

    _batch_update(worksheet, requests)


def format_leaderboard_tab(worksheet: gspread.Worksheet, num_players: int):
    """Format the Leaderboard tab — the main scoreboard."""
    sheet_id = worksheet.id
    requests = []

    # Tab color (green)
    requests.append(_tab_color_request(sheet_id, COLORS["tab_green"]))

    # Header row — white text on green background
    requests.append(_header_format_request(sheet_id, 0, 1, COLORS["header_green"]))

    # Freeze header row
    requests.append(_freeze_rows_request(sheet_id, 1))

    # Player rows with rank-based highlighting
    rank_colors = [
        COLORS["light_gold"],   # 1st place — gold
        COLORS["light_gray"],   # 2nd place — silver
        COLORS["light_red"],    # 3rd place — bronze-ish
        COLORS["white"],        # 4th place
    ]
    for i in range(min(num_players, 4)):
        requests.append(_row_color_request(sheet_id, i + 1, i + 2, rank_colors[i]))

    # Column widths
    requests.append(_column_width_request(sheet_id, 0, 1, 50))    # Rank
    requests.append(_column_width_request(sheet_id, 1, 2, 120))   # Player
    requests.append(_column_width_request(sheet_id, 2, 3, 100))   # Total Points
    for col in range(3, 13):
        requests.append(_column_width_request(sheet_id, col, col + 1, 150))  # Teams

    # Make Total Points column bold
    requests.append(_bold_column_request(sheet_id, 2, 3, 1, num_players + 1))

    # Make Rank and Total Points font larger
    requests.append(_font_size_request(sheet_id, 0, 3, 1, num_players + 1, 11))

    _batch_update(worksheet, requests)


# ============================================================================
# Helper functions for building Sheets API requests
# ============================================================================

def _batch_update(worksheet: gspread.Worksheet, requests: list[dict]):
    """Send a batch update to the Google Sheets API."""
    if not requests:
        return
    try:
        worksheet.spreadsheet.batch_update({"requests": requests})
        logger.info(f"Applied {len(requests)} format requests to '{worksheet.title}'")
    except Exception as e:
        logger.warning(f"Failed to apply formatting to '{worksheet.title}': {e}")


def _tab_color_request(sheet_id: int, color: dict) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "tabColor": color,
            },
            "fields": "tabColor",
        }
    }


def _header_format_request(sheet_id: int, start_row: int, end_row: int, bg_color: dict) -> dict:
    """Bold white text on colored background for header row."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": bg_color,
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": COLORS["text_white"],
                        "fontSize": 10,
                    },
                    "horizontalAlignment": "CENTER",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
        }
    }


def _section_header_request(sheet_id: int, start_row: int, end_row: int, bg_color: dict) -> dict:
    """Bold text on light colored background for section headers."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": bg_color,
                    "textFormat": {
                        "bold": True,
                        "fontSize": 10,
                    },
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }


def _row_color_request(sheet_id: int, start_row: int, end_row: int, color: dict) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": color,
                }
            },
            "fields": "userEnteredFormat.backgroundColor",
        }
    }


def _freeze_rows_request(sheet_id: int, num_rows: int) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": num_rows},
            },
            "fields": "gridProperties.frozenRowCount",
        }
    }


def _freeze_cols_request(sheet_id: int, num_cols: int) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenColumnCount": num_cols},
            },
            "fields": "gridProperties.frozenColumnCount",
        }
    }


def _column_width_request(sheet_id: int, start_col: int, end_col: int, width: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": start_col,
                "endIndex": end_col,
            },
            "properties": {"pixelSize": width},
            "fields": "pixelSize",
        }
    }


def _bold_column_request(
    sheet_id: int, start_col: int, end_col: int, start_row: int, end_row: int
) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"bold": True},
                }
            },
            "fields": "userEnteredFormat.textFormat.bold",
        }
    }


def _font_size_request(
    sheet_id: int, start_col: int, end_col: int, start_row: int, end_row: int, size: int
) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            },
            "cell": {
                "userEnteredFormat": {
                    "textFormat": {"fontSize": size},
                }
            },
            "fields": "userEnteredFormat.textFormat.fontSize",
        }
    }
