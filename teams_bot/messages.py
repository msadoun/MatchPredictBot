"""EID schedule message formatting for /date."""

from __future__ import annotations

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Asia/Dubai"

_AT_MENTION_RE = re.compile(r"<at>.*?</at>", re.IGNORECASE | re.DOTALL)


def format_schedule_date(when: date | datetime | None = None, *, timezone: str = DEFAULT_TIMEZONE) -> str:
    """Return ``{Weekday} , {D Month, YYYY}`` in the given timezone."""
    if when is None:
        when = datetime.now(ZoneInfo(timezone))
    elif isinstance(when, datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=ZoneInfo(timezone))
        else:
            when = when.astimezone(ZoneInfo(timezone))
    else:
        # Plain date — treat as a calendar day in the target zone (no clock conversion).
        when = datetime(when.year, when.month, when.day, tzinfo=ZoneInfo(timezone))

    day_name = when.strftime("%A")
    day_num = when.day
    month_name = when.strftime("%B")
    year = when.year
    return f"{day_name} , {day_num} {month_name}, {year}"


def build_date_message(when: date | datetime | None = None, *, timezone: str = DEFAULT_TIMEZONE) -> str:
    """Build the multi-emirate EID hours reply for /date."""
    stamped = format_schedule_date(when, timezone=timezone)
    return (
        f"Abu Dhabi\n"
        f"EID// {stamped} // 4:00 PM to 9:30 PM\n"
        f"\n"
        f"Sharjah\n"
        f"EID// {stamped} //  PM to 9:30 PM\n"
        f"\n"
        f"Ajman\n"
        f"EID// {stamped} // 3:00 PM to 9:30 PM\n"
        f"\n"
        f"Dubai\n"
        f"EID// {stamped} // 2:30 PM to 6:00 PM\n"
        f"\n"
        f"EID// {stamped} // 6:00 PM to 9:30 PM"
    )


def strip_teams_mentions(text: str) -> str:
    """Remove Teams ``<at>...</at>`` mention markup."""
    return _AT_MENTION_RE.sub("", text or "").strip()


def is_date_command(text: str | None) -> bool:
    """True when the message is /date (ignores Teams @mentions)."""
    if not text:
        return False
    # Teams often prefixes: "<at>Bot Name</at> /date"
    cleaned = strip_teams_mentions(text).lower()
    if cleaned.startswith("/"):
        cleaned = cleaned[1:]
    command = cleaned.split()[0] if cleaned else ""
    return command.rstrip(".,!?") == "date"
