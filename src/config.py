"""Application configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (only used in local dev, ignored on Render)
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


class Config:
    """Central configuration for the FIFA 2026 Fantasy Draft app.

    All secrets are loaded from environment variables so this works on
    hosted services like Render without putting credentials in files.
    """

    # --- Google Sheets ---
    # Option 1 (hosted/Render): Set the entire JSON content as an env var
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    # Option 2 (local dev): Path to the credentials file
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_FILE",
        str(_project_root / "credentials.json"),
    )
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")

    # --- Football Data API (football-data.org v4) ---
    FOOTBALL_API_KEY: str = os.getenv("FOOTBALL_API_KEY", "")
    FOOTBALL_API_BASE_URL: str = "https://api.football-data.org/v4"
    # FIFA World Cup 2026 competition code
    FOOTBALL_API_COMPETITION: str = "WC"

    # --- OpenAI / ChatGPT Fallback ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Sync Schedule ---
    # Cron-style: hour and minute (24h format) for daily auto-sync
    SYNC_HOUR: int = int(os.getenv("SYNC_HOUR", "6"))  # 6 AM default
    SYNC_MINUTE: int = int(os.getenv("SYNC_MINUTE", "0"))
    SYNC_TIMEZONE: str = os.getenv("SYNC_TIMEZONE", "Asia/Kolkata")

    # --- State ---
    # On Render: use /tmp or a persistent disk path
    STATE_FILE: str = os.getenv(
        "STATE_FILE", str(_project_root / "state" / "last_sync.json")
    )

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- Deployment ---
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Demo Mode ---
    # Optional: Use a separate spreadsheet for demo mode testing
    DEMO_GOOGLE_SHEETS_ID: str = os.getenv("DEMO_GOOGLE_SHEETS_ID", "")
    # If set, demo mode will use this instead of GOOGLE_SHEETS_ID

    # --- Share Message ---
    # Optional: URL to include in share messages (e.g., dashboard link)
    DASHBOARD_URL: str = os.getenv("DASHBOARD_URL", "")

    # --- Rate Limiting ---
    # Cooldown period (in seconds) between manual sync/validate calls
    # Default: 600 seconds (10 minutes) to avoid hammering APIs
    SYNC_COOLDOWN_SECONDS: int = int(os.getenv("SYNC_COOLDOWN_SECONDS", "600"))

    @classmethod
    def has_credentials_json(cls) -> bool:
        """Check if credentials are provided as a JSON env var (for hosted deploys)."""
        return bool(cls.GOOGLE_SHEETS_CREDENTIALS_JSON.strip())

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of missing required config values."""
        errors = []
        if not cls.GOOGLE_SHEETS_ID:
            errors.append("GOOGLE_SHEETS_ID is not set")
        # Check credentials: either JSON env var OR file must exist
        if not cls.has_credentials_json():
            if not Path(cls.GOOGLE_SHEETS_CREDENTIALS_FILE).exists():
                errors.append(
                    "Google credentials not found. Set GOOGLE_SHEETS_CREDENTIALS_JSON "
                    "(for hosted) or place credentials.json in project root (for local dev)"
                )
        if not cls.FOOTBALL_API_KEY:
            errors.append("FOOTBALL_API_KEY is not set (needed for primary data source)")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set (needed for LLM fallback)")
        return errors

