"""Automatic per-group leaderboard points when specific users join a group."""

from config import M2USAB_AUTO_GROUP_POINTS, M2USAB_TELEGRAM_ID, M2USAB_USERNAME


def auto_group_points_for_user(
    *,
    telegram_id: int,
    username: str | None,
) -> int | None:
    handle = (username or "").strip().lstrip("@").lower()
    if telegram_id == M2USAB_TELEGRAM_ID or handle == M2USAB_USERNAME:
        if M2USAB_AUTO_GROUP_POINTS <= 0:
            return None
        return M2USAB_AUTO_GROUP_POINTS
    return None
