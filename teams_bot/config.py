"""Configuration for the Microsoft Teams EID schedule bot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

# Azure Bot / Bot Framework credentials (leave empty for local emulator testing)
MICROSOFT_APP_ID = os.getenv("MicrosoftAppId") or os.getenv("MICROSOFT_APP_ID", "")
MICROSOFT_APP_PASSWORD = (
    os.getenv("MicrosoftAppPassword") or os.getenv("MICROSOFT_APP_PASSWORD", "")
)
MICROSOFT_APP_TENANT_ID = (
    os.getenv("MicrosoftAppTenantId") or os.getenv("MICROSOFT_APP_TENANT_ID", "")
)
MICROSOFT_APP_TYPE = os.getenv("MicrosoftAppType") or os.getenv(
    "MICROSOFT_APP_TYPE", "SingleTenant"
)

PORT = int(os.getenv("PORT", "3978"))
TIMEZONE = os.getenv("BOT_TIMEZONE", "Asia/Dubai")
