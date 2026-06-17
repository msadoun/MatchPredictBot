from datetime import datetime
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_USER_IDS
import messages as msg
from user_messaging import edit_or_send_user, is_group_chat, reply_to_user


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def chat_menu_markup(update: Update) -> ReplyKeyboardMarkup | None:
    return None if is_group_chat(update) else MAIN_MENU


BOT_USERNAME = "FTM3naBot"


MAIN_MENU = ReplyKeyboardMarkup(
    [
        [msg.MENU_PREDICT, msg.MENU_MATCHES],
        [msg.MENU_LEADERBOARD, msg.MENU_MY_PREDICTIONS],
    ],
    resize_keyboard=True,
)

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def format_leaderboard_text(
    entries: list[db.LeaderboardEntry],
    *,
    viewer_entry: db.LeaderboardEntry | None = None,
    total_participants: int = 0,
) -> str:
    lines = [msg.LEADERBOARD_TITLE]

    if not entries:
        lines.append(msg.LEADERBOARD_EMPTY)
        return "\n".join(lines)

    for entry in entries:
        medal = RANK_MEDALS.get(entry.rank, f"{entry.rank}.")
        name = entry.display_name
        if entry.username:
            name += f" (@{entry.username})"
        lines.append(
            msg.LEADERBOARD_ROW.format(
                medal=medal,
                name=name,
                points=entry.total_points,
                count=entry.predictions_count,
                exact=entry.exact_hits,
                goals=entry.goal_hits,
                winner=entry.winner_hits,
            )
        )

    if total_participants > len(entries):
        lines.append(
            msg.LEADERBOARD_TOP_N.format(shown=len(entries), total=total_participants)
        )

    if viewer_entry:
        lines.append(
            msg.YOUR_RANK.format(
                rank=viewer_entry.rank,
                points=viewer_entry.total_points,
                count=viewer_entry.predictions_count,
            )
        )

    lines.append(msg.SCORING_RULES)
    return "\n".join(lines)


async def send_leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    viewer_telegram_id: int | None = None,
) -> None:
    entries = db.get_leaderboard(limit=15)
    total = db.count_leaderboard_participants()
    viewer_entry = (
        db.get_user_leaderboard_entry(viewer_telegram_id) if viewer_telegram_id else None
    )
    text = format_leaderboard_text(
        entries, viewer_entry=viewer_entry, total_participants=total
    )

    await reply_to_user(
        update,
        context,
        text,
        bot_username=BOT_USERNAME,
        menu_markup=chat_menu_markup(update),
    )


def format_match(match: db.Match) -> str:
    status = msg.STATUS_OPEN if match.is_open else msg.STATUS_CLOSED
    line = f"#{match.id} {match.home_team} {msg.VS} {match.away_team} ({status})"
    if match.kickoff_at:
        line += f"\n   {msg.KICKOFF}: {match.kickoff_at}"
    if match.home_score is not None and match.away_score is not None:
        line += f"\n   {msg.RESULT}: {match.home_score}-{match.away_score}"
    return line


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    display_name = user.full_name or user.username or str(user.id)
    db.upsert_user(user.id, user.username, display_name)

    await reply_to_user(
        update,
        context,
        msg.START_TEXT,
        bot_username=BOT_USERNAME,
        menu_markup=chat_menu_markup(update),
    )


async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not context.bot:
        return

    bot_id = context.bot.id
    for member in message.new_chat_members:
        if member.id != bot_id:
            continue

        await update.message.reply_text(msg.GROUP_WELCOME.format(bot=BOT_USERNAME))
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    on_date = context.args[0] if context.args else today

    try:
        datetime.fromisoformat(on_date)
    except ValueError:
        await reply_to_user(
            update, context, msg.MATCHES_USAGE, bot_username=BOT_USERNAME
        )
        return

    matches = db.list_matches(open_only=True, on_date=on_date, limit=25)
    total = db.count_matches(open_only=True, on_date=on_date)

    if not matches:
        await reply_to_user(
            update,
            context,
            msg.NO_MATCHES_DATE.format(date=on_date),
            bot_username=BOT_USERNAME,
        )
        return

    lines = [msg.OPEN_MATCHES_HEADER.format(date=on_date)] + [
        format_match(match) for match in matches
    ]
    if total > len(matches):
        lines.append(msg.SHOWING_MATCHES.format(shown=len(matches), total=total))
    await reply_to_user(
        update, context, "\n\n".join(lines), bot_username=BOT_USERNAME
    )


def _ensure_participant(update: Update) -> db.User | None:
    user = update.effective_user
    if not user:
        return None
    participant = db.get_user_by_telegram_id(user.id)
    if participant:
        return participant
    return db.upsert_user(
        user.id, user.username, user.full_name or user.username or str(user.id)
    )


def _clear_prediction_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "prediction_step",
        "prediction_match_id",
        "prediction_pick",
        "prediction_home_team",
        "prediction_away_team",
        "prediction_prompt_id",
    ):
        context.user_data.pop(key, None)


def _winner_keyboard(match_id: int, home_team: str, away_team: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(home_team, callback_data=f"pred:pick:{match_id}:home")],
            [InlineKeyboardButton(msg.DRAW, callback_data=f"pred:pick:{match_id}:draw")],
            [InlineKeyboardButton(away_team, callback_data=f"pred:pick:{match_id}:away")],
        ]
    )


def _match_picker_keyboard(matches: list[db.Match]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"#{match.id} {match.home_team} {msg.VS} {match.away_team}",
                callback_data=f"pred:match:{match.id}",
            )
        ]
        for match in matches
    ]
    return InlineKeyboardMarkup(rows)


async def _prompt_winner_pick(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    match: db.Match,
    *,
    edit: bool = False,
) -> None:
    text = (
        msg.MATCH_HEADER.format(
            id=match.id, home=match.home_team, vs=msg.VS, away=match.away_team
        )
        + f"\n\n{msg.WHO_WINS}"
    )
    keyboard = _winner_keyboard(match.id, match.home_team, match.away_team)
    if edit and update.callback_query:
        await edit_or_send_user(
            update, context, text, keyboard, bot_username=BOT_USERNAME
        )
    else:
        await reply_to_user(
            update, context, text, keyboard, bot_username=BOT_USERNAME
        )


def _parse_score_input(text: str) -> tuple[int, int] | None:
    cleaned = text.strip().replace(":", "-")
    match = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", cleaned)
    if not match:
        return None
    home_score, away_score = int(match.group(1)), int(match.group(2))
    if home_score < 0 or away_score < 0:
        return None
    return home_score, away_score


def _scores_from_pick(
    pick: str, first: int, second: int
) -> tuple[int, int] | str:
    if pick == "draw":
        if first != second:
            return msg.DRAW_SCORES_MUST_EQUAL
        return first, second

    if first == second:
        return msg.UNEAQUAL_SCORES_FOR_WINNER

    high, low = max(first, second), min(first, second)
    if pick == "home":
        return high, low
    return low, high


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    _ensure_participant(update)
    _clear_prediction_state(context)

    if context.args:
        try:
            match_id = int(context.args[0])
        except ValueError:
            await reply_to_user(
                update, context, msg.MATCH_ID_NOT_NUMBER, bot_username=BOT_USERNAME
            )
            return

        match = db.get_match(match_id)
        if not match:
            await reply_to_user(
                update,
                context,
                msg.MATCH_NOT_FOUND.format(id=match_id),
                bot_username=BOT_USERNAME,
            )
            return
        if not match.is_open:
            await reply_to_user(
                update,
                context,
                msg.MATCH_CLOSED.format(id=match_id),
                bot_username=BOT_USERNAME,
            )
            return

        await _prompt_winner_pick(update, context, match)
        return

    today = datetime.utcnow().strftime("%Y-%m-%d")
    matches = db.list_matches(open_only=True, on_date=today, limit=25)
    if not matches:
        await reply_to_user(
            update,
            context,
            msg.NO_MATCHES_TODAY.format(date=today),
            bot_username=BOT_USERNAME,
        )
        return

    await reply_to_user(
        update,
        context,
        msg.CHOOSE_MATCH.format(date=today),
        reply_markup=_match_picker_keyboard(matches),
        bot_username=BOT_USERNAME,
    )


async def predict_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("prediction_step") != "entering_score":
        await reply_to_user(
            update, context, msg.NOTHING_TO_CANCEL, bot_username=BOT_USERNAME
        )
        return
    _clear_prediction_state(context)
    await reply_to_user(
        update, context, msg.PREDICTION_CANCELLED, bot_username=BOT_USERNAME
    )


async def predict_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    user = update.effective_user
    if not user:
        return

    _ensure_participant(update)
    parts = query.data.split(":")
    if len(parts) < 3 or parts[0] != "pred":
        return

    if parts[1] == "match" and len(parts) == 3:
        try:
            match_id = int(parts[2])
        except ValueError:
            return

        match = db.get_match(match_id)
        if not match or not match.is_open:
            await edit_or_send_user(
                update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
            )
            return

        await _prompt_winner_pick(update, context, match, edit=True)
        return

    if parts[1] == "pick" and len(parts) == 4:
        try:
            match_id = int(parts[2])
        except ValueError:
            return

        pick = parts[3]
        if pick not in {"home", "away", "draw"}:
            return

        match = db.get_match(match_id)
        if not match or not match.is_open:
            await edit_or_send_user(
                update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
            )
            _clear_prediction_state(context)
            return

        context.user_data["prediction_step"] = "entering_score"
        context.user_data["prediction_match_id"] = match_id
        context.user_data["prediction_pick"] = pick
        context.user_data["prediction_home_team"] = match.home_team
        context.user_data["prediction_away_team"] = match.away_team

        if pick == "home":
            winner_label = match.home_team
        elif pick == "away":
            winner_label = match.away_team
        else:
            winner_label = msg.DRAW

        pick_text = msg.PICK_WINNER_PROMPT.format(
            id=match.id,
            home=match.home_team,
            vs=msg.VS,
            away=match.away_team,
            winner=winner_label,
        )
        await edit_or_send_user(
            update, context, pick_text, bot_username=BOT_USERNAME
        )


async def predict_score_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_group_chat(update):
        return
    if context.user_data.get("prediction_step") != "entering_score":
        return
    if not update.message or not update.message.text:
        return

    parsed = _parse_score_input(update.message.text)
    if parsed is None:
        await reply_to_user(
            update, context, msg.INVALID_SCORE_FORMAT, bot_username=BOT_USERNAME
        )
        return

    pick = context.user_data["prediction_pick"]
    result = _scores_from_pick(pick, parsed[0], parsed[1])
    if isinstance(result, str):
        await reply_to_user(
            update, context, f"{result}\n{msg.SEND_CANCEL}", bot_username=BOT_USERNAME
        )
        return

    home_score, away_score = result
    match_id = context.user_data["prediction_match_id"]
    home_team = context.user_data["prediction_home_team"]
    away_team = context.user_data["prediction_away_team"]

    participant = _ensure_participant(update)
    if not participant:
        return

    match = db.get_match(match_id)
    if not match or not match.is_open:
        _clear_prediction_state(context)
        await reply_to_user(
            update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
        )
        return

    db.save_prediction(participant.id, match_id, home_score, away_score)
    _clear_prediction_state(context)
    await reply_to_user(
        update,
        context,
        msg.PREDICTION_SAVED.format(
            home=home_team,
            vs=msg.VS,
            away=away_team,
            score=f"{home_score}-{away_score}",
        ),
        bot_username=BOT_USERNAME,
    )


async def my_predictions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user:
        return

    participant = db.get_user_by_telegram_id(user.id)
    if not participant:
        await reply_to_user(
            update, context, msg.NOT_JOINED, bot_username=BOT_USERNAME
        )
        return

    predictions = db.get_user_predictions(participant.id)
    if not predictions:
        await reply_to_user(
            update, context, msg.NO_PREDICTIONS, bot_username=BOT_USERNAME
        )
        return

    lines = [msg.YOUR_PREDICTIONS]
    for prediction, match in predictions:
        line = (
            f"#{match.id} {match.home_team} {msg.VS} {match.away_team}\n"
            f"   {msg.YOUR_PICK}: {prediction.home_score}-{prediction.away_score}"
        )
        if match.home_score is not None and match.away_score is not None:
            line += f"\n   {msg.ACTUAL}: {match.home_score}-{match.away_score}"
            line += f"\n   {msg.POINTS_LABEL}: {prediction.points or 0}"
        lines.append(line)

    await reply_to_user(
        update, context, "\n\n".join(lines), bot_username=BOT_USERNAME
    )


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    telegram_id = user.id if user else None
    await send_leaderboard(update, context, viewer_telegram_id=telegram_id)


async def menu_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_group_chat(update):
        return
    if not update.message or not update.message.text:
        return
    if context.user_data.get("prediction_step") == "entering_score":
        return

    action = update.message.text.strip()
    if action == msg.MENU_PREDICT:
        await predict_command(update, context)
    elif action == msg.MENU_MATCHES:
        await matches_command(update, context)
    elif action == msg.MENU_LEADERBOARD:
        await leaderboard_command(update, context)
    elif action == msg.MENU_MY_PREDICTIONS:
        await my_predictions_command(update, context)


async def add_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) < 2:
        await reply_to_user(
            update, context, msg.ADDMATCH_USAGE, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) == 2:
        home_team, away_team = context.args
        kickoff_at = None
    else:
        home_team = context.args[0]
        away_team = context.args[1]
        kickoff_at = " ".join(context.args[2:])

    match = db.add_match(home_team, away_team, kickoff_at)
    await reply_to_user(
        update,
        context,
        msg.MATCH_CREATED.format(match=format_match(match), id=match.id),
        bot_username=BOT_USERNAME,
    )


async def set_result_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) != 3:
        await reply_to_user(
            update, context, msg.SETRESULT_USAGE, bot_username=BOT_USERNAME
        )
        return

    try:
        match_id = int(context.args[0])
        home_score = int(context.args[1])
        away_score = int(context.args[2])
    except ValueError:
        await reply_to_user(
            update, context, msg.SCORES_MUST_BE_NUMBERS, bot_username=BOT_USERNAME
        )
        return

    match = db.set_match_result(match_id, home_score, away_score)
    if not match:
        await reply_to_user(
            update,
            context,
            msg.MATCH_NOT_FOUND.format(id=match_id),
            bot_username=BOT_USERNAME,
        )
        return

    await reply_to_user(
        update,
        context,
        msg.RESULT_RECORDED.format(match=format_match(match)),
        bot_username=BOT_USERNAME,
    )


async def list_all_matches_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    matches = db.list_matches(open_only=False)
    if not matches:
        await reply_to_user(
            update, context, msg.NO_MATCHES_YET, bot_username=BOT_USERNAME
        )
        return

    lines = [msg.ALL_MATCHES] + [format_match(match) for match in matches]
    await reply_to_user(
        update, context, "\n\n".join(lines), bot_username=BOT_USERNAME
    )


async def close_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) != 1:
        await reply_to_user(
            update, context, msg.CLOSEMATCH_USAGE, bot_username=BOT_USERNAME
        )
        return

    try:
        match_id = int(context.args[0])
    except ValueError:
        await reply_to_user(
            update, context, msg.MATCH_ID_NOT_NUMBER, bot_username=BOT_USERNAME
        )
        return

    match = db.get_match(match_id)
    if not match:
        await reply_to_user(
            update,
            context,
            msg.MATCH_NOT_FOUND.format(id=match_id),
            bot_username=BOT_USERNAME,
        )
        return

    db.close_match(match_id)
    await reply_to_user(
        update,
        context,
        msg.MATCH_NOW_CLOSED.format(id=match_id),
        bot_username=BOT_USERNAME,
    )


async def load_worldcup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    stats = db.seed_world_cup_matches()
    open_count = db.count_matches(open_only=True)
    await reply_to_user(
        update,
        context,
        msg.WORLDCUP_LOADED.format(
            added=stats["added"],
            skipped=stats["skipped"],
            closed=stats["closed"],
            open=open_count,
        ),
        bot_username=BOT_USERNAME,
    )
