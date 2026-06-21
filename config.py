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
PREDICTION_BACKFILLS = os.getenv(
    "PREDICTION_BACKFILLS",
    "M2usab:35:3-0,10140530:35:3-0",
)
