"""Resolve knockout placeholder names to real teams from group results."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from worldcup2026 import (
    WORLD_CUP_2026_FIXTURES,
    is_group_stage_label,
    kickoff_label,
    stage_from_kickoff,
)

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

GROUP_BY_LETTER: dict[str, str] = {
    "أ": "المجموعة أ",
    "ب": "المجموعة ب",
    "ج": "المجموعة ج",
    "د": "المجموعة د",
    "هـ": "المجموعة هـ",
    "و": "المجموعة و",
    "ز": "المجموعة ز",
    "ح": "المجموعة ح",
    "ط": "المجموعة ط",
    "ي": "المجموعة ي",
    "ك": "المجموعة ك",
    "ل": "المجموعة ل",
}

FIRST_IN_GROUP = re.compile(r"^أول المجموعة ([أ-ي]+)$")
SECOND_IN_GROUP = re.compile(r"^ثاني المجموعة ([أ-ي]+)$")
THIRD_IN_GROUP = re.compile(r"^ثالث \(([^)]+)\)$")
WINNER_OF = re.compile(r"^فائز م([\d٠-٩]+)$")
RUNNER_UP_OF = re.compile(r"^وصيف م([\d٠-٩]+)$")


def is_placeholder_team(name: str) -> bool:
    name = name.strip()
    return bool(
        FIRST_IN_GROUP.match(name)
        or SECOND_IN_GROUP.match(name)
        or THIRD_IN_GROUP.match(name)
        or WINNER_OF.match(name)
        or RUNNER_UP_OF.match(name)
    )


def _parse_match_ref(digits: str) -> int:
    return int(digits.translate(_ARABIC_DIGITS))


def _group_teams() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for fixture in WORLD_CUP_2026_FIXTURES:
        if is_group_stage_label(fixture.group):
            groups.setdefault(fixture.group, set()).update({fixture.home, fixture.away})
    return groups


_CANONICAL_TEAM_NAMES: dict[str, str] | None = None


def _canonical_team_lookup() -> dict[str, str]:
    """Map DB/ESPN spellings to canonical Arabic names from the fixture list."""
    global _CANONICAL_TEAM_NAMES
    if _CANONICAL_TEAM_NAMES is not None:
        return _CANONICAL_TEAM_NAMES

    canonical: set[str] = set()
    for fixture in WORLD_CUP_2026_FIXTURES:
        if is_group_stage_label(fixture.group):
            canonical.update({fixture.home, fixture.away})

    lookup: dict[str, str] = {name: name for name in canonical}
    from teams_ar import TEAM_EN_TO_AR

    for english, arabic in TEAM_EN_TO_AR.items():
        if arabic in canonical:
            lookup[english] = arabic
            lookup[arabic] = arabic
    _CANONICAL_TEAM_NAMES = lookup
    return lookup


def _canonical_team_name(name: str) -> str:
    return _canonical_team_lookup().get(name.strip(), name.strip())


_KICKOFF_TO_FIXTURE: dict[str, object] = {}


def _fixture_for_kickoff(kickoff_at: str | None):
    if not kickoff_at:
        return None
    if not _KICKOFF_TO_FIXTURE:
        for fixture in WORLD_CUP_2026_FIXTURES:
            _KICKOFF_TO_FIXTURE[kickoff_label(fixture)] = fixture
    return _KICKOFF_TO_FIXTURE.get(kickoff_at)


def _third_place_home_context(row: object) -> str:
    """Use the canonical fixture home (e.g. أول المجموعة ط) for third-place slot lookup."""
    fixture = _fixture_for_kickoff(getattr(row, "kickoff_at", None))
    if fixture and FIRST_IN_GROUP.match(fixture.home):
        return fixture.home
    home = getattr(row, "home_team", "")
    if FIRST_IN_GROUP.match(home.strip()):
        return home
    return home


def build_fifa_match_map(matches: list) -> dict[int, object]:
    """Map FIFA fixture numbers (1–104) to DB rows via kickoff time."""
    by_kickoff: dict[str, list[object]] = defaultdict(list)
    for match in matches:
        if match.kickoff_at:
            by_kickoff[match.kickoff_at].append(match)

    fifa_map: dict[int, object] = {}
    for fifa_number, fixture in enumerate(WORLD_CUP_2026_FIXTURES, start=1):
        candidates = by_kickoff.get(kickoff_label(fixture), [])
        if not candidates:
            continue
        if len(candidates) == 1:
            fifa_map[fifa_number] = candidates[0]
            continue

        exact = [
            match
            for match in candidates
            if match.home_team == fixture.home and match.away_team == fixture.away
        ]
        if len(exact) == 1:
            fifa_map[fifa_number] = exact[0]
            continue
        if exact:
            candidates = exact

        with_results = [
            match
            for match in candidates
            if match.home_score is not None and match.away_score is not None
        ]
        if len(with_results) == 1:
            fifa_map[fifa_number] = with_results[0]
            continue
        if with_results:
            candidates = with_results

        fifa_map[fifa_number] = min(candidates, key=lambda match: int(match.id))
    return fifa_map


@dataclass
class _TeamStanding:
    team: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    gf: int = 0
    ga: int = 0

    @property
    def points(self) -> int:
        return self.won * 3 + self.drawn

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _rank_key(row: _TeamStanding) -> tuple:
    return (-row.points, -row.gd, -row.gf, row.team)


def compute_group_tables(matches: list) -> dict[str, list[_TeamStanding]]:
    """Return group label -> standings rows sorted 1st to 4th."""
    group_teams = _group_teams()
    tables: dict[str, dict[str, _TeamStanding]] = {
        group: {team: _TeamStanding(team) for team in teams}
        for group, teams in group_teams.items()
    }

    for match in matches:
        stage = stage_from_kickoff(match.kickoff_at)
        if not stage or not is_group_stage_label(stage):
            continue
        if match.home_score is None or match.away_score is None:
            continue
        table = tables.get(stage)
        if not table:
            continue
        home = table.get(_canonical_team_name(match.home_team))
        away = table.get(_canonical_team_name(match.away_team))
        if not home or not away:
            continue
        hs, aws = int(match.home_score), int(match.away_score)
        home.played += 1
        away.played += 1
        home.gf += hs
        home.ga += aws
        away.gf += aws
        away.ga += hs
        if hs > aws:
            home.won += 1
            away.lost += 1
        elif hs < aws:
            away.won += 1
            home.lost += 1
        else:
            home.drawn += 1
            away.drawn += 1

    return {
        group: sorted(rows.values(), key=_rank_key)
        for group, rows in tables.items()
    }


def _group_for_letter(letter: str) -> str | None:
    return GROUP_BY_LETTER.get(letter.strip())


def _qualifying_third_group_letters(
    standings: dict[str, list[_TeamStanding]],
) -> frozenset[str]:
    """FIFA letters A-L for groups whose third-place team ranks in the top eight."""
    from worldcup_third_place import FIFA_LETTER_TO_ARABIC

    candidates: list[tuple[_TeamStanding, str]] = []
    for fifa_letter, arabic_letter in FIFA_LETTER_TO_ARABIC.items():
        group = _group_for_letter(arabic_letter)
        rows = standings.get(group or "", [])
        if len(rows) < 3:
            continue
        third = rows[2]
        if third.played < 3:
            continue
        candidates.append((third, fifa_letter))
    candidates.sort(key=lambda item: _rank_key(item[0]))
    return frozenset(fifa for _, fifa in candidates[:8])


def _winner_slot_from_home(home_name: str) -> str | None:
    from worldcup_third_place import WINNER_ARABIC_TO_SLOT

    if match := FIRST_IN_GROUP.match(home_name.strip()):
        return WINNER_ARABIC_TO_SLOT.get(match.group(1))
    return None


def _third_place_team_for_slot(
    slot: str | None,
    assignments: dict[str, str],
    standings: dict[str, list[_TeamStanding]],
) -> str | None:
    from worldcup_third_place import FIFA_LETTER_TO_ARABIC

    if not slot:
        return None
    third_fifa = assignments.get(slot)
    if not third_fifa:
        return None
    group = _group_for_letter(FIFA_LETTER_TO_ARABIC[third_fifa])
    rows = standings.get(group or "", [])
    return rows[2].team if len(rows) > 2 else None


@dataclass
class _Resolver:
    standings: dict[str, list[_TeamStanding]]
    matches_by_fifa: dict[int, object]
    third_assignments: dict[str, str] = field(default_factory=dict)
    cache: dict[str, str] = field(default_factory=dict)

    def resolve(self, name: str, *, winner_home: str | None = None) -> str | None:
        name = name.strip()
        if not is_placeholder_team(name):
            return name
        if name in self.cache:
            return self.cache[name]

        resolved: str | None = None
        if match := FIRST_IN_GROUP.match(name):
            group = _group_for_letter(match.group(1))
            rows = self.standings.get(group or "", [])
            resolved = rows[0].team if rows else None
        elif match := SECOND_IN_GROUP.match(name):
            group = _group_for_letter(match.group(1))
            rows = self.standings.get(group or "", [])
            resolved = rows[1].team if len(rows) > 1 else None
        elif THIRD_IN_GROUP.match(name):
            slot = _winner_slot_from_home(winner_home or "")
            resolved = _third_place_team_for_slot(
                slot, self.third_assignments, self.standings
            )
        elif match := WINNER_OF.match(name):
            match_id = _parse_match_ref(match.group(1))
            resolved = self._match_participant(match_id, want_winner=True)
        elif match := RUNNER_UP_OF.match(name):
            match_id = _parse_match_ref(match.group(1))
            resolved = self._match_participant(match_id, want_winner=False)

        if resolved and not is_placeholder_team(resolved):
            self.cache[name] = resolved
        return resolved

    def _resolved_away(self, row: object) -> str | None:
        away_name = row.away_team.strip()
        if THIRD_IN_GROUP.match(away_name):
            return self.resolve(
                row.away_team,
                winner_home=_third_place_home_context(row),
            )
        return self.resolve(row.away_team)

    def _match_participant(self, fifa_number: int, *, want_winner: bool) -> str | None:
        row = self.matches_by_fifa.get(fifa_number)
        if not row:
            return None
        if row.home_score is None or row.away_score is None:
            return None
        hs, aws = int(row.home_score), int(row.away_score)
        if hs == aws:
            return None

        home = self.resolve(row.home_team)
        away = self._resolved_away(row)
        home_won = hs > aws
        if want_winner:
            chosen = home if home_won else away
        else:
            chosen = away if home_won else home

        if chosen and not is_placeholder_team(chosen):
            return chosen

        # Fall back to names already written in the DB (e.g. after a prior sync).
        winner_side = row.home_team if home_won else row.away_team
        loser_side = row.away_team if home_won else row.home_team
        if want_winner:
            if not is_placeholder_team(winner_side):
                return winner_side
            if THIRD_IN_GROUP.match(winner_side.strip()):
                resolved = self.resolve(
                    winner_side,
                    winner_home=_third_place_home_context(row),
                )
            else:
                resolved = self.resolve(winner_side)
            if resolved and not is_placeholder_team(resolved):
                return resolved
        else:
            if not is_placeholder_team(loser_side):
                return loser_side
            if THIRD_IN_GROUP.match(loser_side.strip()):
                resolved = self.resolve(
                    loser_side,
                    winner_home=_third_place_home_context(row),
                )
            else:
                resolved = self.resolve(loser_side)
            if resolved and not is_placeholder_team(resolved):
                return resolved
        return None


def build_knockout_resolver(matches: list) -> _Resolver:
    from worldcup_third_place import lookup_third_place_assignments

    standings = compute_group_tables(matches)
    qualifying = _qualifying_third_group_letters(standings)
    third_assignments = lookup_third_place_assignments(qualifying) or {}
    return _Resolver(
        standings=standings,
        matches_by_fifa=build_fifa_match_map(matches),
        third_assignments=third_assignments,
    )


def _resolved_pair(
    match: object,
    resolver: _Resolver,
) -> tuple[str, str]:
    home = resolver.resolve(match.home_team) or match.home_team
    away_name = match.away_team
    if THIRD_IN_GROUP.match(away_name.strip()):
        away = (
            resolver.resolve(
                away_name,
                winner_home=_third_place_home_context(match),
            )
            or match.away_team
        )
    else:
        away = resolver.resolve(away_name) or match.away_team
    if is_placeholder_team(home):
        home = match.home_team
    if is_placeholder_team(away):
        away = match.away_team
    return home, away


def resolved_knockout_display_map(matches: list) -> dict[int, tuple[str, str]]:
    """Resolved home/away names for every match (knockout placeholders filled when possible)."""
    resolver = build_knockout_resolver(matches)
    display: dict[int, tuple[str, str]] = {}
    for match in matches:
        stage = stage_from_kickoff(match.kickoff_at)
        if not stage or is_group_stage_label(stage):
            display[int(match.id)] = (match.home_team, match.away_team)
            continue
        display[int(match.id)] = _resolved_pair(match, resolver)
    return display


def resolve_match_display_teams(
    match: object,
    matches: list | None = None,
    *,
    display_map: dict[int, tuple[str, str]] | None = None,
) -> tuple[str, str]:
    if display_map is not None:
        return display_map.get(int(match.id), (match.home_team, match.away_team))

    stage = stage_from_kickoff(match.kickoff_at)
    if not stage or is_group_stage_label(stage):
        return match.home_team, match.away_team

    if matches is None:
        from database import list_matches

        matches = list_matches(open_only=False)

    return resolved_knockout_display_map(matches).get(
        int(match.id),
        (match.home_team, match.away_team),
    )


def resolve_knockout_teams(matches: list) -> dict[int, tuple[str, str]]:
    """Return match_id -> (home_team, away_team) for resolved knockout rows."""
    resolver = build_knockout_resolver(matches)
    updates: dict[int, tuple[str, str]] = {}

    for match in sorted(matches, key=lambda m: int(m.id)):
        stage = stage_from_kickoff(match.kickoff_at)
        if not stage or is_group_stage_label(stage):
            continue
        new_home, new_away = _resolved_pair(match, resolver)
        if new_home != match.home_team or new_away != match.away_team:
            updates[int(match.id)] = (new_home, new_away)
    return updates


def refresh_knockout_fixture_names() -> int:
    """Reset knockout rows to canonical placeholder names from worldcup2026."""
    from database import get_db
    from worldcup2026 import WORLD_CUP_2026_FIXTURES, is_group_stage_label, kickoff_label

    changed = 0
    with get_db() as conn:
        for fixture in WORLD_CUP_2026_FIXTURES:
            if is_group_stage_label(fixture.group):
                continue
            kickoff_at = kickoff_label(fixture)
            row = conn.execute(
                "SELECT id, home_team, away_team FROM matches WHERE kickoff_at = ?",
                (kickoff_at,),
            ).fetchone()
            if not row:
                continue
            if row["home_team"] == fixture.home and row["away_team"] == fixture.away:
                continue
            conn.execute(
                "UPDATE matches SET home_team = ?, away_team = ? WHERE id = ?",
                (fixture.home, fixture.away, row["id"]),
            )
            changed += 1
    return changed


def sync_knockout_team_names() -> int:
    """Write resolved team names into the matches table."""
    from database import get_db, list_matches

    changed = 0
    for _ in range(8):
        all_matches = list_matches(open_only=False)
        updates = resolve_knockout_teams(all_matches)
        if not updates:
            break
        with get_db() as conn:
            for match_id, (home, away) in updates.items():
                conn.execute(
                    "UPDATE matches SET home_team = ?, away_team = ? WHERE id = ?",
                    (home, away, match_id),
                )
                changed += 1
    return changed
