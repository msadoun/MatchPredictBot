import importlib
import os
import tempfile


def _fresh_db():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def test_group_leaderboard_includes_orphan_predictor_without_membership():
    db = _fresh_db()
    group_id = -1001234567890
    os.environ["ALKORAM3NA_GROUP_CHAT_ID"] = str(group_id)
    import config

    importlib.reload(config)

    user = db.upsert_user(333, "player3", "Player Three")
    match = db.add_match("E", "F", "2030-08-24T12:00:00")
    db.save_prediction(user.id, match.id, 2, 1)
    db.set_match_result(match.id, 2, 1)

    entries = db.get_leaderboard(group_chat_id=group_id)
    assert len(entries) == 1
    assert entries[0].display_name == "Player Three"
    assert entries[0].total_points == 3


def test_group_leaderboard_includes_manual_base_without_group_membership():
    db = _fresh_db()
    group_id = -1001234567890
    user = db.upsert_user(444, "player4", "Player Four")

    db.set_group_manual_points(group_id, user.id, 15)
    with db.get_db() as conn:
        conn.execute("DELETE FROM group_members WHERE user_id = ?", (user.id,))

    entries = db.get_leaderboard(group_chat_id=group_id)
    assert len(entries) == 1
    assert entries[0].total_points == 15


def test_leaderboard_defaults_to_configured_group_without_explicit_scope():
    db = _fresh_db()
    group_id = -1001260044677
    os.environ["ALKORAM3NA_GROUP_CHAT_ID"] = str(group_id)
    import config

    importlib.reload(config)

    user = db.upsert_user(555, "player5", "Player Five")
    db.set_group_manual_points(group_id, user.id, 20)
    match = db.add_match("G", "H", "2030-08-25T12:00:00")
    db.save_prediction(user.id, match.id, 2, 0)
    db.set_match_result(match.id, 2, 0)

    entries = db.get_leaderboard(group_chat_id=None)
    assert len(entries) == 1
    assert entries[0].total_points == 23


def test_group_leaderboard_includes_predictor_with_active_group_only():
    db = _fresh_db()
    group_id = -1001234567890
    user = db.upsert_user(111, "player1", "Player One")

    match = db.add_match("A", "B", "2030-08-22T12:00:00")
    db.set_user_active_group(user.id, group_id)
    db.save_prediction(user.id, match.id, 2, 0)
    db.set_match_result(match.id, 2, 0)

    with db.get_db() as conn:
        conn.execute("DELETE FROM group_members WHERE user_id = ?", (user.id,))

    db.sync_predictors_to_group_members()
    entries = db.get_leaderboard(group_chat_id=group_id)
    assert len(entries) == 1
    assert entries[0].display_name == "Player One"
    assert entries[0].total_points == 3


def test_group_leaderboard_adds_prediction_points_to_manual_base():
    db = _fresh_db()
    group_id = -1001234567890
    user = db.upsert_user(222, "player2", "Player Two")

    db.set_group_manual_points(group_id, user.id, 10)
    match = db.add_match("C", "D", "2030-08-23T12:00:00")
    db.register_group_member(group_id, user.id)
    db.save_prediction(user.id, match.id, 1, 1)
    db.set_match_result(match.id, 1, 1)

    entries = db.get_leaderboard(group_chat_id=group_id)
    assert len(entries) == 1
    assert entries[0].total_points == 13
