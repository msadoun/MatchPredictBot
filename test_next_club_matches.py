"""Next open match per club: UCL included, head-to-heads not duplicated."""

import importlib
import os
import tempfile
from datetime import datetime


def _fresh_db():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def test_seeded_picker_includes_ucl_when_it_is_next():
    """With the live 2026/27 calendar, clubs whose next kickoff is UCL must show it."""
    db = _fresh_db()
    db.seed_league_season_matches()
    matches = db.list_next_open_match_per_league_club()
    assert matches, "expected open fixtures after season seed"

    ucl = [m for m in matches if "دوري أبطال أوروبا" in (m.kickoff_at or "")]
    # After early September domestic midweeks, several clubs' next game is UCL MD1.
    assert ucl, "Champions League matches must appear in the predict picker"

    # Sanity: every listed UCL kickoff is still in the future (or overridden open).
    now = datetime.utcnow()
    for match in ucl:
        assert db.match_accepts_predictions(match, now=now)


def test_head_to_head_between_tracked_clubs_listed_once():
    db = _fresh_db()
    db.seed_league_season_matches()
    matches = db.list_next_open_match_per_league_club()
    ids = [m.id for m in matches]
    assert len(ids) == len(set(ids))

    # Arsenal vs Chelsea is both clubs' next domestic fixture around MD3.
    derby = [
        m
        for m in matches
        if {m.home_team, m.away_team} == {"أرسنال", "تشيلسي"}
    ]
    assert len(derby) <= 1
