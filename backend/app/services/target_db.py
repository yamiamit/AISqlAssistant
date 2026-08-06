"""
Helpers for building/parsing Postgres connection URLs for a user's *target*
database (the external DB they connect to, as opposed to the app's own DB).

Kept separate from schema_introspector/sql_executor so both can share the
same "build a URL, open a short-lived engine" logic without duplicating it.
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.services.encryption import decrypt_value

if TYPE_CHECKING:
    from app.models.db_connection import DBConnection


@dataclass
class ConnectionFields:
    host: str
    port: int
    database_name: str
    username: str
    password: str
    ssl_mode: str = "prefer"


def parse_connection_string(connection_string: str) -> ConnectionFields:
    """Parse a `postgresql://user:pass@host:port/dbname` URI into fields."""
    try:
        url = make_url(connection_string)
    except Exception as exc:
        raise ValueError("That doesn't look like a valid PostgreSQL connection string.") from exc

    if not url.database:
        raise ValueError("Connection string is missing a database name.")

    return ConnectionFields(
        host=url.host or "localhost",
        port=url.port or 5432,
        database_name=url.database,
        username=url.username or "",
        password=url.password or "",
        ssl_mode=url.query.get("sslmode", "prefer"),
    )


def build_url(fields: ConnectionFields) -> str:
    """Build a SQLAlchemy/psycopg2 connection URL from individual fields."""
    return (
        f"postgresql+psycopg2://{fields.username}:{fields.password}"
        f"@{fields.host}:{fields.port}/{fields.database_name}"
        f"?sslmode={fields.ssl_mode}"
    )


def url_from_connection(conn: "DBConnection") -> str:
    """Rebuild a usable connection URL for a stored DBConnection row (decrypts its password)."""
    fields = ConnectionFields(
        host=conn.host,
        port=conn.port,
        database_name=conn.database_name,
        username=conn.username,
        password=decrypt_value(conn.encrypted_password),
        ssl_mode=conn.ssl_mode,
    )
    return build_url(fields)


def test_connection(url: str) -> tuple[bool, str | None]:
    """Try a lightweight `SELECT 1` against the target DB. Returns (ok, error_message)."""
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True, None
    except OperationalError:
        return False, "Could not reach the database. Check host, port, and that the server is online."
    except SQLAlchemyError as exc:
        return False, f"Connection failed: {exc.__class__.__name__}. Check your credentials."
