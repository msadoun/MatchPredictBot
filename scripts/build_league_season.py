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
    "LEE": "\u0644\u064a\u062f\u0632 \u064a\u0648\u0646\u0627\u064a\u062a\u062f",
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
    # UCL opponents — official 2026/27 league-phase draw (27 Aug 2026)
    "AEK": "\u0623\u064a\u0643 \u0623\u062b\u064a\u0646\u0627",
    "ATM": "\u0623\u062a\u0644\u062a\u064a\u0643\u0648 \u0645\u062f\u0631\u064a\u062f",
    "BAY": "\u0628\u0627\u064a\u0631\u0646 \u0645\u064a\u0648\u0646\u062e",
    "BRU": "\u0643\u0644\u0648\u0628 \u0628\u0631\u0648\u062c",
    "COM": "\u0643\u0648\u0645\u0648",
    "DOR": "\u0628\u0648\u0631\u0648\u0633\u064a\u0627 \u062f\u0648\u0631\u062a\u0645\u0648\u0646\u062f",
    "FEY": "\u0641\u064a\u0646\u0648\u0648\u0631\u062f",
    "FEN": "\u0641\u0646\u0631\u0628\u062e\u0686\u0647",
    "GAL": "\u063a\u0644\u0637\u0629 \u0633\u0631\u0627\u064a",
    "INT": "\u0625\u0646\u062a\u0631 \u0645\u064a\u0644\u0627\u0646",
    "LASK": "\u0644\u0627\u0633\u0643",
    "LIL": "\u0644\u064a\u0644",
    "NAP": "\u0646\u0627\u0628\u0648\u0644\u064a",
    "POR": "\u0628\u0648\u0631\u062a\u0648",
    "PSG": "\u0628\u0627\u0631\u064a\u0633 \u0633\u0627\u0646 \u062c\u064a\u0631\u0645\u0627\u0646",
    "PSV": "\u0628\u064a \u0625\u0633 \u0641\u064a",
    "RBL": "\u0644\u0627\u064a\u0628\u0632\u064a\u063a",
    "ROM": "\u0622\u0633 \u0631\u0648\u0645\u0627",
    "SAB": "\u0635\u0628\u0627\u062d",
    "SPO": "\u0633\u0628\u0648\u0631\u062a\u0646\u063a \u0644\u0634\u0628\u0648\u0646\u0629",
    "SLA": "\u0633\u0644\u0627\u0641\u064a\u0627 \u0628\u0631\u0627\u062c",
    "VIL": "\u0641\u064a\u0627\u0631\u064a\u0627\u0644",
    "GET": "\u062e\u064a\u062a\u0627\u0641\u064a",
    "RAC": "\u0631\u0627\u0633\u064a\u0646\u063a \u0633\u0627\u0646\u062a\u0627\u0646\u062f\u0631",
    "SEV": "\u0625\u0634\u0628\u064a\u0644\u064a\u0629",
}


def m(club: str, home: str, away: str, kickoff_at: str, md: int, comp: str) -> tuple:
    if comp == "laliga":
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u0627\u0644\u062f\u0648\u0631\u064a \u0627\u0644\u0625\u0633\u0628\u0627\u0646\u064a"
    elif comp == "pl":
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u0627\u0644\u062f\u0648\u0631\u064a \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a"
    else:
        group = f"\u0627\u0644\u062c\u0648\u0644\u0629 {md} \u00b7 \u062f\u0648\u0631\u064a \u0623\u0628\u0637\u0627\u0644 \u0623\u0648\u0631\u0648\u0628\u0627"
    return (club, home, away, kickoff_at, group)


# (club_code, home, away, kickoff_utc, group) — 2026/27 official domestic + UCL calendars.
# UCL: UEFA league-phase draw 27 Aug 2026 (AS/Sky); kickoffs 19:00 / 16:45 UTC.
FIXTURES: list[tuple[str, str, str, str, str]] = [
    # La Liga — Real Madrid (realmadrid.com / LaLiga MD5–9 window)
    # MD5 Rayo Sat 12 Sep 21:00 CEST; MD6 Elche Tue 15 Sep 21:30; MD7 Atlético Sun 20 Sep 16:15
    m("RM", TEAMS["RM"], O["RAY"], kickoff("2026-09-12", "19:00:00"), 5, "laliga"),
    m("RM", O["ELC"], TEAMS["RM"], kickoff("2026-09-15", "19:30:00"), 6, "laliga"),
    m("RM", O["ATM"], TEAMS["RM"], kickoff("2026-09-20", "14:15:00"), 7, "laliga"),
    m("RM", TEAMS["RM"], O["VIL"], kickoff("2026-10-10", "19:00:00"), 8, "laliga"),  # Sat 10 Oct 21:00 CEST
    m("RM", TEAMS["RM"], O["SEV"], kickoff("2026-10-18", "19:00:00"), 9, "laliga"),
    # La Liga — Barcelona (fcbarcelona.com MD5–9 window)
    # MD5 Levante Sun 13 Sep 16:15; MD6 Racing Wed 16 Sep 21:30; MD7 Sevilla Sat 19 Sep 21:00
    m("BAR", O["LEV"], TEAMS["BAR"], kickoff("2026-09-13", "14:15:00"), 5, "laliga"),
    m("BAR", TEAMS["BAR"], O["RAC"], kickoff("2026-09-16", "19:30:00"), 6, "laliga"),
    m("BAR", O["SEV"], TEAMS["BAR"], kickoff("2026-09-19", "19:00:00"), 7, "laliga"),
    m("BAR", TEAMS["BAR"], O["GET"], kickoff("2026-10-10", "16:30:00"), 8, "laliga"),
    m("BAR", O["BET"], TEAMS["BAR"], kickoff("2026-10-18", "19:00:00"), 9, "laliga"),
    # Premier League — GW5–9 window (Sports Mole / club TV updates, mid-Sep 2026)
    # Arsenal: Brighton A · Leeds H · Forest A · Everton H · Liverpool A
    m("ARS", O["BHA"], TEAMS["ARS"], kickoff("2026-09-19", "14:00:00"), 5, "pl"),
    m("ARS", TEAMS["ARS"], O["LEE"], kickoff("2026-10-10", "11:30:00"), 6, "pl"),
    m("ARS", O["NFO"], TEAMS["ARS"], kickoff("2026-10-18", "15:30:00"), 7, "pl"),
    m("ARS", TEAMS["ARS"], O["EVE"], kickoff("2026-10-24", "14:00:00"), 8, "pl"),
    m("ARS", TEAMS["LIV"], TEAMS["ARS"], kickoff("2026-11-01", "16:30:00"), 9, "pl"),
    # Man United: Fulham A · Spurs H · Leeds A · Bournemouth H · Chelsea A
    m("MU", O["FUL"], TEAMS["MU"], kickoff("2026-09-20", "15:30:00"), 5, "pl"),
    m("MU", TEAMS["MU"], O["TOT"], kickoff("2026-10-10", "16:30:00"), 6, "pl"),
    m("MU", O["LEE"], TEAMS["MU"], kickoff("2026-10-18", "13:00:00"), 7, "pl"),
    m("MU", TEAMS["MU"], O["BOU"], kickoff("2026-10-25", "14:00:00"), 8, "pl"),
    m("MU", TEAMS["CHE"], TEAMS["MU"], kickoff("2026-10-31", "12:30:00"), 9, "pl"),
    # Man City: Sunderland H · Liverpool A · Ipswich H · Villa A · Brighton H
    m("MC", TEAMS["MC"], O["SUN"], kickoff("2026-09-19", "14:00:00"), 5, "pl"),
    m("MC", TEAMS["LIV"], TEAMS["MC"], kickoff("2026-10-11", "15:30:00"), 6, "pl"),
    m("MC", TEAMS["MC"], O["IPS"], kickoff("2026-10-17", "14:00:00"), 7, "pl"),
    m("MC", O["AVL"], TEAMS["MC"], kickoff("2026-10-24", "11:30:00"), 8, "pl"),
    m("MC", TEAMS["MC"], O["BHA"], kickoff("2026-10-31", "15:00:00"), 9, "pl"),
    # Liverpool: Bournemouth A · City H · Brentford A · Brighton H · Arsenal H
    m("LIV", O["BOU"], TEAMS["LIV"], kickoff("2026-09-20", "13:00:00"), 5, "pl"),
    m("LIV", TEAMS["LIV"], TEAMS["MC"], kickoff("2026-10-11", "15:30:00"), 6, "pl"),
    m("LIV", O["BRE"], TEAMS["LIV"], kickoff("2026-10-17", "14:00:00"), 7, "pl"),
    m("LIV", TEAMS["LIV"], O["BHA"], kickoff("2026-10-25", "14:00:00"), 8, "pl"),
    m("LIV", TEAMS["LIV"], TEAMS["ARS"], kickoff("2026-11-01", "16:30:00"), 9, "pl"),
    # Chelsea — no UCL; next 10 PL (GW5–14). Nov 7 is Sunderland A, not Forest.
    m("CHE", O["BRE"], TEAMS["CHE"], kickoff("2026-09-18", "19:00:00"), 5, "pl"),
    m("CHE", TEAMS["CHE"], O["BOU"], kickoff("2026-10-10", "14:00:00"), 6, "pl"),
    m("CHE", O["EVE"], TEAMS["CHE"], kickoff("2026-10-17", "11:30:00"), 7, "pl"),
    m("CHE", TEAMS["CHE"], O["TOT"], kickoff("2026-10-24", "16:30:00"), 8, "pl"),
    m("CHE", TEAMS["CHE"], TEAMS["MU"], kickoff("2026-10-31", "12:30:00"), 9, "pl"),
    m("CHE", O["SUN"], TEAMS["CHE"], kickoff("2026-11-07", "15:00:00"), 10, "pl"),
    m("CHE", TEAMS["CHE"], O["LEE"], kickoff("2026-11-21", "15:00:00"), 11, "pl"),
    m("CHE", O["NFO"], TEAMS["CHE"], kickoff("2026-11-28", "15:00:00"), 12, "pl"),
    m("CHE", TEAMS["CHE"], TEAMS["LIV"], kickoff("2026-12-05", "15:00:00"), 13, "pl"),
    m("CHE", TEAMS["MC"], TEAMS["CHE"], kickoff("2026-12-12", "15:00:00"), 14, "pl"),
    # Champions League — official 2026/27 league-phase draw (matchdays 1–5)
    m("RM", TEAMS["RM"], O["INT"], kickoff("2026-09-08", "19:00:00"), 1, "ucl"),
    m("MC", O["POR"], TEAMS["MC"], kickoff("2026-09-08", "19:00:00"), 1, "ucl"),
    m("BAR", TEAMS["BAR"], O["FEY"], kickoff("2026-09-09", "16:45:00"), 1, "ucl"),
    m("ARS", O["NAP"], TEAMS["ARS"], kickoff("2026-09-09", "19:00:00"), 1, "ucl"),
    m("LIV", TEAMS["LIV"], O["ATM"], kickoff("2026-09-09", "19:00:00"), 1, "ucl"),
    m("MU", TEAMS["MU"], O["SAB"], kickoff("2026-09-10", "19:00:00"), 1, "ucl"),
    m("BAR", O["GAL"], TEAMS["BAR"], kickoff("2026-10-13", "19:00:00"), 2, "ucl"),
    m("ARS", TEAMS["ARS"], O["LIL"], kickoff("2026-10-13", "19:00:00"), 2, "ucl"),
    m("MU", O["ATM"], TEAMS["MU"], kickoff("2026-10-13", "19:00:00"), 2, "ucl"),
    m("RM", O["ROM"], TEAMS["RM"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("MC", TEAMS["MC"], O["PSG"], kickoff("2026-10-14", "19:00:00"), 2, "ucl"),
    m("LIV", O["LASK"], TEAMS["LIV"], kickoff("2026-10-14", "16:45:00"), 2, "ucl"),
    m("BAR", O["PSG"], TEAMS["BAR"], kickoff("2026-10-20", "19:00:00"), 3, "ucl"),
    m("MC", TEAMS["MC"], O["AEK"], kickoff("2026-10-20", "19:00:00"), 3, "ucl"),
    m("LIV", TEAMS["LIV"], O["VIL"], kickoff("2026-10-20", "19:00:00"), 3, "ucl"),
    m("RM", TEAMS["RM"], O["RBL"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("ARS", O["BAY"], TEAMS["ARS"], kickoff("2026-10-21", "19:00:00"), 3, "ucl"),
    m("MU", O["COM"], TEAMS["MU"], kickoff("2026-10-21", "16:45:00"), 3, "ucl"),
    m("BAR", TEAMS["BAR"], O["AVL"], kickoff("2026-11-03", "19:00:00"), 4, "ucl"),
    m("MU", TEAMS["MU"], O["ROM"], kickoff("2026-11-03", "19:00:00"), 4, "ucl"),
    m("MC", O["RBL"], TEAMS["MC"], kickoff("2026-11-04", "19:00:00"), 4, "ucl"),
    m("ARS", O["SLA"], TEAMS["ARS"], kickoff("2026-11-04", "19:00:00"), 4, "ucl"),
    m("RM", O["AEK"], TEAMS["RM"], kickoff("2026-11-04", "16:45:00"), 4, "ucl"),
    m("LIV", O["FEN"], TEAMS["LIV"], kickoff("2026-11-04", "16:45:00"), 4, "ucl"),
    m("MC", TEAMS["MC"], O["NAP"], kickoff("2026-11-24", "19:00:00"), 5, "ucl"),
    m("RM", TEAMS["RM"], O["PSV"], kickoff("2026-11-24", "19:00:00"), 5, "ucl"),
    m("ARS", TEAMS["ARS"], O["DOR"], kickoff("2026-11-24", "19:00:00"), 5, "ucl"),
    m("MU", O["SPO"], TEAMS["MU"], kickoff("2026-11-25", "19:00:00"), 5, "ucl"),
    m("BAR", O["SAB"], TEAMS["BAR"], kickoff("2026-11-25", "16:45:00"), 5, "ucl"),
    m("LIV", O["BRU"], TEAMS["LIV"], kickoff("2026-11-25", "19:00:00"), 5, "ucl"),
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
