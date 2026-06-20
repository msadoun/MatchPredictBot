import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from config import DATABASE_PATH
from scoring import calculate_points


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
    chat_filter = ""
    if group_chat_id is not None:
        chat_filter = "AND p.chat_id = ?"
        params.append(group_chat_id)
    else:
        chat_filter = "AND p.chat_id = 0"

    sql = f"""
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
        INNER JOIN predictions p ON p.user_id = u.id {chat_filter}
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


def _migrate_predictions_for_groups(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(predictions)").fetchall()
    }
    if "chat_id" in columns:
        return

    conn.executescript(
        """
        CREATE TABLE predictions_new (
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
        DROP TABLE predictions;
        ALTER TABLE predictions_new RENAME TO predictions;
        """
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


def list_matches(
    open_only: bool = False,
    limit: int | None = None,
    on_date: str | None = None,
) -> list[Match]:
    query = "SELECT * FROM matches"
    clauses: list[str] = []
    params: list[object] = []

    if on_date:
        clauses.append("kickoff_at LIKE ?")
        params.append(f"{on_date}%")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY kickoff_at ASC, id ASC"
    if limit is not None and not open_only:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    matches = [_row_to_match(row) for row in rows]
    if open_only:
        matches = [m for m in matches if match_accepts_predictions(m)]
        if limit is not None:
            matches = matches[:limit]
    return matches


def count_matches(open_only: bool = False, on_date: str | None = None) -> int:
    if open_only:
        return len(list_predictable_matches(on_date=on_date))

    query = "SELECT COUNT(*) FROM matches"
    clauses: list[str] = []
    params: list[object] = []

    if on_date:
        clauses.append("kickoff_at LIKE ?")
        params.append(f"{on_date}%")

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    with get_db() as conn:
        return int(conn.execute(query, params).fetchone()[0])


def match_has_started(match: Match, *, now: datetime | None = None) -> bool:
    if not match.kickoff_at:
        return False
    from worldcup2026 import kickoff_datetime

    check = now or datetime.utcnow()
    return kickoff_datetime(match.kickoff_at) <= check


def match_accepts_predictions(match: Match, *, now: datetime | None = None) -> bool:
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
) -> list[Match]:
    sync_match_open_flags()
    return list_matches(open_only=True, on_date=on_date, limit=limit)


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


def sync_match_open_flags() -> int:
    from worldcup2026 import kickoff_datetime

    now = datetime.utcnow()
    updated = 0
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, kickoff_at, home_score, away_score, is_open FROM matches"
        ).fetchall()
        for row in rows:
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
        conn.execute("UPDATE matches SET is_open = 0 WHERE id = ?", (match_id,))


def set_match_result(match_id: int, home_score: int, away_score: int) -> Match | None:
    with get_db() as conn:
        conn.execute(
            """
            UPDATE matches
            SET home_score = ?, away_score = ?, is_open = 0
            WHERE id = ?
            """,
            (home_score, away_score, match_id),
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


def save_prediction(
    user_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    *,
    group_chat_id: int = 0,
) -> Prediction:
    match = get_match(match_id)
    if not match or not match_accepts_predictions(match):
        raise ValueError("match_not_open")

    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO predictions (user_id, match_id, chat_id, home_score, away_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, match_id, chat_id) DO UPDATE SET
                home_score = excluded.home_score,
                away_score = excluded.away_score,
                updated_at = excluded.updated_at
            """,
            (user_id, match_id, group_chat_id, home_score, away_score, now, now),
        )
        row = conn.execute(
            """
            SELECT * FROM predictions
            WHERE user_id = ? AND match_id = ? AND chat_id = ?
            """,
            (user_id, match_id, group_chat_id),
        ).fetchone()
    return _row_to_prediction(row)


def get_user_predictions(
    user_id: int, group_chat_id: int | None = None
) -> list[tuple[Prediction, Match]]:
    chat_id = 0 if group_chat_id is None else group_chat_id
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                p.id AS p_id, p.user_id, p.match_id, p.home_score AS p_home,
                p.away_score AS p_away, p.points, p.created_at AS p_created,
                p.updated_at,
                m.id AS m_id, m.home_team, m.away_team, m.kickoff_at,
                m.home_score AS m_home, m.away_score AS m_away, m.is_open, m.created_at AS m_created
            FROM predictions p
            JOIN matches m ON m.id = p.match_id
            WHERE p.user_id = ? AND p.chat_id = ?
            ORDER BY m.id DESC
            """,
            (user_id, chat_id),
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
        match = Match(
            id=row["m_id"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            kickoff_at=row["kickoff_at"],
            home_score=row["m_home"],
            away_score=row["m_away"],
            is_open=bool(row["is_open"]),
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
            ON CONFLICT(chat_id, user_id) DO NOTHING
            """,
            (chat_id, user_id, now),
        )


def get_leaderboard(
    limit: int = 20, group_chat_id: int | None = None
) -> list[LeaderboardEntry]:
    sql, params = _leaderboard_sql(group_chat_id)
    with get_db() as conn:
        rows = conn.execute(f"{sql} LIMIT ?", (*params, limit)).fetchall()
    return [_row_to_leaderboard_entry(row, index) for index, row in enumerate(rows, start=1)]


def get_user_leaderboard_entry(
    telegram_id: int, group_chat_id: int | None = None
) -> LeaderboardEntry | None:
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
                    "SELECT COUNT(DISTINCT user_id) FROM predictions WHERE chat_id = 0"
                ).fetchone()[0]
            )
        return int(
            conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM predictions WHERE chat_id = ?",
                (group_chat_id,),
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
