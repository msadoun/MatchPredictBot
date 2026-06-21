import logging
import re

from database import (
    get_match,
    get_match_by_teams,
    get_user_prediction,
    resolve_user_ref,
    save_prediction,
)

logger = logging.getLogger(__name__)

_BACKFILL_PATTERN = re.compile(
    r"^(?P<user>[^:\s]+):(?P<match_id>\d+):(?P<home>\d+)[\-:](?P<away>\d+)$"
)

# Fallback when match IDs differ between databases (same fixture, different row id).
_MATCH_TEAM_ALIASES: dict[int, tuple[str, str]] = {
    35: ("هولندا", "السويد"),
}


def parse_prediction_backfills(raw: str) -> list[tuple[str, int, int, int]]:
    specs: list[tuple[str, int, int, int]] = []
    seen: set[tuple[str, int]] = set()
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry:
            continue
        match = _BACKFILL_PATTERN.match(entry)
        if not match:
            logger.warning("Skipping invalid prediction backfill entry: %s", entry)
            continue
        user_ref = match.group("user")
        match_id = int(match.group("match_id"))
        key = (user_ref.lower(), match_id)
        if key in seen:
            continue
        seen.add(key)
        specs.append(
            (
                user_ref,
                match_id,
                int(match.group("home")),
                int(match.group("away")),
            )
        )
    return specs


def _resolve_backfill_match_id(match_id: int) -> int | None:
    if get_match(match_id):
        return match_id
    teams = _MATCH_TEAM_ALIASES.get(match_id)
    if not teams:
        return None
    found = get_match_by_teams(*teams)
    if found:
        logger.info(
            "Resolved backfill match #%d to #%d (%s vs %s)",
            match_id,
            found.id,
            teams[0],
            teams[1],
        )
        return found.id
    return None


def _needs_backfill(user_id: int, match_id: int, home_score: int, away_score: int) -> bool:
    existing = get_user_prediction(user_id, match_id)
    if not existing:
        return True
    if existing.home_score != home_score or existing.away_score != away_score:
        return True
    if existing.points is None:
        return True
    return False


def apply_prediction_backfills(raw: str) -> int:
    """Ensure known missing predictions exist and are scored."""
    applied = 0
    for user_ref, requested_match_id, home_score, away_score in parse_prediction_backfills(raw):
        user = resolve_user_ref(user_ref)
        if not user:
            logger.warning(
                "Prediction backfill skipped — user not found: %s match #%d",
                user_ref,
                requested_match_id,
            )
            continue

        match_id = _resolve_backfill_match_id(requested_match_id)
        if not match_id:
            logger.warning(
                "Prediction backfill skipped — match not found: #%d",
                requested_match_id,
            )
            continue

        if not _needs_backfill(user.id, match_id, home_score, away_score):
            continue

        try:
            prediction, _ = save_prediction(
                user.id,
                match_id,
                home_score,
                away_score,
                allow_closed=True,
            )
        except ValueError as exc:
            logger.warning(
                "Prediction backfill failed for %s match #%d: %s",
                user_ref,
                match_id,
                exc,
            )
            continue

        applied += 1
        points = prediction.points if prediction.points is not None else 0
        logger.info(
            "Backfilled prediction for %s (@%s) match #%d as %d-%d (%d pts)",
            user.display_name,
            user.username or user.telegram_id,
            match_id,
            home_score,
            away_score,
            points,
        )
    return applied
