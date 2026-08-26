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
  3. Reject if any blocklisted keyword appears anywhere in the *code* — string
     literals and comments are stripped out first, so a query that merely
     mentions `'Update pending'` in a WHERE clause is not mistaken for one that
     performs an update.
  4. Guarantee a row bound on the OUTERMOST query, capped at `default_row_limit`.

A note on why this module is the weakest of the three safety layers, and is
deliberately not the only one: a keyword blocklist over text can only reason
about keywords. It cannot see that `SELECT set_config(...)` mutates session
state, because that is a function call, not a statement. That is precisely why
`sql_executor` also opens the query inside `SET TRANSACTION READ ONLY` with a
`statement_timeout` — those are enforced by Postgres itself and do not depend
on this module having thought of every spelling.
"""
import re

import sqlparse
from sqlparse import tokens as T

# Statement keywords that must never appear, even nested. INSERT/UPDATE/DELETE/
# MERGE are here specifically because Postgres supports *data-modifying CTEs* --
# `WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x` starts with WITH,
# passes the start-keyword check, and is a real write. The start check alone is
# not sufficient; this list is what closes that hole.
#
# REPLACE is deliberately NOT here: in Postgres it is a string function
# (`REPLACE(name, 'a', 'b')`), and the only statement using it is
# `CREATE OR REPLACE`, which CREATE already blocks. Listing it rejected ordinary
# queries for no security gain.
BLOCKLISTED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "COPY", "VACUUM",
    "ATTACH", "DETACH", "MERGE", "FOR UPDATE", "FOR SHARE",
    "PG_SLEEP", "PG_TERMINATE_BACKEND", "DBLINK", "LOCK", "SET ",
]
ALLOWED_START_KEYWORDS = {"SELECT", "WITH"}

_BLOCKLIST_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(kw.strip()) for kw in BLOCKLISTED_KEYWORDS) + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


class SqlValidationError(Exception):
    """Raised with a user-friendly message when SQL fails validation."""


def _strip_literals_and_comments(statement: str) -> str:
    """
    Blank out string literals and comments so the blocklist scans code only.

    Without this, `WHERE status = 'Update pending'` is rejected for containing
    UPDATE, and `WHERE note = '; DROP TABLE users; --'` is rejected for
    containing DROP -- both of which are ordinary, harmless SELECTs. The quoted
    text is replaced with a space rather than deleted so adjacent tokens cannot
    accidentally fuse into a new word.
    """
    return "".join(
        " " if (token.ttype in T.Literal.String or token.ttype in T.Comment) else token.value
        for token in sqlparse.parse(statement)[0].flatten()
    )


def _find_top_level_row_bound(tokens: list) -> tuple[int | None, int | None]:
    """
    Locate the row-bounding clause that applies to the OUTERMOST query.

    Returns (index of the token holding the row count, that count) or
    (None, None) if the outer query has no bound.

    Depth tracking is the whole point. `SELECT * FROM orders WHERE id IN
    (SELECT id FROM customers LIMIT 1)` contains the text "LIMIT 1", but that
    LIMIT bounds the subquery -- the outer query is still unbounded and can
    return the entire table. A plain substring search for LIMIT treats the two
    as identical, which silently defeats the row cap.
    """
    depth = 0
    for i, token in enumerate(tokens):
        if token.ttype is T.Punctuation:
            if token.value == "(":
                depth += 1
            elif token.value == ")":
                depth -= 1
            continue
        if depth != 0 or token.ttype is not T.Keyword:
            continue
        # LIMIT <n>, or FETCH FIRST <n> ROWS ONLY (the SQL-standard spelling,
        # which bounds rows just as well and must not be double-bounded).
        if token.normalized in ("LIMIT", "FETCH"):
            for j in range(i + 1, len(tokens)):
                nxt = tokens[j]
                if nxt.is_whitespace or nxt.normalized in ("FIRST", "NEXT"):
                    continue
                if nxt.ttype in T.Number:
                    return j, int(nxt.value)
                # `LIMIT ALL` is explicitly unbounded; treat it as a bound we
                # are allowed to overwrite with the cap.
                if nxt.normalized == "ALL":
                    return j, None
                break
    return None, None


def validate_and_prepare(sql: str, default_row_limit: int = 500) -> str:
    """
    Validates `sql` against the allow-list rules above and returns a
    row-bounded, safe-to-execute version. Raises SqlValidationError
    otherwise — never silently "fixes" unsafe SQL.
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

    match = _BLOCKLIST_PATTERN.search(_strip_literals_and_comments(statement))
    if match:
        raise SqlValidationError(f"The query contains a disallowed keyword: '{match.group(1).upper()}'.")

    tokens = list(parsed.flatten())
    count_index, row_count = _find_top_level_row_bound(tokens)

    if count_index is None:
        # No bound on the outer query at all — append one. Newline-separated so
        # a trailing single-line comment can't swallow it.
        return f"{statement}\nLIMIT {default_row_limit}"

    if row_count is None or row_count > default_row_limit:
        # `LIMIT ALL`, or a limit larger than the cap: rewrite that one token in
        # place, which preserves FETCH-vs-LIMIT syntax and everything around it.
        parts = [token.value for token in tokens]
        parts[count_index] = str(default_row_limit)
        return "".join(parts)

    return statement
