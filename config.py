import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip().isdigit()
}
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/bot.db"))

_DEFAULT_PREDICTION_BACKFILLS = ""
_raw_backfills = os.getenv("PREDICTION_BACKFILLS")
if _raw_backfills is None:
    PREDICTION_BACKFILLS = _DEFAULT_PREDICTION_BACKFILLS
else:
    PREDICTION_BACKFILLS = _raw_backfills.strip()
