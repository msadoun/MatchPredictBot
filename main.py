import logging
import sys

from telegram import BotCommand, MenuButtonDefault
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, PREDICTION_BACKFILLS
from database import (
    backfill_match_kickoff_times,
    count_matches,
    ensure_world_cup_seeded,
    init_db,
    score_all_finished_matches,
    sync_auto_group_points,
    sync_match_open_flags,
)
from handlers import (
    add_match_command,
    admin_predictions_callback,
    admin_predictions_command,
    backup_predictions_command,
    close_match_command,
    open_match_command,
    group_welcome,
    help_command,
    leaderboard_command,
    leaderboard_callback,
    menu_callback,
    list_all_matches_command,
    load_worldcup_command,
    matches_command,
    my_predictions_command,
    predict_callback,
    predict_cancel_command,
    predict_command,
    predict_score_message,
    restore_predictions_command,
    set_group_points_command,
    set_prediction_command,
    set_result_command,
    sync_scores_command,
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
    if application.job_queue:
        application.job_queue.run_repeating(
            _sync_open_matches_job, interval=60, first=10
        )


async def _sync_open_matches_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    synced = sync_match_open_flags()
    if synced:
        logger.info("Updated open/closed status on %d matches", synced)
    try:
        stats = score_all_finished_matches()
        if stats["results_updated"]:
            logger.info("Synced %d new match results from ESPN", stats["results_updated"])
        if stats["predictions_scored"]:
            logger.info("Scored %d predictions", stats["predictions_scored"])
        if stats["espn_skipped"]:
            logger.info("ESPN skipped %d unmatched results", stats["espn_skipped"])
    except Exception as exc:
        logger.warning("Score sync failed: %s", exc)
    if PREDICTION_BACKFILLS.strip():
        from prediction_backfills import apply_prediction_backfills

        backfilled = apply_prediction_backfills(PREDICTION_BACKFILLS)
        if backfilled:
            logger.info("Applied %d prediction backfill(s) in sync job", backfilled)

    try:
        from prediction_persistence import backup_database_file, update_highwater_mark
        from prediction_backup import backup_predictions_if_needed
        import time

        last = context.application.bot_data.get("last_prediction_backup", 0)
        now = time.time()
        if now - last >= 3600:
            backup_predictions_if_needed()
            backup_database_file()
            update_highwater_mark()
            context.application.bot_data["last_prediction_backup"] = now
    except Exception as exc:
        logger.warning("Periodic prediction backup failed: %s", exc)


def main() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    init_db()
    from prediction_persistence import run_startup_persistence

    persistence = run_startup_persistence()
    if persistence["recovered"] or persistence["merged"]:
        logger.info(
            "Prediction recovery: restored=%d merged=%d total=%d",
            persistence["recovered"],
            persistence["merged"],
            persistence["count"],
        )
    else:
        logger.info("Predictions in database: %d", persistence["count"])
    auto_points = sync_auto_group_points()
    if auto_points:
        logger.info("Applied auto group points for %d member(s)", auto_points)
    seed_result = ensure_world_cup_seeded()
    if seed_result["added"]:
        logger.info("Seeded %d World Cup matches on startup", seed_result["added"])
    backfilled = backfill_match_kickoff_times()
    if backfilled:
        logger.info("Backfilled kickoff times on %d matches", backfilled)
    synced = sync_match_open_flags()
    if synced:
        logger.info("Updated open/closed status on %d matches", synced)
    try:
        stats = score_all_finished_matches()
        if stats["results_updated"]:
            logger.info("Imported %d finished match results from ESPN", stats["results_updated"])
        if stats["predictions_scored"]:
            logger.info("Scored %d predictions on startup", stats["predictions_scored"])
    except Exception as exc:
        logger.warning("Initial score sync failed: %s", exc)
    if PREDICTION_BACKFILLS.strip():
        from prediction_backfills import apply_prediction_backfills

        backfilled = apply_prediction_backfills(PREDICTION_BACKFILLS)
        if backfilled:
            logger.info("Applied %d missing prediction backfill(s)", backfilled)
    logger.info("%d matches open for predictions", count_matches(open_only=True))

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
    app.add_handler(CommandHandler("setprediction", set_prediction_command))
    app.add_handler(CommandHandler("allmatches", list_all_matches_command))
    app.add_handler(CommandHandler("closematch", close_match_command))
    app.add_handler(CommandHandler("openmatch", open_match_command))
    app.add_handler(CommandHandler("setgrouppoints", set_group_points_command))
    app.add_handler(CommandHandler("backuppredictions", backup_predictions_command))
    app.add_handler(CommandHandler("restorepredictions", restore_predictions_command))
    app.add_handler(CommandHandler("syncscores", sync_scores_command))
    app.add_handler(CommandHandler("adminpredictions", admin_predictions_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^lb:"))
    app.add_handler(CallbackQueryHandler(admin_predictions_callback, pattern=r"^adminpred:"))
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
