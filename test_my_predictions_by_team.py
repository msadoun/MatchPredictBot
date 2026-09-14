"""My predictions: pick a league team, then show that team's picks."""

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


def test_render_team_predictions_empty_and_filled():
    db, handlers, msg = _fresh()
    user = db.upsert_user(12, "u2", "User Two")
    match = db.add_match("برشلونة", "خيتافي", "2026-10-10T16:30:00")
    db.save_prediction(user.id, match.id, 3, 1)
    predictions = db.get_user_predictions(user.id)

    filled = handlers._render_team_predictions_text("برشلونة", predictions)
    assert "برشلونة" in filled
    assert "3-1" in filled

    empty = handlers._render_team_predictions_text("تشيلسي", predictions)
    assert msg.MY_PREDICTIONS_TEAM_EMPTY.format(team="تشيلسي") in empty


def test_my_predictions_team_keyboard_lists_seven_clubs():
    _, handlers, _ = _fresh()
    keyboard = handlers._my_predictions_team_keyboard()
    labels = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "ريال مدريد" in labels
    assert "تشيلسي" in labels
    assert any(btn.callback_data.startswith("mypred:team:") for row in keyboard.inline_keyboard for btn in row)
