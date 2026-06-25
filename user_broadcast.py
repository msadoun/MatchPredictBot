"""Send admin messages to bot users (private chat)."""

import asyncio
import logging

from telegram import Bot
from telegram.error import Forbidden, RetryAfter

logger = logging.getLogger(__name__)

BROADCAST_DELAY_SEC = 0.05


async def send_user_message(bot: Bot, telegram_id: int, text: str) -> str:
    """Send one message. Returns: sent | blocked | failed."""
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        return "sent"
    except Forbidden:
        return "blocked"
    except RetryAfter as exc:
        await asyncio.sleep(float(exc.retry_after) + 1)
        try:
            await bot.send_message(chat_id=telegram_id, text=text)
            return "sent"
        except Forbidden:
            return "blocked"
        except Exception as exc2:
            logger.warning("Send to %s failed after retry: %s", telegram_id, exc2)
            return "failed"
    except Exception as exc:
        logger.warning("Send to %s failed: %s", telegram_id, exc)
        return "failed"


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
