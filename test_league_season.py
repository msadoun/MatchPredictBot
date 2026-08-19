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

CHE = "تشيلسي"
UCL_CLUBS = [club for club in LEAGUE_TEAMS if club != CHE]


def test_seven_clubs_feature_in_every_fixture():
    for fixture in LEAGUE_SEASON_FIXTURES:
        assert fixture.club in LEAGUE_TEAMS
        assert fixture.club in (fixture.home, fixture.away)


def test_ten_matches_per_club():
    for club in LEAGUE_TEAMS:
        club_fixtures = fixtures_for_club(club)
        assert len(club_fixtures) == MATCHES_PER_CLUB
        local = [
            f
            for f in club_fixtures
            if LOCAL_LA_LIGA_LABEL in f.group or LOCAL_PL_LABEL in f.group
        ]
        cl = [f for f in club_fixtures if CHAMPIONS_LEAGUE_LABEL in f.group]
        if club == CHE:
            assert len(local) == MATCHES_PER_CLUB
            assert len(cl) == 0
        else:
            assert len(local) == LOCAL_MATCHES_PER_CLUB
            assert len(cl) == CL_MATCHES_PER_CLUB


def test_total_fixture_count():
    assert len(LEAGUE_SEASON_FIXTURES) == len(LEAGUE_TEAMS) * MATCHES_PER_CLUB
    assert len(LOCAL_LEAGUE_FIXTURES) == len(LEAGUE_TEAMS) * LOCAL_MATCHES_PER_CLUB + 5
    assert len(CHAMPIONS_LEAGUE_FIXTURES) == len(UCL_CLUBS) * CL_MATCHES_PER_CLUB


def test_local_labels_by_domestic_league():
    for fixture in LOCAL_LEAGUE_FIXTURES:
        if fixture.club in LA_LIGA_TEAMS:
            assert LOCAL_LA_LIGA_LABEL in fixture.group
        else:
            assert LOCAL_PL_LABEL in fixture.group
            assert fixture.club in PREMIER_LEAGUE_TEAMS


def test_kickoff_label_includes_competition():
    label = league_kickoff_label(LEAGUE_SEASON_FIXTURES[0])
    assert " · " in label
    competition = label.split(" · ", 1)[1]
    assert any(
        tag in competition
        for tag in (
            LOCAL_LA_LIGA_LABEL,
            LOCAL_PL_LABEL,
            CHAMPIONS_LEAGUE_LABEL,
        )
    )


def test_fixtures_sorted_by_kickoff():
    kickoffs = [fixture.kickoff_utc for fixture in LEAGUE_SEASON_FIXTURES]
    assert kickoffs == sorted(kickoffs)


def test_real_madrid_opens_at_espanyol():
    rm_local = [
        f
        for f in fixtures_for_club("ريال مدريد")
        if LOCAL_LA_LIGA_LABEL in f.group
    ]
    first = min(rm_local, key=lambda f: f.kickoff_utc)
    assert first.away == "ريال مدريد"
    assert first.home == "إسبانيول"


def test_season_starts_in_august_2026():
    assert LEAGUE_SEASON_FIXTURES[0].kickoff_utc.startswith("2026-08")


def test_gw1_opening_fixtures():
    """2026/27 gameweek 1 / jornada opening matches per official calendars."""
    def next_local(club: str) -> tuple[str, str]:
        local = sorted(
            (
                f
                for f in fixtures_for_club(club)
                if LOCAL_LA_LIGA_LABEL in f.group or LOCAL_PL_LABEL in f.group
            ),
            key=lambda f: f.kickoff_utc,
        )
        first = local[0]
        return first.home, first.away

    assert next_local("مانشستر يونايتد") == ("هال", "مانشستر يونايتد")
    assert next_local("مانشستر سيتي") == ("مانشستر سيتي", "بورنموث")
    assert next_local("أرسنال") == ("أرسنال", "كونتري")
    assert next_local("ليفربول") == ("نيوكاسل", "ليفربول")
    assert next_local("تشيلسي") == ("فولهام", "تشيلسي")
    assert next_local("برشلونة") == ("إلتشي", "برشلونة")
    assert next_local("ريال مدريد") == ("إسبانيول", "ريال مدريد")
