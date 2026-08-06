"""
PDF text extraction (pdfplumber) and validation/insertion of AI-extracted
records against a target table's real schema. Kept separate from the
AI call itself (ai_service.extract_pdf_records) so text extraction and
insertion logic can be tested without hitting OpenAI.
"""
import io

import pdfplumber
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


class PdfParsingError(Exception):
    """Raised with a user-friendly message when a PDF can't be read."""


def extract_text(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise PdfParsingError("This file couldn't be read as a PDF. Make sure it isn't corrupted or password-protected.") from exc

    text_content = "\n".join(pages_text).strip()
    if not text_content:
        raise PdfParsingError("No extractable text was found in this PDF (it may be a scanned image).")
    return text_content


def insertable_columns(table_schema: dict) -> list[str]:
    """Non-primary-key columns — PKs are typically auto-generated (SERIAL) and shouldn't be AI-supplied."""
    return [c["name"] for c in table_schema["columns"] if not c["is_primary_key"]]


def validate_records(records: list[dict], table_schema: dict) -> tuple[list[dict], list[str]]:
    """
    Filters each record down to real columns, coerces obviously-typed values,
    and flags rows missing a required (NOT NULL, non-PK) field. Returns
    (cleaned_records, warnings) — cleaned_records still includes flagged rows
    so the user can fix them in the preview grid rather than losing the row.
    """
    valid_columns = {c["name"]: c for c in table_schema["columns"] if not c["is_primary_key"]}
    required_columns = [name for name, col in valid_columns.items() if not col["nullable"]]

    cleaned, warnings = [], []
    for i, record in enumerate(records):
        row = {col: record.get(col) for col in valid_columns}
        missing = [col for col in required_columns if row.get(col) in (None, "")]
        if missing:
            warnings.append(f"Row {i + 1}: missing required field(s) {', '.join(missing)}.")
        cleaned.append(row)

    return cleaned, warnings


def insert_records(url: str, table_name: str, columns: list[str], records: list[dict]) -> int:
    """
    Parameterized bulk insert — column/table names come only from the
    already-discovered schema (never raw user/AI text), and every value is
    bound, never string-interpolated.
    """
    if not records:
        return 0

    placeholders = ", ".join(f":{col}" for col in columns)
    column_list = ", ".join(f'"{col}"' for col in columns)
    stmt = text(f'INSERT INTO "{table_name}" ({column_list}) VALUES ({placeholders})')

    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            with conn.begin():
                for record in records:
                    conn.execute(stmt, {col: record.get(col) for col in columns})
    except SQLAlchemyError as exc:
        raise PdfParsingError(f"Insert failed: {str(exc.orig) if hasattr(exc, 'orig') else exc}") from exc
    finally:
        engine.dispose()

    return len(records)
