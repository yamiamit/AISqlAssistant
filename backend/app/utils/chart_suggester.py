"""
Picks a sensible default chart type from a query result shape. Deliberately
simple, rule-based logic (not another AI call) — the frontend lets the user
switch chart types anyway, so this only needs to guess a reasonable default.
"""
import re
from datetime import date, datetime

_DATE_COLUMN_HINT = re.compile(r"(date|month|year|day|time|created_at|updated_at)", re.IGNORECASE)


def suggest_chart_type(columns: list[str], rows: list[dict]) -> str | None:
    if not rows or len(columns) < 2:
        return None

    sample = rows[0]
    numeric_columns = [c for c in columns if isinstance(sample.get(c), (int, float))]
    if not numeric_columns:
        return None

    label_column = next((c for c in columns if c not in numeric_columns), None)
    if label_column and _DATE_COLUMN_HINT.search(label_column):
        return "line"

    if label_column and isinstance(sample.get(label_column), (datetime, date)):
        return "line"

    if len(columns) == 2 and len(rows) <= 8:
        return "pie"

    return "bar"
