"""
Discovers tables, columns, primary keys, and foreign keys on a target
Postgres database, restricted to what the connecting role may actually read.

The result is what gets cached on DBConnection.cached_schema, shown on the
Schema Viewer page, and injected into the AI prompt so generated SQL only
ever references real tables/columns.

Why this module hand-writes one catalog query instead of using
`inspector.get_table_names()` for everything: SQLAlchemy's Postgres dialect
reflects table names from `pg_catalog.pg_class`, which is world-readable
(`pg_class`'s ACL grants SELECT to PUBLIC). A role granted SELECT on two
tables therefore still reflects all fifty. That is worse than it sounds --
an unreadable table in the schema goes into the AI prompt, the model writes a
perfectly reasonable query against it, and Postgres refuses the result with
42501 at execution time. Filtering here is what makes "the AI can only see
these tables" true rather than aspirational.

Column, PK, and FK reflection still goes through `SQLAlchemy.inspect()` --
those are only ever called for names that already passed the filter.
"""
from sqlalchemy import create_engine, inspect, text

# has_table_privilege() is the privilege filter pg_class does not apply.
# Passing the oid rather than a name keeps identifier quoting out of it
# entirely. relkind ('r', 'p') mirrors SQLAlchemy's RELKINDS_TABLE_NO_FOREIGN
# -- ordinary and partitioned tables -- so an unrestricted role reflects
# exactly the same set it did before this filter existed.
_READABLE_TABLES_SQL = text("""
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = :schema
      AND c.relkind IN ('r', 'p')
      AND has_table_privilege(c.oid, 'SELECT')
    ORDER BY c.relname
""")


# The mirror of the SELECT filter above, asking the question the warning banner
# needs: does this role have any way to change data? Ownership and role
# membership both grant privileges that `information_schema.table_privileges`
# does not list, so this uses has_table_privilege() for the same reason the read
# filter does -- it is the function that knows about every path to a privilege,
# not just directly granted ones.
_WRITE_ACCESS_SQL = text("""
    SELECT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema
          AND c.relkind IN ('r', 'p')
          AND (has_table_privilege(c.oid, 'INSERT')
               OR has_table_privilege(c.oid, 'UPDATE')
               OR has_table_privilege(c.oid, 'DELETE'))
    )
""")


def detect_write_access(url: str) -> bool:
    """
    True if the connecting role can write to any table in `public`.

    Not a security control -- `SET TRANSACTION READ ONLY` in sql_executor is
    what actually stops writes. This only answers whether the user has taken
    the scoping step, so the UI can tell them they haven't.
    """
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as conn:
            return bool(conn.scalar(_WRITE_ACCESS_SQL, {"schema": "public"}))
    finally:
        engine.dispose()


def prune_unreadable_foreign_keys(tables: list[dict]) -> list[dict]:
    """
    Drop foreign keys pointing at tables that aren't in `tables`.

    A restricted role can still read the FK *constraints* on a table it was
    granted, including ones referencing tables it cannot select from. Left in
    the prompt those read as an invitation: the model joins `orders` to a
    `customers` it was never shown, and the query dies at execution with a
    permission error that looks like a bug. Pruning them keeps the prompt
    honest about what is actually reachable.

    Mutates and returns `tables`.
    """
    readable = {table["name"] for table in tables}
    for table in tables:
        table["foreign_keys"] = [
            fk for fk in table["foreign_keys"] if fk["references_table"] in readable
        ]
    return tables


def discover_schema(url: str) -> dict:
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        # One connection for both the privilege query and the reflection, so
        # `has_table_privilege` is evaluated as the same role that will run the
        # user's queries later.
        with engine.connect() as conn:
            table_names = conn.scalars(_READABLE_TABLES_SQL, {"schema": "public"}).all()
            inspector = inspect(conn)
            tables = []

            for table_name in table_names:
                columns = inspector.get_columns(table_name, schema="public")
                pk_constraint = inspector.get_pk_constraint(table_name, schema="public")
                primary_keys = set(pk_constraint.get("constrained_columns") or [])
                foreign_keys_raw = inspector.get_foreign_keys(table_name, schema="public")

                foreign_keys = [
                    {
                        "column": fk["constrained_columns"][0] if fk["constrained_columns"] else None,
                        "references_table": fk["referred_table"],
                        "references_column": fk["referred_columns"][0] if fk["referred_columns"] else None,
                    }
                    for fk in foreign_keys_raw
                ]

                tables.append({
                    "name": table_name,
                    "columns": [
                        {
                            "name": col["name"],
                            "type": str(col["type"]),
                            "nullable": col["nullable"],
                            "is_primary_key": col["name"] in primary_keys,
                        }
                        for col in columns
                    ],
                    "primary_keys": sorted(primary_keys),
                    "foreign_keys": foreign_keys,
                })

        return {"tables": prune_unreadable_foreign_keys(tables)}
    finally:
        engine.dispose()


def schema_to_prompt_text(schema: dict) -> str:
    """Render the discovered schema as compact text for the AI prompt."""
    lines = []
    for table in schema.get("tables", []):
        col_descriptions = []
        for col in table["columns"]:
            marker = " (PK)" if col["is_primary_key"] else ""
            col_descriptions.append(f"{col['name']} {col['type']}{marker}")
        lines.append(f"Table {table['name']}({', '.join(col_descriptions)})")

        for fk in table["foreign_keys"]:
            if fk["column"]:
                lines.append(f"  FK: {table['name']}.{fk['column']} -> {fk['references_table']}.{fk['references_column']}")

    return "\n".join(lines)
