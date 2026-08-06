"""
Turns a stored Message (prompt + SQL + explanation + result set) into
downloadable files: a CSV of the raw results, or a one-page PDF report.

Matplotlib (Agg backend, no display needed) renders the chart image that gets
embedded in the PDF — reusing the same simple chart-type heuristic as the
live chat UI, just server-side since the PDF has no interactive frontend.
"""
import csv
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MAX_PDF_TABLE_ROWS = 30


def build_csv(columns: list[str], rows: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _render_chart_image(columns: list[str], rows: list[dict], chart_type: str | None) -> bytes | None:
    if not chart_type or not rows or len(columns) < 2:
        return None

    sample = rows[0]
    numeric_col = next((c for c in columns if isinstance(sample.get(c), (int, float))), None)
    label_col = next((c for c in columns if c != numeric_col), None)
    if not numeric_col or not label_col:
        return None

    labels = [str(r.get(label_col))[:20] for r in rows[:15]]
    values = [r.get(numeric_col) or 0 for r in rows[:15]]

    fig, ax = plt.subplots(figsize=(6, 3.2))
    if chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.0f%%")
    elif chart_type == "line":
        ax.plot(labels, values, marker="o")
        ax.set_ylabel(numeric_col)
        plt.xticks(rotation=45, ha="right", fontsize=7)
    else:
        ax.bar(labels, values)
        ax.set_ylabel(numeric_col)
        plt.xticks(rotation=45, ha="right", fontsize=7)

    fig.tight_layout()
    image_buffer = io.BytesIO()
    fig.savefig(image_buffer, format="png", dpi=150)
    plt.close(fig)
    image_buffer.seek(0)
    return image_buffer.read()


def build_pdf_report(
    prompt_text: str,
    generated_sql: str,
    explanation: str,
    columns: list[str],
    rows: list[dict],
    execution_time_ms: float,
    row_count: int,
    chart_type: str | None,
    created_at: str,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    code_style = ParagraphStyle("Code", parent=styles["Code"], fontSize=8, leading=10)

    story = [
        Paragraph("AI SQL Assistant — Query Report", styles["Title"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"<b>Generated:</b> {created_at}", styles["Normal"]),
        Spacer(1, 0.4 * cm),
        Paragraph("<b>User Prompt</b>", styles["Heading3"]),
        Paragraph(prompt_text, styles["Normal"]),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Generated SQL</b>", styles["Heading3"]),
        Paragraph(generated_sql.replace("\n", "<br/>"), code_style),
        Spacer(1, 0.3 * cm),
        Paragraph("<b>Explanation</b>", styles["Heading3"]),
        Paragraph(explanation or "—", styles["Normal"]),
        Spacer(1, 0.3 * cm),
        Paragraph(f"<b>Execution time:</b> {execution_time_ms} ms &nbsp;&nbsp; <b>Rows returned:</b> {row_count}", styles["Normal"]),
        Spacer(1, 0.4 * cm),
    ]

    if rows:
        story.append(Paragraph("<b>Result Table</b>", styles["Heading3"]))
        table_data = [columns] + [[str(r.get(c, "")) for c in columns] for r in rows[:MAX_PDF_TABLE_ROWS]]
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ]))
        story.append(table)
        if row_count > MAX_PDF_TABLE_ROWS:
            story.append(Paragraph(f"... and {row_count - MAX_PDF_TABLE_ROWS} more rows (see CSV export for full data).", styles["Italic"]))
        story.append(Spacer(1, 0.4 * cm))

    chart_bytes = _render_chart_image(columns, rows, chart_type)
    if chart_bytes:
        story.append(Paragraph("<b>Chart</b>", styles["Heading3"]))
        story.append(Image(io.BytesIO(chart_bytes), width=15 * cm, height=8 * cm))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
