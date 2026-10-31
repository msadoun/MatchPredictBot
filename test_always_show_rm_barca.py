"""Real Madrid and Barcelona fixtures stay listed outside the 72h window."""

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


def test_rm_barca_accept_predictions_outside_72h():
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
    pl_far = db.add_match(
        "أرسنال",
        "بوروسيا دورتموند",
        "2026-11-24T20:00:00 · الجولة 5 · دوري أبطال أوروبا",
    )
    # Sat 31 Oct — Villa ~86h / AEK ~107h (always shown); PL/UCL others still 72h-gated.
    now = datetime(2026, 10, 31, 6, 0, 0)
    assert not db.match_in_prediction_window(villa, now=now)
    assert not db.match_in_prediction_window(aek, now=now)
    assert not db.match_in_prediction_window(pl_far, now=now)
    assert db.match_accepts_predictions(villa, now=now)
    assert db.match_accepts_predictions(aek, now=now)
    assert not db.match_accepts_predictions(pl_far, now=now)


def test_picker_lists_todays_barca_and_tomorrows_madrid():
    db = _fresh()
    db.seed_league_season_matches()
    # Sat 31 Oct morning — Barça–Alavés tonight, Racing–Madrid Sunday.
    now = datetime(2026, 10, 31, 6, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    pairs = {(m.home_team, m.away_team) for m in matches}
    assert ("برشلونة", "ألافيس") in pairs
    assert ("راسينغ سانتاندر", "ريال مدريد") in pairs
    barca = [m for m in matches if "برشلونة" in (m.home_team, m.away_team)]
    rm = [m for m in matches if "ريال مدريد" in (m.home_team, m.away_team)]
    assert barca, "Barcelona matches must always appear"
    assert rm, "Real Madrid matches must always appear"
