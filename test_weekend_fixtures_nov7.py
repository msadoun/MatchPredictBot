"""This weekend (7–8 Nov 2026) every tracked club has a fixture inside 72h."""

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


def test_picker_lists_all_clubs_on_fri_nov_6():
    db = _fresh()
    db.seed_league_season_matches()
    now = datetime(2026, 11, 6, 20, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    pairs = {(m.home_team, m.away_team) for m in matches}

    assert ("أرسنال", "هال") in pairs
    assert ("نوتنغهام فورست", "مانشستر سيتي") in pairs
    assert ("كريستال بالاس", "ليفربول") in pairs
    assert ("مانشستر يونايتد", "أستون فيلا") in pairs
    assert ("ساندرلاند", "تشيلسي") in pairs
    assert ("فالنسيا", "ريال مدريد") in pairs
    assert ("أتلتيكو مدريد", "برشلونة") in pairs

    for match in matches:
        assert db.match_in_prediction_window(match, now=now)
