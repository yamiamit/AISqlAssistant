"""
CRUD for a user's saved/bookmarked queries (e.g. "Monthly Revenue"), usually
created from a chat message the user wants to re-run later without re-typing
the natural-language prompt.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.saved_query import SavedQuery
from app.models.user import User
from app.schemas.saved_query import SavedQueryCreate, SavedQueryResponse

router = APIRouter(prefix="/api/saved-queries", tags=["saved-queries"])


@router.get("", response_model=list[SavedQueryResponse])
def list_saved_queries(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(SavedQuery)
        .filter(SavedQuery.user_id == user.id)
        .order_by(SavedQuery.created_at.desc())
        .all()
    )


@router.post("", response_model=SavedQueryResponse, status_code=status.HTTP_201_CREATED)
def create_saved_query(payload: SavedQueryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = SavedQuery(user_id=user.id, **payload.model_dump())
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/{saved_query_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_query(saved_query_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    saved = db.get(SavedQuery, saved_query_id)
    if not saved or saved.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved query not found.")
    db.delete(saved)
    db.commit()
