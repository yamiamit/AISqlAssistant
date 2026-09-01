from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DBConnection(Base):
    """
    A user's saved connection to an external Postgres database.

    `encrypted_password` / `encrypted_connection_string` are Fernet-encrypted
    at rest (see services/encryption.py) — never stored or logged in plaintext.
    `cached_schema` holds the last-discovered tables/columns/PKs/FKs as JSON so
    the AI prompt and Schema Viewer page don't need to re-introspect on every load.

    `has_write_access` is a cached answer to "is this connection scoped?", set
    every time the schema is refreshed. It drives the warning banner, and it is
    a *detected* property rather than a declared one -- the app never trusts a
    user's claim that a role is read-only, it asks Postgres.

    `is_demo` marks a row created via POST /api/connections/demo, pointing at
    the shared DEMO_DATABASE_URL rather than credentials the user supplied. It
    goes through the exact same target_db.py / sql_executor.py path as any
    other connection — this flag only gates the API layer (can't be edited or
    deleted) and the frontend (example-question chips, no credentials shown).
    """

    __tablename__ = "db_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=5432)
    database_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_password: Mapped[str] = mapped_column(String(500), nullable=False)
    ssl_mode: Mapped[str] = mapped_column(String(20), default="prefer")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Recorded during schema refresh: True if the connecting role can INSERT,
    # UPDATE or DELETE anywhere in `public`. Nullable because connections saved
    # before scoped access existed have never been probed -- null means
    # "unknown", not "safe", and the UI says so.
    has_write_access: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    cached_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    schema_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="db_connections")
    conversations = relationship("Conversation", back_populates="db_connection")
