import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from config import DATABASE_PATH


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Feed:
    id: str
    user_telegram_id: int
    source_url: str
    source_type: str
    title: str
    description: str
    thumbnail_url: str
    created_at: str
    updated_at: str


@dataclass
class Episode:
    id: str
    feed_id: str
    video_id: str
    title: str
    description: str
    published_at: str
    duration_seconds: int | None
    thumbnail_url: str
    position: int


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS feeds (
                id TEXT PRIMARY KEY,
                user_telegram_id INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                thumbnail_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
                video_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL,
                duration_seconds INTEGER,
                thumbnail_url TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL DEFAULT 0,
                UNIQUE(feed_id, video_id)
            );

            CREATE INDEX IF NOT EXISTS idx_feeds_user ON feeds(user_telegram_id);
            CREATE INDEX IF NOT EXISTS idx_episodes_feed ON episodes(feed_id);
            """
        )


@contextmanager
def _connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_feed(row: sqlite3.Row) -> Feed:
    return Feed(
        id=row["id"],
        user_telegram_id=row["user_telegram_id"],
        source_url=row["source_url"],
        source_type=row["source_type"],
        title=row["title"],
        description=row["description"],
        thumbnail_url=row["thumbnail_url"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_episode(row: sqlite3.Row) -> Episode:
    return Episode(
        id=row["id"],
        feed_id=row["feed_id"],
        video_id=row["video_id"],
        title=row["title"],
        description=row["description"],
        published_at=row["published_at"],
        duration_seconds=row["duration_seconds"],
        thumbnail_url=row["thumbnail_url"],
        position=row["position"],
    )


def create_feed(
    *,
    user_telegram_id: int,
    source_url: str,
    source_type: str,
    title: str,
    description: str = "",
    thumbnail_url: str = "",
) -> Feed:
    feed_id = str(uuid.uuid4())
    now = _utcnow()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO feeds (
                id, user_telegram_id, source_url, source_type,
                title, description, thumbnail_url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feed_id,
                user_telegram_id,
                source_url,
                source_type,
                title,
                description,
                thumbnail_url,
                now,
                now,
            ),
        )
    return get_feed(feed_id)  # type: ignore[return-value]


def upsert_episodes(feed_id: str, episodes: list[dict]) -> int:
    now = _utcnow()
    inserted = 0
    with _connect() as conn:
        for ep in episodes:
            episode_id = str(uuid.uuid4())
            cursor = conn.execute(
                """
                INSERT INTO episodes (
                    id, feed_id, video_id, title, description,
                    published_at, duration_seconds, thumbnail_url, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(feed_id, video_id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    published_at = excluded.published_at,
                    duration_seconds = excluded.duration_seconds,
                    thumbnail_url = excluded.thumbnail_url,
                    position = excluded.position
                """,
                (
                    episode_id,
                    feed_id,
                    ep["video_id"],
                    ep["title"],
                    ep.get("description", ""),
                    ep.get("published_at") or now,
                    ep.get("duration_seconds"),
                    ep.get("thumbnail_url", ""),
                    ep.get("position", 0),
                ),
            )
            if cursor.rowcount:
                inserted += 1
        conn.execute(
            "UPDATE feeds SET updated_at = ? WHERE id = ?",
            (now, feed_id),
        )
    return inserted


def get_feed(feed_id: str) -> Feed | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()
    return _row_to_feed(row) if row else None


def get_feeds_for_user(user_telegram_id: int) -> list[Feed]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM feeds WHERE user_telegram_id = ? ORDER BY created_at DESC",
            (user_telegram_id,),
        ).fetchall()
    return [_row_to_feed(row) for row in rows]


def get_episodes(feed_id: str) -> list[Episode]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM episodes
            WHERE feed_id = ?
            ORDER BY published_at DESC, position ASC
            """,
            (feed_id,),
        ).fetchall()
    return [_row_to_episode(row) for row in rows]


def get_episode(episode_id: str) -> Episode | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM episodes WHERE id = ?",
            (episode_id,),
        ).fetchone()
    return _row_to_episode(row) if row else None


def delete_feed(feed_id: str, user_telegram_id: int) -> bool:
    with _connect() as conn:
        cursor = conn.execute(
            "DELETE FROM feeds WHERE id = ? AND user_telegram_id = ?",
            (feed_id, user_telegram_id),
        )
        return cursor.rowcount > 0


def episode_count(feed_id: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM episodes WHERE feed_id = ?",
            (feed_id,),
        ).fetchone()
    return int(row["c"]) if row else 0
