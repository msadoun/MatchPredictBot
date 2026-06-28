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
