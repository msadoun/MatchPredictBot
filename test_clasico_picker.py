"""El Clásico (Barcelona vs Real Madrid) must appear inside the 72h window."""

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


def test_clasico_appears_in_picker_on_match_eve():
    db = _fresh_db()
    db.seed_league_season_matches()
    # Sat 24 Oct 2026 afternoon — Clasico is Sun 25 Oct 20:00 UTC.
    now = datetime(2026, 10, 24, 14, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    clasico = [
        m
        for m in matches
        if {m.home_team, m.away_team} == {"برشلونة", "ريال مدريد"}
    ]
    assert len(clasico) == 1, "El Clásico must appear once in the prediction picker"
    assert clasico[0].home_team == "برشلونة"
    assert clasico[0].away_team == "ريال مدريد"
    assert "2026-10-25T20:00:00" in (clasico[0].kickoff_at or "")
    assert db.match_accepts_predictions(clasico[0], now=now)
