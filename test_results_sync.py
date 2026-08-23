import importlib
import os
import tempfile
from unittest.mock import patch


def _fresh_db():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db
    import results_sync

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    importlib.reload(results_sync)
    return db, results_sync


def test_scoreboard_leagues_for_la_liga_fixture():
    _, rs = _fresh_db()
    kickoff = "2026-08-22T19:30:00 · الجولة 2 · الدوري الإسباني"
    assert rs._scoreboard_leagues_for_match(kickoff) == ["esp.1"]


def test_scoreboard_leagues_for_premier_league_fixture():
    _, rs = _fresh_db()
    kickoff = "2026-08-22T11:30:00 · الجولة 1 · الدوري الإنجليزي"
    assert rs._scoreboard_leagues_for_match(kickoff) == ["eng.1"]


def test_active_scoreboard_leagues_includes_all_competitions():
    db, rs = _fresh_db()
    db.add_match("A", "B", "2026-08-22T12:00:00 · الجولة 1 · الدوري الإسباني")
    assert rs.active_scoreboard_leagues() == [
        "esp.1",
        "eng.1",
        "uefa.champions",
        "fifa.world",
    ]


def test_espn_coventry_name_matches_league_fixture():
    db, rs = _fresh_db()
    match = db.add_match(
        "أرسنال",
        "كونتري",
        "2030-08-21T19:00:00 · الجولة 1 · الدوري الإنجليزي",
    )

    assert rs._find_match_id("أرسنال", "كوفنتري", "2030-08-21") == match.id

    fake_result = {
        "date": "2030-08-21",
        "home_ar": "أرسنال",
        "away_ar": "كونتري",
        "home_score": 3,
        "away_score": 0,
        "league": "eng.1",
    }

    with patch.object(rs, "_iter_scoreboard_results", return_value=[fake_result]):
        assert rs.restore_match_result_from_espn(match.id)

    updated = db.get_match(match.id)
    assert updated.home_score == 3
    assert updated.away_score == 0


def test_espn_afc_bournemouth_matches_man_city_fixture():
    db, rs = _fresh_db()
    match = db.add_match(
        "مانشستر سيتي",
        "بورنموث",
        "2030-08-23T13:00:00 · الجولة 1 · الدوري الإنجليزي",
    )

    assert rs._english_to_arabic("AFC Bournemouth") == "بورنموث"
    assert rs._find_match_id("مانشستر سيتي", "بورنموث", "2030-08-23") == match.id

    fake_result = {
        "date": "2030-08-23",
        "home_ar": "مانشستر سيتي",
        "away_ar": "بورنموث",
        "home_score": 2,
        "away_score": 1,
        "league": "eng.1",
    }

    with patch.object(rs, "_iter_scoreboard_results", return_value=[fake_result]):
        assert rs.restore_match_result_from_espn(match.id)

    updated = db.get_match(match.id)
    assert updated.home_score == 2
    assert updated.away_score == 1


def test_espn_result_import_scores_predictions():
    db, rs = _fresh_db()
    user = db.upsert_user(101, "fan1", "Fan One")
    match = db.add_match(
        "هال",
        "مانشستر يونايتد",
        "2030-08-22T11:30:00 · الجولة 1 · الدوري الإنجليزي",
    )
    db.save_prediction(user.id, match.id, 2, 0)

    fake_result = {
        "date": "2030-08-22",
        "home_ar": "هال",
        "away_ar": "مانشستر يونايتد",
        "home_score": 2,
        "away_score": 0,
        "league": "eng.1",
    }

    with patch.object(rs, "_iter_scoreboard_results", return_value=[fake_result]):
        assert rs.restore_match_result_from_espn(match.id)

    updated = db.get_match(match.id)
    assert updated.home_score == 2
    assert updated.away_score == 0
    prediction = db.get_user_prediction(user.id, match.id)
    assert prediction.points == 3
