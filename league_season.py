"""Seven-club season: domestic league + Champions League fixtures."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import combinations

from worldcup2026 import kickoff_datetime

LEAGUE_SEASON_LABEL = "موسم 2026"

LA_LIGA_TEAMS: tuple[str, ...] = (
    "ريال مدريد",
    "برشلونة",
)

PREMIER_LEAGUE_TEAMS: tuple[str, ...] = (
    "مانشستر يونايتد",
    "مانشستر سيتي",
    "ليفربول",
    "أرسنال",
    "تشيلسي",
)

LEAGUE_TEAMS: tuple[str, ...] = LA_LIGA_TEAMS + PREMIER_LEAGUE_TEAMS

LOCAL_LA_LIGA_LABEL = "الدوري الإسباني"
LOCAL_PL_LABEL = "الدوري الإنجليزي"
CHAMPIONS_LEAGUE_LABEL = "دوري أبطال أوروبا"

SEASON_START_DATE = date(2026, 8, 23)
DAYS_BETWEEN_MATCHDAYS = 3
MATCHDAY_KICKOFFS_UTC = ("17:00:00", "19:30:00", "22:00:00")


@dataclass(frozen=True)
class LeagueFixture:
    home: str
    away: str
    date: str
    group: str
    kickoff_utc: str = ""


def _ordered_pairs(teams: tuple[str, ...]) -> list[tuple[str, str]]:
    return list(combinations(teams, 2))


def _cross_league_pairs(
    domestic_a: tuple[str, ...],
    domestic_b: tuple[str, ...],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for home in domestic_a:
        for away in domestic_b:
            pairs.append((home, away))
    return pairs


def _assign_schedule(
    labeled_pairs: list[tuple[str, str, str]],
    *,
    start: date,
) -> list[LeagueFixture]:
    """Spread fixtures across matchdays; `group` is the competition label."""
    fixtures: list[LeagueFixture] = []
    matchday = 0
    slot = 0
    current_day = start
    for home, away, competition in labeled_pairs:
        if slot == 0 and fixtures:
            matchday += 1
            current_day = start + timedelta(days=matchday * DAYS_BETWEEN_MATCHDAYS)
        kickoff_time = MATCHDAY_KICKOFFS_UTC[slot % len(MATCHDAY_KICKOFFS_UTC)]
        kickoff_utc = f"{current_day.isoformat()}T{kickoff_time}"
        fixtures.append(
            LeagueFixture(
                home=home,
                away=away,
                date=current_day.isoformat(),
                group=competition,
                kickoff_utc=kickoff_utc,
            )
        )
        slot += 1
        if slot % len(MATCHDAY_KICKOFFS_UTC) == 0:
            matchday += 1
            current_day = start + timedelta(days=matchday * DAYS_BETWEEN_MATCHDAYS)
            slot = 0
    return fixtures


def _build_fixtures() -> list[LeagueFixture]:
    labeled: list[tuple[str, str, str]] = []

    for home, away in _ordered_pairs(LA_LIGA_TEAMS):
        labeled.append((home, away, LOCAL_LA_LIGA_LABEL))

    for home, away in _ordered_pairs(PREMIER_LEAGUE_TEAMS):
        labeled.append((home, away, LOCAL_PL_LABEL))

    for home, away in _cross_league_pairs(LA_LIGA_TEAMS, PREMIER_LEAGUE_TEAMS):
        labeled.append((home, away, CHAMPIONS_LEAGUE_LABEL))

    return _assign_schedule(labeled, start=SEASON_START_DATE)


LEAGUE_SEASON_FIXTURES: list[LeagueFixture] = _build_fixtures()

LOCAL_LEAGUE_FIXTURES = [
    f for f in LEAGUE_SEASON_FIXTURES if f.group in (LOCAL_LA_LIGA_LABEL, LOCAL_PL_LABEL)
]
CHAMPIONS_LEAGUE_FIXTURES = [
    f for f in LEAGUE_SEASON_FIXTURES if f.group == CHAMPIONS_LEAGUE_LABEL
]


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
