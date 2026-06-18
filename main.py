import logging
import sys

from telegram import BotCommand, MenuButtonDefault
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from database import init_db
from handlers import (
    add_match_command,
    close_match_command,
    group_welcome,
    help_command,
    leaderboard_command,
    menu_callback,
    list_all_matches_command,
    load_worldcup_command,
    matches_command,
    my_predictions_command,
    predict_callback,
    predict_cancel_command,
    predict_command,
    predict_score_message,
    set_result_command,
    stale_keyboard_handler,
    start_command,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    await application.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    await application.bot.set_my_commands(
        [
            BotCommand("start", "بدء البوت"),
            BotCommand("predict", "توقع نتيجة مباراة"),
            BotCommand("matches", "مباريات اليوم"),
            BotCommand("leaderboard", "لوحة المتصدرين"),
            BotCommand("mypredictions", "توقعاتك"),
            BotCommand("cancel", "إلغاء التوقع الحالي"),
            BotCommand("help", "المساعدة"),
        ]
    )


def main() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("matches", matches_command))
    app.add_handler(CommandHandler("predict", predict_command))
    app.add_handler(CommandHandler("cancel", predict_cancel_command))
    app.add_handler(CommandHandler("mypredictions", my_predictions_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("lb", leaderboard_command))
    app.add_handler(CommandHandler("addmatch", add_match_command))
    app.add_handler(CommandHandler("loadworldcup", load_worldcup_command))
    app.add_handler(CommandHandler("setresult", set_result_command))
    app.add_handler(CommandHandler("allmatches", list_all_matches_command))
    app.add_handler(CommandHandler("closematch", close_match_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(predict_callback, pattern=r"^pred:"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, stale_keyboard_handler),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, predict_score_message),
        group=1,
    )

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
