import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from database import get_db, set_match_result
from teams_ar import TEAM_EN_TO_AR

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={date}"
)

TEAM_ALIASES: dict[str, str] = {
    "United States": "USA",
    "Turkey": "Turkiye",
    "Curaçao": "Curacao",
    "Korea Republic": "South Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Cabo Verde": "Cape Verde",
    "Congo DR": "DR Congo",
}


def _english_to_arabic(name: str) -> str:
    canonical = TEAM_ALIASES.get(name, name)
    return TEAM_EN_TO_AR.get(canonical, name)


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
        if not event.get("status", {}).get("type", {}).get("completed"):
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
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id FROM matches
            WHERE home_team = ? AND away_team = ? AND kickoff_at LIKE ?
            """,
            (home_ar, away_ar, f"{iso_date}%"),
        ).fetchone()
    return int(row["id"]) if row else None


def sync_match_results_from_espn(days_back: int = 3, days_ahead: int = 1) -> dict[str, int]:
    today = datetime.utcnow().date()
    updated = 0
    scanned = 0
    skipped = 0

    for offset in range(-days_back, days_ahead + 1):
        day = today + timedelta(days=offset)
        date_key = day.strftime("%Y%m%d")
        for result in _fetch_scoreboard(date_key):
            scanned += 1
            match_id = _find_match_id(result["home_ar"], result["away_ar"], result["date"])
            if not match_id:
                skipped += 1
                continue
            match = set_match_result(match_id, result["home_score"], result["away_score"])
            if match:
                updated += 1

    return {"updated": updated, "scanned": scanned, "skipped": skipped}
