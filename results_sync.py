import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from database import get_db, get_match, set_match_result
from teams_ar import TEAM_EN_TO_AR

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date}"
)

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


def _fetch_scoreboard(date_yyyymmdd: str) -> list[dict]:
    url = ESPN_SCOREBOARD_URL.format(date=date_yyyymmdd)
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("ESPN scoreboard fetch failed for %s: %s", date_yyyymmdd, exc)
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
            }
        )
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
    return None


def _date_keys_around(iso_date: str) -> list[str]:
    day = datetime.strptime(iso_date, "%Y-%m-%d").date()
    keys: list[str] = []
    for offset in (-1, 0, 1):
        keys.append((day + timedelta(days=offset)).strftime("%Y%m%d"))
    return keys


def restore_match_result_from_espn(match_id: int) -> bool:
    """Import a finished score for one match (used after admin reopen)."""
    match = get_match(match_id)
    if not match or not match.kickoff_at:
        return False
    if match.home_score is not None and match.away_score is not None:
        return False

    date_part = match.kickoff_at.split(" · ", 1)[0].strip()[:10]
    for date_key in _date_keys_around(date_part):
        for result in _fetch_scoreboard(date_key):
            found_id = _find_match_id(result["home_ar"], result["away_ar"], result["date"])
            if found_id != match_id:
                continue
            updated = set_match_result(match_id, result["home_score"], result["away_score"])
            if updated:
                logger.info(
                    "Restored ESPN result for match #%d: %d-%d",
                    match_id,
                    result["home_score"],
                    result["away_score"],
                )
                return True
    return False


def import_results_for_finished_matches() -> int:
    """Import ESPN scores for started matches that still have no result."""
    from worldcup2026 import kickoff_datetime

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
        if kickoff_datetime(match.kickoff_at) > now:
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

    for offset in range(-days_back, days_ahead + 1):
        day = today + timedelta(days=offset)
        date_key = day.strftime("%Y%m%d")
        for result in _fetch_scoreboard(date_key):
            scanned += 1
            match_id = _find_match_id(result["home_ar"], result["away_ar"], result["date"])
            if not match_id:
                skipped += 1
                logger.warning(
                    "ESPN result not matched: %s vs %s on %s (%d-%d)",
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
            match = set_match_result(match_id, result["home_score"], result["away_score"])
            if match:
                updated += 1

    return {
        "updated": updated,
        "scanned": scanned,
        "skipped": skipped,
        "rescored": rescored,
    }
