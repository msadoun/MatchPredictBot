"""My predictions: team → month → matches in that month."""

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
    db.save_prediction(user.id, rm.id, 2, 0)
    db.save_prediction(user.id, away_rm.id, 1, 1)
    db.save_prediction(user.id, other.id, 3, 2)

    predictions = db.get_user_predictions(user.id)
    filtered = handlers._predictions_for_team(predictions, "ريال مدريد")
    assert {match.id for _, match in filtered} == {rm.id, away_rm.id}


def test_months_for_team_predictions_are_sorted():
    db, handlers, _ = _fresh()
    user = db.upsert_user(12, "u2", "User Two")
    oct_match = db.add_match("برشلونة", "خيتافي", "2026-10-10T16:30:00")
    sep_match = db.add_match("برشلونة", "إشبيلية", "2026-09-19T19:00:00")
    db.save_prediction(user.id, oct_match.id, 3, 1)
    db.save_prediction(user.id, sep_match.id, 2, 2)
    predictions = db.get_user_predictions(user.id)

    months = handlers._months_for_team_predictions(predictions, "برشلونة")
    assert months == ["2026-09", "2026-10"]
    assert handlers._format_year_month_label("2026-09") == "سبتمبر 2026"


def test_render_team_month_predictions_filters_by_month():
    db, handlers, msg = _fresh()
    user = db.upsert_user(13, "u3", "User Three")
    sep = db.add_match("ريال مدريد", "رايو فاليكانو", "2026-09-20T19:00:00")
    oct = db.add_match("ريال مدريد", "فياريال", "2026-10-10T19:00:00")
    db.save_prediction(user.id, sep.id, 2, 1)
    db.save_prediction(user.id, oct.id, 3, 0)
    predictions = db.get_user_predictions(user.id)

    sep_text = handlers._render_team_month_predictions_text(
        "ريال مدريد", "2026-09", predictions
    )
    assert "سبتمبر 2026" in sep_text
    assert "2-1" in sep_text
    assert "3-0" not in sep_text

    empty = handlers._render_team_month_predictions_text(
        "ريال مدريد", "2026-11", predictions
    )
    assert msg.MY_PREDICTIONS_MONTH_EMPTY.format(
        team="ريال مدريد", month="نوفمبر 2026"
    ) in empty


def test_month_keyboard_callbacks_include_team_and_month():
    db, handlers, _ = _fresh()
    user = db.upsert_user(14, "u4", "User Four")
    match = db.add_match("تشيلسي", "آرسنال", "2026-09-20T15:30:00")
    db.save_prediction(user.id, match.id, 1, 1)
    predictions = db.get_user_predictions(user.id)
    months = handlers._months_for_team_predictions(predictions, "تشيلسي")
    keyboard = handlers._my_predictions_month_keyboard(6, months)
    callbacks = [btn.callback_data for row in keyboard.inline_keyboard for btn in row]
    assert "mypred:month:6:2026-09" in callbacks
    assert "mypred:menu" in callbacks
