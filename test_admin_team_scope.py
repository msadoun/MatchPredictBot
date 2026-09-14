"""Admin prediction panel scopes reports by league team."""

import importlib
import os
import tempfile


def _fresh_db():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db
    import prediction_reports as reports

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(reports)
    db.init_db()
    return db, reports


def test_list_league_teams_are_the_seven_clubs():
    _, reports = _fresh_db()
    teams = reports.list_league_teams()
    assert len(teams) == 7
    assert "ريال مدريد" in teams
    assert "برشلونة" in teams
    assert "تشيلسي" in teams


def test_matches_for_scope_team_filters_home_and_away():
    db, reports = _fresh_db()
    db.seed_league_season_matches()
    # Stale pair not in the current calendar window — must be ignored.
    stale = db.add_match(
        "ريال مدريد",
        "برشلونة",
        "2026-09-20T19:00:00 · الجولة 7 · الدوري الإسباني",
    )
    # Off-club fixture also in DB.
    liv = db.add_match(
        "بورنموث",
        "ليفربول",
        "2026-09-20T13:00:00 · الجولة 5 · الدوري الإنجليزي",
    )

    rm_matches = reports.matches_for_scope("team", "ريال مدريد")
    pairs = {(m.home_team, m.away_team) for m in rm_matches}
    assert ("ريال مدريد", "رايو فاليكانو") in pairs
    assert ("إلتشي", "ريال مدريد") in pairs
    assert ("ريال مدريد", "برشلونة") not in pairs
    assert stale.id not in {m.id for m in rm_matches}
    assert liv.id not in {m.id for m in rm_matches}
    assert reports.scope_label("team", "ريال مدريد") == "مباريات ريال مدريد"


def test_build_prediction_report_for_team_scope():
    db, reports = _fresh_db()
    db.seed_league_season_matches()
    report = reports.build_prediction_report("team", "برشلونة")
    assert report.scope_type == "team"
    assert report.scope_key == "برشلونة"
    assert report.scope_label == "مباريات برشلونة"
    assert len(report.matches) >= 1
    assert all(
        "برشلونة" in (m.home_team, m.away_team) for m in report.matches
    )


def test_matches_for_scope_team_arsenal_excludes_napoli_md1():
    db, reports = _fresh_db()
    db.seed_league_season_matches()
    # Past MD1 remnant that may still sit in production DBs.
    napoli = db.add_match(
        "نابولي",
        "أرسنال",
        "2026-09-09T19:00:00 · الجولة 1 · دوري أبطال أوروبا",
    )
    arsenal = reports.matches_for_scope("team", "أرسنال")
    pairs = {(m.home_team, m.away_team) for m in arsenal}
    assert ("برايتون", "أرسنال") in pairs
    assert ("أرسنال", "ليل") in pairs
    assert ("أرسنال", "ريال مدريد") in pairs
    assert ("نابولي", "أرسنال") not in pairs
    assert napoli.id not in {m.id for m in arsenal}
