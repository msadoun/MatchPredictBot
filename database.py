import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from config import DATABASE_PATH
from scoring import calculate_points

logger = logging.getLogger(__name__)


@dataclass
class User:
    id: int
    telegram_id: int
    username: str | None
    display_name: str


@dataclass
class Match:
    id: int
    home_team: str
    away_team: str
    kickoff_at: str | None
    home_score: int | None
    away_score: int | None
    is_open: bool
    predictions_override: bool = False


@dataclass
class Prediction:
    id: int
    user_id: int
    match_id: int
    home_score: int
    away_score: int
    points: int | None


@dataclass
class LeaderboardEntry:
    rank: int
    display_name: str
    username: str | None
    total_points: int
    predictions_count: int
    exact_hits: int
    goal_hits: int
    winner_hits: int


def _leaderboard_sql(group_chat_id: int | None = None) -> tuple[str, list[object]]:
    params: list[object] = []
    if group_chat_id is not None:
        params.append(group_chat_id)
        params.append(group_chat_id)
        sql = """
        SELECT
            u.id,
            u.telegram_id,
            u.display_name,
            u.username,
            COALESCE(MAX(gmp.points), 0) + COALESCE(SUM(p.points), 0) AS total_points,
            COUNT(p.id) AS predictions_count,
            COALESCE(SUM(CASE WHEN p.points = 3 THEN 1 ELSE 0 END), 0) AS exact_hits,
            COALESCE(SUM(CASE WHEN p.points = 2 THEN 1 ELSE 0 END), 0) AS goal_hits,
            COALESCE(SUM(CASE WHEN p.points = 1 THEN 1 ELSE 0 END), 0) AS winner_hits
        FROM users u
        INNER JOIN group_members gm ON gm.user_id = u.id AND gm.chat_id = ?
        LEFT JOIN group_manual_points gmp ON gmp.user_id = u.id AND gmp.chat_id = ?
        LEFT JOIN predictions p ON p.user_id = u.id
        GROUP BY u.id
        HAVING COALESCE(MAX(gmp.points), 0) > 0 OR COUNT(p.id) > 0
        ORDER BY total_points DESC, predictions_count DESC, u.display_name ASC
        """
        return sql, params

    sql = """
        SELECT
            u.id,
            u.telegram_id,
            u.display_name,
            u.username,
            COALESCE(SUM(p.points), 0) AS total_points,
            COUNT(p.id) AS predictions_count,
            COALESCE(SUM(CASE WHEN p.points = 3 THEN 1 ELSE 0 END), 0) AS exact_hits,
            COALESCE(SUM(CASE WHEN p.points = 2 THEN 1 ELSE 0 END), 0) AS goal_hits,
            COALESCE(SUM(CASE WHEN p.points = 1 THEN 1 ELSE 0 END), 0) AS winner_hits
        FROM users u
        INNER JOIN predictions p ON p.user_id = u.id
        GROUP BY u.id
        ORDER BY total_points DESC, predictions_count DESC, u.display_name ASC
    """
    return sql, params


def _row_to_leaderboard_entry(row: sqlite3.Row, rank: int) -> LeaderboardEntry:
    return LeaderboardEntry(
        rank=rank,
        display_name=row["display_name"],
        username=row["username"],
        total_points=row["total_points"],
        predictions_count=row["predictions_count"],
        exact_hits=row["exact_hits"],
        goal_hits=row["goal_hits"],
        winner_hits=row["winner_hits"],
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    try:
        from prediction_backup import backup_before_migrations

        backup_before_migrations()
    except Exception as exc:
        logger.warning("Pre-migration prediction backup skipped: %s", exc)

    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                display_name TEXT NOT NULL,
                joined_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                kickoff_at TEXT,
                home_score INTEGER,
                away_score INTEGER,
                is_open INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                match_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL DEFAULT 0,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                points INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, match_id, chat_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS group_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _migrate_predictions_for_groups(conn)
        _migrate_users_active_group(conn)
        _migrate_predictions_global(conn)
        _migrate_prediction_drafts(conn)
        _migrate_predictions_override(conn)
        _migrate_prediction_exports(conn)
        _migrate_group_manual_points(conn)


@dataclass
class PredictionDraft:
    user_id: int
    match_id: int
    pick: str
    home_team: str
    away_team: str


def _migrate_prediction_drafts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_drafts (
            user_id INTEGER PRIMARY KEY,
            match_id INTEGER NOT NULL,
            pick TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def _migrate_predictions_override(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(matches)").fetchall()
    }
    if "predictions_override" not in columns:
        conn.execute(
            "ALTER TABLE matches ADD COLUMN predictions_override INTEGER NOT NULL DEFAULT 0"
        )


def _migrate_group_manual_points(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS group_manual_points (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def _migrate_prediction_exports(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            scope_key TEXT NOT NULL,
            scope_label TEXT NOT NULL,
            file_path TEXT NOT NULL,
            match_count INTEGER NOT NULL,
            user_count INTEGER NOT NULL,
            prediction_count INTEGER NOT NULL,
            saved_at TEXT NOT NULL,
            saved_by_telegram_id INTEGER
        )
        """
    )


def _migrate_predictions_global(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()
    }
    if "chat_id" in columns:
        conn.execute("UPDATE predictions SET chat_id = 0 WHERE chat_id != 0")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_predictions_user_match
        ON predictions(user_id, match_id)
        """
    )


def _migrate_users_active_group(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "active_group_chat_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN active_group_chat_id INTEGER")


def _migrate_predictions_for_groups(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()
    }
    if "chat_id" in columns:
        return
    conn.execute(
        "ALTER TABLE predictions ADD COLUMN chat_id INTEGER NOT NULL DEFAULT 0"
    )


def upsert_user(telegram_id: int, username: str | None, display_name: str) -> User:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, username, display_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                display_name = excluded.display_name
            """,
            (telegram_id, username, display_name, now),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    return _row_to_user(row)


def get_user_by_telegram_id(telegram_id: int) -> User | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
    return _row_to_user(row) if row else None


def get_user_by_username(username: str) -> User | None:
    handle = username.strip().lstrip("@")
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
            (handle,),
        ).fetchone()
    return _row_to_user(row) if row else None


def set_user_active_group(user_id: int, chat_id: int) -> None:
    if not chat_id:
        return
    register_group_member(chat_id, user_id)
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET active_group_chat_id = ? WHERE id = ?",
            (chat_id, user_id),
        )


def get_user_active_group(user_id: int) -> int | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT active_group_chat_id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row and row["active_group_chat_id"]:
        return int(row["active_group_chat_id"])
    return None


def add_match(home_team: str, away_team: str, kickoff_at: str | None = None) -> Match:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO matches (home_team, away_team, kickoff_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (home_team, away_team, kickoff_at, now),
        )
        match_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    return _row_to_match(row)


def get_match(match_id: int) -> Match | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    return _row_to_match(row) if row else None


def get_match_by_teams(home_team: str, away_team: str) -> Match | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM matches WHERE home_team = ? AND away_team = ?",
            (home_team, away_team),
        ).fetchone()
    return _row_to_match(row) if row else None


def resolve_user_ref(user_ref: str) -> User | None:
    ref = user_ref.strip().lstrip("@")
    if ref.isdigit():
        user = get_user_by_telegram_id(int(ref))
        if user:
            return user
    user = get_user_by_username(ref)
    if user:
        return user
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(display_name) = LOWER(?) LIMIT 1",
            (ref,),
        ).fetchone()
    if row:
        return _row_to_user(row)

    from config import M2USAB_TELEGRAM_ID, M2USAB_USERNAME

    if ref.lower() == M2USAB_USERNAME:
        user = get_user_by_telegram_id(M2USAB_TELEGRAM_ID)
        if user:
            return user
        return upsert_user(M2USAB_TELEGRAM_ID, M2USAB_USERNAME, "M2usab")
    return None


def set_group_manual_points(chat_id: int, user_id: int, points: int) -> None:
    """Set manual base points for a group — added on top of prediction points."""
    register_group_member(chat_id, user_id)
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO group_manual_points (chat_id, user_id, points, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                points = excluded.points,
                updated_at = excluded.updated_at
            """,
            (chat_id, user_id, points, now),
        )


def bulk_set_group_manual_points(
    chat_id: int,
    standings: list[tuple[str, int]],
) -> tuple[list[str], list[str]]:
    """Apply manual points. Returns (applied lines, not_found refs)."""
    applied: list[str] = []
    not_found: list[str] = []
    for user_ref, points in standings:
        user = resolve_user_ref(user_ref)
        if not user:
            not_found.append(user_ref)
            continue
        set_group_manual_points(chat_id, user.id, points)
        label = user.display_name
        if user.username:
            label += f" (@{user.username})"
        applied.append(f"{label}: {points}")
    return applied, not_found


def list_matches(
    open_only: bool = False,
    limit: int | None = None,
    on_date: str | None = None,
) -> list[Match]:
    from worldcup2026 import match_on_day

    query = "SELECT * FROM matches"
    clauses: list[str] = []
    params: list[object] = []

    if on_date:
        next_date = (
            datetime.fromisoformat(on_date) + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        clauses.append("(kickoff_at LIKE ? OR kickoff_at LIKE ?)")
        params.extend([f"{on_date}%", f"{next_date}%"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY kickoff_at ASC, id ASC"
    if limit is not None and not open_only and not on_date:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    matches = [_row_to_match(row) for row in rows]
    if on_date:
        matches = [
            m for m in matches if m.kickoff_at and match_on_day(m.kickoff_at, on_date)
        ]
    if open_only:
        matches = [m for m in matches if match_accepts_predictions(m)]
        if limit is not None:
            matches = matches[:limit]
    elif limit is not None and on_date:
        matches = matches[:limit]
    return matches


def count_matches(open_only: bool = False, on_date: str | None = None) -> int:
    if open_only:
        return len(list_predictable_matches(on_date=on_date))
    if on_date:
        return len(list_matches(open_only=False, on_date=on_date))
    with get_db() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0])


def match_has_started(match: Match, *, now: datetime | None = None) -> bool:
    if not match.kickoff_at:
        return False
    from worldcup2026 import kickoff_datetime

    check = now or datetime.utcnow()
    return kickoff_datetime(match.kickoff_at) <= check


def match_accepts_predictions(match: Match, *, now: datetime | None = None) -> bool:
    if match.predictions_override:
        return True
    if match.home_score is not None and match.away_score is not None:
        return False
    if match_has_started(match, now=now):
        return False
    if not match.is_open:
        return False
    return True


def list_predictable_matches(
    limit: int | None = 25,
    on_date: str | None = None,
    *,
    match_day_only: bool = True,
) -> list[Match]:
    from worldcup2026 import current_match_day

    sync_match_open_flags()
    day: str | None
    if match_day_only:
        day = on_date or current_match_day()
    else:
        day = on_date
    return list_matches(open_only=True, on_date=day, limit=limit)


def resolve_active_match_day(
    start_day: str | None = None,
    *,
    max_days: int = 45,
) -> str | None:
    """First match-day from start_day with at least one open predictable match."""
    from worldcup2026 import current_match_day

    day = start_day or current_match_day()
    for _ in range(max_days):
        if list_predictable_matches(on_date=day, limit=1, match_day_only=True):
            return day
        day = (datetime.fromisoformat(day) + timedelta(days=1)).strftime("%Y-%m-%d")
    return None


def list_active_day_predictable_matches(
    limit: int | None = 25,
) -> tuple[str | None, list[Match]]:
    day = resolve_active_match_day()
    if not day:
        return None, []
    return day, list_predictable_matches(on_date=day, limit=limit, match_day_only=True)


def backfill_match_kickoff_times() -> int:
    from worldcup2026 import WORLD_CUP_2026_FIXTURES, kickoff_label

    by_date: dict[tuple[str, str, str], str] = {}
    by_pair: dict[tuple[str, str], str] = {}
    for fixture in WORLD_CUP_2026_FIXTURES:
        label = kickoff_label(fixture)
        by_date[(fixture.home, fixture.away, fixture.date)] = label
        by_pair[(fixture.home, fixture.away)] = label

    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, home_team, away_team, kickoff_at FROM matches"
        ).fetchall()
        for row in rows:
            kickoff = row["kickoff_at"] or ""
            date_part = kickoff.split(" · ", 1)[0].strip()
            date_only = date_part[:10] if date_part else ""
            new_kickoff = by_date.get(
                (row["home_team"], row["away_team"], date_only)
            ) or by_pair.get((row["home_team"], row["away_team"]))
            if new_kickoff and new_kickoff != kickoff:
                conn.execute(
                    "UPDATE matches SET kickoff_at = ? WHERE id = ?",
                    (new_kickoff, row["id"]),
                )
                updated += 1
    return updated


def seed_world_cup_matches() -> dict[str, int]:
    from worldcup2026 import WORLD_CUP_2026_FIXTURES, kickoff_datetime, kickoff_label

    now = datetime.utcnow()
    added = 0
    skipped = 0
    closed = 0

    with get_db() as conn:
        for fixture in WORLD_CUP_2026_FIXTURES:
            kickoff_at = kickoff_label(fixture)
            existing = conn.execute(
                """
                SELECT id FROM matches
                WHERE home_team = ? AND away_team = ? AND kickoff_at LIKE ?
                """,
                (fixture.home, fixture.away, f"{fixture.date}%"),
            ).fetchone()
            if existing:
                skipped += 1
                continue

            is_open = kickoff_datetime(kickoff_at) > now
            if not is_open:
                closed += 1

            conn.execute(
                """
                INSERT INTO matches (home_team, away_team, kickoff_at, is_open, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    fixture.home,
                    fixture.away,
                    kickoff_at,
                    int(is_open),
                    now.isoformat(),
                ),
            )
            added += 1

    return {"added": added, "skipped": skipped, "closed": closed}


def ensure_world_cup_seeded() -> dict[str, int]:
    if count_matches() == 0:
        return seed_world_cup_matches()
    return {"added": 0, "skipped": count_matches(), "closed": 0}


def _row_get(row: sqlite3.Row, key: str, default: object = None) -> object:
    try:
        return row[key]
    except (IndexError, KeyError):
        return default


def sync_match_open_flags() -> int:
    from worldcup2026 import kickoff_datetime

    now = datetime.utcnow()
    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, kickoff_at, home_score, away_score, is_open, predictions_override
            FROM matches
            """
        ).fetchall()
        for row in rows:
            if bool(_row_get(row, "predictions_override", 0)):
                continue
            if row["home_score"] is not None and row["away_score"] is not None:
                should_open = False
            elif not row["kickoff_at"]:
                should_open = True
            else:
                should_open = kickoff_datetime(row["kickoff_at"]) > now
            if bool(row["is_open"]) != should_open:
                conn.execute(
                    "UPDATE matches SET is_open = ? WHERE id = ?",
                    (int(should_open), row["id"]),
                )
                updated += 1
    return updated


def migrate_team_names_to_arabic() -> dict[str, int]:
    from teams_ar import GROUP_EN_TO_AR, TEAM_EN_TO_AR

    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, home_team, away_team, kickoff_at FROM matches"
        ).fetchall()
        for row in rows:
            home = TEAM_EN_TO_AR.get(row["home_team"], row["home_team"])
            away = TEAM_EN_TO_AR.get(row["away_team"], row["away_team"])
            kickoff = row["kickoff_at"]
            if kickoff and " · " in kickoff:
                date_part, group_part = kickoff.split(" · ", 1)
                group_part = GROUP_EN_TO_AR.get(group_part, group_part)
                kickoff = f"{date_part} · {group_part}"

            if (
                home != row["home_team"]
                or away != row["away_team"]
                or kickoff != row["kickoff_at"]
            ):
                conn.execute(
                    """
                    UPDATE matches
                    SET home_team = ?, away_team = ?, kickoff_at = ?
                    WHERE id = ?
                    """,
                    (home, away, kickoff, row["id"]),
                )
                updated += 1

    return {"updated": updated}


def close_match(match_id: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE matches SET is_open = 0, predictions_override = 0 WHERE id = ?",
            (match_id,),
        )


def open_match(match_id: int, *, clear_result: bool = False) -> Match | None:
    from results_sync import restore_match_result_from_espn

    match = get_match(match_id)
    if not match:
        return None
    with get_db() as conn:
        if clear_result:
            conn.execute(
                """
                UPDATE matches
                SET is_open = 1, predictions_override = 1,
                    home_score = NULL, away_score = NULL
                WHERE id = ?
                """,
                (match_id,),
            )
        else:
            conn.execute(
                """
                UPDATE matches
                SET is_open = 1, predictions_override = 1
                WHERE id = ?
                """,
                (match_id,),
            )

    restore_match_result_from_espn(match_id)
    recalculate_all_prediction_points()
    return get_match(match_id)


def set_match_result(match_id: int, home_score: int, away_score: int) -> Match | None:
    existing = get_match(match_id)
    keep_open = bool(existing and existing.predictions_override)
    with get_db() as conn:
        conn.execute(
            """
            UPDATE matches
            SET home_score = ?, away_score = ?, is_open = ?
            WHERE id = ?
            """,
            (home_score, away_score, int(keep_open), match_id),
        )
        predictions = conn.execute(
            "SELECT id, home_score, away_score FROM predictions WHERE match_id = ?",
            (match_id,),
        ).fetchall()
        for prediction in predictions:
            points = calculate_points(
                prediction["home_score"],
                prediction["away_score"],
                home_score,
                away_score,
            )
            conn.execute(
                "UPDATE predictions SET points = ? WHERE id = ?",
                (points, prediction["id"]),
            )
        row = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    return _row_to_match(row) if row else None


def score_all_finished_matches() -> dict[str, int]:
    """Import ESPN results and recalculate points for every user prediction."""
    from results_sync import restore_missing_override_results, sync_match_results_from_espn

    espn = sync_match_results_from_espn()
    restored = restore_missing_override_results()
    recalculated = recalculate_all_prediction_points()
    return {
        "results_updated": espn["updated"],
        "results_rescored": espn.get("rescored", 0),
        "override_restored": restored,
        "predictions_scored": recalculated,
        "espn_skipped": espn["skipped"],
    }


def rescore_match_predictions(match_id: int) -> int:
    """Recalculate points for every prediction on a finished match."""
    match = get_match(match_id)
    if not match or match.home_score is None or match.away_score is None:
        return 0
    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, home_score, away_score FROM predictions WHERE match_id = ?",
            (match_id,),
        ).fetchall()
        for row in rows:
            points = calculate_points(
                row["home_score"],
                row["away_score"],
                match.home_score,
                match.away_score,
            )
            conn.execute(
                "UPDATE predictions SET points = ? WHERE id = ?",
                (points, row["id"]),
            )
            updated += 1
    return updated


def recalculate_all_prediction_points() -> int:
    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.home_score, p.away_score, m.home_score AS ah, m.away_score AS aa
            FROM predictions p
            INNER JOIN matches m ON m.id = p.match_id
            WHERE m.home_score IS NOT NULL AND m.away_score IS NOT NULL
            """
        ).fetchall()
        for row in rows:
            points = calculate_points(
                row["home_score"],
                row["away_score"],
                row["ah"],
                row["aa"],
            )
            conn.execute(
                "UPDATE predictions SET points = ? WHERE id = ?",
                (points, row["id"]),
            )
            updated += 1
    return updated


def save_prediction(
    user_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    *,
    allow_closed: bool = False,
) -> tuple[Prediction, bool]:
    """Save one global prediction per user per match. Returns (prediction, was_update)."""
    match = get_match(match_id)
    if not match:
        raise ValueError("match_not_found")
    if not allow_closed and not match_accepts_predictions(match):
        raise ValueError("match_not_open")

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id FROM predictions
            WHERE user_id = ? AND match_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (user_id, match_id),
        ).fetchall()
        was_update = bool(rows)
        if rows:
            keep_id = rows[0]["id"]
            if len(rows) > 1:
                logger.warning(
                    "Duplicate predictions for user %s match %s — keeping id %s only",
                    user_id,
                    match_id,
                    keep_id,
                )
            if match.home_score is not None and match.away_score is not None:
                points = calculate_points(
                    home_score,
                    away_score,
                    match.home_score,
                    match.away_score,
                )
                conn.execute(
                    """
                    UPDATE predictions
                    SET home_score = ?, away_score = ?, chat_id = 0, updated_at = ?, points = ?
                    WHERE id = ?
                    """,
                    (home_score, away_score, now, points, keep_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE predictions
                    SET home_score = ?, away_score = ?, chat_id = 0, updated_at = ?, points = NULL
                    WHERE id = ?
                    """,
                    (home_score, away_score, now, keep_id),
                )
        else:
            cursor = conn.execute(
                """
                INSERT INTO predictions (user_id, match_id, chat_id, home_score, away_score, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, ?, ?)
                """,
                (user_id, match_id, home_score, away_score, now, now),
            )
            keep_id = cursor.lastrowid
            if match.home_score is not None and match.away_score is not None:
                points = calculate_points(
                    home_score,
                    away_score,
                    match.home_score,
                    match.away_score,
                )
                conn.execute(
                    "UPDATE predictions SET points = ? WHERE id = ?",
                    (points, keep_id),
                )

        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?",
            (keep_id,),
        ).fetchone()
    clear_prediction_draft(user_id)
    prediction = _row_to_prediction(row)
    try:
        with get_db() as conn:
            user_row = conn.execute(
                "SELECT telegram_id, username, display_name FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if user_row:
            from prediction_persistence import append_prediction_archive, update_highwater_mark

            append_prediction_archive(
                telegram_id=int(user_row["telegram_id"]),
                username=user_row["username"],
                display_name=user_row["display_name"],
                match_id=match_id,
                home_score=home_score,
                away_score=away_score,
                points=prediction.points,
            )
            update_highwater_mark()
            try:
                from remote_prediction_backup import push_remote_backup

                push_remote_backup()
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Prediction archive write failed: %s", exc)
    return prediction, was_update


def link_prediction_to_active_group(user_id: int, chat_id: int | None = None) -> None:
    """Register the user in their active group so predictions show on group leaderboard."""
    group_chat_id = chat_id or get_user_active_group(user_id)
    if group_chat_id:
        register_group_member(group_chat_id, user_id)


def save_prediction_draft(
    user_id: int,
    match_id: int,
    pick: str,
    home_team: str,
    away_team: str,
) -> None:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO prediction_drafts (user_id, match_id, pick, home_team, away_team, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                match_id = excluded.match_id,
                pick = excluded.pick,
                home_team = excluded.home_team,
                away_team = excluded.away_team,
                updated_at = excluded.updated_at
            """,
            (user_id, match_id, pick, home_team, away_team, now),
        )


def get_prediction_draft(user_id: int) -> PredictionDraft | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM prediction_drafts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return PredictionDraft(
        user_id=row["user_id"],
        match_id=row["match_id"],
        pick=row["pick"],
        home_team=row["home_team"],
        away_team=row["away_team"],
    )


def clear_prediction_draft(user_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM prediction_drafts WHERE user_id = ?", (user_id,))


def user_has_prediction(user_id: int, match_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM predictions WHERE user_id = ? AND match_id = ? LIMIT 1",
            (user_id, match_id),
        ).fetchone()
    return row is not None


def get_user_prediction(user_id: int, match_id: int) -> Prediction | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE user_id = ? AND match_id = ? LIMIT 1",
            (user_id, match_id),
        ).fetchone()
    return _row_to_prediction(row) if row else None


def get_user_predictions(user_id: int) -> list[tuple[Prediction, Match]]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id AS p_id, p.user_id, p.match_id, p.home_score AS p_home,
                p.away_score AS p_away, p.points, p.created_at AS p_created,
                p.updated_at,
                m.id AS m_id, m.home_team, m.away_team, m.kickoff_at,
                m.home_score AS m_home, m.away_score AS m_away, m.is_open,
                m.predictions_override, m.created_at AS m_created
            FROM predictions p
            LEFT JOIN matches m ON m.id = p.match_id
            WHERE p.user_id = ?
            ORDER BY COALESCE(m.kickoff_at, p.updated_at) ASC, p.match_id ASC
            """,
            (user_id,),
        ).fetchall()

    results: list[tuple[Prediction, Match]] = []
    for row in rows:
        prediction = Prediction(
            id=row["p_id"],
            user_id=row["user_id"],
            match_id=row["match_id"],
            home_score=row["p_home"],
            away_score=row["p_away"],
            points=row["points"],
        )
        if row["m_id"] is not None:
            match = Match(
                id=row["m_id"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                kickoff_at=row["kickoff_at"],
                home_score=row["m_home"],
                away_score=row["m_away"],
                is_open=bool(row["is_open"]),
                predictions_override=bool(row["predictions_override"] or 0),
            )
        else:
            match = Match(
                id=row["match_id"],
                home_team="?",
                away_team="?",
                kickoff_at=None,
                home_score=None,
                away_score=None,
                is_open=False,
            )
        results.append((prediction, match))
    return results


def register_group_member(chat_id: int, user_id: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO group_members (chat_id, user_id, joined_at)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET joined_at = excluded.joined_at
            """,
            (chat_id, user_id, now),
        )
    apply_auto_group_points(chat_id, user_id)


def ensure_auto_point_user() -> User:
    """Ensure @M2usab exists in users table for auto base points."""
    from config import M2USAB_TELEGRAM_ID, M2USAB_USERNAME

    user = get_user_by_telegram_id(M2USAB_TELEGRAM_ID)
    if user:
        return user
    return upsert_user(M2USAB_TELEGRAM_ID, M2USAB_USERNAME, "M2usab")


def ensure_auto_users_in_configured_groups() -> int:
    """Register auto-point users in groups configured via env chat IDs."""
    from config import configured_group_chat_ids

    chat_ids = configured_group_chat_ids()
    if not chat_ids:
        return 0

    user = ensure_auto_point_user()
    for chat_id in chat_ids:
        register_group_member(chat_id, user.id)
    return len(chat_ids)


def refresh_group_auto_points(chat_id: int) -> None:
    """Re-apply auto base points for every member when showing a group leaderboard."""
    ensure_auto_users_in_configured_groups()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_id FROM group_members WHERE chat_id = ?",
            (chat_id,),
        ).fetchall()
    for row in rows:
        apply_auto_group_points(chat_id, int(row["user_id"]))


def apply_auto_group_points(chat_id: int, user_id: int) -> bool:
    """Set configured auto base points for a user in a group (added to prediction pts)."""
    from group_auto_points import auto_group_points_for_user

    with get_db() as conn:
        row = conn.execute(
            "SELECT telegram_id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return False

    points = auto_group_points_for_user(
        telegram_id=int(row["telegram_id"]),
        username=row["username"],
    )
    if points is None:
        return False

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO group_manual_points (chat_id, user_id, points, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                points = excluded.points,
                updated_at = excluded.updated_at
            """,
            (chat_id, user_id, points, now),
        )
    return True


def sync_auto_group_points() -> int:
    """Apply auto points for all known group members (e.g. @M2usab)."""
    updated = ensure_auto_users_in_configured_groups()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT gm.chat_id, gm.user_id, u.telegram_id, u.username
            FROM group_members gm
            INNER JOIN users u ON u.id = gm.user_id
            """
        ).fetchall()
    for row in rows:
        if apply_auto_group_points(int(row["chat_id"]), int(row["user_id"])):
            updated += 1
    return updated


def get_user_group_chat_ids(user_id: int) -> list[int]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT chat_id FROM group_members
            WHERE user_id = ?
            ORDER BY joined_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [int(row["chat_id"]) for row in rows]


def get_leaderboard(
    limit: int = 20, group_chat_id: int | None = None
) -> list[LeaderboardEntry]:
    if group_chat_id is not None:
        refresh_group_auto_points(group_chat_id)
    recalculate_all_prediction_points()
    sql, params = _leaderboard_sql(group_chat_id)
    with get_db() as conn:
        rows = conn.execute(f"{sql} LIMIT ?", (*params, limit)).fetchall()
    return [_row_to_leaderboard_entry(row, index) for index, row in enumerate(rows, start=1)]


def get_user_leaderboard_entry(
    telegram_id: int, group_chat_id: int | None = None
) -> LeaderboardEntry | None:
    if group_chat_id is not None:
        refresh_group_auto_points(group_chat_id)
    recalculate_all_prediction_points()
    sql, params = _leaderboard_sql(group_chat_id)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()

    for index, row in enumerate(rows, start=1):
        if row["telegram_id"] == telegram_id:
            return _row_to_leaderboard_entry(row, index)
    return None


def count_leaderboard_participants(group_chat_id: int | None = None) -> int:
    with get_db() as conn:
        if group_chat_id is None:
            return int(
                conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM predictions"
                ).fetchone()[0]
            )
        return int(
            conn.execute(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT u.id
                    FROM users u
                    INNER JOIN group_members gm ON gm.user_id = u.id AND gm.chat_id = ?
                    LEFT JOIN group_manual_points gmp
                        ON gmp.user_id = u.id AND gmp.chat_id = ?
                    LEFT JOIN predictions p ON p.user_id = u.id
                    GROUP BY u.id
                    HAVING COALESCE(MAX(gmp.points), 0) > 0 OR COUNT(p.id) > 0
                )
                """,
                (group_chat_id, group_chat_id),
            ).fetchone()[0]
        )


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        telegram_id=row["telegram_id"],
        username=row["username"],
        display_name=row["display_name"],
    )


def _row_to_match(row: sqlite3.Row) -> Match:
    return Match(
        id=row["id"],
        home_team=row["home_team"],
        away_team=row["away_team"],
        kickoff_at=row["kickoff_at"],
        home_score=row["home_score"],
        away_score=row["away_score"],
        is_open=bool(row["is_open"]),
        predictions_override=bool(_row_get(row, "predictions_override", 0)),
    )


def _row_to_prediction(row: sqlite3.Row) -> Prediction:
    return Prediction(
        id=row["id"],
        user_id=row["user_id"],
        match_id=row["match_id"],
        home_score=row["home_score"],
        away_score=row["away_score"],
        points=row["points"],
    )
