import json
import logging
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

BACKUPS_DIR = DATABASE_PATH.parent / "backups"
MAX_BACKUPS = 100


def _backup_path(stamp: str | None = None) -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    if stamp is None:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return BACKUPS_DIR / f"predictions_{stamp}.json"


def count_predictions() -> int:
    from database import get_db

    with get_db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])


def export_predictions_payload() -> dict:
    from database import get_db

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                u.telegram_id,
                u.username,
                u.display_name,
                p.match_id,
                p.home_score,
                p.away_score,
                p.points,
                p.created_at,
                p.updated_at
            FROM predictions p
            INNER JOIN users u ON u.id = p.user_id
            ORDER BY p.id ASC
            """
        ).fetchall()

    return {
        "saved_at": datetime.utcnow().isoformat(),
        "count": len(rows),
        "predictions": [
            {
                "telegram_id": row["telegram_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "match_id": row["match_id"],
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "points": row["points"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ],
    }


def _read_backup_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    return int(payload.get("count") or len(payload.get("predictions") or []))


def list_backup_paths() -> list[Path]:
    if not BACKUPS_DIR.is_dir():
        return []
    return sorted(BACKUPS_DIR.glob("predictions_*.json"), reverse=True)


def latest_backup_path() -> Path | None:
    files = list_backup_paths()
    return files[0] if files else None


def best_backup_path() -> Path | None:
    best_path: Path | None = None
    best_count = -1
    for path in list_backup_paths():
        count = _read_backup_count(path)
        if count > best_count:
            best_count = count
            best_path = path
    return best_path


def backup_predictions(*, force: bool = False) -> Path | None:
    count = count_predictions()
    if count == 0:
        return None

    best_path = best_backup_path()
    best_count = _read_backup_count(best_path) if best_path else 0
    if not force and best_count >= count:
        return best_path

    payload = export_predictions_payload()
    path = _backup_path()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_old_backups()
    logger.info("Backed up %d predictions to %s", count, path.name)
    return path


def backup_predictions_if_needed() -> Path | None:
    return backup_predictions()


def backup_before_migrations() -> Path | None:
    """Snapshot predictions before schema migrations — never deletes data."""
    if count_predictions() == 0:
        return None
    return backup_predictions(force=True)


def restore_predictions_from_file(
    path: Path,
    *,
    only_if_empty: bool = False,
) -> tuple[int, int]:
    """Insert missing predictions only — never overwrite or delete existing rows."""
    from database import get_db, get_user_by_telegram_id, save_prediction, upsert_user

    if only_if_empty and count_predictions() > 0:
        return 0, 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("predictions") or []
    restored = 0
    skipped = 0

    for item in items:
        telegram_id = int(item["telegram_id"])
        match_id = int(item["match_id"])
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            user = upsert_user(
                telegram_id,
                item.get("username"),
                item.get("display_name") or str(telegram_id),
            )

        with get_db() as conn:
            existing = conn.execute(
                """
                SELECT 1 FROM predictions
                WHERE user_id = ? AND match_id = ?
                LIMIT 1
                """,
                (user.id, match_id),
            ).fetchone()
        if existing:
            skipped += 1
            continue

        try:
            save_prediction(
                user.id,
                match_id,
                int(item["home_score"]),
                int(item["away_score"]),
                allow_closed=True,
            )
            restored += 1
        except ValueError:
            skipped += 1

    return restored, skipped


def merge_missing_predictions_from_backup() -> int:
    """On startup: fill in any predictions missing from the richest backup."""
    path = best_backup_path()
    if not path:
        return 0
    restored, _ = restore_predictions_from_file(path, only_if_empty=False)
    if restored:
        logger.info("Merged %d missing predictions from %s", restored, path.name)
    return restored


def maybe_auto_restore_predictions() -> int:
    """Legacy alias — merge missing rows, never replace the whole database."""
    return merge_missing_predictions_from_backup()


def _prune_old_backups() -> None:
    files = list_backup_paths()
    if len(files) <= MAX_BACKUPS:
        return
    best_count = max((_read_backup_count(path) for path in files), default=0)
    for path in files[MAX_BACKUPS:]:
        if best_count > 0 and _read_backup_count(path) >= best_count:
            continue
        path.unlink(missing_ok=True)
