import logging

from aiohttp import web

import database as db
from rss import build_rss
from youtube_extractor import get_audio_url

logger = logging.getLogger(__name__)


async def health_handler(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def rss_handler(request: web.Request) -> web.Response:
    feed_id = request.match_info["feed_id"]
    feed = db.get_feed(feed_id)
    if not feed:
        raise web.HTTPNotFound(text="Feed not found")
    episodes = db.get_episodes(feed_id)
    body = build_rss(feed, episodes)
    return web.Response(
        body=body,
        content_type="application/rss+xml",
        charset="utf-8",
    )


async def audio_handler(request: web.Request) -> web.Response:
    episode_id = request.match_info["episode_id"]
    episode = db.get_episode(episode_id)
    if not episode:
        raise web.HTTPNotFound(text="Episode not found")
    try:
        url = await get_audio_url(episode.video_id)
    except Exception as exc:
        logger.warning("Audio redirect failed for %s: %s", episode.video_id, exc)
        raise web.HTTPBadGateway(text="Could not resolve audio stream") from exc
    raise web.HTTPFound(url)


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/feed/{feed_id}.xml", rss_handler)
    app.router.add_get("/audio/{episode_id}", audio_handler)
    return app
