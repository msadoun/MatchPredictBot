"""My predictions: recent per team on main; older in team→month archive."""

import importlib
import os
import tempfile


def _fresh():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db
    import handlers
    import messages as msg

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(handlers)
    importlib.reload(msg)
    db.init_db()
    return db, handlers, msg


def test_predictions_for_team_filters_home_and_away():
    db, handlers, _ = _fresh()
    user = db.upsert_user(11, "u", "User")
    rm = db.add_match("ريال مدريد", "إشبيلية", "2026-10-18T19:00:00")
    away_rm = db.add_match("أتلتيكو مدريد", "ريال مدريد", "2026-09-20T14:15:00")
    other = db.add_match("ليفربول", "آرسنال", "2026-09-21T15:00:00")
    db.save_prediction(user.id, rm.id, 2, 0, allow_closed=True)
    db.save_prediction(user.id, away_rm.id, 1, 1, allow_closed=True)
    db.save_prediction(user.id, other.id, 3, 2, allow_closed=True)

    predictions = db.get_user_predictions(user.id)
    filtered = handlers._predictions_for_team(predictions, "ريال مدريد")
    assert {match.id for _, match in filtered} == {rm.id, away_rm.id}


def test_recent_prediction_is_latest_kickoff_per_team():
    db, handlers, _ = _fresh()
    user = db.upsert_user(12, "u2", "User Two")
    older = db.add_match("برشلونة", "خيتافي", "2026-09-19T19:00:00")
    newer = db.add_match("برشلونة", "ألافيس", "2026-10-31T20:00:00")
    db.save_prediction(user.id, older.id, 2, 2, allow_closed=True)
    db.save_prediction(user.id, newer.id, 3, 1, allow_closed=True)
    predictions = db.get_user_predictions(user.id)

    recent = handlers._recent_predictions_for_team(predictions, "برشلونة")
    assert len(recent) == 1
    assert recent[0][1].id == newer.id

    archive = handlers._archive_predictions_for_team(predictions, "برشلونة")
    assert {match.id for _, match in archive} == {older.id}


def test_recent_view_lists_latest_per_team():
    db, handlers, msg = _fresh()
    user = db.upsert_user(13, "u3", "User Three")
    rm_old = db.add_match("ريال مدريد", "رايو فاليكانو", "2026-09-12T19:00:00")
    rm_new = db.add_match("راسينغ سانتاندر", "ريال مدريد", "2026-11-01T14:15:00")
    barca = db.add_match("برشلونة", "ألافيس", "2026-10-31T20:00:00")
    db.save_prediction(user.id, rm_old.id, 2, 1, allow_closed=True)
    db.save_prediction(user.id, rm_new.id, 1, 0, allow_closed=True)
    db.save_prediction(user.id, barca.id, 3, 0, allow_closed=True)
    predictions = db.get_user_predictions(user.id)

    text = handlers._render_recent_predictions_text(predictions)
    assert msg.MY_PREDICTIONS_RECENT_HEADER in text
    assert "راسينغ سانتاندر" in text
    assert "1-0" in text
    assert "ألافيس" in text
    assert "3-0" in text
    # Older Madrid prediction is archived, not on the recent screen.
    assert "رايو فاليكانو" not in text


def test_archive_month_excludes_recent_match():
    db, handlers, msg = _fresh()
    user = db.upsert_user(14, "u4", "User Four")
    sep = db.add_match("ريال مدريد", "رايو فاليكانو", "2026-09-20T19:00:00")
    oct = db.add_match("ريال مدريد", "فياريال", "2026-10-10T19:00:00")
    db.save_prediction(user.id, sep.id, 2, 1, allow_closed=True)
    db.save_prediction(user.id, oct.id, 3, 0, allow_closed=True)
    predictions = db.get_user_predictions(user.id)

    sep_text = handlers._render_archive_month_predictions_text(
        "ريال مدريد", "2026-09", predictions
    )
    assert "سبتمبر 2026" in sep_text
    assert "2-1" in sep_text
    assert "3-0" not in sep_text

    # October is the recent match — empty in archive for that month.
    oct_archive = handlers._render_archive_month_predictions_text(
        "ريال مدريد", "2026-10", predictions
    )
    assert msg.MY_PREDICTIONS_MONTH_EMPTY.format(
        team="ريال مدريد", month="أكتوبر 2026"
    ) in oct_archive

    empty = handlers._render_archive_month_predictions_text(
        "ريال مدريد", "2026-11", predictions
    )
    assert msg.MY_PREDICTIONS_MONTH_EMPTY.format(
        team="ريال مدريد", month="نوفمبر 2026"
    ) in empty


def test_archive_months_and_keyboard_callbacks():
    db, handlers, _ = _fresh()
    user = db.upsert_user(15, "u5", "User Five")
    older = db.add_match("تشيلسي", "آرسنال", "2026-09-20T15:30:00")
    newer = db.add_match("تشيلسي", "بورنموث", "2026-10-10T14:00:00")
    db.save_prediction(user.id, older.id, 1, 1, allow_closed=True)
    db.save_prediction(user.id, newer.id, 2, 0, allow_closed=True)
    predictions = db.get_user_predictions(user.id)

    months = handlers._months_for_archive_team(predictions, "تشيلسي")
    assert months == ["2026-09"]
    keyboard = handlers._my_predictions_month_keyboard(6, months)
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "mypred:month:6:2026-09" in callbacks
    assert "mypred:archive" in callbacks
    assert "mypred:menu" in callbacks

    archive_teams = handlers._archive_teams_with_predictions(predictions)
    assert any(team == "تشيلسي" for _, team in archive_teams)
