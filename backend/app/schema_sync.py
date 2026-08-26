"""
Adds columns that exist on the ORM models but not yet in the app database.

`Base.metadata.create_all()` only ever CREATEs missing tables — it never ALTERs
an existing one. So the moment a column is added to a model, every database
created before that change keeps working right up until the first query that
selects the new column, then fails with `UndefinedColumn`. That is a confusing
failure for something the app already knows how to detect.

This is deliberately not Alembic (see the note in main.py). It handles exactly
the additive case that `create_all` leaves open — a new nullable column, or a
new non-nullable column with a server default — which is the only kind of
change this project has actually needed. Renames, drops, and type changes are
NOT handled: those are destructive, ambiguous without a revision history, and
are the point at which a real migration tool becomes worth its weight.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base

logger = logging.getLogger("ai_sql_assistant")


def _column_ddl(column, dialect) -> str | None:
    """
    Render one ADD COLUMN clause, or None if it can't be applied safely.

    A NOT NULL column with no server default has no value to backfill existing
    rows with, so Postgres rejects the ALTER on any non-empty table. Rather than
    guess at a backfill value, we skip it and say so.
    """
    if not column.nullable and column.server_default is None:
        return None

    parts = [f'ADD COLUMN "{column.name}" {column.type.compile(dialect=dialect)}']
    if column.server_default is not None:
        parts.append(f"DEFAULT {column.server_default.arg}")
    if not column.nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def sync_columns(engine: Engine) -> None:
    """Bring every existing table up to date with its model's columns."""
    inspector = inspect(engine)

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # create_all() just made it, so it's already current.

        existing = {col["name"] for col in inspector.get_columns(table.name)}
        missing = [col for col in table.columns if col.name not in existing]

        for column in missing:
            clause = _column_ddl(column, engine.dialect)
            if clause is None:
                logger.warning(
                    "Cannot auto-add %s.%s: it is NOT NULL with no server default. "
                    "Add it by hand with a backfill value.",
                    table.name,
                    column.name,
                )
                continue

            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE "{table.name}" {clause}'))
            logger.info("Added missing column %s.%s", table.name, column.name)
