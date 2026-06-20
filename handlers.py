from datetime import datetime
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_USER_IDS
import messages as msg
from user_messaging import edit_or_send_user, is_group_chat, reply_to_user


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


BOT_USERNAME = "FTM3naBot"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(msg.BTN_MATCHES, callback_data="menu:matches"),
                InlineKeyboardButton(msg.BTN_PREDICT, callback_data="menu:predict"),
            ],
            [
                InlineKeyboardButton(msg.BTN_MY_PREDICTIONS, callback_data="menu:mypredictions"),
                InlineKeyboardButton(msg.BTN_LEADERBOARD, callback_data="menu:leaderboard"),
            ],
            [
                InlineKeyboardButton(msg.BTN_CANCEL, callback_data="menu:cancel"),
                InlineKeyboardButton(msg.BTN_HELP, callback_data="menu:help"),
            ],
        ]
    )

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def format_leaderboard_text(
    entries: list[db.LeaderboardEntry],
    *,
    viewer_entry: db.LeaderboardEntry | None = None,
    total_participants: int = 0,
    group_chat: bool = False,
    group_name: str | None = None,
) -> str:
    if group_name:
        title = msg.LEADERBOARD_TITLE_GROUP_NAMED.format(group=group_name)
    elif group_chat:
        title = msg.LEADERBOARD_TITLE_GROUP
    else:
        title = msg.LEADERBOARD_TITLE
    lines = [title]

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
                medal=medal, name=name, points=entry.total_points
            )
        )

    if total_participants > len(entries):
        lines.append(
            msg.LEADERBOARD_TOP_N.format(shown=len(entries), total=total_participants)
        )

    if viewer_entry:
        lines.append(
            msg.YOUR_RANK.format(
                rank=viewer_entry.rank, points=viewer_entry.total_points
            )
        )

    return "\n".join(lines)


async def send_leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    viewer_telegram_id: int | None = None,
    *,
    group_chat_id: int | None = None,
) -> None:
    is_group_scope = group_chat_id is not None and group_chat_id != 0
    group_name: str | None = None
    if is_group_scope:
        try:
            chat = await context.bot.get_chat(group_chat_id)
            group_name = chat.title
        except Exception:
            group_name = None

    entries = db.get_leaderboard(limit=15, group_chat_id=group_chat_id if is_group_scope else None)
    total = db.count_leaderboard_participants(
        group_chat_id=group_chat_id if is_group_scope else None
    )
    viewer_entry = (
        db.get_user_leaderboard_entry(
            viewer_telegram_id,
            group_chat_id=group_chat_id if is_group_scope else None,
        )
        if viewer_telegram_id
        else None
    )
    text = format_leaderboard_text(
        entries,
        viewer_entry=viewer_entry,
        total_participants=total,
        group_chat=is_group_scope,
        group_name=group_name,
    )

    markup = None
    if (
        is_group_scope
        and not is_group_chat(update)
        and viewer_telegram_id
    ):
        participant = db.get_user_by_telegram_id(viewer_telegram_id)
        if participant and len(db.get_user_group_chat_ids(participant.id)) > 1:
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(msg.BTN_SWITCH_GROUP, callback_data="lb:pick")]]
            )

    await user_response(
        update,
        context,
        text,
        reply_markup=markup,
        bot_username=BOT_USERNAME,
    )


def _resolve_leaderboard_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant: db.User | None,
) -> tuple[int | None, bool]:
    """Return (group_chat_id or None for private, need_group_picker)."""
    if is_group_chat(update) and update.effective_chat:
        chat_id = update.effective_chat.id
        context.user_data["leaderboard_group_chat_id"] = chat_id
        return chat_id, False

    if not participant:
        return None, False

    stored = context.user_data.get("leaderboard_group_chat_id")
    if stored:
        return int(stored), False

    active = db.get_user_active_group(participant.id)
    if active:
        context.user_data["leaderboard_group_chat_id"] = active
        return active, False

    groups = db.get_user_group_chat_ids(participant.id)
    if len(groups) == 1:
        context.user_data["leaderboard_group_chat_id"] = groups[0]
        return groups[0], False
    if len(groups) > 1:
        return None, True
    return None, False


async def _group_leaderboard_picker_keyboard(
    context: ContextTypes.DEFAULT_TYPE,
    group_chat_ids: list[int],
) -> InlineKeyboardMarkup:
    rows = []
    for chat_id in group_chat_ids:
        try:
            chat = await context.bot.get_chat(chat_id)
            label = chat.title or str(chat_id)
        except Exception:
            label = str(chat_id)
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"lb:group:{chat_id}")]
        )
    return InlineKeyboardMarkup(rows)


async def _show_group_leaderboard_picker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant: db.User,
) -> None:
    groups = db.get_user_group_chat_ids(participant.id)
    if not groups:
        await user_response(update, context, msg.LEADERBOARD_PRIVATE_ONLY)
        return
    keyboard = await _group_leaderboard_picker_keyboard(context, groups)
    await user_response(
        update,
        context,
        msg.CHOOSE_GROUP_LEADERBOARD,
        reply_markup=keyboard,
    )


async def leaderboard_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    parts = query.data.split(":")
    if len(parts) < 2 or parts[0] != "lb":
        return

    if parts[1] == "pick":
        user = update.effective_user
        if not user:
            return
        participant = db.get_user_by_telegram_id(user.id)
        if not participant:
            return
        context.user_data.pop("leaderboard_group_chat_id", None)
        await _show_group_leaderboard_picker(update, context, participant)
        return

    user = update.effective_user
    if not user:
        return

    participant = db.get_user_by_telegram_id(user.id)
    if not participant:
        return

    if parts[1] == "group":
        try:
            chat_id = int(parts[2])
        except (ValueError, IndexError):
            return
        groups = db.get_user_group_chat_ids(participant.id)
        if chat_id not in groups:
            return
        context.user_data["leaderboard_group_chat_id"] = chat_id
        db.set_user_active_group(participant.id, chat_id)
        await send_leaderboard(
            update,
            context,
            viewer_telegram_id=user.id,
            group_chat_id=chat_id,
        )


async def user_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    *,
    bot_username: str = BOT_USERNAME,
    drop_reply_keyboard: bool = False,
) -> bool:
    if update.callback_query and not is_group_chat(update):
        return await edit_or_send_user(
            update, context, text, reply_markup, bot_username=bot_username
        )
    return await reply_to_user(
        update,
        context,
        text,
        reply_markup=reply_markup,
        bot_username=bot_username,
        drop_reply_keyboard=drop_reply_keyboard,
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    action = query.data.split(":", 1)[1] if ":" in query.data else ""

    if action == "matches":
        await matches_command(update, context)
    elif action == "predict":
        await predict_command(update, context)
    elif action == "cancel":
        await predict_cancel_command(update, context)
    elif action == "mypredictions":
        await my_predictions_command(update, context)
    elif action == "leaderboard":
        await leaderboard_command(update, context)
    elif action == "help":
        await start_command(update, context)


def format_match(match: db.Match) -> str:
    status = msg.STATUS_OPEN if db.match_accepts_predictions(match) else msg.STATUS_CLOSED
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
    participant = db.upsert_user(user.id, user.username, display_name)
    _track_group_member(update, participant)

    await user_response(
        update,
        context,
        msg.START_TEXT,
        reply_markup=main_menu_keyboard(),
        drop_reply_keyboard=True,
    )


async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not context.bot:
        return

    bot_id = context.bot.id
    for member in message.new_chat_members:
        if member.id != bot_id:
            continue

        await update.message.reply_text(msg.GROUP_WELCOME)
        return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ensure_participant(update)

    from worldcup2026 import current_match_day

    today = current_match_day()
    on_date = context.args[0] if context.args else today

    try:
        datetime.fromisoformat(on_date)
    except ValueError:
        await reply_to_user(
            update, context, msg.MATCHES_USAGE, bot_username=BOT_USERNAME
        )
        return

    matches = db.list_predictable_matches(on_date=on_date, limit=25)
    total = db.count_matches(open_only=True, on_date=on_date)
    header = msg.OPEN_MATCHES_HEADER.format(date=on_date)

    if not matches and not context.args:
        matches = db.list_predictable_matches(limit=25, match_day_only=False)
        total = len(matches)
        if matches:
            header = msg.UPCOMING_OPEN_MATCHES

    if not matches:
        await user_response(
            update,
            context,
            msg.NO_OPEN_MATCHES if not context.args else msg.NO_MATCHES_DATE.format(date=on_date),
        )
        return

    lines = [header] + [format_match(match) for match in matches]
    if total > len(matches):
        lines.append(msg.SHOWING_MATCHES.format(shown=len(matches), total=total))
    await user_response(update, context, "\n\n".join(lines))


def _track_group_member(update: Update, participant: db.User) -> None:
    if not is_group_chat(update):
        return
    chat = update.effective_chat
    if chat:
        db.set_user_active_group(participant.id, chat.id)


def _ensure_participant(update: Update) -> db.User | None:
    user = update.effective_user
    if not user:
        return None
    participant = db.get_user_by_telegram_id(user.id)
    if participant:
        _track_group_member(update, participant)
        return participant
    participant = db.upsert_user(
        user.id, user.username, user.full_name or user.username or str(user.id)
    )
    _track_group_member(update, participant)
    return participant


def _group_chat_id(update: Update) -> int:
    if is_group_chat(update) and update.effective_chat:
        return update.effective_chat.id
    return 0


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


async def _prompt_score_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    match: db.Match,
    pick: str,
) -> None:
    context.user_data["prediction_step"] = "entering_score"
    context.user_data["prediction_match_id"] = match.id
    context.user_data["prediction_pick"] = pick
    context.user_data["prediction_home_team"] = match.home_team
    context.user_data["prediction_away_team"] = match.away_team

    if pick == "draw":
        text = msg.PICK_DRAW_PROMPT.format(
            id=match.id,
            home=match.home_team,
            vs=msg.VS,
            away=match.away_team,
            draw=msg.DRAW,
        )
    else:
        winner = match.home_team if pick == "home" else match.away_team
        text = msg.PICK_WINNER_PROMPT.format(
            id=match.id,
            home=match.home_team,
            vs=msg.VS,
            away=match.away_team,
            winner=winner,
        )

    await edit_or_send_user(update, context, text, bot_username=BOT_USERNAME)


def _winner_keyboard(match_id: int, home_team: str, away_team: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(home_team, callback_data=f"pred:pick:{match_id}:home")],
            [InlineKeyboardButton(msg.DRAW, callback_data=f"pred:pick:{match_id}:draw")],
            [InlineKeyboardButton(away_team, callback_data=f"pred:pick:{match_id}:away")],
        ]
    )


def _match_picker_keyboard(
    matches: list[db.Match],
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    open_matches = [m for m in matches if db.match_accepts_predictions(m)]
    rows = []
    for match in open_matches:
        prefix = "✓ " if user_id and db.user_has_prediction(user_id, match.id) else ""
        rows.append(
            [
                InlineKeyboardButton(
                    f"{prefix}#{match.id} {match.home_team} {msg.VS} {match.away_team}",
                    callback_data=f"pred:match:{match.id}",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def _predictable_matches(limit: int = 25) -> tuple[list[db.Match], str]:
    from worldcup2026 import current_match_day

    match_day = current_match_day()
    matches = db.list_predictable_matches(on_date=match_day, limit=limit)
    if not matches:
        matches = db.list_predictable_matches(limit=limit, match_day_only=False)
        prompt = msg.CHOOSE_MATCH_UPCOMING
    else:
        prompt = msg.CHOOSE_MATCH.format(date=match_day)
    return matches, prompt


async def _show_match_picker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    edit: bool = False,
) -> None:
    matches, prompt = _predictable_matches()
    participant = None
    user = update.effective_user
    if user:
        participant = db.get_user_by_telegram_id(user.id)
    user_db_id = participant.id if participant else None

    if not matches:
        text = msg.NO_OPEN_MATCHES
        markup = None
    else:
        text = f"{prompt}\n\n{msg.PREDICTION_ONCE_NOTE}"
        markup = _match_picker_keyboard(matches, user_id=user_db_id)

    if edit and update.callback_query:
        await edit_or_send_user(
            update, context, text, markup, bot_username=BOT_USERNAME
        )
    else:
        await user_response(update, context, text, reply_markup=markup)


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


async def predict_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    _ensure_participant(update)
    _clear_prediction_state(context)
    participant = db.get_user_by_telegram_id(user.id)
    group_chat_id = _group_chat_id(update)
    if group_chat_id and participant:
        db.set_user_active_group(participant.id, group_chat_id)
        context.user_data["leaderboard_group_chat_id"] = group_chat_id

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
        if not match or not db.match_accepts_predictions(match):
            await reply_to_user(
                update,
                context,
                msg.MATCH_CLOSED.format(id=match_id),
                bot_username=BOT_USERNAME,
            )
            return

        await _prompt_winner_pick(update, context, match)
        return

    await _show_match_picker(update, context)


async def predict_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("prediction_step") != "entering_score":
        _clear_prediction_state(context)
        await user_response(
            update,
            context,
            msg.START_TEXT,
            reply_markup=main_menu_keyboard(),
        )
        return
    _clear_prediction_state(context)
    await user_response(update, context, msg.PREDICTION_CANCELLED)


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

    if parts[1] == "cancel":
        _clear_prediction_state(context)
        await edit_or_send_user(
            update, context, msg.PREDICTION_CANCELLED, bot_username=BOT_USERNAME
        )
        return

    if parts[1] == "match" and len(parts) == 3:
        try:
            match_id = int(parts[2])
        except ValueError:
            return

        match = db.get_match(match_id)
        if not match or not db.match_accepts_predictions(match):
            await _show_match_picker(update, context, edit=True)
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
        if not match or not db.match_accepts_predictions(match):
            await edit_or_send_user(
                update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
            )
            _clear_prediction_state(context)
            return

        await _prompt_score_text(update, context, match, pick)


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
    if parsed[0] == parsed[1]:
        home_score, away_score = parsed[0], parsed[1]
    else:
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

    if home_score == away_score:
        outcome = msg.DRAW
    elif home_score > away_score:
        outcome = home_team
    else:
        outcome = away_team

    participant = _ensure_participant(update)
    if not participant:
        return

    match = db.get_match(match_id)
    if not match or not db.match_accepts_predictions(match):
        _clear_prediction_state(context)
        await reply_to_user(
            update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
        )
        return

    try:
        prediction, was_update = db.save_prediction(
            participant.id,
            match_id,
            home_score,
            away_score,
        )
    except ValueError:
        _clear_prediction_state(context)
        await reply_to_user(
            update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
        )
        return
    _clear_prediction_state(context)
    template = msg.PREDICTION_UPDATED if was_update else msg.PREDICTION_SAVED
    await reply_to_user(
        update,
        context,
        template.format(
            home=home_team,
            vs=msg.VS,
            away=away_team,
            outcome=outcome,
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

    _track_group_member(update, participant)
    predictions = db.get_user_predictions(participant.id)
    if not predictions:
        await user_response(update, context, msg.NO_PREDICTIONS)
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

    await user_response(update, context, "\n\n".join(lines))


async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    participant = None
    if user:
        participant = db.get_user_by_telegram_id(user.id)
        if not participant:
            participant = db.upsert_user(
                user.id, user.username, user.full_name or user.username or str(user.id)
            )
        _track_group_member(update, participant)

    group_chat_id, need_picker = _resolve_leaderboard_group(
        update, context, participant
    )
    if need_picker and participant:
        await _show_group_leaderboard_picker(update, context, participant)
        return

    telegram_id = user.id if user else None
    await send_leaderboard(
        update,
        context,
        viewer_telegram_id=telegram_id,
        group_chat_id=group_chat_id,
    )


STALE_KEYBOARD_LABELS = {
    "⚽ توقع",
    "📅 المباريات",
    "🏆 المتصدرين",
    "📋 توقعاتي",
    "توقع",
    "المباريات",
    "المتصدرين",
    "توقعاتي",
}


async def stale_keyboard_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if is_group_chat(update):
        return
    if not update.message or not update.message.text:
        return
    if update.message.text.strip() not in STALE_KEYBOARD_LABELS:
        return
    if context.user_data.get("prediction_step") == "entering_score":
        return

    await start_command(update, context)


async def add_match_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    db.backfill_match_kickoff_times()
    db.sync_match_open_flags()
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
