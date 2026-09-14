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
    rm_bar = db.add_match(
        "ريال مدريد",
        "برشلونة",
        "2026-09-20T19:00:00 · الجولة 7 · الدوري الإسباني",
    )
    liv = db.add_match(
        "ليفربول",
        "أرسنال",
        "2026-09-20T15:00:00 · الجولة 5 · الدوري الإنجليزي",
    )
    atm_rm = db.add_match(
        "أتلتيكو مدريد",
        "ريال مدريد",
        "2026-09-20T14:15:00 · الجولة 7 · الدوري الإسباني",
    )

    rm_matches = reports.matches_for_scope("team", "ريال مدريد")
    assert {m.id for m in rm_matches} == {rm_bar.id, atm_rm.id}
    assert liv.id not in {m.id for m in rm_matches}
    assert reports.scope_label("team", "ريال مدريد") == "مباريات ريال مدريد"


def test_build_prediction_report_for_team_scope():
    db, reports = _fresh_db()
    db.add_match(
        "برشلونة",
        "خيتافي",
        "2026-10-10T16:30:00 · الجولة 8 · الدوري الإسباني",
    )
    report = reports.build_prediction_report("team", "برشلونة")
    assert report.scope_type == "team"
    assert report.scope_key == "برشلونة"
    assert report.scope_label == "مباريات برشلونة"
    assert len(report.matches) == 1
