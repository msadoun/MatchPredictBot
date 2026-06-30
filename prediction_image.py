"""Generate PNG table images of match predictions for admin use."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from database import Match, User, list_predictions_for_match

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
BUNDLED_ARABIC_REGULAR = FONTS_DIR / "NotoNaskhArabic-Regular.ttf"
BUNDLED_ARABIC_BOLD = FONTS_DIR / "NotoNaskhArabic-Bold.ttf"
BUNDLED_LATIN_REGULAR = FONTS_DIR / "DejaVuSans.ttf"
BUNDLED_LATIN_BOLD = FONTS_DIR / "DejaVuSans-Bold.ttf"

ARABIC_FONT_CANDIDATES_REGULAR = (
    BUNDLED_ARABIC_REGULAR,
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
)
ARABIC_FONT_CANDIDATES_BOLD = (
    BUNDLED_ARABIC_BOLD,
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoKufiArabic-Bold.ttf",
)
LATIN_FONT_CANDIDATES_REGULAR = (
    BUNDLED_LATIN_REGULAR,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
LATIN_FONT_CANDIDATES_BOLD = (
    BUNDLED_LATIN_BOLD,
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# Layout
WIDTH = 920
MARGIN = 24
ROW_HEIGHT = 46
HEADER_HEIGHT = 130
TABLE_HEADER_HEIGHT = 44
FOOTER_HEIGHT = 36

BG = (248, 250, 252)
HEADER_BG = (15, 76, 58)
HEADER_TEXT = (255, 255, 255)
TABLE_HEADER_BG = (226, 232, 240)
ROW_EVEN = (255, 255, 255)
ROW_ODD = (241, 245, 249)
BORDER = (203, 213, 225)
TEXT = (15, 23, 42)
MUTED = (100, 116, 139)
ACCENT = (22, 163, 74)
DOUBLE_COLOR = (180, 83, 9)

COL_WEIGHTS = (0.07, 0.40, 0.22, 0.16, 0.15)


@dataclass
class FontPair:
    arabic: ImageFont.FreeTypeFont | ImageFont.ImageFont
    latin: ImageFont.FreeTypeFont | ImageFont.ImageFont


@dataclass
class MatchPredictionRow:
    index: int
    display_name: str
    username: str | None
    home_score: int
    away_score: int
    points: int | None
    is_doubled: bool


def _is_arabic_char(char: str) -> bool:
    code = ord(char)
    return (
        0x0600 <= code <= 0x06FF
        or 0x0750 <= code <= 0x077F
        or 0x08A0 <= code <= 0x08FF
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


def _load_font_file(
    candidates: tuple[Path | str, ...],
    size: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in candidates:
        font_path = Path(path)
        if font_path.is_file():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _load_fonts(size: int, *, bold: bool = False) -> FontPair:
    if bold:
        return FontPair(
            arabic=_load_font_file(ARABIC_FONT_CANDIDATES_BOLD, size),
            latin=_load_font_file(LATIN_FONT_CANDIDATES_BOLD, size),
        )
    return FontPair(
        arabic=_load_font_file(ARABIC_FONT_CANDIDATES_REGULAR, size),
        latin=_load_font_file(LATIN_FONT_CANDIDATES_REGULAR, size),
    )


def _split_text_runs(text: str) -> list[tuple[str, bool]]:
    if not text:
        return []

    runs: list[tuple[str, bool]] = []
    current: list[str] = []
    current_is_arabic: bool | None = None

    for char in text:
        if char.isspace():
            if current_is_arabic is None:
                current_is_arabic = False
            current.append(char)
            continue

        is_arabic = _is_arabic_char(char)
        if current_is_arabic is None:
            current_is_arabic = is_arabic
            current.append(char)
            continue
        if is_arabic == current_is_arabic:
            current.append(char)
            continue

        runs.append(("".join(current), current_is_arabic))
        current = [char]
        current_is_arabic = is_arabic

    if current:
        runs.append(("".join(current), bool(current_is_arabic)))
    return runs


def _text_width(draw: ImageDraw.ImageDraw, text: str, fonts: FontPair) -> float:
    total = 0.0
    for chunk, is_arabic in _split_text_runs(text):
        font = fonts.arabic if is_arabic else fonts.latin
        total += draw.textlength(chunk, font=font)
    return total


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fonts: FontPair,
    fill: tuple[int, int, int],
) -> None:
    x, y = xy
    for chunk, is_arabic in _split_text_runs(text):
        font = fonts.arabic if is_arabic else fonts.latin
        draw.text((x, y), chunk, font=font, fill=fill)
        x += draw.textlength(chunk, font=font)


def _draw_text_right(
    draw: ImageDraw.ImageDraw,
    x_right: float,
    y: float,
    text: str,
    fonts: FontPair,
    fill: tuple[int, int, int],
) -> None:
    width = _text_width(draw, text, fonts)
    _draw_text(draw, (x_right - width, y), text, fonts, fill)


def _truncate(
    draw: ImageDraw.ImageDraw,
    text: str,
    fonts: FontPair,
    max_width: int,
) -> str:
    if _text_width(draw, text, fonts) <= max_width:
        return text
    ellipsis = "…"
    trimmed = text
    while trimmed and _text_width(draw, trimmed + ellipsis, fonts) > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + ellipsis) if trimmed else ellipsis


def _column_bounds() -> list[tuple[int, int]]:
    usable = WIDTH - 2 * MARGIN
    x = MARGIN
    bounds: list[tuple[int, int]] = []
    for weight in COL_WEIGHTS:
        col_width = int(usable * weight)
        bounds.append((x, x + col_width))
        x += col_width
    bounds[-1] = (bounds[-1][0], WIDTH - MARGIN)
    return bounds


def _format_user_label(user: User) -> str:
    return user.display_name


def rows_for_match(match_id: int) -> list[MatchPredictionRow]:
    pairs = list_predictions_for_match(match_id)
    rows: list[MatchPredictionRow] = []
    for index, (user, prediction) in enumerate(pairs, start=1):
        rows.append(
            MatchPredictionRow(
                index=index,
                display_name=user.display_name,
                username=user.username,
                home_score=prediction.home_score,
                away_score=prediction.away_score,
                points=prediction.points,
                is_doubled=prediction.is_doubled,
            )
        )
    return rows


def _match_header_lines(match: Match) -> tuple[str, str, str]:
    title = f"#{match.id}  {match.home_team}  ضد  {match.away_team}"
    kickoff = f"الموعد: {match.kickoff_at}" if match.kickoff_at else "الموعد: —"
    if match.home_score is not None and match.away_score is not None:
        result = f"النتيجة: {match.home_score}-{match.away_score}"
    else:
        result = "النتيجة: لم تُسجَّل بعد"
    return title, kickoff, result


def _image_height(row_count: int) -> int:
    body_rows = max(row_count, 1)
    return HEADER_HEIGHT + TABLE_HEADER_HEIGHT + body_rows * ROW_HEIGHT + FOOTER_HEIGHT + MARGIN


def render_match_prediction_image(match: Match, rows: list[MatchPredictionRow]) -> bytes:
    height = _image_height(len(rows))
    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)
    cols = _column_bounds()

    title_fonts = _load_fonts(26, bold=True)
    sub_fonts = _load_fonts(18)
    header_fonts = _load_fonts(17, bold=True)
    body_fonts = _load_fonts(17)
    footer_fonts = _load_fonts(15)

    draw.rectangle((0, 0, WIDTH, HEADER_HEIGHT), fill=HEADER_BG)
    title, kickoff, result = _match_header_lines(match)
    _draw_text(draw, (MARGIN, 18), title, title_fonts, HEADER_TEXT)
    _draw_text(draw, (MARGIN, 58), kickoff, sub_fonts, (220, 235, 228))
    _draw_text(draw, (MARGIN, 88), result, sub_fonts, (220, 235, 228))

    table_top = HEADER_HEIGHT
    draw.rectangle(
        (MARGIN, table_top, WIDTH - MARGIN, table_top + TABLE_HEADER_HEIGHT),
        fill=TABLE_HEADER_BG,
        outline=BORDER,
    )

    headers = ("#", "اللاعب", "التوقع", "النقاط", "مضاعف")
    for (x0, x1), label in zip(cols, headers):
        if label == "#":
            _draw_text(draw, (x0 + 8, table_top + 12), label, header_fonts, TEXT)
        else:
            _draw_text_right(
                draw, x1 - 10, table_top + 12, label, header_fonts, TEXT
            )

    y = table_top + TABLE_HEADER_HEIGHT
    if not rows:
        draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + ROW_HEIGHT), fill=ROW_EVEN, outline=BORDER)
        empty = "لا توجد توقعات لهذه المباراة بعد"
        empty_width = _text_width(draw, empty, body_fonts)
        _draw_text(
            draw,
            ((WIDTH - empty_width) / 2, y + 14),
            empty,
            body_fonts,
            MUTED,
        )
        y += ROW_HEIGHT
    else:
        for row_index, row in enumerate(rows):
            row_bg = ROW_EVEN if row_index % 2 == 0 else ROW_ODD
            draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + ROW_HEIGHT), fill=row_bg, outline=BORDER)

            _draw_text(
                draw,
                (cols[0][0] + 10, y + 13),
                str(row.index),
                body_fonts,
                MUTED,
            )

            user_label = _format_user_label(
                User(
                    id=0,
                    telegram_id=0,
                    username=row.username,
                    display_name=row.display_name,
                )
            )
            user_text = _truncate(
                draw,
                user_label,
                body_fonts,
                cols[1][1] - cols[1][0] - 16,
            )
            _draw_text(draw, (cols[1][0] + 8, y + 13), user_text, body_fonts, TEXT)

            score_text = f"{row.home_score}-{row.away_score}"
            _draw_text_right(
                draw, cols[2][1] - 10, y + 13, score_text, body_fonts, TEXT
            )

            points_text = "—" if row.points is None else str(row.points)
            points_color = ACCENT if row.points and row.points > 0 else MUTED
            _draw_text_right(
                draw, cols[3][1] - 10, y + 13, points_text, body_fonts, points_color
            )

            double_text = "نعم" if row.is_doubled else "—"
            double_color = DOUBLE_COLOR if row.is_doubled else MUTED
            _draw_text_right(
                draw, cols[4][1] - 10, y + 13, double_text, body_fonts, double_color
            )
            y += ROW_HEIGHT

    footer_y = y + 8
    footer = f"عدد التوقعات: {len(rows)}"
    _draw_text(draw, (MARGIN, footer_y), footer, footer_fonts, MUTED)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build_match_prediction_image(match: Match) -> bytes:
    rows = rows_for_match(match.id)
    return render_match_prediction_image(match, rows)
