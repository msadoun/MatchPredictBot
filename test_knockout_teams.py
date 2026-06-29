from types import SimpleNamespace

from knockout_teams import compute_group_tables, resolve_knockout_teams


def _match(
    mid: int,
    home: str,
    away: str,
    stage: str,
    *,
    hs: int | None = None,
    aws: int | None = None,
):
    return SimpleNamespace(
        id=mid,
        home_team=home,
        away_team=away,
        kickoff_at=f"2026-06-20T18:00:00 · {stage}",
        home_score=hs,
        away_score=aws,
    )


def test_group_first_place_resolves_in_knockout():
    matches = [
        _match(
            1,
            "المكسيك",
            "جنوب أفريقيا",
            "المجموعة أ",
            hs=2,
            aws=0,
        ),
        _match(
            73,
            "ثاني المجموعة أ",
            "ثاني المجموعة ب",
            "دور الـ32",
        ),
    ]
    tables = compute_group_tables(matches)
    assert tables["المجموعة أ"][0].team == "المكسيك"
    updates = resolve_knockout_teams(matches)
    assert updates[73][0] != "ثاني المجموعة أ"
    assert updates[73][0] != "المكسيك"


def test_winner_placeholder_resolves_after_result():
    matches = [
        _match(73, "المكسيك", "البرازيل", "دور الـ32", hs=2, aws=1),
        _match(89, "فائز م٧٣", "فائز م٧٤", "دور الـ16"),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[89][0] == "المكسيك"


def test_group_e_winner_plays_third_from_group_d_not_ecuador():
    """Round of 32: Germany (Group E winner) vs Paraguay (3rd Group D), not Ecuador."""
    matches = [
        _match(1, "ألمانيا", "كوراساو", "المجموعة هـ", hs=7, aws=1),
        _match(2, "ساحل العاج", "الإكوادور", "المجموعة هـ", hs=1, aws=1),
        _match(3, "ألمانيا", "ساحل العاج", "المجموعة هـ", hs=2, aws=1),
        _match(4, "الإكوادور", "كوراساو", "المجموعة هـ", hs=2, aws=0),
        _match(5, "كوراساو", "ساحل العاج", "المجموعة هـ", hs=0, aws=3),
        _match(6, "الإكوادور", "ألمانيا", "المجموعة هـ", hs=1, aws=2),
        _match(7, "الولايات المتحدة", "باراغواي", "المجموعة د", hs=1, aws=0),
        _match(8, "أستراليا", "تركيا", "المجموعة د", hs=2, aws=1),
        _match(9, "تركيا", "باراغواي", "المجموعة د", hs=1, aws=1),
        _match(10, "الولايات المتحدة", "أستراليا", "المجموعة د", hs=2, aws=1),
        _match(11, "تركيا", "الولايات المتحدة", "المجموعة د", hs=0, aws=2),
        _match(12, "باراغواي", "أستراليا", "المجموعة د", hs=1, aws=2),
        _match(74, "أول المجموعة هـ", "ثالث (أ/ب/ج/د/و)", "دور الـ32"),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[74] == ("ألمانيا", "باراغواي")
