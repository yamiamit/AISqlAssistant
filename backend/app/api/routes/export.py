"""
Downloadable exports of a chat message's results: raw CSV, or a formatted
PDF report. (PNG chart export is done entirely client-side from the
rendered chart, via html-to-image — no backend round trip needed for that one.)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.export_service import build_csv, build_pdf_report

router = APIRouter(prefix="/api/export", tags=["export"])


def _get_owned_message(db: Session, message_id: int, user: User) -> Message:
    message = (
        db.query(Message)
        .join(Conversation)
        .options(joinedload(Message.conversation))
        .filter(Message.id == message_id, Conversation.user_id == user.id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    if not message.result_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This message has no results to export.")
    return message


@router.get("/csv/{message_id}")
def export_csv(message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = _get_owned_message(db, message_id, user)
    csv_content = build_csv(message.result_columns, message.result_rows)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=query_results_{message_id}.csv"},
    )


@router.get("/pdf-report/{message_id}")
def export_pdf_report(message_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = _get_owned_message(db, message_id, user)
    pdf_bytes = build_pdf_report(
        prompt_text=message.prompt_text,
        generated_sql=message.generated_sql or "",
        explanation=message.explanation or "",
        columns=message.result_columns or [],
        rows=message.result_rows or [],
        execution_time_ms=message.execution_time_ms or 0,
        row_count=message.row_count or 0,
        chart_type=message.chart_type,
        created_at=message.created_at.strftime("%Y-%m-%d %H:%M UTC"),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=query_report_{message_id}.pdf"},
    )
