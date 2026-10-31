"""La Liga MD11: Barcelona–Alavés (31 Oct) and Racing–Real Madrid (1 Nov)."""

from league_season import fixtures_for_club, LOCAL_LA_LIGA_LABEL


def test_barcelona_alaves_md11_today():
    local = [
        f
        for f in fixtures_for_club("برشلونة")
        if LOCAL_LA_LIGA_LABEL in f.group and f.away == "ألافيس"
    ]
    assert len(local) == 1
    assert local[0].home == "برشلونة"
    assert local[0].kickoff_utc == "2026-10-31T20:00:00"
    assert "الجولة 11" in local[0].group


def test_racing_real_madrid_md11_tomorrow():
    local = [
        f
        for f in fixtures_for_club("ريال مدريد")
        if LOCAL_LA_LIGA_LABEL in f.group and f.home == "راسينغ سانتاندر"
    ]
    assert len(local) == 1
    assert local[0].away == "ريال مدريد"
    assert local[0].kickoff_utc == "2026-11-01T14:15:00"
    assert "الجولة 11" in local[0].group
