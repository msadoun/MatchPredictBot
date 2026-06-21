import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import yt_dlp

from config import MAX_EPISODES

YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.)?"
    r"(youtube\.com/(watch\?[^\s]+|playlist\?[^\s]+|channel/[^\s]+|@[^\s/]+|c/[^\s]+)|"
    r"youtu\.be/[^\s]+)",
    re.IGNORECASE,
)


def is_youtube_url(text: str) -> bool:
    return bool(YOUTUBE_URL_RE.search(text.strip()))


def extract_youtube_url(text: str) -> str | None:
    match = YOUTUBE_URL_RE.search(text.strip())
    if not match:
        return None
    url = match.group(0)
    if not url.startswith("http"):
        url = "https://" + url
    return url


def _published_at(entry: dict[str, Any]) -> str:
    ts = entry.get("timestamp") or entry.get("release_timestamp")
    if ts:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    upload_date = entry.get("upload_date")
    if upload_date and len(upload_date) == 8:
        dt = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()


def _episode_from_entry(entry: dict[str, Any], position: int) -> dict[str, Any]:
    video_id = entry.get("id") or entry.get("url", "").split("=")[-1]
    return {
        "video_id": video_id,
        "title": entry.get("title") or f"Video {video_id}",
        "description": entry.get("description") or "",
        "published_at": _published_at(entry),
        "duration_seconds": entry.get("duration"),
        "thumbnail_url": entry.get("thumbnail") or "",
        "position": position,
    }


def _source_type(info: dict[str, Any]) -> str:
    if info.get("_type") == "playlist":
        if info.get("extractor_key") == "YoutubeTab" and info.get("playlist_count", 0) > 1:
            return "channel"
        return "playlist"
    return "video"


def _extract_sync(url: str) -> dict[str, Any]:
    flat_opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": MAX_EPISODES,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(flat_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Could not extract YouTube metadata.")

    source_type = _source_type(info)
    title = info.get("title") or info.get("channel") or "YouTube Podcast"
    description = info.get("description") or ""
    thumbnail = info.get("thumbnail") or ""

    entries = info.get("entries") or [info]
    entries = [e for e in entries if e and e.get("id")]

    if source_type == "video" and len(entries) == 1:
        full_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(full_opts) as ydl:
            full = ydl.extract_info(url, download=False)
        if full:
            entries = [full]
            title = full.get("title") or title
            description = full.get("description") or description
            thumbnail = full.get("thumbnail") or thumbnail

    episodes: list[dict[str, Any]] = []
    video_ids = [e["id"] for e in entries[:MAX_EPISODES]]

    if source_type != "video" and video_ids:
        detail_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(detail_opts) as ydl:
            for idx, video_id in enumerate(video_ids):
                try:
                    detail = ydl.extract_info(
                        f"https://www.youtube.com/watch?v={video_id}",
                        download=False,
                    )
                    if detail:
                        episodes.append(_episode_from_entry(detail, idx))
                except Exception:
                    episodes.append(
                        {
                            "video_id": video_id,
                            "title": f"Video {video_id}",
                            "description": "",
                            "published_at": datetime.now(timezone.utc).isoformat(),
                            "duration_seconds": None,
                            "thumbnail_url": "",
                            "position": idx,
                        }
                    )
    else:
        for idx, entry in enumerate(entries[:MAX_EPISODES]):
            episodes.append(_episode_from_entry(entry, idx))

    return {
        "source_type": source_type,
        "title": title,
        "description": description[:4000],
        "thumbnail_url": thumbnail,
        "episodes": episodes,
    }


async def extract_youtube(url: str) -> dict[str, Any]:
    return await asyncio.to_thread(_extract_sync, url)


def get_audio_url_sync(video_id: str) -> str:
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False,
        )
    if not info:
        raise ValueError("Could not resolve audio stream.")
    url = info.get("url")
    if not url:
        raise ValueError("No direct audio URL available.")
    return url


async def get_audio_url(video_id: str) -> str:
    return await asyncio.to_thread(get_audio_url_sync, video_id)
