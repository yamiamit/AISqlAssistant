"""
CRUD for a user's saved database connections, plus "test connection" and
"refresh schema" actions. Every route filters by the authenticated user so
one user can never see or touch another user's connections.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.db_connection import DBConnection
from app.models.user import User
from app.schemas.connection import (
    DBConnectionCreate,
    DBConnectionResponse,
    DBConnectionUpdate,
    SchemaResponse,
    TestConnectionResult,
)
from app.services import target_db
from app.services.encryption import encrypt_value
from app.services.schema_introspector import discover_schema

router = APIRouter(prefix="/api/connections", tags=["connections"])


def _get_owned_connection(db: Session, connection_id: int, user: User) -> DBConnection:
    conn = db.get(DBConnection, connection_id)
    if not conn or conn.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database connection not found.")
    return conn


def _resolve_fields(payload: DBConnectionCreate) -> target_db.ConnectionFields:
    if payload.connection_string:
        return target_db.parse_connection_string(payload.connection_string)
    return target_db.ConnectionFields(
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username,
        password=payload.password,
        ssl_mode=payload.ssl_mode,
    )


@router.get("", response_model=list[DBConnectionResponse])
def list_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(DBConnection).filter(DBConnection.user_id == user.id).order_by(DBConnection.created_at.desc()).all()


@router.post("/test", response_model=TestConnectionResult)
def test_connection(payload: DBConnectionCreate, user: User = Depends(get_current_user)):
    try:
        fields = _resolve_fields(payload)
    except ValueError as exc:
        return TestConnectionResult(success=False, message=str(exc))

    ok, error = target_db.test_connection(target_db.build_url(fields))
    return TestConnectionResult(success=ok, message="Connection successful." if ok else error)


@router.post("/demo", response_model=DBConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_demo_connection(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Attaches the shared, read-only demo database to the current user as a
    normal connection row (flagged is_demo=True) so a visitor can start
    chatting without supplying any credentials of their own. Deliberately
    reuses target_db.py / schema_introspector.py / sql_executor.py exactly
    as any other connection would — there is no separate "demo mode" code
    path for the chat pipeline to diverge from.

    Idempotent: calling it again just returns the user's existing demo
    connection instead of stacking up duplicates.
    """
    if not settings.DEMO_DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The sample database isn't configured on this server yet.",
        )

    existing = (
        db.query(DBConnection)
        .filter(DBConnection.user_id == user.id, DBConnection.is_demo.is_(True))
        .first()
    )
    if existing:
        return existing

    try:
        fields = target_db.parse_connection_string(settings.DEMO_DATABASE_URL)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    conn = DBConnection(
        user_id=user.id,
        name="Sample E-Commerce Data",
        host=fields.host,
        port=fields.port,
        database_name=fields.database_name,
        username=fields.username,
        encrypted_password=encrypt_value(fields.password),
        ssl_mode=fields.ssl_mode,
        is_demo=True,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    _refresh_schema_inplace(db, conn)
    return conn


@router.post("", response_model=DBConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(payload: DBConnectionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        fields = _resolve_fields(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    conn = DBConnection(
        user_id=user.id,
        name=payload.name,
        host=fields.host,
        port=fields.port,
        database_name=fields.database_name,
        username=fields.username,
        encrypted_password=encrypt_value(fields.password),
        ssl_mode=fields.ssl_mode,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    _refresh_schema_inplace(db, conn)
    return conn


@router.put("/{connection_id}", response_model=DBConnectionResponse)
def update_connection(
    connection_id: int,
    payload: DBConnectionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conn = _get_owned_connection(db, connection_id, user)
    if conn.is_demo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The sample database connection can't be edited.")

    if payload.connection_string:
        try:
            fields = target_db.parse_connection_string(payload.connection_string)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        conn.host, conn.port, conn.database_name, conn.username, conn.ssl_mode = (
            fields.host, fields.port, fields.database_name, fields.username, fields.ssl_mode
        )
        conn.encrypted_password = encrypt_value(fields.password)
    else:
        if payload.host is not None:
            conn.host = payload.host
        if payload.port is not None:
            conn.port = payload.port
        if payload.database_name is not None:
            conn.database_name = payload.database_name
        if payload.username is not None:
            conn.username = payload.username
        if payload.ssl_mode is not None:
            conn.ssl_mode = payload.ssl_mode
        if payload.password:
            conn.encrypted_password = encrypt_value(payload.password)

    if payload.name is not None:
        conn.name = payload.name

    db.commit()
    db.refresh(conn)
    _refresh_schema_inplace(db, conn)
    return conn


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _get_owned_connection(db, connection_id, user)
    if conn.is_demo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The sample database connection can't be removed.")
    db.delete(conn)
    db.commit()


@router.post("/{connection_id}/refresh-schema", response_model=SchemaResponse)
def refresh_schema(connection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _get_owned_connection(db, connection_id, user)
    schema = _refresh_schema_inplace(db, conn)
    return schema


@router.get("/{connection_id}/schema", response_model=SchemaResponse)
def get_schema(connection_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _get_owned_connection(db, connection_id, user)
    if not conn.cached_schema:
        return _refresh_schema_inplace(db, conn)
    return conn.cached_schema


def _refresh_schema_inplace(db: Session, conn: DBConnection) -> dict:
    """Re-introspect the target DB and persist the result on the connection row."""
    try:
        schema = discover_schema(target_db.url_from_connection(conn))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not read schema from the database: {exc.__class__.__name__}.",
        )

    conn.cached_schema = schema
    conn.schema_updated_at = datetime.now(timezone.utc)
    db.commit()
    return schema
