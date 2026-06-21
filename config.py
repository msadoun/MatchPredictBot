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

# Optional: survives Railway redeploys when mounted volume is missing
REMOTE_PREDICTION_BACKUP_URL = os.getenv("REMOTE_PREDICTION_BACKUP_URL", "").strip()
REMOTE_PREDICTION_BACKUP_TOKEN = os.getenv("REMOTE_PREDICTION_BACKUP_TOKEN", "").strip()

# Optional: Telegram chat ID for https://t.me/alkoram3na (used if @username lookup fails)
ALKORAM3NA_GROUP_CHAT_ID = os.getenv("ALKORAM3NA_GROUP_CHAT_ID", "").strip()
# Optional: Telegram chat ID for K m3na groub (https://t.me/+2TIcPEGwjo8wOTg0)
KM3NA_GROUP_CHAT_ID = os.getenv("KM3NA_GROUP_CHAT_ID", "").strip()

# Auto leaderboard points for @M2usab in any group (does not change predictions)
M2USAB_TELEGRAM_ID = int(os.getenv("M2USAB_TELEGRAM_ID", "10140530"))
M2USAB_USERNAME = os.getenv("M2USAB_USERNAME", "M2usab").strip().lstrip("@").lower()
M2USAB_AUTO_GROUP_POINTS = int(os.getenv("M2USAB_AUTO_GROUP_POINTS", "24"))


def configured_group_chat_ids() -> list[int]:
    ids: list[int] = []
    for raw in (ALKORAM3NA_GROUP_CHAT_ID, KM3NA_GROUP_CHAT_ID):
        if raw.lstrip("-").isdigit():
            ids.append(int(raw))
    return ids

_DEFAULT_PREDICTION_BACKFILLS = ""
_raw_backfills = os.getenv("PREDICTION_BACKFILLS")
if _raw_backfills is None:
    PREDICTION_BACKFILLS = _DEFAULT_PREDICTION_BACKFILLS
else:
    PREDICTION_BACKFILLS = _raw_backfills.strip()
