"""Predefined manual group leaderboard standings."""

# https://t.me/alkoram3na — الكورة معنا
ALKORAM3NA_GROUP_USERNAME = "alkoram3na"

# Removed K m3na groub — purge any remaining DB rows for this chat ID on startup.
LEGACY_KM3NA_GROUP_CHAT_ID = -1001298782951

ALKORAM3NA_STANDINGS: list[tuple[str, int]] = [
    ("M2usab", 24),
    ("Abdullah7K", 22),
    ("bader91Z", 21),
    ("Saeedentist", 20),
    ("waelalamoudi", 19),
    ("حازم .", 17),
    ("Skyrim_Husband", 17),
    ("AHMED", 17),
    ("Muharebkk", 17),
    ("Ali", 16),
    ("ابوبكر عبدالله", 10),
    ("MOAYAD21", 8),
    ("xOlivier", 6),
    ("HMAsir0", 4),
    ("shamlan1998", 1),
]


def group_display_name(
    chat_id: int,
    *,
    telegram_title: str | None = None,
) -> str | None:
    """Human-readable group label — never returns a raw chat ID."""
    title = (telegram_title or "").strip()
    if title and title != str(chat_id) and not title.lstrip("-").isdigit():
        return title

    from config import ALKORAM3NA_GROUP_CHAT_ID

    if ALKORAM3NA_GROUP_CHAT_ID.lstrip("-").isdigit():
        if chat_id == int(ALKORAM3NA_GROUP_CHAT_ID):
            return "الكورة معنا"
    return None


GROUP_STANDING_ALIASES: dict[str, list[tuple[str, int]]] = {
    ALKORAM3NA_GROUP_USERNAME: ALKORAM3NA_STANDINGS,
    "alkora": ALKORAM3NA_STANDINGS,
    "الكورة_معنا": ALKORAM3NA_STANDINGS,
}

GROUP_TITLE_HINTS: dict[str, set[str]] = {
    ALKORAM3NA_GROUP_USERNAME: {"alkoram3na", "الكورة معنا", "alkora"},
}

PREDEFINED_GROUP_STANDINGS = GROUP_STANDING_ALIASES

EXCEL_ALWAYS_INCLUDE_USERS: list[str] = [
    name for name, _ in ALKORAM3NA_STANDINGS
]

EXCEL_USER_ALIASES: dict[str, tuple[str, ...]] = {
    "M2usab": ("M2usab", "m2usab"),
    "Abdullah7K": ("Abdullah7K", "AbduIIah7k", "AbduIIah7K"),
    "waelalamoudi": ("waelalamoudi",),
    "shamlan1998": ("shamlan1998",),
    "HMAsir0": ("HMAsir0",),
    "AHMED": ("AHMED",),
    "حازم .": ("حازم .", "حازم"),
}


def resolve_excel_user(ref: str):
    """Resolve an Excel roster username/display name to a User (or None)."""
    from database import resolve_user_ref

    aliases = EXCEL_USER_ALIASES.get(ref, (ref,))
    for alias in aliases:
        user = resolve_user_ref(alias)
        if user:
            return user
    return None
