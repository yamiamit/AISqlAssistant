from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatQueryRequest(BaseModel):
    prompt: str
    db_connection_id: int
    conversation_id: int | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    prompt_text: str
    generated_sql: str | None
    explanation: str | None
    result_columns: list[str] | None
    result_rows: list[dict] | None
    row_count: int | None
    execution_time_ms: float | None
    chart_type: str | None
    error_message: str | None
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    db_connection_id: int | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]
