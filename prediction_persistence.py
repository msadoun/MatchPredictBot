import json
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH

logger = logging.getLogger(__name__)

DATA_DIR = DATABASE_PATH.parent
ARCHIVE_PATH = DATA_DIR / "predictions_archive.jsonl"
HIGHWATER_PATH = DATA_DIR / "prediction_highwater.json"
DB_BACKUPS_DIR = DATA_DIR / "db_backups"
MAX_DB_BACKUPS = 30


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DB_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def count_predictions() -> int:
    from database import get_db

    try:
        with get_db() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    except sqlite3.OperationalError:
        return 0


def append_prediction_archive(
    *,
    telegram_id: int,
    username: str | None,
    display_name: str,
    match_id: int,
    home_score: int,
    away_score: int,
    points: int | None,
) -> None:
    """Append-only log — never deleted by the bot."""
    _ensure_dirs()
    record = {
        "saved_at": datetime.utcnow().isoformat(),
        "telegram_id": telegram_id,
        "username": username,
        "display_name": display_name,
        "match_id": match_id,
        "home_score": home_score,
        "away_score": away_score,
        "points": points,
    }
    with ARCHIVE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_highwater() -> int:
    if not HIGHWATER_PATH.is_file():
        return 0
    try:
        payload = json.loads(HIGHWATER_PATH.read_text(encoding="utf-8"))
        return int(payload.get("max_predictions") or 0)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0


def update_highwater_mark() -> int:
    count = count_predictions()
    previous = _load_highwater()
    if count > previous:
        _ensure_dirs()
        HIGHWATER_PATH.write_text(
            json.dumps(
                {
                    "max_predictions": count,
                    "updated_at": datetime.utcnow().isoformat(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return count
    return previous


def backup_database_file() -> Path | None:
    """Copy the full SQLite file — preserves everything."""
    if not DATABASE_PATH.is_file():
        return None
    if count_predictions() == 0:
        return None
    _ensure_dirs()
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = DB_BACKUPS_DIR / f"bot_{stamp}.db"
    shutil.copy2(DATABASE_PATH, dest)
    files = sorted(DB_BACKUPS_DIR.glob("bot_*.db"), reverse=True)
    for old in files[MAX_DB_BACKUPS:]:
        old.unlink(missing_ok=True)
    logger.info("Full database backup: %s", dest.name)
    return dest


def _insert_missing_prediction(item: dict) -> bool:
    from database import get_user_by_telegram_id, save_prediction, upsert_user

    telegram_id = int(item["telegram_id"])
    match_id = int(item["match_id"])
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        user = upsert_user(
            telegram_id,
            item.get("username"),
            item.get("display_name") or str(telegram_id),
        )

    from database import get_db

    with get_db() as conn:
        exists = conn.execute(
            """
            SELECT 1 FROM predictions
            WHERE user_id = ? AND match_id = ?
            LIMIT 1
            """,
            (user.id, match_id),
        ).fetchone()
    if exists:
        return False

    try:
        save_prediction(
            user.id,
            match_id,
            int(item["home_score"]),
            int(item["away_score"]),
            allow_closed=True,
        )
        return True
    except ValueError:
        return False


def restore_from_archive() -> int:
    if not ARCHIVE_PATH.is_file():
        return 0
    latest: dict[tuple[int, int], dict] = {}
    with ARCHIVE_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                key = (int(item["telegram_id"]), int(item["match_id"]))
                latest[key] = item
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    restored = 0
    for item in latest.values():
        if _insert_missing_prediction(item):
            restored += 1
    if restored:
        logger.info("Restored %d predictions from archive", restored)
    return restored


def _count_predictions_in_db(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        conn = sqlite3.connect(path)
        try:
            return int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def best_database_backup_path() -> Path | None:
    if not DB_BACKUPS_DIR.is_dir():
        return None
    best_path: Path | None = None
    best_count = -1
    for path in DB_BACKUPS_DIR.glob("bot_*.db"):
        count = _count_predictions_in_db(path)
        if count > best_count:
            best_count = count
            best_path = path
    return best_path


def restore_database_from_best_backup() -> bool:
    """Replace bot.db with the richest full-database copy when predictions were lost."""
    best_path = best_database_backup_path()
    if not best_path:
        return False

    best_count = _count_predictions_in_db(best_path)
    if best_count <= 0:
        return False

    current_count = _count_predictions_in_db(DATABASE_PATH) if DATABASE_PATH.is_file() else 0
    if current_count >= best_count:
        return False

    _ensure_dirs()
    shutil.copy2(best_path, DATABASE_PATH)
    logger.warning(
        "Restored full database from %s (%d predictions, was %d)",
        best_path.name,
        best_count,
        current_count,
    )
    return True


def recover_predictions_if_regressed() -> int:
    """If prediction count dropped or DB is empty, merge back from all local backups."""
    current = count_predictions()
    highwater = _load_highwater()

    if current == 0 or (highwater > 0 and current < highwater):
        if highwater > 0 and current < highwater:
            logger.warning(
                "Prediction count dropped (%d -> %d). Recovering from archive/backups.",
                highwater,
                current,
            )
        elif current == 0:
            logger.warning("Predictions database is empty. Attempting recovery.")

        restore_database_from_best_backup()
        current = count_predictions()

    if highwater > 0 and current >= highwater:
        update_highwater_mark()
        return 0

    restored = restore_from_archive()
    from prediction_backup import merge_missing_predictions_from_backup

    restored += merge_missing_predictions_from_backup()
    update_highwater_mark()
    return restored


def prepare_database_before_init() -> None:
    """Run before schema init — recover from full DB copy if wiped."""
    _ensure_dirs()
    current_count = _count_predictions_in_db(DATABASE_PATH) if DATABASE_PATH.is_file() else 0
    if not DATABASE_PATH.is_file() or current_count == 0:
        restore_database_from_best_backup()


def run_startup_persistence() -> dict[str, int | str | None]:
    """Backup, detect regression, recover. Never deletes predictions."""
    from prediction_backup import backup_predictions_if_needed, merge_missing_predictions_from_backup

    if count_predictions() == 0:
        try:
            from remote_prediction_backup import fetch_remote_backup

            fetched = fetch_remote_backup()
            if fetched:
                logger.info("Recovered %d predictions from remote backup", fetched)
        except Exception as exc:
            logger.warning("Remote backup fetch skipped: %s", exc)

    results: dict[str, int | str | None] = {
        "recovered": 0,
        "merged": 0,
        "count": count_predictions(),
        "db_backup": None,
        "json_backup": None,
        "storage_warning": None,
    }

    recovered = recover_predictions_if_regressed()
    results["recovered"] = recovered

    merged = merge_missing_predictions_from_backup()
    results["merged"] = merged

    db_backup = backup_database_file()
    if db_backup:
        results["db_backup"] = db_backup.name

    json_backup = backup_predictions_if_needed()
    if json_backup:
        results["json_backup"] = json_backup.name

    final_count = count_predictions()
    results["count"] = final_count
    update_highwater_mark()

    highwater = _load_highwater()
    if final_count == 0 and highwater == 0:
        has_local = bool(best_database_backup_path() or ARCHIVE_PATH.is_file())
        if not has_local:
            results["storage_warning"] = "ephemeral"
            logger.error(
                "No predictions and no local backups. "
                "Mount a Railway volume at /app/data or set REMOTE_PREDICTION_BACKUP_URL."
            )
    elif highwater > 0 and final_count < highwater:
        results["storage_warning"] = "partial_loss"
        logger.error(
            "Could not fully recover predictions (%d of %d). "
            "Check Railway volume at /app/data.",
            final_count,
            highwater,
        )

    return results
