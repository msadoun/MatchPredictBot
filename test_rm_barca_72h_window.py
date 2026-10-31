"""Real Madrid and Barcelona use the same 72h prediction window as other clubs."""

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


def test_rm_barca_gated_by_72h_like_other_clubs():
    db = _fresh()
    villa = db.add_match(
        "برشلونة",
        "أستون فيلا",
        "2026-11-03T20:00:00 · الجولة 4 · دوري أبطال أوروبا",
    )
    aek = db.add_match(
        "أيك أثينا",
        "ريال مدريد",
        "2026-11-04T17:45:00 · الجولة 4 · دوري أبطال أوروبا",
    )
    now = datetime(2026, 10, 31, 6, 0, 0)
    assert not db.match_in_prediction_window(villa, now=now)
    assert not db.match_in_prediction_window(aek, now=now)
    assert not db.match_accepts_predictions(villa, now=now)
    assert not db.match_accepts_predictions(aek, now=now)


def test_picker_lists_md11_rm_barca_inside_72h():
    db = _fresh()
    db.seed_league_season_matches()
    # Sat 31 Oct morning — Barça–Alavés tonight (~14h), Racing–Madrid Sunday (~32h).
    now = datetime(2026, 10, 31, 6, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    pairs = {(m.home_team, m.away_team) for m in matches}
    assert ("برشلونة", "ألافيس") in pairs
    assert ("راسينغ سانتاندر", "ريال مدريد") in pairs
    # Far UCL fixtures stay hidden until inside 72h.
    assert ("برشلونة", "أستون فيلا") not in pairs
    assert ("أيك أثينا", "ريال مدريد") not in pairs
    for match in matches:
        assert db.match_in_prediction_window(match, now=now)
