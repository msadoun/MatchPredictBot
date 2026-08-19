from league_season import (
    CHAMPIONS_LEAGUE_FIXTURES,
    CHAMPIONS_LEAGUE_LABEL,
    LA_LIGA_TEAMS,
    LEAGUE_SEASON_FIXTURES,
    LEAGUE_TEAMS,
    LOCAL_LA_LIGA_LABEL,
    LOCAL_LEAGUE_FIXTURES,
    LOCAL_PL_LABEL,
    PREMIER_LEAGUE_TEAMS,
    league_kickoff_label,
)


def test_seven_clubs():
    teams_in_fixtures: set[str] = set()
    for fixture in LEAGUE_SEASON_FIXTURES:
        teams_in_fixtures.add(fixture.home)
        teams_in_fixtures.add(fixture.away)
    assert teams_in_fixtures == set(LEAGUE_TEAMS)


def test_local_and_champions_league_split():
    assert len(LOCAL_LEAGUE_FIXTURES) == 11  # 1 La Liga + 10 PL
    assert len(CHAMPIONS_LEAGUE_FIXTURES) == 10  # 2 × 5 cross-league
    assert len(LEAGUE_SEASON_FIXTURES) == 21


def test_local_pairs_only_within_domestic_league():
    for fixture in LOCAL_LEAGUE_FIXTURES:
        if fixture.group == LOCAL_LA_LIGA_LABEL:
            assert fixture.home in LA_LIGA_TEAMS and fixture.away in LA_LIGA_TEAMS
        elif fixture.group == LOCAL_PL_LABEL:
            assert (
                fixture.home in PREMIER_LEAGUE_TEAMS
                and fixture.away in PREMIER_LEAGUE_TEAMS
            )


def test_champions_league_is_cross_border():
    for fixture in CHAMPIONS_LEAGUE_FIXTURES:
        assert fixture.group == CHAMPIONS_LEAGUE_LABEL
        teams = {fixture.home, fixture.away}
        assert teams & set(LA_LIGA_TEAMS)
        assert teams & set(PREMIER_LEAGUE_TEAMS)


def test_each_pair_plays_once_per_competition():
    for fixtures in (LOCAL_LEAGUE_FIXTURES, CHAMPIONS_LEAGUE_FIXTURES):
        seen: set[tuple[str, str]] = set()
        for fixture in fixtures:
            pair = tuple(sorted((fixture.home, fixture.away)))
            assert pair not in seen
            seen.add(pair)


def test_kickoff_label_includes_competition():
    label = league_kickoff_label(LEAGUE_SEASON_FIXTURES[0])
    assert " · " in label
    assert label.split(" · ", 1)[1] in {
        LOCAL_LA_LIGA_LABEL,
        LOCAL_PL_LABEL,
        CHAMPIONS_LEAGUE_LABEL,
    }
