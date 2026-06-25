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
    assert calculate_points(2, 2, 1, 1) == 1
    assert calculate_points(0, 0, 2, 2) == 1


def test_iraq_norway_winner_goals():
    # Iraq (home) vs Norway (away): predicted Norway 4-0 → 0-4, actual 1-4
    assert calculate_points(0, 4, 1, 4) == 2


def test_wrong_prediction():
    assert calculate_points(2, 0, 0, 2) == 0
    assert calculate_points(1, 0, 1, 1) == 0


def test_doubled_exact_only():
    assert calculate_points(2, 1, 2, 1, is_doubled=True) == 6
    assert calculate_points(1, 1, 1, 1, is_doubled=True) == 6
    assert calculate_points(3, 0, 4, 1, is_doubled=True) == 0
    assert calculate_points(4, 0, 4, 1, is_doubled=True) == 0
    assert calculate_points(1, 1, 0, 0, is_doubled=True) == 0
