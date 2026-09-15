"""Tests for EID /date message formatting."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from messages import build_date_message, format_schedule_date, is_date_command


def test_format_schedule_date_fixed_day():
    stamped = format_schedule_date(date(2026, 9, 15), timezone="Asia/Dubai")
    assert stamped == "Tuesday , 15 September, 2026"


def test_format_schedule_date_uses_dubai_timezone():
    # 2026-09-14 22:00 UTC == 2026-09-15 02:00 Asia/Dubai → Tuesday
    when = datetime(2026, 9, 14, 22, 0, tzinfo=ZoneInfo("UTC"))
    stamped = format_schedule_date(when, timezone="Asia/Dubai")
    assert stamped == "Tuesday , 15 September, 2026"


def test_build_date_message_contains_all_emirates():
    text = build_date_message(date(2026, 9, 15), timezone="Asia/Dubai")
    assert "Abu Dhabi" in text
    assert "Sharjah" in text
    assert "Ajman" in text
    assert "Dubai" in text
    assert "EID// Tuesday , 15 September, 2026 // 4:00 PM to 9:30 PM" in text
    assert "EID// Tuesday , 15 September, 2026 //  PM to 9:30 PM" in text
    assert "EID// Tuesday , 15 September, 2026 // 3:00 PM to 9:30 PM" in text
    assert "EID// Tuesday , 15 September, 2026 // 2:30 PM to 6:00 PM" in text
    assert "EID// Tuesday , 15 September, 2026 // 6:00 PM to 9:30 PM" in text


def test_is_date_command_variants():
    assert is_date_command("/date")
    assert is_date_command(" /date ")
    assert is_date_command("/DATE")
    assert is_date_command("<at>EID Bot</at> /date")
    assert is_date_command("date")
    assert not is_date_command("/dates")
    assert not is_date_command("/help")
    assert not is_date_command("")
    assert not is_date_command(None)
