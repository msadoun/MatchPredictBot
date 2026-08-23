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


def test_leaderboard_includes_users_with_unscored_predictions():
    db = _fresh_db()
    user_a = db.upsert_user(601, "alpha", "Alpha")
    user_b = db.upsert_user(602, "beta", "Beta")
    match = db.add_match("Home", "Away", "2031-01-01T12:00:00")
    db.save_prediction(user_a.id, match.id, 2, 1)
    db.save_prediction(user_b.id, match.id, 0, 0)

    entries = db.get_leaderboard()
    assert len(entries) == 2
    assert entries[0].total_points == 0
    assert entries[1].total_points == 0


def test_group_leaderboard_excludes_predictor_without_group_membership():
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
    assert entries == []


def test_group_leaderboard_includes_registered_group_member():
    db = _fresh_db()
    group_id = -1001234567890
    user = db.upsert_user(333, "player3", "Player Three")
    db.register_group_member(group_id, user.id)
    match = db.add_match("E", "F", "2030-08-24T12:00:00")
    db.save_prediction(user.id, match.id, 2, 1)
    db.set_match_result(match.id, 2, 1)

    entries = db.get_leaderboard(group_chat_id=group_id)
    assert len(entries) == 1
    assert entries[0].display_name == "Player Three"
    assert entries[0].total_points == 3


def test_group_leaderboard_includes_manual_base_only_for_group_members():
    db = _fresh_db()
    group_id = -1001234567890
    user = db.upsert_user(444, "player4", "Player Four")

    db.set_group_manual_points(group_id, user.id, 15)
    with db.get_db() as conn:
        conn.execute("DELETE FROM group_members WHERE user_id = ?", (user.id,))

    entries = db.get_leaderboard(group_chat_id=group_id)
    assert entries == []


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


def test_group_leaderboard_scoped_to_selected_group_only():
    db = _fresh_db()
    group_a = -1001111111111
    group_b = -1002222222222
    user_a = db.upsert_user(701, "alice", "Alice")
    user_b = db.upsert_user(702, "bob", "Bob")
    match = db.add_match("X", "Y", "2030-08-26T12:00:00")

    db.register_group_member(group_a, user_a.id)
    db.register_group_member(group_b, user_b.id)
    db.save_prediction(user_a.id, match.id, 2, 0)
    db.save_prediction(user_b.id, match.id, 0, 1)
    db.set_match_result(match.id, 2, 0)

    entries_a = db.get_leaderboard(group_chat_id=group_a)
    entries_b = db.get_leaderboard(group_chat_id=group_b)

    assert [entry.display_name for entry in entries_a] == ["Alice"]
    assert [entry.display_name for entry in entries_b] == ["Bob"]


def test_unregister_group_member_hides_group_from_user():
    db = _fresh_db()
    group_id = -1003333333333
    user = db.upsert_user(801, "carol", "Carol")
    db.register_group_member(group_id, user.id)
    db.set_user_active_group(user.id, group_id)

    assert db.get_user_group_chat_ids(user.id) == [group_id]
    assert db.get_user_active_group(user.id) == group_id

    db.unregister_group_member(group_id, user.id)

    assert db.get_user_group_chat_ids(user.id) == []
    assert db.get_user_active_group(user.id) is None


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
