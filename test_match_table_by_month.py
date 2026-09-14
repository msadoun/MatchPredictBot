"""Admin match prediction table: team → month → matches."""

import importlib
import os
import tempfile


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


def test_month_keyboard_callbacks_include_team_and_month():
    _, handlers, _ = _fresh()
    keyboard = handlers._admin_match_table_month_keyboard(2, ["2026-09", "2026-10"])
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "adminpred:photomonth:2:2026-09" in callbacks
    assert "adminpred:photomonth:2:2026-10" in callbacks
    assert "adminpred:photopick" in callbacks


def test_match_picker_back_goes_to_months():
    db, handlers, _ = _fresh()
    match = db.add_match("تشيلسي", "آرسنال", "2026-09-20T15:30:00")
    keyboard = handlers._admin_match_photo_picker_keyboard(
        [match], team_index=6
    )
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert f"adminpred:photo:{match.id}" in callbacks
    assert "adminpred:phototeam:6" in callbacks
