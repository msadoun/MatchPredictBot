"""Optional off-server backup so predictions survive Railway redeploys without a volume."""

import json
import logging
import tempfile
from pathlib import Path

import httpx

from config import REMOTE_PREDICTION_BACKUP_TOKEN, REMOTE_PREDICTION_BACKUP_URL

logger = logging.getLogger(__name__)

_last_pushed_count = -1


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if REMOTE_PREDICTION_BACKUP_TOKEN:
        headers["Authorization"] = f"Bearer {REMOTE_PREDICTION_BACKUP_TOKEN}"
    return headers


def push_remote_backup(*, force: bool = False) -> bool:
    """POST the latest predictions JSON to REMOTE_PREDICTION_BACKUP_URL."""
    global _last_pushed_count
    if not REMOTE_PREDICTION_BACKUP_URL:
        return False

    from prediction_backup import count_predictions, export_predictions_payload

    count = count_predictions()
    if count == 0:
        return False
    if not force and count == _last_pushed_count:
        return False

    payload = export_predictions_payload()
    try:
        response = httpx.post(
            REMOTE_PREDICTION_BACKUP_URL,
            json=payload,
            headers=_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Remote prediction backup push failed: %s", exc)
        return False

    _last_pushed_count = count
    logger.info("Pushed %d predictions to remote backup", count)
    return True


def fetch_remote_backup() -> int:
    """GET predictions JSON from REMOTE_PREDICTION_BACKUP_URL and merge missing rows."""
    if not REMOTE_PREDICTION_BACKUP_URL:
        return 0

    from prediction_backup import restore_predictions_from_file

    try:
        response = httpx.get(
            REMOTE_PREDICTION_BACKUP_URL,
            headers=_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.warning("Remote prediction backup fetch failed: %s", exc)
        return 0

    items = payload.get("predictions") if isinstance(payload, dict) else None
    if not items:
        return 0

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        temp_path = Path(handle.name)

    try:
        restored, _ = restore_predictions_from_file(temp_path, only_if_empty=False)
        return restored
    finally:
        temp_path.unlink(missing_ok=True)
