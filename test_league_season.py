from league_season import (
    CHAMPIONS_LEAGUE_FIXTURES,
    CHAMPIONS_LEAGUE_LABEL,
    CL_MATCHES_PER_CLUB,
    LA_LIGA_TEAMS,
    LEAGUE_SEASON_FIXTURES,
    LEAGUE_TEAMS,
    LOCAL_LA_LIGA_LABEL,
    LOCAL_LEAGUE_FIXTURES,
    LOCAL_MATCHES_PER_CLUB,
    LOCAL_PL_LABEL,
    MATCHES_PER_CLUB,
    PREMIER_LEAGUE_TEAMS,
    fixtures_for_club,
    league_kickoff_label,
)


def test_seven_clubs_feature_in_every_fixture():
    for fixture in LEAGUE_SEASON_FIXTURES:
        assert fixture.club in LEAGUE_TEAMS
        assert fixture.club in (fixture.home, fixture.away)


def test_no_head_to_head_between_tracked_clubs():
    tracked = set(LEAGUE_TEAMS)
    for fixture in LEAGUE_SEASON_FIXTURES:
        assert not (fixture.home in tracked and fixture.away in tracked)


def test_ten_matches_per_club():
    for club in LEAGUE_TEAMS:
        club_fixtures = fixtures_for_club(club)
        assert len(club_fixtures) == MATCHES_PER_CLUB
        local = [f for f in club_fixtures if f.group in (LOCAL_LA_LIGA_LABEL, LOCAL_PL_LABEL)]
        cl = [f for f in club_fixtures if f.group == CHAMPIONS_LEAGUE_LABEL]
        assert len(local) == LOCAL_MATCHES_PER_CLUB
        assert len(cl) == CL_MATCHES_PER_CLUB


def test_total_fixture_count():
    assert len(LEAGUE_SEASON_FIXTURES) == len(LEAGUE_TEAMS) * MATCHES_PER_CLUB
    assert len(LOCAL_LEAGUE_FIXTURES) == len(LEAGUE_TEAMS) * LOCAL_MATCHES_PER_CLUB
    assert len(CHAMPIONS_LEAGUE_FIXTURES) == len(LEAGUE_TEAMS) * CL_MATCHES_PER_CLUB


def test_local_labels_by_domestic_league():
    for fixture in LOCAL_LEAGUE_FIXTURES:
        if fixture.club in LA_LIGA_TEAMS:
            assert fixture.group == LOCAL_LA_LIGA_LABEL
        else:
            assert fixture.group == LOCAL_PL_LABEL
            assert fixture.club in PREMIER_LEAGUE_TEAMS


def test_kickoff_label_includes_competition():
    label = league_kickoff_label(LEAGUE_SEASON_FIXTURES[0])
    assert " · " in label
    assert label.split(" · ", 1)[1] in {
        LOCAL_LA_LIGA_LABEL,
        LOCAL_PL_LABEL,
        CHAMPIONS_LEAGUE_LABEL,
    }
