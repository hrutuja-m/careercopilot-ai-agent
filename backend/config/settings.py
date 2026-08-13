import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file():
    """Load backend/.env without failing if python-dotenv is not installed yet."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        if not ENV_FILE.exists():
            return
        for line in ENV_FILE.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        return

    load_dotenv(ENV_FILE)


def _get_int(name, default):
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


_load_env_file()

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail")
USER_EMAIL = os.getenv("USER_EMAIL", "rutujamore9499@gmail.com")
GMAIL_LOOKBACK_DAYS = _get_int("GMAIL_LOOKBACK_DAYS", 30)
GMAIL_MAX_RESULTS = _get_int("GMAIL_MAX_RESULTS", 20)
GMAIL_APPLIED_LABEL = os.getenv("GMAIL_APPLIED_LABEL", "CareerCopilot/Applied")
