"""Permanent gap-fill: every tracked club stays visible when calendar has holes."""

import importlib
import os
import tempfile
from datetime import datetime

from league_season import LEAGUE_TEAMS


def _fresh():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def _clubs_in_picker(matches) -> set[str]:
    clubs: set[str] = set()
    league = set(LEAGUE_TEAMS)
    for match in matches:
        for team in (match.home_team, match.away_team):
            if team in league:
                clubs.add(team)
    return clubs


def test_every_club_visible_on_fri_nov_27():
    """Regression: only Chelsea used to appear this evening."""
    db = _fresh()
    db.seed_league_season_matches()
    now = datetime(2026, 11, 27, 18, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    clubs = _clubs_in_picker(matches)
    assert clubs == set(LEAGUE_TEAMS), f"missing clubs: {set(LEAGUE_TEAMS) - clubs}"
    pairs = {(m.home_team, m.away_team) for m in matches}
    assert ("نوتنغهام فورست", "تشيلسي") in pairs
    assert ("أرسنال", "مانشستر سيتي") in pairs
    assert ("مانشستر يونايتد", "برنتفورد") in pairs
    assert ("إيفرتون", "ليفربول") in pairs
    assert ("ريال مدريد", "ألافيس") in pairs
    assert ("ديبورتيفو", "برشلونة") in pairs


def test_gap_fill_accepts_next_match_outside_72h():
    db = _fresh()
    db.seed_league_season_matches()
    # Mid-gap date where next fixtures are >72h away for most clubs.
    now = datetime(2026, 11, 25, 12, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    assert _clubs_in_picker(matches) == set(LEAGUE_TEAMS)
    for match in matches:
        assert db.match_accepts_predictions(match, now=now)


def test_calendar_covers_every_club_beyond_horizon():
    """Fail loudly when a club has no future fixture seeded (empty picker root cause)."""
    from worldcup2026 import safe_kickoff_datetime

    db = _fresh()
    db.seed_league_season_matches()
    # Anchor: the recurring "only Chelsea" evening + a week later.
    for now in (
        datetime(2026, 11, 27, 18, 0, 0),
        datetime(2026, 12, 4, 12, 0, 0),
    ):
        for club in LEAGUE_TEAMS:
            nxt = db.next_upcoming_league_match_for_club(club, now=now)
            assert nxt is not None, f"{club} has no future fixture at {now.isoformat()}"
            kickoff = safe_kickoff_datetime(nxt.kickoff_at)
            assert kickoff is not None and kickoff > now


def test_far_secondary_fixture_still_gated_by_72h():
    """Gap-fill is only the next match — later ones stay behind 72h."""
    db = _fresh()
    db.seed_league_season_matches()
    now = datetime(2026, 11, 6, 12, 0, 0)
    # Hull is Arsenal's next (inside 72h). Newcastle is later (>72h) and not
    # next for either side, so it stays closed.
    hull = next(
        m
        for m in db.list_matches(open_only=False, limit=None)
        if m.home_team == "أرسنال" and m.away_team == "هال"
    )
    newcastle = next(
        m
        for m in db.list_matches(open_only=False, limit=None)
        if m.home_team == "نيوكاسل" and m.away_team == "أرسنال"
    )
    assert db.match_in_prediction_window(hull, now=now)
    assert db.match_accepts_predictions(hull, now=now)
    assert not db.match_in_prediction_window(newcastle, now=now)
    assert not db.match_is_next_for_tracked_club(newcastle, now=now)
    assert not db.match_accepts_predictions(newcastle, now=now)
