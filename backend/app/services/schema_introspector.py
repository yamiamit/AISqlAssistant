"""
Discovers tables, columns, primary keys, and foreign keys on a target
Postgres database using SQLAlchemy's `inspect()` (which reads Postgres'
information_schema/pg_catalog under the hood — we never hand-write that SQL).

The result is what gets cached on DBConnection.cached_schema, shown on the
Schema Viewer page, and injected into the AI prompt so generated SQL only
ever references real tables/columns.
"""
from sqlalchemy import create_engine, inspect


def discover_schema(url: str) -> dict:
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        inspector = inspect(engine)
        tables = []

        for table_name in inspector.get_table_names(schema="public"):
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

        return {"tables": tables}
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
