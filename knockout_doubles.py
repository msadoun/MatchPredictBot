"""Knockout-stage double points: half of matches per stage, exact score only."""

from worldcup2026 import KNOCKOUT_STAGES, WORLD_CUP_2026_FIXTURES, stage_from_kickoff


def is_knockout_stage(stage: str | None) -> bool:
    return bool(stage and stage in KNOCKOUT_STAGES)


def match_knockout_stage(kickoff_at: str | None) -> str | None:
    stage = stage_from_kickoff(kickoff_at)
    return stage if is_knockout_stage(stage) else None


def doubles_allowed_for_stage(stage: str) -> int:
    if not is_knockout_stage(stage):
        return 0
    count = sum(1 for fixture in WORLD_CUP_2026_FIXTURES if fixture.group == stage)
    return count // 2


def list_knockout_stages() -> list[str]:
    return list(KNOCKOUT_STAGES)
