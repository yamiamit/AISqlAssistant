"""
Executes an already-validated SELECT/WITH query against a user's target
database with several safety nets beyond the allow-list check in
sql_validator: a hard statement timeout, and `SET TRANSACTION READ ONLY`
so even a validator bypass couldn't mutate data within this transaction.

Each call opens a short-lived engine/connection and disposes it immediately —
target databases are arbitrary and infrequent, so a long-lived pool per
connection isn't worth the complexity here.
"""
import decimal
import time
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as datetime_time  # aliased: plain `time` is the stdlib module imported above

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError


class QueryExecutionError(Exception):
    """Raised with a user-friendly message when query execution fails."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict]
    row_count: int
    execution_time_ms: float


def _json_safe(value):
    """
    Coerce one Postgres value into something `json.dumps` can handle.

    The final `str(value)` fallback matters more than the named cases above it.
    Target databases are arbitrary, so a UUID primary key, an INTERVAL, a TIME,
    or a BYTEA column is entirely ordinary -- and an unconvertible value does
    NOT fail here. It fails later, at `db.commit()` in the chat route, when
    SQLAlchemy serializes result_rows into its JSON column. That call sits
    outside the route's try/except, so the user gets an unhandled 500 instead of
    a friendly message. Degrading an unknown type to its string form keeps the
    question answerable.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime, date, datetime_time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    # Postgres arrays arrive as lists and json/jsonb as dicts; recurse so a
    # Decimal or date *inside* one is converted too.
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def execute_query(url: str, sql: str, statement_timeout_ms: int = 10_000) -> QueryResult:
    # statement_timeout is set via SQL (below), not as a libpq startup "options"
    # connect_arg — Neon's pooled (PgBouncer) connections reject startup-time
    # options with "unsupported startup parameter in options: statement_timeout".
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        start = time.perf_counter()
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text(f"SET statement_timeout = {statement_timeout_ms}"))
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = [
                    {col: _json_safe(value) for col, value in zip(columns, row)}
                    for row in result.fetchall()
                ]
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    except OperationalError as exc:
        raise QueryExecutionError(
            "Could not reach the database — it may be offline or the connection details are stale."
        ) from exc
    except SQLAlchemyError as exc:
        # Postgres error messages (via psycopg2) are already human-readable
        # (e.g. 'column "foo" does not exist') — surface them directly.
        raise QueryExecutionError(f"The database rejected the query: {str(exc.orig) if hasattr(exc, 'orig') else exc}") from exc
    finally:
        engine.dispose()

    return QueryResult(columns=columns, rows=rows, row_count=len(rows), execution_time_ms=elapsed_ms)
