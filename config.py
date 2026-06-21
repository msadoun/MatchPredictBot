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

# Optional: Telegram chat ID for https://t.me/alkoram3na (used if @username lookup fails)
ALKORAM3NA_GROUP_CHAT_ID = os.getenv("ALKORAM3NA_GROUP_CHAT_ID", "").strip()
# Optional: Telegram chat ID for K m3na groub (https://t.me/+2TIcPEGwjo8wOTg0)
KM3NA_GROUP_CHAT_ID = os.getenv("KM3NA_GROUP_CHAT_ID", "").strip()

_DEFAULT_PREDICTION_BACKFILLS = ""
_raw_backfills = os.getenv("PREDICTION_BACKFILLS")
if _raw_backfills is None:
    PREDICTION_BACKFILLS = _DEFAULT_PREDICTION_BACKFILLS
else:
    PREDICTION_BACKFILLS = _raw_backfills.strip()
