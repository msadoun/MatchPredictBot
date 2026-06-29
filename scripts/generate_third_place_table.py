"""One-off generator for worldcup_third_place.py from FIFA Annex C table."""

import re
from pathlib import Path

SLOTS = ("1Avs", "1Bvs", "1Dvs", "1Evs", "1Gvs", "1Ivs", "1Kvs", "1Lvs")
ROOT = Path(__file__).resolve().parent.parent
WIKI = Path(
    r"C:\Users\moham\.cursor\projects\c-Users-moham-Desktop-Dev-musab"
    r"\agent-tools\00362cb5-7055-47ae-8e60-e040b0b55a99.txt"
)


def main() -> None:
    text = WIKI.read_text(encoding="utf-8")
    lookup: dict[str, tuple[str, ...]] = {}
    for line in text.splitlines():
        match = re.match(
            r"^\|\s*(\d+)\*?\s*\|\s*([A-L](?:\s*\|\s*[A-L]){7})\s*"
            r"\|\s*((?:3[A-L]\s*\|\s*){7}3[A-L])\s*\|",
            line,
        )
        if not match:
            continue
        groups = frozenset(part.strip() for part in match.group(2).split("|"))
        assigns = tuple(part.strip()[1] for part in match.group(3).split("|"))
        lookup["".join(sorted(groups))] = assigns

    lines = [
        '"""FIFA World Cup 2026 Annex C third-place combination table."""',
        "",
        "from __future__ import annotations",
        "",
        "SLOTS: tuple[str, ...] = " + repr(SLOTS),
        "",
        "FIFA_LETTER_TO_ARABIC: dict[str, str] = {",
        '    "A": "أ", "B": "ب", "C": "ج", "D": "د",',
        '    "E": "هـ", "F": "و", "G": "ز", "H": "ح",',
        '    "I": "ط", "J": "ي", "K": "ك", "L": "ل",',
        "}",
        "",
        "ARABIC_LETTER_TO_FIFA: dict[str, str] = {",
        "    v: k for k, v in FIFA_LETTER_TO_ARABIC.items()",
        "}",
        "",
        "WINNER_ARABIC_TO_SLOT: dict[str, str] = {",
        '    "أ": "1Avs", "ب": "1Bvs", "د": "1Dvs", "هـ": "1Evs",',
        '    "ز": "1Gvs", "ط": "1Ivs", "ك": "1Kvs", "ل": "1Lvs",',
        "}",
        "",
        "_COMBINATIONS: dict[str, tuple[str, ...]] = {",
    ]
    for key in sorted(lookup):
        lines.append(f"    {key!r}: {lookup[key]!r},")
    lines += [
        "}",
        "",
        "",
        "def lookup_third_place_assignments(",
        "    qualifying_groups: frozenset[str],",
        ") -> dict[str, str] | None:",
        '    """Return winner slot -> third-place group letter (A-L)."""',
        '    key = "".join(sorted(qualifying_groups))',
        "    row = _COMBINATIONS.get(key)",
        "    if not row:",
        "        return None",
        "    return dict(zip(SLOTS, row, strict=True))",
        "",
    ]
    out = ROOT / "worldcup_third_place.py"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(lookup)} combinations)")


if __name__ == "__main__":
    main()
