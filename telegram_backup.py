"""Send prediction backups to admins via Telegram — survives server redeploys."""

import io
import json
import logging
from datetime import datetime

from telegram import Bot

from config import ADMIN_USER_IDS

logger = logging.getLogger(__name__)

_last_sent_count = -1


async def send_backup_to_admins(bot: Bot, *, force: bool = False) -> bool:
    """Upload the latest predictions JSON to every admin's private chat."""
    global _last_sent_count
    if not ADMIN_USER_IDS:
        return False

    from prediction_backup import count_predictions, export_predictions_payload

    count = count_predictions()
    if count == 0:
        return False
    if not force and count == _last_sent_count:
        return False

    payload = export_predictions_payload()
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    sent_any = False

    for admin_id in ADMIN_USER_IDS:
        bio = io.BytesIO(data)
        bio.name = f"predictions_{stamp}.json"
        try:
            await bot.send_document(
                chat_id=admin_id,
                document=bio,
                caption=f"نسخة احتياطية: {count} توقع",
            )
            sent_any = True
        except Exception as exc:
            logger.warning("Telegram backup to admin %s failed: %s", admin_id, exc)

    if sent_any:
        _last_sent_count = count
        logger.info("Sent Telegram backup (%d predictions) to admins", count)
    return sent_any
