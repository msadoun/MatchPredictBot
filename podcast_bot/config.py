import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("PODCAST_BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
DATABASE_PATH = Path(os.getenv("PODCAST_DATABASE_PATH", "data/podcast_bot.db"))
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
MAX_EPISODES = int(os.getenv("MAX_EPISODES", "50"))
