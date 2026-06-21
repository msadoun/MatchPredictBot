import logging
import re

from database import (
    get_user_by_telegram_id,
    get_user_by_username,
    save_prediction,
    user_has_prediction,
)

logger = logging.getLogger(__name__)

_BACKFILL_PATTERN = re.compile(
    r"^(?P<user>[^:\s]+):(?P<match_id>\d+):(?P<home>\d+)[\-:](?P<away>\d+)$"
)


def parse_prediction_backfills(raw: str) -> list[tuple[str, int, int, int]]:
    specs: list[tuple[str, int, int, int]] = []
    for chunk in raw.split(","):
        entry = chunk.strip()
        if not entry:
            continue
        match = _BACKFILL_PATTERN.match(entry)
        if not match:
            logger.warning("Skipping invalid prediction backfill entry: %s", entry)
            continue
        specs.append(
            (
                match.group("user"),
                int(match.group("match_id")),
                int(match.group("home")),
                int(match.group("away")),
            )
        )
    return specs


def _resolve_backfill_user(user_ref: str):
    ref = user_ref.strip().lstrip("@")
    if ref.isdigit():
        return get_user_by_telegram_id(int(ref))
    return get_user_by_username(ref)


def apply_prediction_backfills(raw: str) -> int:
    """Insert missing predictions that were lost before save (e.g. bot restart)."""
    applied = 0
    for user_ref, match_id, home_score, away_score in parse_prediction_backfills(raw):
        user = _resolve_backfill_user(user_ref)
        if not user:
            logger.warning(
                "Prediction backfill skipped — user not found: %s match #%d",
                user_ref,
                match_id,
            )
            continue
        if user_has_prediction(user.id, match_id):
            continue
        try:
            save_prediction(
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
        logger.info(
            "Backfilled prediction for %s (@%s) match #%d as %d-%d",
            user.display_name,
            user.username or user.telegram_id,
            match_id,
            home_score,
            away_score,
        )
    return applied
