"""
Generates the `CREATE ROLE` / `GRANT` script a user runs by hand to scope a
connection down to a chosen set of tables.

The app deliberately does not run this itself. Creating a role needs privileges
well beyond what a query tool should ever hold, and a product that can mint
database roles on your server is a much larger thing to trust than one that
hands you SQL to read first. The copy-paste step is the feature, not a
limitation of it.

Everything interpolated here is either a Postgres identifier (double-quoted,
embedded quotes doubled) or a generated password (single-quoted, and drawn from
an alphabet with no quote characters in it). Table names arrive from the cached
schema rather than raw user input, but they are quoted anyway -- a table really
can be called `my "table"`, and the caller shouldn't have to know that.
"""
import secrets

# token_urlsafe draws from [A-Za-z0-9_-], so a generated password can never
# contain the single quote that would break out of the literal below. The
# escape in _quote_literal is belt-and-braces for callers passing their own.
_PASSWORD_BYTES = 24


class AccessScriptError(Exception):
    """Raised with a user-friendly message when a script can't be generated."""


def generate_password() -> str:
    return secrets.token_urlsafe(_PASSWORD_BYTES)


def role_name_for(connection_id: int) -> str:
    """
    Roles are cluster-wide, not per-database, so a fixed name like `app_reader`
    collides the moment someone scopes a second database on the same server.
    Deriving from the connection id keeps it unique and stable across regenerations.
    """
    return f"ai_sql_reader_{connection_id}"


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_access_script(
    *,
    database: str,
    role: str,
    password: str,
    tables: list[str],
    schema: str = "public",
) -> str:
    if not tables:
        raise AccessScriptError("Select at least one table for the role to read.")

    role_q = _quote_ident(role)
    schema_q = _quote_ident(schema)
    grants = "\n".join(
        f"GRANT SELECT ON {schema_q}.{_quote_ident(table)} TO {role_q};" for table in tables
    )

    return f"""-- Grants a read-only role access to {len(tables)} table(s) and nothing else.
-- Run this as a user that can CREATE ROLE (the database owner is usually enough),
-- then paste the connection string below back into the app.
--
-- Safe to run more than once: re-scoping an existing role rotates its password
-- and replaces its grants rather than failing on the role already existing.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(role)}) THEN
    ALTER ROLE {role_q} LOGIN PASSWORD {_quote_literal(password)};
  ELSE
    CREATE ROLE {role_q} LOGIN PASSWORD {_quote_literal(password)};
  END IF;
END
$$;

GRANT CONNECT ON DATABASE {_quote_ident(database)} TO {role_q};
GRANT USAGE ON SCHEMA {schema_q} TO {role_q};

-- Clear any grants from a previous run so the list below is the whole truth
-- about what this role can read. Affects only this role.
REVOKE ALL ON ALL TABLES IN SCHEMA {schema_q} FROM {role_q};

{grants}

-- Optional, and it affects every role rather than just this one: on PostgreSQL 14
-- and older, any role may CREATE objects in the `public` schema. PostgreSQL 15
-- changed that default, so skip this if you are on 15+.
-- REVOKE CREATE ON SCHEMA {schema_q} FROM PUBLIC;
"""


def connection_string_hint(*, host: str, port: int, database: str, role: str, password: str, ssl_mode: str) -> str:
    """The URL the user pastes back, so they don't have to assemble it themselves."""
    return f"postgresql://{role}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"
