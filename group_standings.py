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

PREDEFINED_GROUP_STANDINGS: dict[str, list[tuple[str, int]]] = {
    ALKORAM3NA_GROUP_USERNAME: ALKORAM3NA_STANDINGS,
    "alkora": ALKORAM3NA_STANDINGS,
    "الكورة_معنا": ALKORAM3NA_STANDINGS,
}
