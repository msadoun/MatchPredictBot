import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from database import get_db, get_match, set_match_result
from teams_ar import TEAM_EN_TO_AR

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date}"
)
WORLD_CUP_LEAGUE = "fifa.world"

_scoreboard_cache: dict[str, list[dict]] = {}


def clear_scoreboard_cache() -> None:
    _scoreboard_cache.clear()


TEAM_ALIASES: dict[str, str] = {
    "United States": "USA",
    "Turkey": "Turkiye",
    "Türkiye": "Turkiye",
    "Turkiye": "Turkiye",
    "Curaçao": "Curacao",
    "Korea Republic": "South Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia Herzegovina": "Bosnia and Herzegovina",
    # ESPN display names → canonical keys in teams_ar
    "Athletic Club": "Athletic Bilbao",
    "Tottenham Hotspur": "Tottenham",
    "Newcastle United": "Newcastle",
    "Brighton & Hove Albion": "Brighton",
    "Brighton and Hove Albion": "Brighton",
    "Wolverhampton Wanderers": "Wolves",
    "West Ham United": "West Ham",
    "Leeds United": "Leeds United",
}


def _english_to_arabic(name: str) -> str:
    canonical = TEAM_ALIASES.get(name, name)
    if canonical in TEAM_EN_TO_AR:
        return TEAM_EN_TO_AR[canonical]

    normalized = canonical.replace("-", " ").strip().lower()
    for english, arabic in TEAM_EN_TO_AR.items():
        english_norm = english.replace("-", " ").strip().lower()
        if english_norm == normalized:
            return arabic
    return TEAM_EN_TO_AR.get(canonical, canonical)


def _event_is_finished(event: dict) -> bool:
    status = event.get("status") or {}
    type_info = status.get("type") or {}
    if type_info.get("completed"):
        return True
    state = str(type_info.get("state") or "").lower()
    name = str(type_info.get("name") or type_info.get("description") or "").lower()
    if state in {"post", "final", "status_final"}:
        return True
    if "final" in name or name in {"ft", "full time", "full-time"}:
        return True
    detail = str(status.get("detail") or "").lower()
    return detail in {"ft", "full time", "full-time", "final"}


def _scoreboard_leagues_for_match(kickoff_at: str | None) -> list[str]:
    """Pick ESPN competition slug(s) for a fixture kickoff label."""
    if not kickoff_at:
        return [WORLD_CUP_LEAGUE]

    from league_season import (
        CHAMPIONS_LEAGUE_LABEL,
        LOCAL_LA_LIGA_LABEL,
        LOCAL_PL_LABEL,
    )

    leagues: list[str] = []
    if LOCAL_LA_LIGA_LABEL in kickoff_at:
        leagues.append("esp.1")
    if LOCAL_PL_LABEL in kickoff_at:
        leagues.append("eng.1")
    if CHAMPIONS_LEAGUE_LABEL in kickoff_at:
        leagues.append("uefa.champions")
    if leagues:
        return leagues
    return [WORLD_CUP_LEAGUE]


def active_scoreboard_leagues() -> list[str]:
    """Leagues polled on each background sync."""
    from database import is_league_season_loaded

    if is_league_season_loaded():
        return ["esp.1", "eng.1", "uefa.champions"]
    return [WORLD_CUP_LEAGUE]


def _fetch_scoreboard(date_yyyymmdd: str, league: str) -> list[dict]:
    cache_key = f"{league}:{date_yyyymmdd}"
    if cache_key in _scoreboard_cache:
        return _scoreboard_cache[cache_key]

    url = ESPN_SCOREBOARD_URL.format(league=league, date=date_yyyymmdd)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning(
            "ESPN scoreboard fetch failed for %s %s: %s",
            league,
            date_yyyymmdd,
            exc,
        )
        _scoreboard_cache[cache_key] = []
        return []

    finished: list[dict] = []
    for event in payload.get("events", []):
        if not _event_is_finished(event):
            continue
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors") or []
        if len(competitors) != 2:
            continue
        by_side = {item.get("homeAway"): item for item in competitors}
        home = by_side.get("home")
        away = by_side.get("away")
        if not home or not away:
            continue
        try:
            home_score = int(home.get("score") or 0)
            away_score = int(away.get("score") or 0)
        except (TypeError, ValueError):
            continue
        home_name = (home.get("team") or {}).get("displayName") or ""
        away_name = (away.get("team") or {}).get("displayName") or ""
        if not home_name or not away_name:
            continue
        finished.append(
            {
                "date": f"{date_yyyymmdd[:4]}-{date_yyyymmdd[4:6]}-{date_yyyymmdd[6:8]}",
                "home_ar": _english_to_arabic(home_name),
                "away_ar": _english_to_arabic(away_name),
                "home_score": home_score,
                "away_score": away_score,
                "league": league,
            }
        )
    _scoreboard_cache[cache_key] = finished
    return finished


def _find_match_id(home_ar: str, away_ar: str, iso_date: str) -> int | None:
    from worldcup2026 import match_day_date

    with get_db() as conn:
        for date_prefix in {iso_date}:
            row = conn.execute(
                """
                SELECT id FROM matches
                WHERE home_team = ? AND away_team = ? AND kickoff_at LIKE ?
                """,
                (home_ar, away_ar, f"{date_prefix}%"),
            ).fetchone()
            if row:
                return int(row["id"])

        rows = conn.execute(
            """
            SELECT id, kickoff_at FROM matches
            WHERE home_team = ? AND away_team = ?
            ORDER BY kickoff_at ASC
            """,
            (home_ar, away_ar),
        ).fetchall()
        for row in rows:
            kickoff = row["kickoff_at"]
            if not kickoff:
                continue
            if match_day_date(kickoff) == iso_date:
                return int(row["id"])
        if rows:
            return int(rows[0]["id"])

        from knockout_teams import is_placeholder_team, teams_match_knockout_fixture

        placeholder_rows = conn.execute(
            """
            SELECT id, kickoff_at, home_team, away_team
            FROM matches
            WHERE kickoff_at LIKE ?
              AND (home_score IS NULL OR away_score IS NULL)
            """,
            (f"{iso_date}%",),
        ).fetchall()
        for row in placeholder_rows:
            if not (
                is_placeholder_team(row["home_team"])
                or is_placeholder_team(row["away_team"])
            ):
                continue
            if teams_match_knockout_fixture(
                home_ar, away_ar, row["kickoff_at"]
            ):
                return int(row["id"])
    return None


def _date_keys_around(iso_date: str) -> list[str]:
    day = datetime.strptime(iso_date, "%Y-%m-%d").date()
    keys: list[str] = []
    for offset in (-1, 0, 1):
        keys.append((day + timedelta(days=offset)).strftime("%Y%m%d"))
    return keys


def _orient_espn_result_for_match(match, result: dict) -> tuple[str, str, int, int]:
    """Align ESPN home/away with the fixture slot (group winner vs runner-up, etc.)."""
    from knockout_teams import (
        _fixture_for_kickoff,
        participant_pools_for_placeholder,
    )
    from teams_ar import normalize_team_name

    fixture = _fixture_for_kickoff(match.kickoff_at)
    if not fixture:
        return (
            result["home_ar"],
            result["away_ar"],
            result["home_score"],
            result["away_score"],
        )

    home_ar = normalize_team_name(result["home_ar"])
    away_ar = normalize_team_name(result["away_ar"])
    home_pool = participant_pools_for_placeholder(fixture.home)
    away_pool = participant_pools_for_placeholder(fixture.away)
    if home_pool and away_pool:
        if home_ar in home_pool and away_ar in away_pool:
            return home_ar, away_ar, result["home_score"], result["away_score"]
        if away_ar in home_pool and home_ar in away_pool:
            return away_ar, home_ar, result["away_score"], result["home_score"]

    return home_ar, away_ar, result["home_score"], result["away_score"]


def _iter_scoreboard_results(date_key: str, leagues: list[str]) -> list[dict]:
    results: list[dict] = []
    for league in leagues:
        results.extend(_fetch_scoreboard(date_key, league))
    return results


def restore_match_result_from_espn(match_id: int) -> bool:
    """Import a finished score for one match (used after admin reopen)."""
    from knockout_teams import is_placeholder_team, teams_match_knockout_fixture

    match = get_match(match_id)
    if not match or not match.kickoff_at:
        return False
    if match.home_score is not None and match.away_score is not None:
        return False

    leagues = _scoreboard_leagues_for_match(match.kickoff_at)
    date_part = match.kickoff_at.split(" · ", 1)[0].strip()[:10]
    for date_key in _date_keys_around(date_part):
        for result in _iter_scoreboard_results(date_key, leagues):
            found_id = _find_match_id(result["home_ar"], result["away_ar"], result["date"])
            if found_id != match_id:
                if found_id is not None:
                    continue
                if not (
                    is_placeholder_team(match.home_team)
                    or is_placeholder_team(match.away_team)
                ):
                    continue
                if not teams_match_knockout_fixture(
                    result["home_ar"],
                    result["away_ar"],
                    match.kickoff_at,
                ):
                    continue
            home_team, away_team, home_score, away_score = _orient_espn_result_for_match(
                match, result
            )
            updated = set_match_result(
                match_id,
                home_score,
                away_score,
                home_team=home_team,
                away_team=away_team,
            )
            if updated:
                logger.info(
                    "Restored ESPN result for match #%d (%s): %s vs %s %d-%d",
                    match_id,
                    result.get("league", "?"),
                    home_team,
                    away_team,
                    home_score,
                    away_score,
                )
                return True
    return False


def import_results_for_finished_matches() -> int:
    """Import ESPN scores for started matches that still have no result."""
    from worldcup2026 import safe_kickoff_datetime

    now = datetime.utcnow()
    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id FROM matches
            WHERE kickoff_at IS NOT NULL
              AND (home_score IS NULL OR away_score IS NULL)
            """
        ).fetchall()

    for row in rows:
        match = get_match(int(row["id"]))
        if not match or not match.kickoff_at:
            continue
        kickoff = safe_kickoff_datetime(match.kickoff_at)
        if kickoff is None or kickoff > now:
            continue
        if restore_match_result_from_espn(int(row["id"])):
            updated += 1
    return updated


def restore_missing_override_results() -> int:
    """Re-import ESPN results for admin-reopened matches missing scores."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id FROM matches
            WHERE predictions_override = 1
              AND (home_score IS NULL OR away_score IS NULL)
            """
        ).fetchall()
    restored = 0
    for row in rows:
        if restore_match_result_from_espn(int(row["id"])):
            restored += 1
    return restored


def sync_match_results_from_espn(days_back: int = 60, days_ahead: int = 1) -> dict[str, int]:
    today = datetime.utcnow().date()
    updated = 0
    scanned = 0
    skipped = 0
    rescored = 0
    leagues = active_scoreboard_leagues()

    for offset in range(-days_back, days_ahead + 1):
        day = today + timedelta(days=offset)
        date_key = day.strftime("%Y%m%d")
        for result in _iter_scoreboard_results(date_key, leagues):
            scanned += 1
            match_id = _find_match_id(result["home_ar"], result["away_ar"], result["date"])
            if not match_id:
                skipped += 1
                logger.debug(
                    "ESPN result not matched (%s): %s vs %s on %s (%d-%d)",
                    result.get("league", "?"),
                    result["home_ar"],
                    result["away_ar"],
                    result["date"],
                    result["home_score"],
                    result["away_score"],
                )
                continue
            match = get_match(match_id)
            if match and match.predictions_override:
                if match.home_score is not None and match.away_score is not None:
                    skipped += 1
                    continue
            if (
                match
                and match.home_score == result["home_score"]
                and match.away_score == result["away_score"]
            ):
                from database import rescore_match_predictions

                rescored += rescore_match_predictions(match_id)
                continue
            home_team, away_team, home_score, away_score = (
                _orient_espn_result_for_match(match, result)
                if match
                else (
                    result["home_ar"],
                    result["away_ar"],
                    result["home_score"],
                    result["away_score"],
                )
            )
            match = set_match_result(
                match_id,
                home_score,
                away_score,
                home_team=home_team,
                away_team=away_team,
            )
            if match:
                updated += 1
                logger.info(
                    "ESPN imported match #%d (%s): %s vs %s %d-%d",
                    match_id,
                    result.get("league", "?"),
                    home_team,
                    away_team,
                    home_score,
                    away_score,
                )

    if skipped:
        logger.info("ESPN sync skipped %d unmatched finished result(s)", skipped)

    return {
        "updated": updated,
        "scanned": scanned,
        "skipped": skipped,
        "rescored": rescored,
    }
