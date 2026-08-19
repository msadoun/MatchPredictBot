"""Generate league_season.py with stable Arabic team names."""
from __future__ import annotations

import textwrap
from pathlib import Path

TEAMS = {
    "RM": "\u0631\u064a\u0627\u0644 \u0645\u062f\u0631\u064a\u062f",
    "BAR": "\u0628\u0631\u0634\u0644\u0648\u0646\u0629",
    "MU": "\u0645\u0627\u0646\u0634\u0633\u062a\u0631 \u064a\u0648\u0646\u0627\u064a\u062a\u062f",
    "MC": "\u0645\u0627\u0646\u0634\u0633\u062a\u0631 \u0633\u064a\u062a\u064a",
    "LIV": "\u0644\u064a\u0641\u0631\u0628\u0648\u0644",
    "ARS": "\u0623\u0631\u0633\u0646\u0627\u0644",
    "CHE": "\u062a\u0634\u064a\u0644\u0633\u064a",
}
OPP = {
    "ATM": "\u0623\u062a\u0644\u062a\u064a\u0643\u0648 \u0645\u062f\u0631\u064a\u062f",
    "SEV": "\u0625\u0634\u0628\u064a\u0644\u064a\u0629",
    "VAL": "\u0641\u0627\u0644\u0646\u0633\u064a\u0627",
    "RSO": "\u0631\u064a\u0627\u0644 \u0633\u0648\u0633\u064a\u062f\u0627\u062f",
    "VIL": "\u0641\u064a\u0627\u0631\u064a\u0627\u0644",
    "ATH": "\u0623\u062a\u0644\u062a\u064a\u0643 \u0628\u064a\u0644\u0628\u0627\u0648",
    "BET": "\u0631\u064a\u0627\u0644 \u0628\u064a\u062a\u064a\u0633",
    "GIR": "\u062c\u064a\u0631\u0648\u0646\u0627",
    "TOT": "\u062a\u0648\u062a\u0646\u0647\u0627\u0645",
    "NEW": "\u0646\u064a\u0648\u0643\u0627\u0633\u0644",
    "AVL": "\u0623\u0633\u062a\u0648\u0646 \u0641\u064a\u0644\u0627",
    "WHU": "\u0648\u064a\u0633\u062a \u0647\u0627\u0645",
    "EVE": "\u0625\u064a\u0641\u0631\u062a\u0648\u0646",
    "BHA": "\u0628\u0631\u0627\u064a\u062a\u0648\u0646",
    "CRY": "\u0643\u0631\u064a\u0633\u062a\u0627\u0644 \u0628\u0627\u0644\u0627\u0633",
    "WOL": "\u0648\u0644\u0641\u0631\u0647\u0627\u0645\u0628\u062a\u0648\u0646",
    "BOU": "\u0628\u0648\u0631\u0646\u0645\u0648\u062b",
    "FUL": "\u0641\u0648\u0644\u0647\u0627\u0645",
    "BAY": "\u0628\u0627\u064a\u0631\u0646 \u0645\u064a\u0648\u0646\u062e",
    "PSG": "\u0628\u0627\u0631\u064a\u0633 \u0633\u0627\u0646 \u062c\u064a\u0631\u0645\u0627\u0646",
    "JUV": "\u064a\u0648\u0641\u0646\u062a\u0648\u0633",
    "INT": "\u0625\u0646\u062a\u0631 \u0645\u064a\u0644\u0627\u0646",
    "BVB": "\u0628\u0648\u0631\u0648\u0633\u064a\u0627 \u062f\u0648\u0631\u062a\u0645\u0648\u0646\u062f",
    "NAP": "\u0646\u0627\u0628\u0648\u0644\u064a",
    "BEN": "\u0628\u0646\u0641\u064a\u0643\u0627",
    "POR": "\u0628\u0648\u0631\u062a\u0648",
    "AJA": "\u0623\u064a\u0627\u0643\u0633",
    "CEL": "\u0633\u0644\u062a\u064a\u0643",
    "LEV": "\u0628\u0627\u064a\u0644 \u0644\u064a\u0641\u0631\u0643\u0648\u0632\u0646",
    "ATA": "\u0623\u062a\u0644\u0646\u062a\u0627",
    "SPO": "\u0633\u0628\u0648\u0631\u062a\u0646\u062c \u0644\u064a\u0634\u0628\u0648\u0646\u0629",
    "FEY": "\u0641\u064a\u0646\u0648\u0648\u0631\u062f",
    "SAL": "\u0633\u0627\u0644\u0632\u0628\u0648\u0631\u062c",
    "MIL": "\u0645\u064a\u0644\u0627\u0646",
    "LAZ": "\u0644\u0627\u062a\u0633\u064a\u0648",
}

LOCAL = {
    TEAMS["RM"]: [(OPP["ATM"], True), (OPP["SEV"], False), (OPP["VAL"], True), (OPP["RSO"], False), (OPP["VIL"], True)],
    TEAMS["BAR"]: [(OPP["ATH"], True), (OPP["BET"], False), (OPP["GIR"], True), (OPP["ATM"], False), (OPP["SEV"], True)],
    TEAMS["MU"]: [(OPP["TOT"], True), (OPP["NEW"], False), (OPP["AVL"], True), (OPP["WHU"], False), (OPP["EVE"], True)],
    TEAMS["MC"]: [(OPP["BHA"], True), (OPP["CRY"], False), (OPP["WOL"], True), (OPP["BOU"], False), (OPP["FUL"], True)],
    TEAMS["LIV"]: [(OPP["NEW"], False), (OPP["WHU"], True), (OPP["BHA"], False), (OPP["AVL"], True), (OPP["EVE"], False)],
    TEAMS["ARS"]: [(OPP["TOT"], False), (OPP["CRY"], True), (OPP["WOL"], False), (OPP["FUL"], True), (OPP["BOU"], False)],
    TEAMS["CHE"]: [(OPP["NEW"], True), (OPP["BHA"], False), (OPP["AVL"], False), (OPP["EVE"], True), (OPP["FUL"], False)],
}
CL = {
    TEAMS["RM"]: [(OPP["BAY"], True), (OPP["PSG"], False), (OPP["JUV"], True), (OPP["INT"], False), (OPP["BVB"], True)],
    TEAMS["BAR"]: [(OPP["NAP"], True), (OPP["BEN"], False), (OPP["POR"], True), (OPP["AJA"], False), (OPP["CEL"], True)],
    TEAMS["MU"]: [(OPP["LEV"], True), (OPP["ATA"], False), (OPP["SPO"], True), (OPP["FEY"], False), (OPP["SAL"], True)],
    TEAMS["MC"]: [(OPP["BAY"], False), (OPP["MIL"], True), (OPP["BEN"], False), (OPP["NAP"], True), (OPP["BVB"], False)],
    TEAMS["LIV"]: [(OPP["PSG"], True), (OPP["INT"], False), (OPP["POR"], False), (OPP["AJA"], True), (OPP["LAZ"], False)],
    TEAMS["ARS"]: [(OPP["BVB"], True), (OPP["JUV"], False), (OPP["SPO"], False), (OPP["CEL"], False), (OPP["ATA"], True)],
    TEAMS["CHE"]: [(OPP["NAP"], False), (OPP["MIL"], False), (OPP["FEY"], True), (OPP["SAL"], False), (OPP["LEV"], True)],
}


def fmt_dict(mapping: dict[str, tuple[tuple[str, bool], ...]]) -> str:
    lines = ["{"]
    for club, matches in mapping.items():
        lines.append(f"    {club!r}: (")
        for opponent, home in matches:
            lines.append(f"        ({opponent!r}, {home!r}),")
        lines.append("    ),")
    lines.append("}")
    return "\n".join(lines)


BODY = textwrap.dedent(
    '''
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
    '''
).strip("\n")


def main() -> None:
    header = f'''"""Seven-club season: each club\'s own local + Champions League fixtures."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from worldcup2026 import kickoff_datetime

LEAGUE_SEASON_LABEL = "موسم 2026"

LA_LIGA_TEAMS: tuple[str, ...] = (
    {TEAMS["RM"]!r},
    {TEAMS["BAR"]!r},
)

PREMIER_LEAGUE_TEAMS: tuple[str, ...] = (
    {TEAMS["MU"]!r},
    {TEAMS["MC"]!r},
    {TEAMS["LIV"]!r},
    {TEAMS["ARS"]!r},
    {TEAMS["CHE"]!r},
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

CLUB_LOCAL_MATCHES: dict[str, tuple[tuple[str, bool], ...]] = {fmt_dict(LOCAL)}

CLUB_CHAMPIONS_LEAGUE_MATCHES: dict[str, tuple[tuple[str, bool], ...]] = {fmt_dict(CL)}

{BODY}
'''
    Path(__file__).resolve().parents[1].joinpath("league_season.py").write_text(
        header, encoding="utf-8"
    )


if __name__ == "__main__":
    main()
