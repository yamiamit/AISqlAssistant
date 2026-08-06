"""
PDF -> structured data -> Postgres pipeline:
  upload (extract + AI-structure + validate, nothing written yet)
    -> user edits the preview in the UI
    -> confirm (re-validate + parameterized insert).

Splitting upload/confirm into two requests is what makes the "editable
preview before insertion" and "cancel insertion" requirements possible —
nothing touches the database until the user explicitly confirms.
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.db_connection import DBConnection
from app.models.user import User
from app.schemas.pdf import PdfConfirmRequest, PdfConfirmResponse, PdfPreviewResponse
from app.services import target_db
from app.services.ai_service import AIServiceError, extract_pdf_records
from app.services.pdf_service import PdfParsingError, extract_text, insert_records, insertable_columns, validate_records

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _get_table_schema(connection: DBConnection, table_name: str) -> dict:
    tables = (connection.cached_schema or {}).get("tables", [])
    table = next((t for t in tables if t["name"] == table_name), None)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Table '{table_name}' was not found on this connection. Refresh the schema and try again.",
        )
    return table


def _get_owned_connection(db: Session, connection_id: int, user: User) -> DBConnection:
    connection = db.get(DBConnection, connection_id)
    if not connection or connection.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found.")
    return connection


@router.post("/upload", response_model=PdfPreviewResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    db_connection_id: int = Form(...),
    target_table: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large — max {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    connection = _get_owned_connection(db, db_connection_id, user)
    table_schema = _get_table_schema(connection, target_table)
    columns = insertable_columns(table_schema)

    try:
        document_text = extract_text(file_bytes)
        raw_records = extract_pdf_records(columns, document_text)
    except (PdfParsingError, AIServiceError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if not raw_records:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No structured records could be extracted from this PDF.",
        )

    cleaned, warnings = validate_records(raw_records, table_schema)
    return PdfPreviewResponse(target_table=target_table, columns=columns, records=cleaned, warnings=warnings)


@router.post("/confirm", response_model=PdfConfirmResponse)
def confirm_pdf_insert(payload: PdfConfirmRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = _get_owned_connection(db, payload.db_connection_id, user)
    table_schema = _get_table_schema(connection, payload.target_table)
    columns = insertable_columns(table_schema)

    clean_records, warnings = validate_records(payload.records, table_schema)
    required_columns = [c["name"] for c in table_schema["columns"] if not c["is_primary_key"] and not c["nullable"]]
    insertable = [r for r in clean_records if all(r.get(col) not in (None, "") for col in required_columns)]
    skipped = len(clean_records) - len(insertable)

    try:
        inserted = insert_records(target_db.url_from_connection(connection), payload.target_table, columns, insertable)
    except PdfParsingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return PdfConfirmResponse(inserted_count=inserted, skipped_count=skipped, warnings=warnings)
