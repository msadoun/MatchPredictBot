"""Generate league_season.py from 2026/27 La Liga, PL, and UCL calendars."""
from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path


def kickoff(iso_date: str, time_utc: str) -> str:
    return f"{iso_date}T{time_utc}"


TEAMS = {
    "RM": "\u0631\u064a\u0627\u0644 \u0645\u062f\u0631\u064a\u062f",
    "BAR": "\u0628\u0631\u0634\u0644\u0648\u0646\u0629",
    "MU": "\u0645\u0627\u0646\u0634\u0633\u062a\u0631 \u064a\u0648\u0646\u0627\u064a\u062a\u062f",
    "MC": "\u0645\u0627\u0646\u0634\u0633\u062a\u0631 \u0633\u064a\u062a\u064a",
    "LIV": "\u0644\u064a\u0641\u0631\u0628\u0648\u0644",
    "ARS": "\u0623\u0631\u0633\u0646\u0627\u0644",
    "CHE": "\u062a\u0634\u064a\u0644\u0633\u064a",
}

O = {
    "ATH": "\u0623\u062a\u0644\u062a\u064a\u0643 \u0628\u064a\u0644\u0628\u0627\u0648",
    "BET": "\u0631\u064a\u0627\u0644 \u0628\u064a\u062a\u064a\u0633",
    "BOU": "\u0628\u0648\u0631\u0646\u0645\u0648\u062b",
    "BRE": "\u0628\u0631\u0646\u062a\u0641\u0648\u0631\u062f",
    "BHA": "\u0628\u0631\u0627\u064a\u062a\u0648\u0646",
    "COV": "\u0643\u0648\u0646\u062a\u0631\u064a",
    "CRY": "\u0643\u0631\u064a\u0633\u062a\u0627\u0644 \u0628\u0627\u0644\u0627\u0633",
    "EVE": "\u0625\u064a\u0641\u0631\u062a\u0648\u0646",
    "ELC": "\u0625\u0644\u062a\u0634\u064a",
    "ESP": "\u0625\u0633\u0628\u0627\u0646\u064a\u0648\u0644",
    "FUL": "\u0641\u0648\u0644\u0647\u0627\u0645",
    "HUL": "\u0647\u0627\u0644",
    "IPS": "\u0625\u0628\u0633\u0648\u064a\u062a\u0634",
    "LEV": "\u0644\u064a\u0641\u0627\u0646\u062a\u064a",
    "MAL": "\u0645\u0627\u0644\u0627\u0642\u0627",
    "NEW": "\u0646\u064a\u0648\u0643\u0627\u0633\u0644",
    "NFO": "\u0646\u0648\u062a\u0646\u063a\u0647\u0627\u0645 \u0641\u0648\u0631\u0633\u062a",
    "RAY": "\u0631\u0627\u064a\u0648 \u0641\u0627\u0644\u064a\u0643\u0627\u0646\u0648",
    "RSO": "\u0631\u064a\u0627\u0644 \u0633\u0648\u0633\u064a\u062f\u0627\u062f",
    "SUN": "\u0633\u0627\u0646\u062f\u0631\u0644\u0627\u0646\u062f",
    "TOT": "\u062a\u0648\u062a\u0646\u0647\u0627\u0645",
    "VAL": "\u0641\u0627\u0644\u0646\u0633\u064a\u0627",
    "AVL": "\u0623\u0633\u062a\u0648\u0646 \u0641\u064a\u0644\u0627",
    # UCL opponents (2026/27 qualified teams — pairings provisional until league draw)
    "ATM": "\u0623\u062a\u0644\u062a\u064a\u0643\u0648 \u0645\u062f\u0631\u064a\u062f",
    "BAY": "\u0628\u0627\u064a\u0631\u0646 \u0645\u064a\u0648\u0646\u062e",
    "BRU": "\u0643\u0644\u0648\u0628 \u0628\u0631\u0648\u062c",
    "COM": "\u0643\u0648\u0645\u0648",
    "DOR": "\u0628\u0648\u0631\u0648\u0633\u064a\u0627 \u062f\u0648\u0631\u062a\u0645\u0648\u0646\u062f",
    "FEY": "\u0641\u064a\u0646\u0648\u0648\u0631\u062f",
    "GAL": "\u063a\u0644\u0637\u0629 \u0633\u0631\u0627\u064a",
    "INT": "\u0625\u0646\u062a\u0631 \u0645\u064a\u0644\u0627\u0646",
    "LIL": "\u0644\u064a\u0644",
    "NAP": "\u0646\u0627\u0628\u0648\u0644\u064a",
    "PSG": "\u0628\u0627\u0631\u064a\u0633 \u0633\u0627\u0646 \u062c\u064a\u0631\u0645\u0627\u0646",
    "PSV": "\u0628\u064a \u0625\u0633 \u0641\u064a",
    "ROM": "\u0622\u0633 \u0631\u0648\u0645\u0627",
    "SHA": "\u0634\u0627\u062e\u062a\u0627\u0631 \u062f\u0648\u0646\u064a\u062a\u0633\u0643",
    "SPO": "\u0633\u0628\u0648\u0631\u062a\u0646\u063a \u0644\u0634\u0628\u0648\u0646\u0629",
    "SLA": "\u0633\u0644\u0627\u0641\u064a\u0627 \u0628\u0631\u0627\u062c",
    "VIL": "\u0641\u064a\u0627\u0631\u064a\u0627\u0644",
}


def m(club: str, home: str, away: str, kickoff_at: str, md: int, comp: str) -> tuple:
    if comp == "laliga":
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u0627\u0644\u062f\u0648\u0631\u064a \u0627\u0644\u0625\u0633\u0628\u0627\u0646\u064a"
    elif comp == "pl":
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u0627\u0644\u062f\u0648\u0631\u064a \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a"
    else:
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u062f\u0648\u0631\u064a \u0623\u0628\u0637\u0627\u0644 \u0623\u0648\u0631\u0648\u0628\u0627"
    return (club, home, away, kickoff_at, group)


# (club_code, home, away, kickoff_utc, group) — 2026/27 official domestic calendars.
# UCL dates from UEFA; opponents from qualified-team pool until the 27 Aug 2026 draw.
FIXTURES: list[tuple[str, str, str, str, str]] = [
    # La Liga — Real Madrid (RFEF / realmadrid.com)
    m("RM", O["ESP"], TEAMS["RM"], kickoff("2026-08-22", "19:30:00"), 2, "laliga"),
    m("RM", TEAMS["RM"], O["RSO"], kickoff("2026-08-26", "19:00:00"), 1, "laliga"),
    m("RM", TEAMS["RM"], O["MAL"], kickoff("2026-08-30", "15:00:00"), 3, "laliga"),
    m("RM", O["BET"], TEAMS["RM"], kickoff("2026-09-04", "19:00:00"), 4, "laliga"),
    m("RM", TEAMS["RM"], O["RAY"], kickoff("2026-09-13", "19:00:00"), 5, "laliga"),
    # La Liga — Barcelona (RFEF / sport.es)
    m("BAR", O["ELC"], TEAMS["BAR"], kickoff("2026-08-23", "15:00:00"), 2, "laliga"),
    m("BAR", TEAMS["BAR"], O["ATH"], kickoff("2026-08-27", "19:00:00"), 1, "laliga"),
    m("BAR", TEAMS["BAR"], O["RAY"], kickoff("2026-08-30", "19:00:00"), 3, "laliga"),
    m("BAR", O["VAL"], TEAMS["BAR"], kickoff("2026-09-06", "19:00:00"), 4, "laliga"),
    m("BAR", O["LEV"], TEAMS["BAR"], kickoff("2026-09-13", "19:00:00"), 5, "laliga"),
    # Premier League — gameweeks 1–5 (premierleague.com / Sports Mole)
    m("ARS", TEAMS["ARS"], O["COV"], kickoff("2026-08-21", "19:00:00"), 1, "pl"),
    m("MU", O["HUL"], TEAMS["MU"], kickoff("2026-08-22", "11:30:00"), 1, "pl"),
    m("MC", TEAMS["MC"], O["BOU"], kickoff("2026-08-23", "13:00:00"), 1, "pl"),
    m("LIV", O["NEW"], TEAMS["LIV"], kickoff("2026-08-23", "15:30:00"), 1, "pl"),
    m("CHE", O["FUL"], TEAMS["CHE"], kickoff("2026-08-24", "19:00:00"), 1, "pl"),
    m("MC", O["CRY"], TEAMS["MC"], kickoff("2026-08-28", "19:00:00"), 2, "pl"),
    m("LIV", TEAMS["LIV"], O["NFO"], kickoff("2026-08-29", "11:30:00"), 2, "pl"),
    m("CHE", TEAMS["CHE"], O["BHA"], kickoff("2026-08-30", "13:00:00"), 2, "pl"),
    m("MU", TEAMS["MU"], O["IPS"], kickoff("2026-08-30", "15:30:00"), 2, "pl"),
    m("ARS", O["AVL"], TEAMS["ARS"], kickoff("2026-08-31", "19:00:00"), 2, "pl"),
    m("LIV", O["IPS"], TEAMS["LIV"], kickoff("2026-09-04", "19:00:00"), 3, "pl"),
    m("MC", TEAMS["MC"], O["COV"], kickoff("2026-09-05", "14:00:00"), 3, "pl"),
    m("MU", O["EVE"], TEAMS["MU"], kickoff("2026-09-06", "13:00:00"), 3, "pl"),
    m("ARS", TEAMS["ARS"], TEAMS["CHE"], kickoff("2026-09-06", "15:30:00"), 3, "pl"),
    m("CHE", TEAMS["ARS"], TEAMS["CHE"], kickoff("2026-09-06", "15:30:00"), 3, "pl"),
    m("LIV", TEAMS["LIV"], O["FUL"], kickoff("2026-09-12", "14:00:00"), 4, "pl"),
    m("CHE", TEAMS["CHE"], O["HUL"], kickoff("2026-09-12", "14:00:00"), 4, "pl"),
    m("ARS", O["SUN"], TEAMS["ARS"], kickoff("2026-09-12", "19:00:00"), 4, "pl"),
    m("MU", TEAMS["MU"], TEAMS["MC"], kickoff("2026-09-13", "15:30:00"), 4, "pl"),
    m("MC", TEAMS["MU"], TEAMS["MC"], kickoff("2026-09-13", "15:30:00"), 4, "pl"),
    m("CHE", O["BRE"], TEAMS["CHE"], kickoff("2026-09-18", "19:00:00"), 5, "pl"),
    m("MC", TEAMS["MC"], O["SUN"], kickoff("2026-09-19", "14:00:00"), 5, "pl"),
    m("LIV", O["BOU"], TEAMS["LIV"], kickoff("2026-09-20", "13:00:00"), 5, "pl"),
    m("MU", O["FUL"], TEAMS["MU"], kickoff("2026-09-20", "15:30:00"), 5, "pl"),
    m("ARS", O["BHA"], TEAMS["ARS"], kickoff("2026-09-19", "14:00:00"), 5, "pl"),
    # Chelsea — no European football in 2026/27; extra PL gameweeks 6–10
    m("CHE", TEAMS["CHE"], O["BOU"], kickoff("2026-10-10", "14:00:00"), 6, "pl"),
    m("CHE", O["EVE"], TEAMS["CHE"], kickoff("2026-10-17", "11:30:00"), 7, "pl"),
    m("CHE", TEAMS["CHE"], O["TOT"], kickoff("2026-10-24", "16:30:00"), 8, "pl"),
    m("CHE", TEAMS["CHE"], TEAMS["MU"], kickoff("2026-10-31", "12:30:00"), 9, "pl"),
    m("CHE", O["NFO"], TEAMS["CHE"], kickoff("2026-11-07", "15:00:00"), 10, "pl"),
    # Champions League — UEFA 2026/27 league-phase dates
    m("RM", TEAMS["RM"], O["SPO"], kickoff("2026-09-16", "19:00:00"), 1, "ucl"),
    m("ARS", TEAMS["ARS"], O["PSV"], kickoff("2026-09-16", "19:00:00"), 1, "ucl"),
    m("LIV", TEAMS["LIV"], O["ATM"], kickoff("2026-09-17", "19:00:00"), 1, "ucl"),
    m("BAR", O["PSG"], TEAMS["BAR"], kickoff("2026-09-17", "19:00:00"), 1, "ucl"),
    m("MC", TEAMS["MC"], O["NAP"], kickoff("2026-09-18", "19:00:00"), 1, "ucl"),
    m("MU", TEAMS["MU"], O["LIL"], kickoff("2026-09-18", "19:00:00"), 1, "ucl"),
    m("RM", O["DOR"], TEAMS["RM"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("BAR", TEAMS["BAR"], O["BAY"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("MC", TEAMS["MC"], O["BRU"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("LIV", TEAMS["LIV"], O["FEY"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("ARS", TEAMS["ARS"], O["SPO"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("MU", TEAMS["MU"], O["GAL"], kickoff("2026-10-13", "19:00:00"), 2, "ucl"),
    m("RM", TEAMS["RM"], O["PSV"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("BAR", TEAMS["BAR"], O["NAP"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("MC", O["VIL"], TEAMS["MC"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("LIV", TEAMS["LIV"], O["GAL"], kickoff("2026-10-22", "19:00:00"), 3, "ucl"),
    m("ARS", O["BAY"], TEAMS["ARS"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("MU", O["ROM"], TEAMS["MU"], kickoff("2026-10-20", "19:00:00"), 3, "ucl"),
    m("RM", O["AVL"], TEAMS["RM"], kickoff("2026-11-04", "20:00:00"), 4, "ucl"),
    m("BAR", O["DOR"], TEAMS["BAR"], kickoff("2026-11-04", "20:00:00"), 4, "ucl"),
    m("MC", TEAMS["MC"], O["ROM"], kickoff("2026-11-04", "20:00:00"), 4, "ucl"),
    m("LIV", O["PSG"], TEAMS["LIV"], kickoff("2026-11-05", "20:00:00"), 4, "ucl"),
    m("ARS", TEAMS["ARS"], O["INT"], kickoff("2026-11-04", "20:00:00"), 4, "ucl"),
    m("MU", TEAMS["MU"], O["SHA"], kickoff("2026-11-03", "20:00:00"), 4, "ucl"),
    m("RM", TEAMS["RM"], O["INT"], kickoff("2026-11-25", "20:00:00"), 5, "ucl"),
    m("BAR", TEAMS["BAR"], O["SPO"], kickoff("2026-11-25", "20:00:00"), 5, "ucl"),
    m("MC", O["BAY"], TEAMS["MC"], kickoff("2026-11-25", "20:00:00"), 5, "ucl"),
    m("LIV", TEAMS["LIV"], O["NAP"], kickoff("2026-11-25", "20:00:00"), 5, "ucl"),
    m("ARS", O["SLA"], TEAMS["ARS"], kickoff("2026-11-25", "20:00:00"), 5, "ucl"),
    m("MU", O["COM"], TEAMS["MU"], kickoff("2026-11-24", "20:00:00"), 5, "ucl"),
]


def fmt_fixtures() -> str:
    lines = ["CLUB_FIXTURE_ROWS: tuple[tuple[str, str, str, str, str], ...] = ("]
    for club, home, away, kickoff_at, group in FIXTURES:
        lines.append(f"    ({club!r}, {home!r}, {away!r}, {kickoff_at!r}, {group!r}),")
    lines.append(")")
    return "\n".join(lines)


BODY = textwrap.dedent(
    '''
    CLUB_CODE_TO_NAME: dict[str, str] = dict(
        zip(
            ("RM", "BAR", "MU", "MC", "LIV", "ARS", "CHE"),
            LEAGUE_TEAMS,
            strict=True,
        )
    )


    @dataclass(frozen=True)
    class LeagueFixture:
        home: str
        away: str
        date: str
        group: str
        kickoff_utc: str = ""
        club: str = ""


    def _build_fixtures() -> list[LeagueFixture]:
        rows = sorted(CLUB_FIXTURE_ROWS, key=lambda row: row[3])
        fixtures: list[LeagueFixture] = []
        for club_code, home, away, kickoff_utc, group in rows:
            fixtures.append(
                LeagueFixture(
                    home=home,
                    away=away,
                    date=kickoff_utc.split("T", 1)[0],
                    group=group,
                    kickoff_utc=kickoff_utc,
                    club=CLUB_CODE_TO_NAME[club_code],
                )
            )
        return fixtures


    LEAGUE_SEASON_FIXTURES: list[LeagueFixture] = _build_fixtures()

    LOCAL_LEAGUE_FIXTURES = [
        f for f in LEAGUE_SEASON_FIXTURES
        if LOCAL_LA_LIGA_LABEL in f.group or LOCAL_PL_LABEL in f.group
    ]
    CHAMPIONS_LEAGUE_FIXTURES = [
        f for f in LEAGUE_SEASON_FIXTURES if CHAMPIONS_LEAGUE_LABEL in f.group
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
    header = f'''"""Seven-club season: 2026/27 La Liga, Premier League, and UCL calendars."""

from dataclasses import dataclass
from datetime import datetime

from worldcup2026 import kickoff_datetime

LEAGUE_SEASON_LABEL = "موسم 2026/27"

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

{fmt_fixtures()}

{BODY}
'''
    Path(__file__).resolve().parents[1].joinpath("league_season.py").write_text(
        header, encoding="utf-8"
    )


if __name__ == "__main__":
    main()
