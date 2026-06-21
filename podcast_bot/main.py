import asyncio
import logging
import sys

from aiohttp import web
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import database as db
from config import BOT_TOKEN, WEB_PORT
from handlers import (
    delete_command,
    feeds_command,
    help_command,
    refresh_command,
    start_command,
    youtube_link_handler,
)
from web_server import create_web_app

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Get started"),
            BotCommand("feeds", "List your RSS feeds"),
            BotCommand("refresh", "Sync new episodes"),
            BotCommand("delete", "Remove a feed"),
            BotCommand("help", "How to use this bot"),
        ]
    )


async def run() -> None:
    if not BOT_TOKEN:
        logger.error("Set PODCAST_BOT_TOKEN or TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    db.init_db()

    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    logger.info("RSS server listening on port %s", WEB_PORT)

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("feeds", feeds_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, youtube_link_handler)
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=["message"])

    try:
        await asyncio.Event().wait()
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
