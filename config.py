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

_DEFAULT_PREDICTION_BACKFILLS = "M2usab:35:3-0,10140530:35:3-0,Musab:35:3-0"
_raw_backfills = os.getenv("PREDICTION_BACKFILLS")
if _raw_backfills is None or not _raw_backfills.strip():
    PREDICTION_BACKFILLS = _DEFAULT_PREDICTION_BACKFILLS
else:
    PREDICTION_BACKFILLS = _raw_backfills.strip()
