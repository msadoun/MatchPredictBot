def match_outcome(home: int, away: int) -> str:
    if home > away:
        return "home"
    if home < away:
        return "away"
    return "draw"


def calculate_points(
    predicted_home: int,
    predicted_away: int,
    actual_home: int,
    actual_away: int,
) -> int:
    if predicted_home == actual_home and predicted_away == actual_away:
        return 3

    predicted = match_outcome(predicted_home, predicted_away)
    actual = match_outcome(actual_home, actual_away)
    if predicted != actual:
        return 0

    if actual == "draw":
        return 0

    if actual == "home":
        predicted_winner_goals = predicted_home
        actual_winner_goals = actual_home
    else:
        predicted_winner_goals = predicted_away
        actual_winner_goals = actual_away

    if predicted_winner_goals == actual_winner_goals:
        return 2

    return 1
