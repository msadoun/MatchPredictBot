"""Admin match prediction table: available matches + archive by team/month."""

import importlib
import os
import tempfile
from datetime import datetime


def _fresh():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db
    import handlers
    import messages as msg

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(handlers)
    importlib.reload(msg)
    db.init_db()
    return db, handlers, msg


def test_months_for_matches_are_sorted():
    db, handlers, _ = _fresh()
    db.add_match("برشلونة", "خيتافي", "2026-10-10T16:30:00")
    db.add_match("برشلونة", "إشبيلية", "2026-09-19T19:00:00")
    db.add_match("ليفربول", "آرسنال", "2026-09-21T15:00:00")
    matches = [
        m
        for m in db.list_matches(open_only=False)
        if "برشلونة" in (m.home_team, m.away_team)
    ]
    months = handlers._months_for_matches(matches)
    assert months == ["2026-09", "2026-10"]
    assert handlers._format_year_month_label("2026-09") == "سبتمبر 2026"


def test_matches_for_month_filters_kickoff():
    db, handlers, _ = _fresh()
    sep = db.add_match("ريال مدريد", "رايو فاليكانو", "2026-09-20T19:00:00")
    oct_match = db.add_match("ريال مدريد", "فياريال", "2026-10-10T19:00:00")
    matches = [sep, oct_match]
    assert [m.id for m in handlers._matches_for_month(matches, "2026-09")] == [sep.id]
    assert [m.id for m in handlers._matches_for_month(matches, "2026-10")] == [
        oct_match.id
    ]


def test_month_keyboard_callbacks_go_to_archive():
    _, handlers, _ = _fresh()
    keyboard = handlers._admin_match_table_month_keyboard(2, ["2026-09", "2026-10"])
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "adminpred:photomonth:2:2026-09" in callbacks
    assert "adminpred:photomonth:2:2026-10" in callbacks
    assert "adminpred:photoarchive" in callbacks
    assert "adminpred:photopick" in callbacks


def test_available_match_picker_includes_archive_button():
    db, handlers, _ = _fresh()
    match = db.add_match("تشيلسي", "آرسنال", "2026-09-20T15:30:00")
    keyboard = handlers._admin_match_photo_picker_keyboard(
        [match], available=True
    )
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert f"adminpred:photo:{match.id}" in callbacks
    assert "adminpred:photoarchive" in callbacks
    assert "adminpred:menu" in callbacks


def test_archive_match_picker_back_goes_to_months():
    db, handlers, _ = _fresh()
    match = db.add_match("تشيلسي", "آرسنال", "2026-09-20T15:30:00")
    keyboard = handlers._admin_match_photo_picker_keyboard(
        [match], team_index=6
    )
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert f"adminpred:photo:{match.id}" in callbacks
    assert "adminpred:phototeam:6" in callbacks
    assert "adminpred:photoarchive" in callbacks


def test_available_vs_archive_split_for_seeded_season():
    db, handlers, _ = _fresh()
    db.seed_league_season_matches()
    now = datetime(2026, 11, 6, 20, 0, 0)
    available = handlers._admin_available_matches(now=now)
    available_ids = {m.id for m in available}
    pairs = {(m.home_team, m.away_team) for m in available}
    assert ("أرسنال", "هال") in pairs
    assert ("فالنسيا", "ريال مدريد") in pairs

    archive_rm = handlers._admin_archive_matches_for_team("ريال مدريد", now=now)
    archive_pairs = {(m.home_team, m.away_team) for m in archive_rm}
    assert ("ريال مدريد", "رايو فاليكانو") in archive_pairs
    assert ("فالنسيا", "ريال مدريد") not in archive_pairs
    assert available_ids.isdisjoint({m.id for m in archive_rm})
