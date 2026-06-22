import asyncio
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
    purge_legacy_km3na_group,
    clear_legacy_km3na_manual_points,
    score_all_finished_matches,
    sync_auto_group_points,
    sync_live_match_scores,
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
    clear_userdata_command,
    clear_groups_command,
    reset_points_command,
    import_excel_command,
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

SCORE_SYNC_INTERVAL_SEC = 60
SCORE_SYNC_FULL_SCAN_EVERY = 60  # full ESPN scan every N quick polls (~1 hour)


def _log_score_sync_stats(stats: dict[str, int], *, label: str = "Score sync") -> None:
    if stats["results_updated"]:
        logger.info("%s: imported %d new result(s) from ESPN", label, stats["results_updated"])
    if stats["predictions_scored"]:
        logger.info("%s: recalculated %d prediction point(s)", label, stats["predictions_scored"])
    if stats["espn_skipped"]:
        logger.info("%s: ESPN skipped %d unmatched result(s)", label, stats["espn_skipped"])


def _run_score_sync(application: Application, *, full_scan: bool) -> dict[str, int]:
    stats = sync_live_match_scores(full_scan=full_scan)
    _log_score_sync_stats(stats)
    return stats


async def _run_prediction_backups(application: Application) -> None:
    try:
        from prediction_persistence import backup_database_file, update_highwater_mark
        from prediction_backup import backup_predictions_if_needed
        from remote_prediction_backup import push_remote_backup
        from telegram_backup import send_backup_to_admins
        import time

        backup_predictions_if_needed()
        push_remote_backup()
        await send_backup_to_admins(application.bot)

        last = application.bot_data.get("last_prediction_backup", 0)
        now = time.time()
        if now - last >= 3600:
            backup_database_file()
            update_highwater_mark()
            push_remote_backup(force=True)
            await send_backup_to_admins(application.bot, force=True)
            application.bot_data["last_prediction_backup"] = now
    except Exception as exc:
        logger.warning("Periodic prediction backup failed: %s", exc)


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
    try:
        from telegram_backup import send_backup_to_admins

        await send_backup_to_admins(application.bot, force=True)
    except Exception as exc:
        logger.warning("Startup Telegram backup failed: %s", exc)

    if application.job_queue:
        application.job_queue.run_repeating(
            _sync_open_matches_job,
            interval=SCORE_SYNC_INTERVAL_SEC,
            first=10,
        )
        logger.info(
            "Scheduled match score sync every %ds (job queue)",
            SCORE_SYNC_INTERVAL_SEC,
        )
    else:
        asyncio.create_task(_score_sync_background_loop(application))
        logger.warning(
            "Job queue unavailable — using background score sync every %ds",
            SCORE_SYNC_INTERVAL_SEC,
        )


async def _score_sync_background_loop(application: Application) -> None:
    await asyncio.sleep(10)
    while True:
        try:
            await _sync_score_and_backups(application)
        except Exception as exc:
            logger.warning("Background score sync failed: %s", exc)
        await asyncio.sleep(SCORE_SYNC_INTERVAL_SEC)


async def _sync_score_and_backups(application: Application) -> None:
    ticks = int(application.bot_data.get("score_sync_ticks", 0)) + 1
    application.bot_data["score_sync_ticks"] = ticks
    full_scan = ticks % SCORE_SYNC_FULL_SCAN_EVERY == 0
    _run_score_sync(application, full_scan=full_scan)
    if PREDICTION_BACKFILLS.strip():
        from prediction_backfills import apply_prediction_backfills

        backfilled = apply_prediction_backfills(PREDICTION_BACKFILLS)
        if backfilled:
            logger.info("Applied %d prediction backfill(s) in sync job", backfilled)
    await _run_prediction_backups(application)


async def _sync_open_matches_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    application = context.application
    try:
        await _sync_score_and_backups(application)
    except Exception as exc:
        logger.warning("Score sync failed: %s", exc)


def main() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    from prediction_persistence import (
        consume_factory_reset_pending,
        prepare_database_before_init,
        run_startup_persistence,
        should_skip_data_recovery,
        should_skip_group_sync,
    )

    prepare_database_before_init()
    init_db()
    purged = purge_legacy_km3na_group()
    if purged:
        logger.info("Removed %d legacy K m3na group membership(s)", purged)
    cleared_pts = clear_legacy_km3na_manual_points()
    if cleared_pts:
        logger.info("Cleared legacy K m3na manual points for @M2usab")
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
    if persistence.get("storage_warning") == "ephemeral":
        logger.error(
            "DATA WILL BE LOST ON EVERY DEPLOY — add Railway volume at /app/data "
            "or REMOTE_PREDICTION_BACKUP_URL"
        )

    try:
        from excel_import import import_if_database_empty

        if should_skip_data_recovery():
            logger.info(
                "Factory reset — skipping Excel import and auto group standings."
            )
        elif should_skip_group_sync():
            logger.info("Groups cleared — skipping auto group registration.")
        else:
            excel_restore = import_if_database_empty()
            if excel_restore:
                logger.info(
                    "Excel restore on startup: merged=%d group_pts=%d",
                    excel_restore.merged,
                    excel_restore.group_points_applied,
                )
    except Exception as exc:
        logger.warning("Excel/group restore skipped: %s", exc)

    if not should_skip_data_recovery() and not should_skip_group_sync():
        registered = sync_auto_group_points()
        if registered:
            logger.info("Registered auto-point users in %d group(s)", registered)
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

    if consume_factory_reset_pending():
        logger.info("Factory reset complete — bot is in fresh-launch state.")

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
    app.add_handler(CommandHandler("setpoints", set_group_points_command))
    app.add_handler(CommandHandler("backuppredictions", backup_predictions_command))
    app.add_handler(CommandHandler("restorepredictions", restore_predictions_command))
    app.add_handler(CommandHandler("cleargroups", clear_groups_command))
    app.add_handler(CommandHandler("resetpoints", reset_points_command))
    app.add_handler(CommandHandler("clearuserdata", clear_userdata_command))
    app.add_handler(CommandHandler("resetall", clear_userdata_command))
    app.add_handler(CommandHandler("factoryreset", clear_userdata_command))
    app.add_handler(CommandHandler("importexcel", import_excel_command))
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
