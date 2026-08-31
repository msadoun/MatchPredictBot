"""Send admin messages to bot users (private chat)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Bot, Message

logger = logging.getLogger(__name__)

BROADCAST_DELAY_SEC = 0.05


def split_bot_command(text: str | None) -> tuple[str, list[str]] | None:
    """Parse `/command@bot args` from message text or photo caption."""
    if not text:
        return None
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    first, *rest = stripped.split()
    name = first[1:].split("@", 1)[0].lower()
    if not name:
        return None
    return name, rest


def is_image_message(message: Message | None) -> bool:
    if not message:
        return False
    if message.photo:
        return True
    document = message.document
    if document and str(document.mime_type or "").startswith("image/"):
        return True
    return False


def image_source_message(message: Message | None) -> Message | None:
    """Photo on this message, or a photo the admin replied to."""
    if not message:
        return None
    if is_image_message(message):
        return message
    replied = message.reply_to_message
    if is_image_message(replied):
        return replied
    return None


def copy_caption_for_command(
    extra_text: str,
    *,
    image_is_command_message: bool,
) -> str | None:
    """Caption to send with a copied image.

    Extra text after the command always wins. If the image itself carries the
    slash-command caption, drop that command so users don't see it. Otherwise
    keep the original photo caption (return None).
    """
    if extra_text:
        return extra_text
    if image_is_command_message:
        return ""
    return None


async def _deliver(send) -> str:
    from telegram.error import Forbidden, RetryAfter

    try:
        await send()
        return "sent"
    except Forbidden:
        return "blocked"
    except RetryAfter as exc:
        await asyncio.sleep(float(exc.retry_after) + 1)
        try:
            await send()
            return "sent"
        except Forbidden:
            return "blocked"
        except Exception as exc2:
            logger.warning("Send failed after retry: %s", exc2)
            return "failed"
    except Exception as exc:
        logger.warning("Send failed: %s", exc)
        return "failed"


async def send_user_message(bot: Bot, telegram_id: int, text: str) -> str:
    """Send one text message. Returns: sent | blocked | failed."""
    return await _deliver(lambda: bot.send_message(chat_id=telegram_id, text=text))


async def send_user_image(
    bot: Bot,
    telegram_id: int,
    *,
    from_chat_id: int,
    message_id: int,
    caption: str | None = None,
) -> str:
    """Copy an admin photo/image to one user. Returns: sent | blocked | failed."""

    async def _send():
        kwargs: dict[str, object] = {
            "chat_id": telegram_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        if caption is not None:
            kwargs["caption"] = caption
        await bot.copy_message(**kwargs)

    return await _deliver(_send)


async def broadcast_message(
    bot: Bot,
    text: str,
    telegram_ids: list[int],
) -> dict[str, int]:
    sent = blocked = failed = 0
    for telegram_id in telegram_ids:
        result = await send_user_message(bot, telegram_id, text)
        if result == "sent":
            sent += 1
        elif result == "blocked":
            blocked += 1
        else:
            failed += 1
        await asyncio.sleep(BROADCAST_DELAY_SEC)
    return {
        "total": len(telegram_ids),
        "sent": sent,
        "blocked": blocked,
        "failed": failed,
    }


async def broadcast_image(
    bot: Bot,
    telegram_ids: list[int],
    *,
    from_chat_id: int,
    message_id: int,
    caption: str | None = None,
) -> dict[str, int]:
    sent = blocked = failed = 0
    for telegram_id in telegram_ids:
        result = await send_user_image(
            bot,
            telegram_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            caption=caption,
        )
        if result == "sent":
            sent += 1
        elif result == "blocked":
            blocked += 1
        else:
            failed += 1
        await asyncio.sleep(BROADCAST_DELAY_SEC)
    return {
        "total": len(telegram_ids),
        "sent": sent,
        "blocked": blocked,
        "failed": failed,
    }
