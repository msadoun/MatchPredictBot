"""Prediction window: matches appear only within 72 hours of kickoff."""

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


def test_match_accepts_only_within_72_hours():
    db = _fresh()
    soon = db.add_match(
        "برايتون",
        "أرسنال",
        "2026-09-19T14:00:00 · الجولة 5 · الدوري الإنجليزي",
    )
    later = db.add_match(
        "أرسنال",
        "ليدز يونايتد",
        "2026-10-10T11:30:00 · الجولة 6 · الدوري الإنجليزي",
    )
    now = datetime(2026, 9, 17, 12, 0, 0)
    assert db.match_in_prediction_window(soon, now=now)
    assert db.match_accepts_predictions(soon, now=now)
    assert not db.match_in_prediction_window(later, now=now)
    assert not db.match_accepts_predictions(later, now=now)


def test_league_picker_only_lists_matches_in_72h_window():
    db = _fresh()
    db.seed_league_season_matches()
    now = datetime(2026, 9, 17, 12, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    assert matches
    pairs = {(m.home_team, m.away_team) for m in matches}
    assert ("برايتون", "أرسنال") in pairs
    # Leeds is weeks away — must not appear yet.
    assert ("أرسنال", "ليدز يونايتد") not in pairs
    for match in matches:
        assert db.match_in_prediction_window(match, now=now)


def test_stale_arsenal_psv_never_shown_even_in_window():
    db = _fresh()
    db.add_match(
        "أرسنال",
        "بي إس في",
        "2026-09-16T19:00:00 · الجولة 1 · دوري أبطال أوروبا",
    )
    db.seed_league_season_matches()
    now = datetime(2026, 9, 17, 12, 0, 0)
    remaining = {
        (m.home_team, m.away_team)
        for m in db.list_matches(open_only=False, limit=None)
    }
    assert ("أرسنال", "بي إس في") not in remaining
    next_ars = [
        m
        for m in db.list_next_open_match_per_league_club(now=now)
        if "أرسنال" in (m.home_team, m.away_team)
    ]
    assert len(next_ars) == 1
    assert (next_ars[0].home_team, next_ars[0].away_team) == ("برايتون", "أرسنال")
