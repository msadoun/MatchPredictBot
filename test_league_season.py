from league_season import (
    LEAGUE_SEASON_FIXTURES,
    LEAGUE_TEAMS,
    league_kickoff_label,
)


def test_seven_clubs():
    teams_in_fixtures: set[str] = set()
    for fixture in LEAGUE_SEASON_FIXTURES:
        teams_in_fixtures.add(fixture.home)
        teams_in_fixtures.add(fixture.away)
    assert teams_in_fixtures == set(LEAGUE_TEAMS)


def test_single_round_robin_match_count():
    n = len(LEAGUE_TEAMS)
    assert len(LEAGUE_SEASON_FIXTURES) == n * (n - 1) // 2


def test_each_pair_plays_once():
    seen: set[tuple[str, str]] = set()
    for fixture in LEAGUE_SEASON_FIXTURES:
        pair = tuple(sorted((fixture.home, fixture.away)))
        assert pair not in seen
        seen.add(pair)


def test_kickoff_label_includes_round():
    label = league_kickoff_label(LEAGUE_SEASON_FIXTURES[0])
    assert " · الجولة " in label
    assert label.startswith("2026-")
