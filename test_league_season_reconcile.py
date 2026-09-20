"""League season seed upserts kickoffs and drops stale English fixtures."""

import importlib
import os
import tempfile
from datetime import datetime


def _fresh():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def test_seed_updates_moved_city_sunderland_kickoff():
    db = _fresh()
    stale = db.add_match(
        "مانشستر سيتي",
        "ساندرلاند",
        "2026-09-19T14:00:00 · الجولة 5 · الدوري الإنجليزي",
    )
    result = db.seed_league_season_matches()
    assert result["updated"] >= 1
    match = db.get_match(stale.id)
    assert match is not None
    assert match.kickoff_at.startswith("2026-09-20T13:00:00")


def test_reconcile_removes_stale_english_openers():
    db = _fresh()
    db.add_match(
        "أرسنال",
        "كونتري",
        "2026-08-21T19:00:00 · الجولة 1 · الدوري الإنجليزي",
    )
    db.add_match(
        "هال",
        "مانشستر يونايتد",
        "2026-08-22T11:30:00 · الجولة 1 · الدوري الإنجليزي",
    )
    result = db.seed_league_season_matches()
    assert result["removed"] >= 2
    remaining = db.list_matches(open_only=False, limit=None)
    pairs = {(m.home_team, m.away_team) for m in remaining}
    assert ("أرسنال", "كونتري") not in pairs
    assert ("هال", "مانشستر يونايتد") not in pairs


def test_reconcile_removes_arsenal_ucl_md1_napoli():
    db = _fresh()
    db.add_match(
        "نابولي",
        "أرسنال",
        "2026-09-09T19:00:00 · الجولة 1 · دوري أبطال أوروبا",
    )
    result = db.seed_league_season_matches()
    assert result["removed"] >= 1
    remaining = db.list_matches(open_only=False, limit=None)
    pairs = {(m.home_team, m.away_team) for m in remaining}
    assert ("نابولي", "أرسنال") not in pairs
    assert ("برايتون", "أرسنال") in pairs
    assert ("أرسنال", "ليل") in pairs
    assert ("أرسنال", "ريال مدريد") in pairs


def test_stale_arsenal_psv_never_shown_as_next():
    """Old wrong UCL Arsenal–PSV must not beat Brighton as Arsenal's next match."""
    db = _fresh()
    db.add_match(
        "أرسنال",
        "بي إس في",
        "2026-09-16T19:00:00 · الجولة 1 · دوري أبطال أوروبا",
    )
    db.seed_league_season_matches()
    remaining = {(m.home_team, m.away_team) for m in db.list_matches(open_only=False, limit=None)}
    assert ("أرسنال", "بي إس في") not in remaining
    now = datetime(2026, 9, 17, 12, 0, 0)
    next_ars = [
        m
        for m in db.list_next_open_match_per_league_club(now=now)
        if "أرسنال" in (m.home_team, m.away_team)
    ]
    assert len(next_ars) == 1
    assert (next_ars[0].home_team, next_ars[0].away_team) == ("برايتون", "أرسنال")
