from pydantic import BaseModel


class PdfPreviewResponse(BaseModel):
    target_table: str
    columns: list[str]
    records: list[dict]
    warnings: list[str]


class PdfConfirmRequest(BaseModel):
    db_connection_id: int
    target_table: str
    records: list[dict]


class PdfConfirmResponse(BaseModel):
    inserted_count: int
    skipped_count: int
    warnings: list[str]
