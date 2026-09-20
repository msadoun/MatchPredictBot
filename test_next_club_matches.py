"""Next open match per club: UCL included, head-to-heads not duplicated."""

import importlib
import os
import tempfile
from datetime import datetime, timedelta


def _fresh_db():
    path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_PATH"] = path
    import config
    import database as db

    importlib.reload(config)
    importlib.reload(db)
    db.init_db()
    return db


def test_seeded_picker_includes_ucl_when_it_is_next():
    """If a club's soonest future fixture is UCL and inside 72h, picker shows it."""
    from league_season import (
        CHAMPIONS_LEAGUE_LABEL,
        LEAGUE_TEAMS,
        fixtures_for_club,
        league_kickoff_datetime,
    )

    db = _fresh_db()
    db.seed_league_season_matches()
    now = datetime(2026, 9, 17, 12, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    assert matches, "expected open fixtures inside the 72h window"

    from datetime import timedelta

    clubs_with_ucl_next = []
    for club in LEAGUE_TEAMS:
        future = sorted(
            (
                f
                for f in fixtures_for_club(club)
                if league_kickoff_datetime(f"{f.kickoff_utc} · {f.group}") > now
            ),
            key=lambda f: f.kickoff_utc,
        )
        if (
            future
            and CHAMPIONS_LEAGUE_LABEL in future[0].group
            and league_kickoff_datetime(f"{future[0].kickoff_utc} · {future[0].group}")
            <= now + timedelta(hours=72)
        ):
            clubs_with_ucl_next.append(club)

    if clubs_with_ucl_next:
        ucl = [m for m in matches if CHAMPIONS_LEAGUE_LABEL in (m.kickoff_at or "")]
        assert ucl, "Champions League matches must appear when they are next"
        for match in ucl:
            assert db.match_accepts_predictions(match, now=now)
    else:
        # Mid-season window: next kickoffs are domestic; still seed future UCL rows.
        with db.get_db() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM matches
                WHERE kickoff_at LIKE ? AND is_open = 1
                """,
                (f"%{CHAMPIONS_LEAGUE_LABEL}%",),
            ).fetchone()
        assert row["n"] > 0, "future UCL fixtures must remain seeded and open"


def test_head_to_head_between_tracked_clubs_listed_once():
    db = _fresh_db()
    db.seed_league_season_matches()
    now = datetime(2026, 9, 17, 12, 0, 0)
    matches = db.list_next_open_match_per_league_club(now=now)
    ids = [m.id for m in matches]
    assert len(ids) == len(set(ids))

    derby = [
        m
        for m in matches
        if {m.home_team, m.away_team} == {"أرسنال", "تشيلسي"}
    ]
    assert len(derby) <= 1
