"""
The core product pipeline: natural language -> SQL -> validate -> execute ->
persist -> return. Every step is a separate, individually-testable module
(ai_service, sql_validator, sql_executor); this route just orchestrates them
and turns failures at any step into a friendly, persisted chat message
instead of a raw 500 error, so the UI can always render *something* in the
conversation thread.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from app.models.db_connection import DBConnection
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatQueryRequest, ConversationDetail, ConversationSummary, MessageResponse
from app.services import target_db
from app.services.ai_service import AIServiceError, generate_sql
from app.services.schema_introspector import discover_schema, schema_to_prompt_text
from app.services.sql_executor import QueryExecutionError, execute_query
from app.services.sql_validator import SqlValidationError, validate_and_prepare
from app.utils.chart_suggester import suggest_chart_type

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def run_query(payload: ChatQueryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.get(DBConnection, payload.db_connection_id)
    if not connection or connection.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found.")

    conversation = _get_or_create_conversation(db, user, payload.conversation_id, connection.id, payload.prompt)

    message = Message(conversation_id=conversation.id, prompt_text=payload.prompt)

    try:
        try:
            schema = connection.cached_schema or discover_schema(target_db.url_from_connection(connection))
        except Exception as exc:
            raise QueryExecutionError(
                "Could not reach the connected database to read its schema — it may be offline."
            ) from exc
        schema_text = schema_to_prompt_text(schema)

        history = _recent_history(db, conversation.id)
        ai_result = generate_sql(schema_text, payload.prompt, history)
        message.generated_sql = ai_result["sql"]
        message.explanation = ai_result["explanation"]

        safe_sql = validate_and_prepare(ai_result["sql"], settings.SQL_DEFAULT_ROW_LIMIT)
        message.generated_sql = safe_sql  # reflect any auto-appended LIMIT

        result = execute_query(target_db.url_from_connection(connection), safe_sql, settings.SQL_STATEMENT_TIMEOUT_MS)
        message.result_columns = result.columns
        message.result_rows = result.rows
        message.row_count = result.row_count
        message.execution_time_ms = result.execution_time_ms
        message.chart_type = suggest_chart_type(result.columns, result.rows)

    except (AIServiceError, SqlValidationError, QueryExecutionError) as exc:
        message.error_message = str(exc)
    except Exception as exc:  # noqa: BLE001 - last-resort friendly fallback for anything unexpected
        message.error_message = f"Something went wrong while processing your request: {exc.__class__.__name__}."

    db.add(message)
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Conversation).filter(Conversation.user_id == user.id)
    if search:
        like = f"%{search}%"
        query = query.outerjoin(Message).filter(
            or_(Conversation.title.ilike(like), Message.prompt_text.ilike(like))
        ).distinct()
    return query.order_by(Conversation.updated_at.desc()).all()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = _get_owned_conversation(db, conversation_id, user)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = _get_owned_conversation(db, conversation_id, user)
    db.delete(conversation)
    db.commit()


def _get_owned_conversation(db: Session, conversation_id: int, user: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


def _get_or_create_conversation(
    db: Session, user: User, conversation_id: int | None, db_connection_id: int, first_prompt: str
) -> Conversation:
    if conversation_id:
        conversation = _get_owned_conversation(db, conversation_id, user)
        return conversation

    title = first_prompt.strip()[:60] + ("..." if len(first_prompt.strip()) > 60 else "")
    conversation = Conversation(user_id=user.id, db_connection_id=db_connection_id, title=title or "New Chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _recent_history(db: Session, conversation_id: int, limit: int = 3) -> list[dict]:
    recent = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.generated_sql.isnot(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return [{"prompt": m.prompt_text, "sql": m.generated_sql} for m in reversed(recent)]
