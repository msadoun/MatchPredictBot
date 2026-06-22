"""Predefined manual group leaderboard standings."""

# https://t.me/alkoram3na — الكورة معنا
ALKORAM3NA_GROUP_USERNAME = "alkoram3na"

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

# https://t.me/+2TIcPEGwjo8wOTg0 — K m3na groub
KM3NA_GROUP_USERNAME = "km3na"
KM3NA_INVITE_SLUG = "2tiecpegwjo8wotg0"

KM3NA_STANDINGS: list[tuple[str, int]] = [
    ("M2usab", 27),
    ("AbduIIah7k", 25),
    ("Abdullah7K", 25),
    ("waelalamoudi", 22),
    ("حازم .", 21),
    ("AHMED", 17),
    ("HMAsir0", 7),
    ("shamlan1998", 1),
]

# K m3na groub — Telegram supergroup (user ID: 1001298782951 → -1001298782951)
ROSTER_GROUP_CHAT_ID = -1001298782951

GROUP_CHAT_DISPLAY_NAMES: dict[int, str] = {
    ROSTER_GROUP_CHAT_ID: "K m3na groub",
}


def group_display_name(
    chat_id: int,
    *,
    telegram_title: str | None = None,
) -> str | None:
    """Human-readable group label — never returns a raw chat ID."""
    title = (telegram_title or "").strip()
    if title and title != str(chat_id) and not title.lstrip("-").isdigit():
        return title

    from config import ALKORAM3NA_GROUP_CHAT_ID, KM3NA_GROUP_CHAT_ID

    names = dict(GROUP_CHAT_DISPLAY_NAMES)
    if KM3NA_GROUP_CHAT_ID.lstrip("-").isdigit():
        names[int(KM3NA_GROUP_CHAT_ID)] = "K m3na groub"
    if ALKORAM3NA_GROUP_CHAT_ID.lstrip("-").isdigit():
        names[int(ALKORAM3NA_GROUP_CHAT_ID)] = "الكورة معنا"
    return names.get(chat_id)


GROUP_STANDING_ALIASES: dict[str, list[tuple[str, int]]] = {
    ALKORAM3NA_GROUP_USERNAME: ALKORAM3NA_STANDINGS,
    "alkora": ALKORAM3NA_STANDINGS,
    "الكورة_معنا": ALKORAM3NA_STANDINGS,
    KM3NA_GROUP_USERNAME: KM3NA_STANDINGS,
    "k_m3na_groub": KM3NA_STANDINGS,
    "k m3na groub": KM3NA_STANDINGS,
    "k_m3na": KM3NA_STANDINGS,
    KM3NA_INVITE_SLUG: KM3NA_STANDINGS,
    str(ROSTER_GROUP_CHAT_ID).lstrip("-"): KM3NA_STANDINGS,
}

GROUP_TITLE_HINTS: dict[str, set[str]] = {
    ALKORAM3NA_GROUP_USERNAME: {"alkoram3na", "الكورة معنا", "alkora"},
    KM3NA_GROUP_USERNAME: {"k m3na groub", "km3na groub", "k m3na", "km3na"},
}

PREDEFINED_GROUP_STANDINGS = GROUP_STANDING_ALIASES

# Always listed in admin Excel exports (empty cells if no prediction yet).
# Existing members with predictions are never removed — this list only adds rows.
EXCEL_ALWAYS_INCLUDE_USERS: list[str] = [
    "M2usab",
    "waelalamoudi",
    "AbduIIah7k",
    "حازم .",
    "shamlan1998",
    "AHMED",
    "HMAsir0",
]

# Alternate spellings tried when resolving Excel roster usernames.
EXCEL_USER_ALIASES: dict[str, tuple[str, ...]] = {
    "M2usab": ("M2usab", "m2usab"),
    "AbduIIah7k": ("AbduIIah7k", "Abdullah7K", "AbduIIah7K"),
    "waelalamoudi": ("waelalamoudi",),
    "shamlan1998": ("shamlan1998",),
    "HMAsir0": ("HMAsir0",),
    "AHMED": ("AHMED",),
    "حازم .": ("حازم .", "حازم"),
}


def resolve_roster_user(ref: str):
    """Resolve a roster username/display name to a User (or None)."""
    from database import resolve_user_ref

    aliases = EXCEL_USER_ALIASES.get(ref, (ref,))
    for alias in aliases:
        user = resolve_user_ref(alias)
        if user:
            return user
    return None


def roster_manual_points(ref: str) -> int | None:
    """Target leaderboard total for a roster member (base + existing prediction pts)."""
    aliases = {a.lower() for a in EXCEL_USER_ALIASES.get(ref, (ref,))}
    aliases.add(ref.strip().lstrip("@").lower())
    for name, points in KM3NA_STANDINGS:
        if name.lower() in aliases:
            return points
        for alias in EXCEL_USER_ALIASES.get(name, (name,)):
            if alias.lower() in aliases:
                return points
    return None
