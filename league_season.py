"""Seven-club season: each club's own local + Champions League fixtures."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from worldcup2026 import kickoff_datetime

LEAGUE_SEASON_LABEL = "موسم 2026"

LA_LIGA_TEAMS: tuple[str, ...] = (
    'ريال مدريد',
    'برشلونة',
)

PREMIER_LEAGUE_TEAMS: tuple[str, ...] = (
    'مانشستر يونايتد',
    'مانشستر سيتي',
    'ليفربول',
    'أرسنال',
    'تشيلسي',
)

LEAGUE_TEAMS: tuple[str, ...] = LA_LIGA_TEAMS + PREMIER_LEAGUE_TEAMS

LOCAL_LA_LIGA_LABEL = "الدوري الإسباني"
LOCAL_PL_LABEL = "الدوري الإنجليزي"
CHAMPIONS_LEAGUE_LABEL = "دوري أبطال أوروبا"

MATCHES_PER_CLUB = 10
LOCAL_MATCHES_PER_CLUB = 5
CL_MATCHES_PER_CLUB = 5

SEASON_START_DATE = date(2026, 8, 23)
DAYS_BETWEEN_MATCHDAYS = 2
MATCHDAY_KICKOFFS_UTC = ("17:00:00", "19:30:00", "22:00:00")

CLUB_LOCAL_MATCHES: dict[str, tuple[tuple[str, bool], ...]] = {
    'ريال مدريد': (
        ('أتلتيكو مدريد', True),
        ('إشبيلية', False),
        ('فالنسيا', True),
        ('ريال سوسيداد', False),
        ('فياريال', True),
    ),
    'برشلونة': (
        ('أتلتيك بيلباو', True),
        ('ريال بيتيس', False),
        ('جيرونا', True),
        ('أتلتيكو مدريد', False),
        ('إشبيلية', True),
    ),
    'مانشستر يونايتد': (
        ('توتنهام', True),
        ('نيوكاسل', False),
        ('أستون فيلا', True),
        ('ويست هام', False),
        ('إيفرتون', True),
    ),
    'مانشستر سيتي': (
        ('برايتون', True),
        ('كريستال بالاس', False),
        ('ولفرهامبتون', True),
        ('بورنموث', False),
        ('فولهام', True),
    ),
    'ليفربول': (
        ('نيوكاسل', False),
        ('ويست هام', True),
        ('برايتون', False),
        ('أستون فيلا', True),
        ('إيفرتون', False),
    ),
    'أرسنال': (
        ('توتنهام', False),
        ('كريستال بالاس', True),
        ('ولفرهامبتون', False),
        ('فولهام', True),
        ('بورنموث', False),
    ),
    'تشيلسي': (
        ('نيوكاسل', True),
        ('برايتون', False),
        ('أستون فيلا', False),
        ('إيفرتون', True),
        ('فولهام', False),
    ),
}

CLUB_CHAMPIONS_LEAGUE_MATCHES: dict[str, tuple[tuple[str, bool], ...]] = {
    'ريال مدريد': (
        ('بايرن ميونخ', True),
        ('باريس سان جيرمان', False),
        ('يوفنتوس', True),
        ('إنتر ميلان', False),
        ('بوروسيا دورتموند', True),
    ),
    'برشلونة': (
        ('نابولي', True),
        ('بنفيكا', False),
        ('بورتو', True),
        ('أياكس', False),
        ('سلتيك', True),
    ),
    'مانشستر يونايتد': (
        ('بايل ليفركوزن', True),
        ('أتلنتا', False),
        ('سبورتنج ليشبونة', True),
        ('فينوورد', False),
        ('سالزبورج', True),
    ),
    'مانشستر سيتي': (
        ('بايرن ميونخ', False),
        ('ميلان', True),
        ('بنفيكا', False),
        ('نابولي', True),
        ('بوروسيا دورتموند', False),
    ),
    'ليفربول': (
        ('باريس سان جيرمان', True),
        ('إنتر ميلان', False),
        ('بورتو', False),
        ('أياكس', True),
        ('لاتسيو', False),
    ),
    'أرسنال': (
        ('بوروسيا دورتموند', True),
        ('يوفنتوس', False),
        ('سبورتنج ليشبونة', False),
        ('سلتيك', False),
        ('أتلنتا', True),
    ),
    'تشيلسي': (
        ('نابولي', False),
        ('ميلان', False),
        ('فينوورد', True),
        ('سالزبورج', False),
        ('بايل ليفركوزن', True),
    ),
}

@dataclass(frozen=True)
class LeagueFixture:
    home: str
    away: str
    date: str
    group: str
    kickoff_utc: str = ""
    club: str = ""


def _local_label(club: str) -> str:
    return LOCAL_LA_LIGA_LABEL if club in LA_LIGA_TEAMS else LOCAL_PL_LABEL


def _fixture_triples() -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for club, matches in CLUB_LOCAL_MATCHES.items():
        for opponent, club_home in matches:
            home = club if club_home else opponent
            away = opponent if club_home else club
            rows.append((home, away, _local_label(club), club))
    for club, matches in CLUB_CHAMPIONS_LEAGUE_MATCHES.items():
        for opponent, club_home in matches:
            home = club if club_home else opponent
            away = opponent if club_home else club
            rows.append((home, away, CHAMPIONS_LEAGUE_LABEL, club))
    return rows


def _assign_schedule(
    rows: list[tuple[str, str, str, str]],
    *,
    start: date,
) -> list[LeagueFixture]:
    fixtures: list[LeagueFixture] = []
    matchday = 0
    slot = 0
    current_day = start
    for home, away, competition, club in rows:
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
                club=club,
            )
        )
        slot += 1
        if slot % len(MATCHDAY_KICKOFFS_UTC) == 0:
            matchday += 1
            current_day = start + timedelta(days=matchday * DAYS_BETWEEN_MATCHDAYS)
            slot = 0
    return fixtures


def _build_fixtures() -> list[LeagueFixture]:
    return _assign_schedule(_fixture_triples(), start=SEASON_START_DATE)


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


def fixtures_for_club(club: str) -> list[LeagueFixture]:
    return [f for f in LEAGUE_SEASON_FIXTURES if f.club == club]


def ordered_league_rounds() -> list[str]:
    seen: set[str] = set()
    rounds: list[str] = []
    for fixture in LEAGUE_SEASON_FIXTURES:
        if fixture.group not in seen:
            seen.add(fixture.group)
            rounds.append(fixture.group)
    return rounds
