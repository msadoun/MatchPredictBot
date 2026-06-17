from telegram import Update
from telegram.constants import ChatType
from telegram.error import Forbidden
from telegram.ext import ContextTypes

import messages as msg


def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type in {ChatType.GROUP, ChatType.SUPERGROUP})


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
    menu_markup=None,
) -> bool:
    user = update.effective_user
    if not user:
        return False

    markup = menu_markup if menu_markup is not None else reply_markup

    if not is_group_chat(update):
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
        await query.edit_message_text(text, reply_markup=reply_markup)
        return True

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
