from scoring import calculate_points


def test_exact_score():
    assert calculate_points(2, 1, 2, 1) == 3
    assert calculate_points(1, 1, 1, 1) == 3


def test_winning_team_goals():
    assert calculate_points(4, 0, 4, 1) == 2
    assert calculate_points(0, 4, 1, 4) == 2


def test_correct_winner_only():
    assert calculate_points(3, 0, 4, 1) == 1
    assert calculate_points(2, 1, 4, 1) == 1


def test_correct_draw_only():
    assert calculate_points(1, 1, 0, 0) == 1


def test_wrong_prediction():
    assert calculate_points(2, 0, 0, 2) == 0
    assert calculate_points(1, 0, 1, 1) == 0
