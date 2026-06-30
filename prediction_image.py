"""Render match prediction photos from the same Excel row data as prediction_reports."""

from __future__ import annotations

import html
import io
from pathlib import Path

import pypdfium2 as pdfium
from openpyxl import Workbook
from weasyprint import HTML

import prediction_reports as reports
from database import Match

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
ROW_FILL = "#C5D9F1"

DISPLAY_HEADERS = {
    "user name": "اللاعب",
    "prediction": "التوقع",
    "double": "مضاعف",
}


def _match_title(match: Match) -> str:
    if match.home_score is not None and match.away_score is not None:
        result = f"النتيجة: {match.home_score}-{match.away_score}"
    else:
        result = "النتيجة: لم تُسجَّل بعد"
    kickoff = match.kickoff_at or "—"
    return (
        f"#{match.id} · {match.home_team} ضد {match.away_team}<br>"
        f"الموعد: {html.escape(kickoff)}<br>"
        f"{html.escape(result)}"
    )


def _display_header(header: str) -> str:
    return DISPLAY_HEADERS.get(header, header)


def _workbook_table_html(workbook: Workbook, *, title: str) -> str:
    sheet = workbook.active
    all_rows = list(sheet.iter_rows(values_only=True))
    if not all_rows:
        body_rows = (
            '<tr class="white"><td colspan="3">لا توجد توقعات لهذه المباراة بعد</td></tr>'
        )
    else:
        header_cells = "".join(
            f"<th>{html.escape(_display_header(str(value or '')))}</th>"
            for value in all_rows[0]
        )
        header_row = f'<tr class="header">{header_cells}</tr>'

        data_rows: list[str] = []
        for index, row in enumerate(all_rows[1:]):
            css_class = "white" if index % 2 == 0 else "alt"
            cells = "".join(
                f"<td>{html.escape(str(value) if value is not None else '')}</td>"
                for value in row
            )
            data_rows.append(f'<tr class="{css_class}">{cells}</tr>')

        if data_rows:
            body_rows = header_row + "".join(data_rows)
        else:
            body_rows = header_row + (
                '<tr class="white"><td colspan="3">لا توجد توقعات لهذه المباراة بعد</td></tr>'
            )

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
@font-face {{
  font-family: "NotoArabic";
  src: url("NotoNaskhArabic-Regular.ttf");
  font-weight: 400;
}}
@font-face {{
  font-family: "NotoArabic";
  src: url("NotoNaskhArabic-Bold.ttf");
  font-weight: 700;
}}
body {{
  font-family: "NotoArabic", sans-serif;
  margin: 20px;
  color: #111827;
}}
.title {{
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 14px;
  line-height: 1.5;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  direction: rtl;
  font-size: 16px;
}}
th, td {{
  border: 1px solid #94a3b8;
  padding: 12px 14px;
  text-align: right;
  vertical-align: middle;
}}
.header th {{
  background: {ROW_FILL};
  font-weight: 700;
}}
.white td {{
  background: #ffffff;
}}
.alt td {{
  background: {ROW_FILL};
}}
</style>
</head>
<body>
<div class="title">{title}</div>
<table>
{body_rows}
</table>
</body>
</html>"""


def workbook_to_png(workbook: Workbook, *, title: str) -> bytes:
    html_doc = _workbook_table_html(workbook, title=title)
    pdf_bytes = HTML(string=html_doc, base_url=str(FONTS_DIR)).write_pdf()
    pdf_doc = pdfium.PdfDocument(pdf_bytes)
    page = pdf_doc[0]
    bitmap = page.render(scale=2)
    image = bitmap.to_pil()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build_match_prediction_image(match: Match) -> bytes:
    workbook = reports.build_match_photo_workbook(match)
    return workbook_to_png(workbook, title=_match_title(match))
