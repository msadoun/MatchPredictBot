"""Admin Excel exports use one sheet per match."""

import importlib
import os
import tempfile
from pathlib import Path


def _fresh():
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


def test_report_to_excel_one_sheet_per_match():
    db, reports = _fresh()
    m1 = db.add_match(
        "برايتون",
        "أرسنال",
        "2026-09-19T14:00:00 · الجولة 5 · الدوري الإنجليزي",
    )
    m2 = db.add_match(
        "أرسنال",
        "ليدز يونايتد",
        "2026-10-10T11:30:00 · الجولة 6 · الدوري الإنجليزي",
    )
    user = db.upsert_user(101, "alice", "Alice")
    db.save_prediction(user.id, m1.id, 1, 2, allow_closed=True)
    db.save_prediction(user.id, m2.id, 3, 0, allow_closed=True)

    report = reports.build_prediction_report("team", "أرسنال")
    # May include more calendar matches after seed filter; force known pair set.
    report.matches = [m1, m2]
    workbook = reports.report_to_excel(report)
    assert len(workbook.worksheets) == 2
    assert str(m1.id) in workbook.worksheets[0].title
    assert str(m2.id) in workbook.worksheets[1].title
    assert workbook.worksheets[0]["A1"].value == "user name"
    assert workbook.worksheets[0]["A2"].value == "Alice"


def test_save_match_prediction_export_single_sheet():
    db, reports = _fresh()
    match = db.add_match(
        "برايتون",
        "أرسنال",
        "2026-09-19T14:00:00 · الجولة 5 · الدوري الإنجليزي",
    )
    user = db.upsert_user(202, "bob", "Bob")
    db.save_prediction(user.id, match.id, 0, 0, allow_closed=True)

    path, saved = reports.save_match_prediction_export(
        match,
        saved_by_telegram_id=1,
    )
    assert path.exists()
    assert path.suffix == ".xlsx"
    assert saved.scope_type == "match"
    assert saved.match_count == 1
    assert saved.prediction_count >= 1

    from openpyxl import load_workbook

    workbook = load_workbook(path)
    assert len(workbook.worksheets) == 1
    assert str(match.id) in workbook.active.title
    workbook.close()
    path.unlink(missing_ok=True)
