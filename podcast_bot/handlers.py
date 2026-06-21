import logging
import re

from telegram import Update
from telegram.ext import ContextTypes

import database as db
import messages as msg
from rss import feed_url
from youtube_extractor import extract_youtube, extract_youtube_url, is_youtube_url

logger = logging.getLogger(__name__)

FEED_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(msg.WELCOME, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(msg.HELP, parse_mode="Markdown")


async def feeds_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    feeds = db.get_feeds_for_user(user_id)
    if not feeds:
        await update.message.reply_text(msg.FEED_LIST_EMPTY)
        return
    text = msg.FEED_LIST_HEADER
    for feed in feeds:
        count = db.episode_count(feed.id)
        text += msg.FEED_LIST_ITEM.format(
            title=feed.title,
            count=count,
            feed_url=feed_url(feed.id),
            feed_id=feed.id,
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not FEED_ID_RE.match(context.args[0]):
        await update.message.reply_text(msg.DELETE_USAGE, parse_mode="Markdown")
        return
    feed_id = context.args[0]
    if db.delete_feed(feed_id, update.effective_user.id):
        await update.message.reply_text(msg.FEED_DELETED)
    else:
        await update.message.reply_text(msg.FEED_NOT_FOUND)


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not FEED_ID_RE.match(context.args[0]):
        await update.message.reply_text(msg.REFRESH_USAGE, parse_mode="Markdown")
        return
    feed_id = context.args[0]
    feed = db.get_feed(feed_id)
    if not feed or feed.user_telegram_id != update.effective_user.id:
        await update.message.reply_text(msg.FEED_NOT_FOUND)
        return
    await update.message.reply_text(msg.REFRESHING)
    try:
        data = await extract_youtube(feed.source_url)
    except Exception:
        logger.exception("Refresh failed for %s", feed_id)
        await update.message.reply_text(msg.EXTRACTION_FAILED)
        return
    db.upsert_episodes(feed_id, data["episodes"])
    count = db.episode_count(feed_id)
    await update.message.reply_text(
        msg.REFRESH_DONE.format(title=feed.title, count=count),
        parse_mode="Markdown",
    )


async def _create_feed_from_url(
    update: Update,
    url: str,
) -> None:
    status = await update.message.reply_text(msg.PROCESSING)
    try:
        data = await extract_youtube(url)
    except Exception:
        logger.exception("Extraction failed for %s", url)
        await status.edit_text(msg.EXTRACTION_FAILED)
        return

    feed = db.create_feed(
        user_telegram_id=update.effective_user.id,
        source_url=url,
        source_type=data["source_type"],
        title=data["title"],
        description=data["description"],
        thumbnail_url=data["thumbnail_url"],
    )
    db.upsert_episodes(feed.id, data["episodes"])
    count = db.episode_count(feed.id)

    await status.edit_text(
        msg.FEED_CREATED.format(
            title=data["title"],
            source_type=data["source_type"],
            count=count,
            feed_url=feed_url(feed.id),
            feed_id=feed.id,
        ),
        parse_mode="Markdown",
    )


async def youtube_link_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    text = update.message.text or ""
    if not is_youtube_url(text):
        return
    url = extract_youtube_url(text)
    if not url:
        await update.message.reply_text(msg.INVALID_URL)
        return
    await _create_feed_from_url(update, url)
