from datetime import datetime
import re
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import database as db
from config import ADMIN_USER_IDS, ALKORAM3NA_GROUP_CHAT_ID
import messages as msg
from group_standings import (
    ALKORAM3NA_GROUP_USERNAME,
    GROUP_TITLE_HINTS,
    PREDEFINED_GROUP_STANDINGS,
    group_display_name,
)
from user_messaging import edit_or_send_user, is_group_chat, reply_to_user

import prediction_reports as reports


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


BOT_USERNAME = "FTM3naBot"


def main_menu_keyboard(*, show_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
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
    if show_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    msg.BTN_ADMIN_PREDICTIONS,
                    callback_data="menu:adminpredictions",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)

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
        if viewer_entry:
            lines.append(
                msg.YOUR_RANK.format(
                    rank=viewer_entry.rank, points=viewer_entry.total_points
                )
            )
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


async def _resolve_group_display_name(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> str | None:
    telegram_title: str | None = None
    try:
        chat = await context.bot.get_chat(chat_id)
        telegram_title = chat.title
    except Exception:
        pass
    return group_display_name(chat_id, telegram_title=telegram_title)


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
        group_name = await _resolve_group_display_name(context, group_chat_id)

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
    if is_group_scope and not is_group_chat(update) and viewer_telegram_id:
        participant = db.get_user_by_telegram_id(viewer_telegram_id)
        if participant and db.get_user_group_chat_ids(participant.id):
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
        from config import configured_group_chat_ids

        chat_id = int(stored)
        if chat_id in configured_group_chat_ids():
            return chat_id, False
        context.user_data.pop("leaderboard_group_chat_id", None)

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


async def _group_picker_keyboard(
    context: ContextTypes.DEFAULT_TYPE,
    group_chat_ids: list[int],
    *,
    active_chat_id: int | None,
    select_callback: str,
) -> InlineKeyboardMarkup | None:
    rows = []
    for chat_id in group_chat_ids:
        label = await _resolve_group_display_name(context, chat_id)
        if not label:
            continue
        if chat_id == active_chat_id:
            label = f"✓ {label}"
        rows.append(
            [InlineKeyboardButton(label, callback_data=f"{select_callback}:{chat_id}")]
        )
    if not rows:
        return None
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
    active = db.get_user_active_group(participant.id) or groups[0]
    keyboard = await _group_picker_keyboard(
        context,
        groups,
        active_chat_id=active,
        select_callback="lb:group",
    )
    if keyboard is None:
        await user_response(update, context, msg.LEADERBOARD_PRIVATE_ONLY)
        return
    await user_response(
        update,
        context,
        msg.CHOOSE_GROUP_LEADERBOARD,
        reply_markup=keyboard,
    )


def _set_active_group(
    participant: db.User,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    groups = db.get_user_group_chat_ids(participant.id)
    if chat_id not in groups:
        return False
    context.user_data["leaderboard_group_chat_id"] = chat_id
    db.set_user_active_group(participant.id, chat_id)
    return True


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
        if not _set_active_group(participant, chat_id, context):
            return
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
    elif action == "adminpredictions":
        await admin_predictions_command(update, context)


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
        reply_markup=main_menu_keyboard(show_admin=is_admin(user.id)),
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

    if context.args:
        matches = db.list_predictable_matches(on_date=on_date, limit=25)
        total = db.count_matches(open_only=True, on_date=on_date)
        header = msg.OPEN_MATCHES_HEADER.format(date=on_date)
    else:
        active_day, matches = db.list_active_day_predictable_matches(limit=25)
        if not active_day:
            matches = []
            total = 0
            header = ""
        else:
            on_date = active_day
            total = db.count_matches(open_only=True, on_date=on_date)
            header = msg.OPEN_MATCHES_HEADER.format(date=on_date)

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


def _clear_prediction_state(context: ContextTypes.DEFAULT_TYPE, user_id: int | None = None) -> None:
    for key in (
        "prediction_step",
        "prediction_match_id",
        "prediction_pick",
        "prediction_home_team",
        "prediction_away_team",
        "prediction_prompt_id",
        "pending_score_pair",
    ):
        context.user_data.pop(key, None)
    if user_id is not None:
        db.clear_prediction_draft(user_id)


def _load_prediction_draft(
    context: ContextTypes.DEFAULT_TYPE, user_id: int
) -> bool:
    draft = db.get_prediction_draft(user_id)
    if not draft:
        return False
    context.user_data["prediction_step"] = "entering_score"
    context.user_data["prediction_match_id"] = draft.match_id
    context.user_data["prediction_pick"] = draft.pick
    context.user_data["prediction_home_team"] = draft.home_team
    context.user_data["prediction_away_team"] = draft.away_team
    return True


async def _finalize_prediction(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant: db.User,
    match_id: int,
    home_score: int,
    away_score: int,
    *,
    allow_closed: bool = False,
) -> bool:
    home_team = ""
    away_team = ""
    match = db.get_match(match_id)
    if not match:
        await reply_to_user(
            update,
            context,
            msg.MATCH_NOT_FOUND.format(id=match_id),
            bot_username=BOT_USERNAME,
        )
        return False

    home_team = match.home_team
    away_team = match.away_team

    if not allow_closed and not db.match_accepts_predictions(match):
        _clear_prediction_state(context, participant.id)
        await reply_to_user(
            update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
        )
        return False

    try:
        prediction, was_update = db.save_prediction(
            participant.id,
            match_id,
            home_score,
            away_score,
            allow_closed=allow_closed,
        )
    except ValueError:
        _clear_prediction_state(context, participant.id)
        await reply_to_user(
            update, context, msg.MATCH_NO_LONGER_OPEN, bot_username=BOT_USERNAME
        )
        return False

    if not db.get_user_prediction(participant.id, match_id):
        await reply_to_user(
            update,
            context,
            msg.PREDICTION_SAVE_FAILED,
            bot_username=BOT_USERNAME,
        )
        return False

    lb_group = context.user_data.get("leaderboard_group_chat_id")
    if lb_group:
        db.link_prediction_to_active_group(participant.id, int(lb_group))
    else:
        db.link_prediction_to_active_group(participant.id)

    _clear_prediction_state(context, participant.id)
    if home_score == away_score:
        outcome = msg.DRAW
    elif home_score > away_score:
        outcome = home_team
    else:
        outcome = away_team

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
    return True


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

    participant = _ensure_participant(update)
    if participant:
        db.save_prediction_draft(
            participant.id,
            match.id,
            pick,
            match.home_team,
            match.away_team,
        )

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
    match_day, matches = db.list_active_day_predictable_matches(limit=limit)
    if not match_day:
        return [], msg.NO_OPEN_MATCHES
    return matches, msg.CHOOSE_MATCH.format(date=match_day)


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
    participant = db.get_user_by_telegram_id(user.id)
    _clear_prediction_state(context, participant.id if participant else None)
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

        if len(context.args) >= 2 and participant:
            score_text = context.args[1] if len(context.args) == 2 else "-".join(
                context.args[1:]
            )
            parsed = _parse_score_input(score_text)
            if parsed is None:
                await reply_to_user(
                    update,
                    context,
                    f"{msg.INVALID_SCORE_FORMAT}\n{msg.PREDICT_USAGE}",
                    bot_username=BOT_USERNAME,
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
            if not db.match_accepts_predictions(match):
                await reply_to_user(
                    update,
                    context,
                    msg.MATCH_CLOSED.format(id=match_id),
                    bot_username=BOT_USERNAME,
                )
                return
            context.user_data["pending_score_pair"] = parsed
            await _prompt_winner_pick(update, context, match)
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
    participant = _ensure_participant(update)
    user_id = participant.id if participant else None
    if context.user_data.get("prediction_step") != "entering_score" and participant:
        if not _load_prediction_draft(context, participant.id):
            _clear_prediction_state(context, user_id)
            await user_response(
                update,
                context,
                msg.START_TEXT,
                reply_markup=main_menu_keyboard(),
            )
            return
    _clear_prediction_state(context, user_id)
    await user_response(update, context, msg.PREDICTION_CANCELLED)


async def predict_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    user = update.effective_user
    if not user:
        return

    participant = _ensure_participant(update)
    user_db_id = participant.id if participant else None
    parts = query.data.split(":")
    if len(parts) < 3 or parts[0] != "pred":
        return

    if parts[1] == "cancel":
        _clear_prediction_state(context, user_db_id)
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
            _clear_prediction_state(context, user_db_id)
            return

        pending = context.user_data.pop("pending_score_pair", None)
        if pending:
            result = _scores_from_pick(pick, pending[0], pending[1])
            if isinstance(result, str):
                await edit_or_send_user(
                    update, context, f"{result}\n{msg.SEND_CANCEL}", bot_username=BOT_USERNAME
                )
                return
            home_score, away_score = result
            participant = db.get_user_by_telegram_id(user.id)
            if not participant:
                return
            await _finalize_prediction(
                update,
                context,
                participant,
                match_id,
                home_score,
                away_score,
            )
            return

        await _prompt_score_text(update, context, match, pick)


async def predict_score_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_group_chat(update):
        return
    if not update.message or not update.message.text:
        return

    participant = _ensure_participant(update)
    if not participant:
        return

    if context.user_data.get("prediction_step") != "entering_score":
        if not _load_prediction_draft(context, participant.id):
            return

    parsed = _parse_score_input(update.message.text)
    if parsed is None:
        await reply_to_user(
            update, context, msg.INVALID_SCORE_FORMAT, bot_username=BOT_USERNAME
        )
        return

    pick = context.user_data["prediction_pick"]
    if pick == "draw":
        if parsed[0] != parsed[1]:
            await reply_to_user(
                update, context, f"{msg.DRAW_SCORES_MUST_EQUAL}\n{msg.SEND_CANCEL}",
                bot_username=BOT_USERNAME,
            )
            return
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
    await _finalize_prediction(
        update,
        context,
        participant,
        match_id,
        home_score,
        away_score,
    )


async def my_predictions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user:
        return

    participant = _ensure_participant(update)
    if not participant:
        await reply_to_user(
            update, context, msg.NOT_JOINED, bot_username=BOT_USERNAME
        )
        return

    _track_group_member(update, participant)
    db.recalculate_all_prediction_points()
    predictions = db.get_user_predictions(participant.id)
    if not predictions:
        await user_response(update, context, msg.NO_PREDICTIONS)
        return

    lines = [msg.YOUR_PREDICTIONS, msg.SCORING_RULES]
    for prediction, match in predictions:
        line = (
            f"#{match.id} {match.home_team} {msg.VS} {match.away_team}\n"
            f"   {msg.YOUR_PICK}: {prediction.home_score}-{prediction.away_score}"
        )
        if match.home_score is not None and match.away_score is not None:
            line += f"\n   {msg.ACTUAL}: {match.home_score}-{match.away_score}"
            line += f"\n   {msg.POINTS_LABEL}: {prediction.points if prediction.points is not None else 0}"
        else:
            line += f"\n   {msg.POINTS_PENDING}"
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


async def set_prediction_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) < 3:
        await reply_to_user(
            update, context, msg.SETPREDICTION_USAGE, bot_username=BOT_USERNAME
        )
        return

    try:
        telegram_id = int(context.args[0])
        match_id = int(context.args[1])
    except ValueError:
        await reply_to_user(
            update, context, msg.SCORES_MUST_BE_NUMBERS, bot_username=BOT_USERNAME
        )
        return

    score_text = context.args[2] if len(context.args) == 3 else "-".join(context.args[2:])
    parsed = _parse_score_input(score_text)
    if parsed is None:
        await reply_to_user(
            update, context, msg.INVALID_SCORE_FORMAT, bot_username=BOT_USERNAME
        )
        return

    participant = db.get_user_by_telegram_id(telegram_id)
    if not participant:
        await reply_to_user(
            update, context, msg.USER_NOT_FOUND, bot_username=BOT_USERNAME
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

    home_score, away_score = parsed
    try:
        prediction, _ = db.save_prediction(
            participant.id,
            match_id,
            home_score,
            away_score,
            allow_closed=True,
        )
    except ValueError as exc:
        await reply_to_user(
            update, context, str(exc), bot_username=BOT_USERNAME
        )
        return

    db.recalculate_all_prediction_points()
    points = prediction.points if prediction.points is not None else 0
    await reply_to_user(
        update,
        context,
        msg.PREDICTION_SET.format(
            home=match.home_team,
            vs=msg.VS,
            away=match.away_team,
            score=f"{home_score}-{away_score}",
            points=points,
        ),
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


async def open_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if len(context.args) < 1:
        await reply_to_user(
            update, context, msg.OPENMATCH_USAGE, bot_username=BOT_USERNAME
        )
        return

    try:
        match_id = int(context.args[0])
    except ValueError:
        await reply_to_user(
            update, context, msg.MATCH_ID_NOT_NUMBER, bot_username=BOT_USERNAME
        )
        return

    clear_result = len(context.args) >= 2 and context.args[1].lower() == "clear"
    existing = db.get_match(match_id)
    if not existing:
        await reply_to_user(
            update,
            context,
            msg.MATCH_NOT_FOUND.format(id=match_id),
            bot_username=BOT_USERNAME,
        )
        return

    match = db.open_match(match_id, clear_result=clear_result)
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
        msg.MATCH_NOW_OPEN.format(id=match_id, match=format_match(match)),
        bot_username=BOT_USERNAME,
    )


async def sync_scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    stats = db.score_all_finished_matches()
    await reply_to_user(
        update,
        context,
        msg.SYNCSCORES_DONE.format(
            results_updated=stats["results_updated"],
            predictions_scored=stats["predictions_scored"],
            espn_skipped=stats["espn_skipped"],
        ),
        bot_username=BOT_USERNAME,
    )


def _admin_predictions_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BY_DAY, callback_data="adminpred:pick:day")],
            [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BY_STAGE, callback_data="adminpred:pick:stage")],
            [
                InlineKeyboardButton(
                    msg.ADMIN_PREDICTIONS_GROUP_STAGE,
                    callback_data="adminpred:scope:group_stage:all",
                )
            ],
            [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_SAVED, callback_data="adminpred:saved")],
        ]
    )


def _admin_scope_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    msg.ADMIN_PREDICTIONS_BTN_VIEW,
                    callback_data="adminpred:view",
                ),
                InlineKeyboardButton(
                    msg.ADMIN_PREDICTIONS_BTN_SAVE,
                    callback_data="adminpred:save",
                ),
            ],
            [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BTN_BACK, callback_data="adminpred:menu")],
        ]
    )


def _admin_day_picker_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for day in reports.list_available_days():
        rows.append(
            [
                InlineKeyboardButton(
                    day,
                    callback_data=f"adminpred:scope:day:{day}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BTN_BACK, callback_data="adminpred:menu")]
    )
    return InlineKeyboardMarkup(rows)


def _admin_stage_picker_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    stages = reports.list_available_stages()
    context.user_data["adminpred_stages"] = stages
    rows: list[list[InlineKeyboardButton]] = []
    for index, stage in enumerate(stages):
        rows.append(
            [
                InlineKeyboardButton(
                    stage,
                    callback_data=f"adminpred:scope:stage:{index}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BTN_BACK, callback_data="adminpred:menu")]
    )
    return InlineKeyboardMarkup(rows)


def _store_admin_scope(
    context: ContextTypes.DEFAULT_TYPE,
    scope_type: str,
    scope_key: str,
) -> None:
    context.user_data["adminpred_scope"] = {
        "type": scope_type,
        "key": scope_key,
    }


def _current_admin_scope(
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[str, str] | None:
    scope = context.user_data.get("adminpred_scope")
    if not scope:
        return None
    return scope["type"], scope["key"]


async def _send_admin_report_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    path,
    caption: str,
) -> bool:
    user = update.effective_user
    if not user:
        return False

    chat_id = user.id if is_group_chat(update) else update.effective_chat.id
    with open(path, "rb") as handle:
        await context.bot.send_document(
            chat_id=chat_id,
            document=handle,
            filename=path.name,
            caption=caption,
        )
    return True


async def admin_predictions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    await reply_to_user(
        update,
        context,
        msg.ADMIN_PREDICTIONS_MENU,
        reply_markup=_admin_predictions_menu_keyboard(),
        bot_username=BOT_USERNAME,
    )


async def admin_predictions_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    if not user or not is_admin(user.id):
        await query.answer(msg.ADMIN_ONLY, show_alert=True)
        return

    await query.answer()
    parts = query.data.split(":")
    if len(parts) < 2 or parts[0] != "adminpred":
        return

    action = parts[1]

    if action == "menu":
        await edit_or_send_user(
            update,
            context,
            msg.ADMIN_PREDICTIONS_MENU,
            reply_markup=_admin_predictions_menu_keyboard(),
            bot_username=BOT_USERNAME,
        )
        return

    if action == "pick" and len(parts) >= 3:
        pick_type = parts[2]
        if pick_type == "day":
            await edit_or_send_user(
                update,
                context,
                msg.ADMIN_PREDICTIONS_PICK_DAY,
                reply_markup=_admin_day_picker_keyboard(),
                bot_username=BOT_USERNAME,
            )
        elif pick_type == "stage":
            await edit_or_send_user(
                update,
                context,
                msg.ADMIN_PREDICTIONS_PICK_STAGE,
                reply_markup=_admin_stage_picker_keyboard(context),
                bot_username=BOT_USERNAME,
            )
        return

    if action == "scope" and len(parts) >= 4:
        scope_type = parts[2]
        scope_key = parts[3]
        if scope_type == "stage" and scope_key.isdigit():
            stages = context.user_data.get("adminpred_stages") or reports.list_available_stages()
            index = int(scope_key)
            if 0 <= index < len(stages):
                scope_key = stages[index]
        _store_admin_scope(context, scope_type, scope_key)
        report = reports.build_prediction_report(scope_type, scope_key)
        summary = reports.report_summary_text(report, max_users=8)
        await edit_or_send_user(
            update,
            context,
            msg.ADMIN_PREDICTIONS_SCOPE_HEADER.format(summary=summary),
            reply_markup=_admin_scope_action_keyboard(),
            bot_username=BOT_USERNAME,
        )
        return

    if action == "view":
        current = _current_admin_scope(context)
        if not current:
            return
        scope_type, scope_key = current
        report = reports.build_prediction_report(scope_type, scope_key)
        text = reports.report_summary_text(report, max_users=20)
        if len(text) > 3900:
            text = text[:3900] + "\n…"
        await edit_or_send_user(
            update,
            context,
            text,
            reply_markup=_admin_scope_action_keyboard(),
            bot_username=BOT_USERNAME,
        )
        return

    if action == "save":
        current = _current_admin_scope(context)
        if not current:
            return
        scope_type, scope_key = current
        report = reports.build_prediction_report(scope_type, scope_key)
        path, saved = reports.save_prediction_export(
            report,
            saved_by_telegram_id=user.id,
        )
        summary = reports.report_summary_text(report, max_users=5)
        await edit_or_send_user(
            update,
            context,
            msg.ADMIN_PREDICTIONS_EXPORT_DONE.format(
                summary=summary,
                filename=path.name,
            ),
            reply_markup=_admin_scope_action_keyboard(),
            bot_username=BOT_USERNAME,
        )
        await _send_admin_report_document(
            update,
            context,
            path,
            msg.ADMIN_PREDICTIONS_FILE_CAPTION.format(label=report.scope_label),
        )
        return

    if action == "saved":
        exports = reports.list_saved_exports()
        if not exports:
            await edit_or_send_user(
                update,
                context,
                msg.ADMIN_PREDICTIONS_SAVED_EMPTY,
                reply_markup=_admin_predictions_menu_keyboard(),
                bot_username=BOT_USERNAME,
            )
            return

        lines = [msg.ADMIN_PREDICTIONS_SAVED_LIST]
        rows: list[list[InlineKeyboardButton]] = []
        for export in exports[:15]:
            saved_at = export.saved_at.replace("T", " ")[:16]
            lines.append(
                msg.ADMIN_PREDICTIONS_SAVED_ROW.format(
                    id=export.id,
                    label=export.scope_label,
                    users=export.user_count,
                    predictions=export.prediction_count,
                    saved_at=saved_at,
                )
            )
            rows.append(
                [
                    InlineKeyboardButton(
                        f"📥 #{export.id} {export.scope_label}",
                        callback_data=f"adminpred:dl:{export.id}",
                    )
                ]
            )
        rows.append(
            [InlineKeyboardButton(msg.ADMIN_PREDICTIONS_BTN_BACK, callback_data="adminpred:menu")]
        )
        await edit_or_send_user(
            update,
            context,
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(rows),
            bot_username=BOT_USERNAME,
        )
        return

    if action == "dl" and len(parts) >= 3:
        try:
            export_id = int(parts[2])
        except ValueError:
            return
        export = reports.get_saved_export(export_id)
        if not export:
            return
        path = Path(export.file_path)
        if not path.is_file():
            await edit_or_send_user(
                update,
                context,
                "الملف غير موجود على الخادم.",
                reply_markup=_admin_predictions_menu_keyboard(),
                bot_username=BOT_USERNAME,
            )
            return
        await _send_admin_report_document(
            update,
            context,
            path,
            msg.ADMIN_PREDICTIONS_FILE_CAPTION.format(label=export.scope_label),
        )
        return


async def _resolve_group_chat_id(
    context: ContextTypes.DEFAULT_TYPE,
    group_ref: str,
    *,
    update: Update | None = None,
) -> int | None:
    raw = group_ref.strip()
    if raw.lstrip("-").isdigit():
        return int(raw)

    slug = raw
    if "t.me/" in raw:
        slug = raw.rsplit("/", 1)[-1].strip().lstrip("+")

    key = slug.lstrip("@").lower()

    env_ids = {
        ALKORAM3NA_GROUP_USERNAME: ALKORAM3NA_GROUP_CHAT_ID,
        "alkora": ALKORAM3NA_GROUP_CHAT_ID,
        "الكورة_معنا": ALKORAM3NA_GROUP_CHAT_ID,
    }
    configured = env_ids.get(key, "")
    if configured.lstrip("-").isdigit():
        return int(configured)

    if update and is_group_chat(update) and update.effective_chat:
        title = (update.effective_chat.title or "").lower()
        for canonical, hints in GROUP_TITLE_HINTS.items():
            if key == canonical or key in hints or any(h in title for h in hints):
                return update.effective_chat.id

    try:
        chat = await context.bot.get_chat(f"@{key}")
        return chat.id
    except Exception:
        return None


async def set_group_points_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if not context.args:
        await reply_to_user(
            update, context, msg.SETGROUPPOINTS_USAGE, bot_username=BOT_USERNAME
        )
        return

    if context.args[0].lower() == "load":
        group_key = context.args[1].lower() if len(context.args) > 1 else ALKORAM3NA_GROUP_USERNAME
        standings = PREDEFINED_GROUP_STANDINGS.get(group_key)
        if not standings:
            await reply_to_user(
                update,
                context,
                msg.SETGROUPPOINTS_USAGE,
                bot_username=BOT_USERNAME,
            )
            return

        chat_id = await _resolve_group_chat_id(context, group_key, update=update)
        if chat_id is None:
            await reply_to_user(
                update,
                context,
                msg.SETGROUPPOINTS_GROUP_NOT_FOUND,
                bot_username=BOT_USERNAME,
            )
            return

        applied, not_found = db.bulk_set_group_manual_points(chat_id, standings)
        from prediction_persistence import clear_groups_cleared_flag

        clear_groups_cleared_flag()
        lines = [
            msg.SETGROUPPOINTS_LOAD_DONE.format(
                group=group_key,
                applied_count=len(applied),
                missing_count=len(not_found),
            )
        ]
        if applied:
            lines.append("\n✅:")
            lines.extend(msg.SETGROUPPOINTS_APPLIED_ROW.format(line=line) for line in applied)
        if not_found:
            lines.append("\n❌ لم يُعثر عليهم (يجب /start أولاً):")
            lines.extend(
                msg.SETGROUPPOINTS_MISSING_ROW.format(ref=ref) for ref in not_found
            )
        lines.append(f"\n{msg.SETGROUPPOINTS_NOTE}")
        await reply_to_user(
            update,
            context,
            "\n".join(lines),
            bot_username=BOT_USERNAME,
        )
        return

    group_ref: str
    user_ref: str
    points: int

    if len(context.args) == 2:
        group_ref = ALKORAM3NA_GROUP_USERNAME
        user_ref = context.args[0]
        try:
            points = int(context.args[1])
        except ValueError:
            await reply_to_user(
                update, context, msg.SCORES_MUST_BE_NUMBERS, bot_username=BOT_USERNAME
            )
            return
    elif len(context.args) >= 3:
        group_ref = context.args[0]
        user_ref = context.args[1]
        try:
            points = int(context.args[2])
        except ValueError:
            await reply_to_user(
                update, context, msg.SCORES_MUST_BE_NUMBERS, bot_username=BOT_USERNAME
            )
            return
    else:
        await reply_to_user(
            update, context, msg.SETGROUPPOINTS_USAGE, bot_username=BOT_USERNAME
        )
        return

    chat_id = await _resolve_group_chat_id(context, group_ref, update=update)
    if chat_id is None:
        await reply_to_user(
            update,
            context,
            msg.SETGROUPPOINTS_GROUP_NOT_FOUND,
            bot_username=BOT_USERNAME,
        )
        return

    target = db.ensure_user_ref(user_ref)
    if not target:
        await reply_to_user(
            update, context, msg.SETGROUPPOINTS_USER_NOT_FOUND, bot_username=BOT_USERNAME
        )
        return

    db.set_group_manual_points(chat_id, target.id, points)
    from prediction_persistence import clear_groups_cleared_flag

    clear_groups_cleared_flag()
    group_label = group_ref.lstrip("@")
    name = target.display_name
    if target.username:
        name += f" (@{target.username})"
    await reply_to_user(
        update,
        context,
        msg.SETGROUPPOINTS_ONE_DONE.format(
            name=name,
            points=points,
            group=group_label,
        ),
        bot_username=BOT_USERNAME,
    )


async def backup_predictions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    from prediction_backup import backup_predictions, count_predictions

    path = backup_predictions(force=True)
    if not path:
        await reply_to_user(
            update,
            context,
            msg.RESTORE_PREDICTIONS_EMPTY,
            bot_username=BOT_USERNAME,
        )
        return

    await reply_to_user(
        update,
        context,
        msg.BACKUP_PREDICTIONS_DONE.format(
            count=count_predictions(),
            filename=path.name,
        ),
        bot_username=BOT_USERNAME,
    )


async def clear_groups_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if not context.args or context.args[0].lower() != "confirm":
        await reply_to_user(
            update, context, msg.CLEAR_GROUPS_CONFIRM, bot_username=BOT_USERNAME
        )
        return

    result = db.clear_all_groups()
    await reply_to_user(
        update,
        context,
        msg.CLEAR_GROUPS_DONE.format(
            group_members=int(result.get("group_members", 0) or 0),
            active_groups_cleared=int(result.get("active_groups_cleared", 0) or 0),
        ),
        bot_username=BOT_USERNAME,
    )


async def reset_points_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if not context.args or context.args[0].lower() != "confirm":
        await reply_to_user(
            update, context, msg.RESET_POINTS_CONFIRM, bot_username=BOT_USERNAME
        )
        return

    result = db.reset_all_user_points()
    await reply_to_user(
        update,
        context,
        msg.RESET_POINTS_DONE.format(
            users_zeroed=int(result.get("users_zeroed", 0) or 0),
            prediction_scores_cleared=int(
                result.get("prediction_scores_cleared", 0) or 0
            ),
        ),
        bot_username=BOT_USERNAME,
    )


async def clear_userdata_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    if not context.args or context.args[0].lower() != "confirm":
        await reply_to_user(
            update, context, msg.CLEAR_USERDATA_CONFIRM, bot_username=BOT_USERNAME
        )
        return

    result = db.factory_reset_to_fresh_launch()
    seeded = int(result.get("seeded", 0) or 0)
    await reply_to_user(
        update,
        context,
        msg.CLEAR_USERDATA_DONE.format(
            users=int(result.get("users", 0) or 0),
            predictions=int(result.get("predictions", 0) or 0),
            group_members=int(result.get("group_members", 0) or 0),
            manual_points=int(result.get("group_manual_points", 0) or 0),
            matches=int(result.get("matches", 0) or 0),
            seeded=seeded,
        ),
        bot_username=BOT_USERNAME,
    )


async def restore_predictions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    import tempfile

    from prediction_backup import best_backup_path, restore_predictions_from_file
    from prediction_persistence import (
        ARCHIVE_PATH,
        clear_factory_reset_pending,
        restore_from_archive,
        update_highwater_mark,
    )

    restored = 0
    skipped_total = 0
    upload_path: Path | None = None

    message = update.effective_message
    reply_doc = message.reply_to_message.document if message and message.reply_to_message else None
    attached_doc = message.document if message else None
    doc = reply_doc or attached_doc

    if doc:
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            suffix = Path(doc.file_name or "backup.json").suffix or ".json"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                upload_path = Path(handle.name)
            await tg_file.download_to_drive(custom_path=str(upload_path))
            merged, skipped_total = restore_predictions_from_file(
                upload_path, only_if_empty=False
            )
            restored += merged
        except Exception:
            await reply_to_user(
                update,
                context,
                msg.RESTORE_PREDICTIONS_FILE_FAILED,
                bot_username=BOT_USERNAME,
            )
            return
        finally:
            if upload_path:
                upload_path.unlink(missing_ok=True)
    else:
        restored = restore_from_archive()
        path = best_backup_path()
        if path:
            merged, skipped_total = restore_predictions_from_file(path, only_if_empty=False)
            restored += merged

    update_highwater_mark()
    clear_factory_reset_pending()
    if restored == 0 and not doc and not best_backup_path() and not ARCHIVE_PATH.is_file():
        await reply_to_user(
            update,
            context,
            msg.RESTORE_PREDICTIONS_EMPTY,
            bot_username=BOT_USERNAME,
        )
        return

    db.recalculate_all_prediction_points()
    await reply_to_user(
        update,
        context,
        msg.RESTORE_PREDICTIONS_DONE.format(restored=restored, skipped=skipped_total),
        bot_username=BOT_USERNAME,
    )


async def import_excel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        await reply_to_user(
            update, context, msg.ADMIN_ONLY, bot_username=BOT_USERNAME
        )
        return

    import tempfile

    from excel_import import (
        IMPORTS_DIR,
        import_all_excel_sources,
        import_predictions_from_excel,
    )

    message = update.effective_message
    reply_doc = message.reply_to_message.document if message and message.reply_to_message else None
    attached_doc = message.document if message else None
    doc = reply_doc or attached_doc

    if doc:
        if not (doc.file_name or "").lower().endswith(".xlsx"):
            await reply_to_user(
                update,
                context,
                msg.IMPORT_EXCEL_USAGE,
                bot_username=BOT_USERNAME,
            )
            return
        try:
            IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
            tg_file = await context.bot.get_file(doc.file_id)
            dest = IMPORTS_DIR / (doc.file_name or "import.xlsx")
            await tg_file.download_to_drive(custom_path=str(dest))
            result = import_predictions_from_excel(dest)
            from excel_import import apply_predefined_group_standings

            applied, missing = apply_predefined_group_standings()
            result.group_points_applied = applied
            result.group_points_missing = missing
            db.recalculate_all_prediction_points()
        except Exception:
            await reply_to_user(
                update,
                context,
                msg.IMPORT_EXCEL_FILE_FAILED,
                bot_username=BOT_USERNAME,
            )
            return
    else:
        result = import_all_excel_sources()
        if not result.files_read:
            await reply_to_user(
                update,
                context,
                msg.IMPORT_EXCEL_EMPTY,
                bot_username=BOT_USERNAME,
            )
            return

    lines = [
        msg.IMPORT_EXCEL_DONE.format(
            merged=result.merged,
            points_updated=result.points_updated,
            skipped=result.skipped,
            group_points=result.group_points_applied,
            files=", ".join(result.files_read) or "—",
        )
    ]
    if result.users_not_found:
        lines.append(
            msg.IMPORT_EXCEL_USERS_MISSING.format(
                users=", ".join(result.users_not_found[:10])
            )
        )
    if result.matches_not_found:
        lines.append(
            msg.IMPORT_EXCEL_MATCHES_MISSING.format(
                matches=", ".join(result.matches_not_found[:5])
            )
        )

    await reply_to_user(
        update,
        context,
        "\n".join(lines),
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
