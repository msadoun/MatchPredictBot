from types import SimpleNamespace

from knockout_teams import (
    build_fifa_match_map,
    compute_group_tables,
    is_placeholder_team,
    resolve_knockout_teams,
    resolved_knockout_display_map,
)
from worldcup2026 import (
    WORLD_CUP_2026_FIXTURES,
    is_group_stage_label,
    kickoff_label,
    stage_from_kickoff,
)


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


def _fifa_match(
    fifa_number: int,
    mid: int,
    *,
    hs: int | None = None,
    aws: int | None = None,
    home: str | None = None,
    away: str | None = None,
):
    fixture = WORLD_CUP_2026_FIXTURES[fifa_number - 1]
    return SimpleNamespace(
        id=mid,
        home_team=home if home is not None else fixture.home,
        away_team=away if away is not None else fixture.away,
        kickoff_at=kickoff_label(fixture),
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
        _fifa_match(73, 73),
    ]
    tables = compute_group_tables(matches)
    assert tables["المجموعة أ"][0].team == "المكسيك"
    updates = resolve_knockout_teams(matches)
    assert updates[73][0] != "ثاني المجموعة أ"
    assert updates[73][0] != "المكسيك"


def test_winner_placeholder_resolves_after_result():
    matches = [
        _fifa_match(73, 73, home="المكسيك", away="البرازيل", hs=2, aws=1),
        _fifa_match(90, 90),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[90][0] == "المكسيك"


def test_winner_resolves_when_loser_still_placeholder():
    matches = [
        _fifa_match(74, 74, home="ألمانيا", away="ثالث (أ/ب/ج/د/و)", hs=1, aws=0),
        _fifa_match(89, 89),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[89][0] == "ألمانيا"


def test_fifa_combination_assigns_paraguay_to_germany_slot():
    from worldcup_third_place import lookup_third_place_assignments

    assignments = lookup_third_place_assignments(frozenset("BDEFGIJL"))
    assert assignments is not None
    assert assignments["1Evs"] == "D"
    assert assignments["1Ivs"] == "F"


def test_group_e_winner_plays_third_from_group_d_not_ecuador(monkeypatch):
    """Round of 32: Germany (Group E winner) vs Paraguay (3rd Group D), not Sweden."""
    monkeypatch.setattr(
        "knockout_teams._qualifying_third_group_letters",
        lambda _standings: frozenset("BDEFGIJL"),
    )
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
        _fifa_match(74, 74),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[74] == ("ألمانيا", "باراغواي")
    assert updates[74][1] != "السويد"


def test_winner_placeholder_uses_fifa_number_not_db_id():
    """فائز م٧٤ must follow FIFA match 74 even when DB id differs."""
    matches = [
        _fifa_match(74, 99, home="ألمانيا", away="باراغواي", hs=2, aws=1),
        _fifa_match(89, 89),
    ]
    fifa_map = build_fifa_match_map(matches)
    assert int(fifa_map[74].id) == 99
    updates = resolve_knockout_teams(matches)
    assert updates[89][0] == "ألمانيا"


def test_third_place_home_context_uses_fixture_placeholder():
    match = _fifa_match(77, 77, home="فرنسا", away="ثالث (ج/د/و/ز/ح)")
    from knockout_teams import _third_place_home_context

    assert _third_place_home_context(match) == "أول المجموعة ط"


def test_third_place_winner_resolves_after_home_team_synced(monkeypatch):
    """Third-place winner must resolve even when fixture home was already synced."""
    monkeypatch.setattr(
        "knockout_teams._third_place_team_for_slot",
        lambda slot, assignments, standings: "تونس" if slot == "1Ivs" else None,
    )
    matches = [
        _fifa_match(74, 74, home="ألمانيا", away="باراغواي", hs=2, aws=1),
        _fifa_match(
            77,
            77,
            home="فرنسا",
            away="ثالث (ج/د/و/ز/ح)",
            hs=0,
            aws=1,
        ),
        _fifa_match(89, 89),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[89] == ("ألمانيا", "تونس")


def test_english_match_winner_placeholder_resolves():
    from teams_ar import normalize_team_name

    assert normalize_team_name("Match Winner 75") == "فائز م٧٥"

    matches = [
        _fifa_match(75, 75, home="Netherlands", away="Scotland", hs=2, aws=1),
        _fifa_match(90, 90, home="Canada", away="Match Winner 75"),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[90] == ("كندا", "هولندا")

    matches = [
        _fifa_match(74, 74, home="Germany", away="Paraguay", hs=2, aws=1),
        _fifa_match(89, 89, home="Match Winner 74", away="France"),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[89] == ("ألمانيا", "فرنسا")

    matches = [
        _fifa_match(86, 86, home="Argentina", away="Haiti", hs=1, aws=0),
        _fifa_match(88, 88, home="Turkey", away="Paraguay", hs=0, aws=1),
        _fifa_match(95, 95, home="Argentina", away="Match Winner 88"),
    ]
    updates = resolve_knockout_teams(matches)
    assert updates[95] == ("الأرجنتين", "باراغواي")


def test_r16_names_resolve_after_all_r32_results():
    matches = []
    for fifa_number, fixture in enumerate(WORLD_CUP_2026_FIXTURES, start=1):
        stage = fixture.group
        hs = 1 if is_group_stage_label(stage) or stage == "دور الـ32" else None
        aws = 0 if hs is not None else None
        matches.append(
            SimpleNamespace(
                id=fifa_number,
                home_team=fixture.home,
                away_team=fixture.away,
                kickoff_at=kickoff_label(fixture),
                home_score=hs,
                away_score=aws,
            )
        )

    display = resolved_knockout_display_map(matches)
    for match in matches:
        stage = stage_from_kickoff(match.kickoff_at)
        if stage == "دور الـ16":
            home, away = display[match.id]
            assert not is_placeholder_team(home), home
            assert not is_placeholder_team(away), away
