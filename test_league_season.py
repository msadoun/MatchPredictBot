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


def test_real_madrid_next_local_is_rayo():
    """MD5 window: Real Madrid host Rayo on Sat 12 Sep 2026, 21:00 CEST."""
    rm_local = [
        f
        for f in fixtures_for_club("ريال مدريد")
        if LOCAL_LA_LIGA_LABEL in f.group
    ]
    first = min(rm_local, key=lambda f: f.kickoff_utc)
    assert first.home == "ريال مدريد"
    assert first.away == "رايو فاليكانو"
    assert first.kickoff_utc == "2026-09-12T19:00:00"


def test_season_starts_in_september_2026():
    """Sliding window starts at UCL MD1 / La Liga MD5 (mid-Sep 2026)."""
    assert LEAGUE_SEASON_FIXTURES[0].kickoff_utc.startswith("2026-09")


def test_next_local_fixtures_mid_september_window():
    """Next domestic matches after mid-Sep 2026 (PL GW5 / La Liga MD5)."""
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

    assert next_local("مانشستر يونايتد") == ("فولهام", "مانشستر يونايتد")
    assert next_local("مانشستر سيتي") == ("مانشستر سيتي", "ساندرلاند")
    assert next_local("أرسنال") == ("برايتون", "أرسنال")
    assert next_local("ليفربول") == ("بورنموث", "ليفربول")
    assert next_local("تشيلسي") == ("برنتفورد", "تشيلسي")
    assert next_local("برشلونة") == ("ليفانتي", "برشلونة")
    assert next_local("ريال مدريد") == ("ريال مدريد", "رايو فاليكانو")


def test_barcelona_levante_jornada_5_official_date():
    """La Liga lists Levante vs Barça on Sun 13 Sep 2026, 16:15 CEST."""
    local = [
        f
        for f in fixtures_for_club("برشلونة")
        if LOCAL_LA_LIGA_LABEL in f.group
        and f.home == "ليفانتي"
        and f.away == "برشلونة"
    ]
    assert len(local) == 1
    assert local[0].kickoff_utc == "2026-09-13T14:15:00"


def test_real_madrid_barcelona_md5_to_md9_opponents():
    """Official La Liga MD5–9 opponents for Real Madrid and Barcelona."""
    def local_pairs(club: str) -> list[tuple[str, str, str]]:
        local = sorted(
            (
                f
                for f in fixtures_for_club(club)
                if LOCAL_LA_LIGA_LABEL in f.group
            ),
            key=lambda f: f.kickoff_utc,
        )
        return [(f.home, f.away, f.kickoff_utc) for f in local]

    assert local_pairs("ريال مدريد") == [
        ("ريال مدريد", "رايو فاليكانو", "2026-09-12T19:00:00"),
        ("إلتشي", "ريال مدريد", "2026-09-15T19:30:00"),
        ("أتلتيكو مدريد", "ريال مدريد", "2026-09-20T14:15:00"),
        ("ريال مدريد", "فياريال", "2026-10-10T19:00:00"),
        ("ريال مدريد", "إشبيلية", "2026-10-18T19:00:00"),
    ]
    assert local_pairs("برشلونة") == [
        ("ليفانتي", "برشلونة", "2026-09-13T14:15:00"),
        ("برشلونة", "راسينغ سانتاندر", "2026-09-16T19:30:00"),
        ("إشبيلية", "برشلونة", "2026-09-19T19:00:00"),
        ("برشلونة", "خيتافي", "2026-10-10T16:30:00"),
        ("ريال بيتيس", "برشلونة", "2026-10-18T19:00:00"),
    ]


def test_premier_league_gw5_window_opponents():
    """Official PL GW5+ window (Sports Mole TV schedule, mid-Sep 2026)."""
    def local_pairs(club: str) -> list[tuple[str, str, str]]:
        local = sorted(
            (
                f
                for f in fixtures_for_club(club)
                if LOCAL_PL_LABEL in f.group
            ),
            key=lambda f: f.kickoff_utc,
        )
        return [(f.home, f.away, f.kickoff_utc) for f in local]

    assert local_pairs("أرسنال") == [
        ("برايتون", "أرسنال", "2026-09-19T14:00:00"),
        ("أرسنال", "ليدز يونايتد", "2026-10-10T11:30:00"),
        ("نوتنغهام فورست", "أرسنال", "2026-10-18T15:30:00"),
        ("أرسنال", "إيفرتون", "2026-10-24T14:00:00"),
        ("ليفربول", "أرسنال", "2026-11-01T16:30:00"),
    ]
    assert local_pairs("مانشستر يونايتد")[:5] == [
        ("فولهام", "مانشستر يونايتد", "2026-09-20T15:30:00"),
        ("مانشستر يونايتد", "توتنهام", "2026-10-10T16:30:00"),
        ("ليدز يونايتد", "مانشستر يونايتد", "2026-10-18T13:00:00"),
        ("مانشستر يونايتد", "بورنموث", "2026-10-25T14:00:00"),
        ("تشيلسي", "مانشستر يونايتد", "2026-10-31T12:30:00"),
    ]
    assert local_pairs("مانشستر سيتي") == [
        ("مانشستر سيتي", "ساندرلاند", "2026-09-20T13:00:00"),
        ("ليفربول", "مانشستر سيتي", "2026-10-11T15:30:00"),
        ("مانشستر سيتي", "إبسويتش", "2026-10-17T14:00:00"),
        ("أستون فيلا", "مانشستر سيتي", "2026-10-24T11:30:00"),
        ("مانشستر سيتي", "برايتون", "2026-10-31T15:00:00"),
    ]
    assert local_pairs("ليفربول") == [
        ("بورنموث", "ليفربول", "2026-09-20T13:00:00"),
        ("ليفربول", "مانشستر سيتي", "2026-10-11T15:30:00"),
        ("برنتفورد", "ليفربول", "2026-10-17T14:00:00"),
        ("ليفربول", "برايتون", "2026-10-25T14:00:00"),
        ("ليفربول", "أرسنال", "2026-11-01T16:30:00"),
    ]
    che = local_pairs("تشيلسي")
    assert len(che) == 10
    assert che[0] == ("برنتفورد", "تشيلسي", "2026-09-18T19:00:00")
    assert che[5] == ("ساندرلاند", "تشيلسي", "2026-11-07T15:00:00")
    assert che[9] == ("مانشستر سيتي", "تشيلسي", "2026-12-12T15:00:00")


def test_ucl_md1_official_2026_27_draw():
    """League phase MD1 from UEFA draw (27 Aug 2026)."""
    label = CHAMPIONS_LEAGUE_LABEL

    def first_ucl(club: str) -> tuple[str, str]:
        cl = sorted(
            (f for f in fixtures_for_club(club) if label in f.group),
            key=lambda f: f.kickoff_utc,
        )
        first = cl[0]
        return first.home, first.away

    assert first_ucl("ريال مدريد") == ("ريال مدريد", "إنتر ميلان")
    assert first_ucl("مانشستر سيتي") == ("بورتو", "مانشستر سيتي")
    assert first_ucl("برشلونة") == ("برشلونة", "فينوورد")
    assert first_ucl("أرسنال") == ("نابولي", "أرسنال")
    assert first_ucl("ليفربول") == ("ليفربول", "أتلتيكو مدريد")
    assert first_ucl("مانشستر يونايتد") == ("مانشستر يونايتد", "صباح")
