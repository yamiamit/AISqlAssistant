"""
Allow-list SQL validator. This is the last line of defense before any
AI-generated (or user-edited) SQL touches a real database: even if the model
hallucinates or a prompt-injection attempt sneaks a destructive statement
into the text, this module blocks it before `sql_executor` ever runs it.

Strategy (defense in depth, not just one check):
  1. Reject anything that isn't exactly one statement (blocks stacked queries
     like `SELECT 1; DROP TABLE users;`).
  2. The statement must start with SELECT or WITH (a CTE that must itself
     resolve to a SELECT).
  3. Reject if any blocklisted keyword appears anywhere in the statement,
     even inside a CTE or subquery.
  4. Auto-append a LIMIT if the query doesn't already have one, so a runaway
     query can't return an unbounded result set.
"""
import re

import sqlparse

BLOCKLISTED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "COPY", "VACUUM",
    "ATTACH", "DETACH", "REPLACE", "MERGE", "FOR UPDATE", "FOR SHARE",
    "PG_SLEEP", "PG_TERMINATE_BACKEND", "DBLINK", "LOCK", "SET ",
]
ALLOWED_START_KEYWORDS = {"SELECT", "WITH"}

_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+\b", re.IGNORECASE)
_BLOCKLIST_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(kw.strip()) for kw in BLOCKLISTED_KEYWORDS) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


class SqlValidationError(Exception):
    """Raised with a user-friendly message when SQL fails validation."""


def validate_and_prepare(sql: str, default_row_limit: int = 500) -> str:
    """
    Validates `sql` against the allow-list rules above and returns a
    (possibly LIMIT-appended) safe-to-execute version. Raises
    SqlValidationError otherwise — never silently "fixes" unsafe SQL.
    """
    if not sql or not sql.strip():
        raise SqlValidationError("The AI did not return any SQL to run.")

    statements = [s for s in sqlparse.split(sql) if s.strip()]
    if len(statements) != 1:
        raise SqlValidationError("Only a single SELECT statement is allowed — multiple statements were detected.")

    statement = statements[0].strip().rstrip(";")
    parsed = sqlparse.parse(statement)[0]

    first_token = parsed.token_first(skip_cm=True)
    first_keyword = first_token.value.upper() if first_token else ""
    if first_keyword not in ALLOWED_START_KEYWORDS:
        raise SqlValidationError(
            f"Only SELECT / WITH queries are allowed. Statement started with '{first_keyword or '?'}'."
        )

    match = _BLOCKLIST_PATTERN.search(statement)
    if match:
        raise SqlValidationError(f"The query contains a disallowed keyword: '{match.group(1).upper()}'.")

    if not _LIMIT_PATTERN.search(statement):
        statement = f"{statement}\nLIMIT {default_row_limit}"

    return statement
