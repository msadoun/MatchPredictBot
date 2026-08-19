"""Seven-club league season fixtures (single round-robin)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from worldcup2026 import kickoff_datetime

LEAGUE_SEASON_LABEL = "دوري الأبطال 2026"

LEAGUE_TEAMS: tuple[str, ...] = (
    "ريال مدريد",
    "برشلونة",
    "مانشستر يونايتد",
    "مانشستر سيتي",
    "ليفربول",
    "أرسنال",
    "تشيلسي",
)

# First match-day (UTC calendar date for round 1).
SEASON_START_DATE = date(2026, 8, 23)
DAYS_BETWEEN_ROUNDS = 3
ROUND_KICKOFFS_UTC = ("17:00:00", "19:30:00", "22:00:00")


@dataclass(frozen=True)
class LeagueFixture:
    home: str
    away: str
    date: str
    group: str
    kickoff_utc: str = ""


def _round_robin_pairings(teams: tuple[str, ...]) -> list[list[tuple[str, str]]]:
    """Circle method; odd team count uses a bye each round."""
    roster = list(teams)
    if len(roster) % 2:
        roster.append("")
    n = len(roster)
    rounds = n - 1
    rotation = roster[:]
    all_rounds: list[list[tuple[str, str]]] = []
    for _ in range(rounds):
        pairs: list[tuple[str, str]] = []
        for i in range(n // 2):
            home, away = rotation[i], rotation[n - 1 - i]
            if home and away:
                pairs.append((home, away))
        all_rounds.append(pairs)
        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
    return all_rounds


def _build_fixtures() -> list[LeagueFixture]:
    fixtures: list[LeagueFixture] = []
    for round_idx, pairs in enumerate(_round_robin_pairings(LEAGUE_TEAMS), start=1):
        round_day = SEASON_START_DATE + timedelta(days=(round_idx - 1) * DAYS_BETWEEN_ROUNDS)
        round_label = f"الجولة {round_idx}"
        for match_idx, (home, away) in enumerate(pairs):
            kickoff_time = ROUND_KICKOFFS_UTC[match_idx % len(ROUND_KICKOFFS_UTC)]
            kickoff_utc = f"{round_day.isoformat()}T{kickoff_time}"
            fixtures.append(
                LeagueFixture(
                    home=home,
                    away=away,
                    date=round_day.isoformat(),
                    group=round_label,
                    kickoff_utc=kickoff_utc,
                )
            )
    return fixtures


LEAGUE_SEASON_FIXTURES: list[LeagueFixture] = _build_fixtures()


def league_kickoff_label(fixture: LeagueFixture) -> str:
    return f"{fixture.kickoff_utc} · {fixture.group}"


def league_kickoff_datetime(kickoff_at: str) -> datetime:
    return kickoff_datetime(kickoff_at)


def ordered_league_rounds() -> list[str]:
    seen: set[str] = set()
    rounds: list[str] = []
    for fixture in LEAGUE_SEASON_FIXTURES:
        if fixture.group not in seen:
            seen.add(fixture.group)
            rounds.append(fixture.group)
    return rounds
