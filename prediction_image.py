"""Generate PNG table images of match predictions for admin use."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from database import Match, User, list_predictions_for_match


FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
class MatchPredictionRow:
    index: int
    display_name: str
    username: str | None
    home_score: int
    away_score: int
    points: int | None
    is_doubled: bool


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    trimmed = text
    while trimmed and draw.textlength(trimmed + ellipsis, font=font) > max_width:
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

    title_font = _load_font(26, bold=True)
    sub_font = _load_font(18)
    header_font = _load_font(17, bold=True)
    body_font = _load_font(17)
    footer_font = _load_font(15)

    draw.rectangle((0, 0, WIDTH, HEADER_HEIGHT), fill=HEADER_BG)
    title, kickoff, result = _match_header_lines(match)
    draw.text((MARGIN, 18), title, font=title_font, fill=HEADER_TEXT)
    draw.text((MARGIN, 58), kickoff, font=sub_font, fill=(220, 235, 228))
    draw.text((MARGIN, 88), result, font=sub_font, fill=(220, 235, 228))

    table_top = HEADER_HEIGHT
    draw.rectangle(
        (MARGIN, table_top, WIDTH - MARGIN, table_top + TABLE_HEADER_HEIGHT),
        fill=TABLE_HEADER_BG,
        outline=BORDER,
    )

    headers = ("#", "اللاعب", "التوقع", "النقاط", "مضاعف")
    for (x0, x1), label in zip(cols, headers):
        text = label
        text_width = draw.textlength(text, font=header_font)
        if label == "#":
            tx = x0 + 8
        else:
            tx = x1 - text_width - 10
        draw.text((tx, table_top + 12), text, font=header_font, fill=TEXT)

    y = table_top + TABLE_HEADER_HEIGHT
    if not rows:
        draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + ROW_HEIGHT), fill=ROW_EVEN, outline=BORDER)
        empty = "لا توجد توقعات لهذه المباراة بعد"
        text_width = draw.textlength(empty, font=body_font)
        draw.text(
            ((WIDTH - text_width) / 2, y + 14),
            empty,
            font=body_font,
            fill=MUTED,
        )
        y += ROW_HEIGHT
    else:
        for row_index, row in enumerate(rows):
            row_bg = ROW_EVEN if row_index % 2 == 0 else ROW_ODD
            draw.rectangle((MARGIN, y, WIDTH - MARGIN, y + ROW_HEIGHT), fill=row_bg, outline=BORDER)

            index_text = str(row.index)
            draw.text((cols[0][0] + 10, y + 13), index_text, font=body_font, fill=MUTED)

            user_label = _format_user_label(
                User(
                    id=0,
                    telegram_id=0,
                    username=row.username,
                    display_name=row.display_name,
                )
            )
            user_text = _truncate(draw, user_label, body_font, cols[1][1] - cols[1][0] - 16)
            draw.text((cols[1][0] + 8, y + 13), user_text, font=body_font, fill=TEXT)

            score_text = f"{row.home_score}-{row.away_score}"
            score_width = draw.textlength(score_text, font=body_font)
            draw.text((cols[2][1] - score_width - 10, y + 13), score_text, font=body_font, fill=TEXT)

            points_text = "—" if row.points is None else str(row.points)
            points_width = draw.textlength(points_text, font=body_font)
            points_color = ACCENT if row.points and row.points > 0 else MUTED
            draw.text(
                (cols[3][1] - points_width - 10, y + 13),
                points_text,
                font=body_font,
                fill=points_color,
            )

            double_text = "نعم" if row.is_doubled else "—"
            double_width = draw.textlength(double_text, font=body_font)
            double_color = DOUBLE_COLOR if row.is_doubled else MUTED
            draw.text(
                (cols[4][1] - double_width - 10, y + 13),
                double_text,
                font=body_font,
                fill=double_color,
            )
            y += ROW_HEIGHT

    footer_y = y + 8
    footer = f"عدد التوقعات: {len(rows)}"
    draw.text((MARGIN, footer_y), footer, font=footer_font, fill=MUTED)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build_match_prediction_image(match: Match) -> bytes:
    rows = rows_for_match(match.id)
    return render_match_prediction_image(match, rows)
