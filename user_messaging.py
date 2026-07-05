from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ChatType
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

import messages as msg


def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in {ChatType.GROUP, ChatType.SUPERGROUP})


def _private_markup(
    reply_markup,
) -> ReplyKeyboardRemove | ReplyKeyboardMarkup | InlineKeyboardMarkup | None:
    if isinstance(reply_markup, (InlineKeyboardMarkup, ReplyKeyboardMarkup)):
        return reply_markup
    if isinstance(reply_markup, ReplyKeyboardRemove):
        return reply_markup
    return None


async def _notify_dm_required(update: Update, bot_username: str) -> None:
    if update.callback_query:
        await update.callback_query.answer(
            msg.DM_REQUIRED_ALERT.format(bot=bot_username),
            show_alert=True,
        )
        return
    if update.message:
        await update.message.reply_text(
            msg.DM_REQUIRED.format(bot=bot_username)
        )


async def reply_to_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    *,
    bot_username: str,
    drop_reply_keyboard: bool = False,
) -> bool:
    user = update.effective_user
    if not user:
        return False

    if not is_group_chat(update):
        markup = _private_markup(reply_markup)
        if drop_reply_keyboard and update.message:
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=".",
                reply_markup=ReplyKeyboardRemove(),
            )
        if update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, reply_markup=markup)
        return True

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=reply_markup,
        )
        return True
    except Forbidden:
        await _notify_dm_required(update, bot_username)
        return False


TELEGRAM_TEXT_LIMIT = 4096
SAFE_TEXT_CHUNK = 3800


def split_text_chunks(text: str, max_len: int = SAFE_TEXT_CHUNK) -> list[str]:
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return [chunk for chunk in chunks if chunk]


async def edit_or_send_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    *,
    bot_username: str,
) -> bool:
    query = update.callback_query
    if not query or not query.message:
        return False

    user = update.effective_user
    if not user:
        return False

    if query.message.chat.type == ChatType.PRIVATE:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
            return True
        except BadRequest as exc:
            err = str(exc).lower()
            if "message is not modified" in err and reply_markup is not None:
                try:
                    await query.edit_message_reply_markup(reply_markup=reply_markup)
                    return True
                except BadRequest:
                    pass
            if "message is too long" in err:
                return await send_chunked_user_text(
                    update,
                    context,
                    text,
                    reply_markup,
                    bot_username=bot_username,
                    prefer_edit=False,
                )
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=text,
                reply_markup=reply_markup,
            )
            return True
        except BadRequest as exc:
            if "message is too long" in str(exc).lower():
                return await send_chunked_user_text(
                    update,
                    context,
                    text,
                    reply_markup,
                    bot_username=bot_username,
                    prefer_edit=False,
                )
            raise
        except Forbidden:
            await _notify_dm_required(update, bot_username)
            return False
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=reply_markup,
        )
        try:
            await query.message.delete()
        except Exception:
            await query.edit_message_text("📩")
        return True
    except Forbidden:
        await _notify_dm_required(update, bot_username)
        return False


async def send_chunked_user_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    *,
    bot_username: str,
    prefer_edit: bool = False,
) -> bool:
    chunks = split_text_chunks(text)
    if not chunks:
        return False

    user = update.effective_user
    if not user:
        return False

    if prefer_edit and update.callback_query and not is_group_chat(update):
        first_markup = reply_markup if len(chunks) == 1 else None
        if await edit_or_send_user(
            update, context, chunks[0], first_markup, bot_username=bot_username
        ):
            for chunk in chunks[1:-1]:
                await context.bot.send_message(chat_id=user.id, text=chunk)
            if len(chunks) > 1:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=chunks[-1],
                    reply_markup=reply_markup,
                )
            return True

    chat_id = user.id if not is_group_chat(update) else user.id
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        try:
            if index == 0 and update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(chunk, reply_markup=markup)
            elif update.message:
                await update.message.reply_text(chunk, reply_markup=markup)
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    reply_markup=markup,
                )
        except Forbidden:
            await _notify_dm_required(update, bot_username)
            return False
    return True
