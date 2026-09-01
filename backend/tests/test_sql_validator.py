"""
Unit tests for services/sql_validator.py -- the last line of defense between
AI-generated text and a real database.

These are hermetic: no database, no network, no environment variables. The
validator is pure text analysis, so every security property it claims can be
asserted directly.

Tests are grouped by the four defenses the module documents, plus a final group
pinning down the limitations it *admits* to -- those exist so that if someone
later "fixes" one, the test tells them the executor's read-only transaction was
load-bearing for that case, not this module.
"""
import pytest

from app.services.sql_validator import (
    BLOCKLISTED_KEYWORDS,
    SqlValidationError,
    validate_and_prepare,
)


def assert_rejected(sql: str, *, because: str = "") -> str:
    """Assert the validator refuses `sql`, and hand back the message."""
    with pytest.raises(SqlValidationError) as exc:
        validate_and_prepare(sql)
    return str(exc.value)


# ---------------------------------------------------------------- defense 1:
# exactly one statement (blocks stacked queries)

class TestSingleStatement:
    def test_empty_is_rejected(self):
        assert_rejected("")

    @pytest.mark.parametrize("blank", ["   ", "\n", "\t", "  \n  "])
    def test_whitespace_only_is_rejected(self, blank):
        assert_rejected(blank)

    def test_none_is_rejected(self):
        with pytest.raises(SqlValidationError):
            validate_and_prepare(None)

    def test_stacked_statement_is_rejected(self):
        msg = assert_rejected("SELECT 1; DROP TABLE users;")
        assert "multiple statements" in msg.lower()

    def test_stacked_statement_with_two_selects_is_rejected(self):
        """Even two harmless SELECTs are refused -- the rule is structural."""
        assert_rejected("SELECT 1; SELECT 2")

    def test_trailing_semicolon_is_fine(self):
        """One statement that merely ends in `;` is not 'multiple statements'."""
        assert "LIMIT" in validate_and_prepare("SELECT id FROM orders;")


# ---------------------------------------------------------------- defense 2:
# must start with SELECT or WITH

class TestAllowedStartKeyword:
    @pytest.mark.parametrize("sql", [
        "INSERT INTO users (name) VALUES ('x')",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN x int",
        "TRUNCATE users",
        "CREATE TABLE t (id int)",
        "GRANT ALL ON users TO public",
        "COPY users FROM '/etc/passwd'",
        "VACUUM",
    ])
    def test_write_statements_are_rejected(self, sql):
        assert_rejected(sql)

    def test_select_is_allowed(self):
        assert validate_and_prepare("SELECT 1").startswith("SELECT 1")

    def test_with_cte_is_allowed(self):
        sql = "WITH t AS (SELECT id FROM orders) SELECT * FROM t"
        assert validate_and_prepare(sql).startswith("WITH")

    def test_leading_comment_does_not_hide_the_keyword(self):
        """token_first(skip_cm=True) must look past comments, not trip on them."""
        assert validate_and_prepare("-- a comment\nSELECT 1").startswith("-- a comment")

    def test_lowercase_select_is_allowed(self):
        assert validate_and_prepare("select id from orders").lower().startswith("select")


# ---------------------------------------------------------------- defense 3:
# blocklist over code (literals/comments stripped first)

class TestKeywordBlocklist:
    def test_data_modifying_cte_is_rejected(self):
        """
        The hole the start-keyword check alone does NOT close: this begins with
        WITH, so defense 2 passes it, and it is a real write.
        """
        sql = "WITH x AS (DELETE FROM users RETURNING *) SELECT * FROM x"
        msg = assert_rejected(sql)
        assert "DELETE" in msg

    def test_insert_returning_cte_is_rejected(self):
        sql = "WITH x AS (INSERT INTO users (n) VALUES (1) RETURNING *) SELECT * FROM x"
        assert "INSERT" in assert_rejected(sql)

    def test_select_for_update_is_rejected(self):
        """Row locking is a write-intent operation even though it reads."""
        assert_rejected("SELECT * FROM users FOR UPDATE")

    def test_pg_sleep_is_rejected(self):
        """DoS via the query planner, not a data write."""
        assert_rejected("SELECT pg_sleep(10)")

    def test_nested_subquery_write_is_rejected(self):
        assert_rejected("SELECT * FROM (SELECT 1) t WHERE EXISTS (DELETE FROM users)")

    @pytest.mark.parametrize("keyword", [k.strip() for k in BLOCKLISTED_KEYWORDS])
    def test_every_blocklisted_keyword_is_actually_caught(self, keyword):
        """
        Guards the regex itself. If a keyword is added to the list but the
        pattern is not rebuilt (or is escaped wrongly), this catches it.
        """
        assert_rejected(f"SELECT * FROM t WHERE x = 1 {keyword} y")


class TestLiteralsAndCommentsAreNotCode:
    """
    The blocklist scans code only. These are all ordinary SELECTs that a naive
    substring search would reject -- false positives that would break the
    product for users whose data merely contains these words.
    """

    def test_blocklisted_word_inside_a_string_literal_is_allowed(self):
        sql = "SELECT * FROM orders WHERE status = 'Update pending'"
        assert "Update pending" in validate_and_prepare(sql)

    def test_injection_looking_string_literal_is_allowed(self):
        sql = "SELECT * FROM notes WHERE body = '; DROP TABLE users; --'"
        assert validate_and_prepare(sql).startswith("SELECT")

    def test_blocklisted_word_inside_a_comment_is_allowed(self):
        sql = "SELECT id FROM orders -- TODO: delete this later"
        assert validate_and_prepare(sql).startswith("SELECT")

    def test_block_comment_is_allowed(self):
        sql = "SELECT id /* we should truncate this table someday */ FROM orders"
        assert validate_and_prepare(sql).startswith("SELECT")

    @pytest.mark.parametrize("identifier", [
        "created_at",       # contains CREATE
        "updated_at",       # contains UPDATE
        "deleted_flag",     # contains DELETE
        "dropoff_point",    # contains DROP
        "settings",         # contains SET
        "insertion_order",  # contains INSERT
    ])
    def test_identifiers_containing_keywords_are_allowed(self, identifier):
        """Word-boundary lookarounds, not naive substring matching."""
        sql = f"SELECT {identifier} FROM orders"
        assert identifier in validate_and_prepare(sql)

    def test_replace_function_is_allowed(self):
        """
        REPLACE is deliberately absent from the blocklist: in Postgres it is a
        string function, and CREATE already blocks `CREATE OR REPLACE`.
        """
        sql = "SELECT REPLACE(name, 'a', 'b') FROM products"
        assert "REPLACE" in validate_and_prepare(sql)


# ---------------------------------------------------------------- defense 4:
# a row bound on the OUTERMOST query

class TestRowLimit:
    def test_limit_is_appended_when_absent(self):
        assert validate_and_prepare("SELECT id FROM orders", 500).endswith("LIMIT 500")

    def test_existing_smaller_limit_is_preserved(self):
        out = validate_and_prepare("SELECT id FROM orders LIMIT 10", 500)
        assert out.endswith("LIMIT 10")
        assert "500" not in out

    def test_limit_over_the_cap_is_rewritten_down(self):
        out = validate_and_prepare("SELECT id FROM orders LIMIT 99999", 500)
        assert "99999" not in out
        assert "500" in out

    def test_limit_equal_to_cap_is_left_alone(self):
        assert validate_and_prepare("SELECT id FROM orders LIMIT 500", 500).endswith("LIMIT 500")

    def test_limit_all_is_rewritten_to_the_cap(self):
        """`LIMIT ALL` is explicitly unbounded and must not be trusted."""
        out = validate_and_prepare("SELECT id FROM orders LIMIT ALL", 500)
        assert "ALL" not in out.upper().replace("SELECT", "")
        assert "500" in out

    def test_subquery_limit_does_not_bound_the_outer_query(self):
        """
        The depth-tracking case. This contains the text "LIMIT 1", but that
        bounds the subquery -- the outer query is unbounded and could return
        the whole table. A substring search for LIMIT silently defeats the cap.
        """
        sql = "SELECT * FROM orders WHERE id IN (SELECT id FROM customers LIMIT 1)"
        out = validate_and_prepare(sql, 500)
        assert out.rstrip().endswith("LIMIT 500"), "outer query was left unbounded"
        assert "LIMIT 1" in out, "the subquery's own limit should be preserved"

    def test_fetch_first_n_rows_only_counts_as_a_bound(self):
        """The SQL-standard spelling bounds rows just as well as LIMIT."""
        out = validate_and_prepare("SELECT id FROM orders FETCH FIRST 10 ROWS ONLY", 500)
        assert "LIMIT 500" not in out, "double-bounded a query that was already bounded"

    def test_fetch_over_the_cap_is_rewritten_in_place(self):
        out = validate_and_prepare("SELECT id FROM orders FETCH FIRST 9999 ROWS ONLY", 500)
        assert "9999" not in out
        assert "FETCH" in out.upper(), "rewrite should preserve FETCH syntax"

    def test_cte_outer_query_gets_bounded(self):
        sql = "WITH t AS (SELECT id FROM orders LIMIT 5) SELECT * FROM t"
        assert validate_and_prepare(sql, 500).rstrip().endswith("LIMIT 500")

    def test_appended_limit_survives_a_trailing_line_comment(self):
        """
        Newline-separated on purpose: `... -- note LIMIT 500` on one line would
        be swallowed by the comment and the cap silently lost.
        """
        out = validate_and_prepare("SELECT id FROM orders -- trailing note", 500)
        assert out.splitlines()[-1].strip() == "LIMIT 500"

    def test_custom_row_limit_is_honoured(self):
        assert validate_and_prepare("SELECT id FROM orders", 25).endswith("LIMIT 25")


# ---------------------------------------------------------------- documented
# limitations -- these pin *known* gaps so a later change can't quietly widen
# them. The executor's read-only transaction is what actually covers these.

class TestKnownLimitations:
    def test_set_config_is_not_caught_by_the_blocklist(self):
        """
        The module's own docstring calls this out: a keyword blocklist over text
        cannot see that `set_config(...)` mutates session state, because it is a
        function call rather than a SET statement. It passes validation.

        This is NOT a bug in this module -- it is why sql_executor also opens
        every query inside `SET TRANSACTION READ ONLY`. If this test ever starts
        failing because the blocklist got stricter, that is fine; delete it.
        """
        out = validate_and_prepare("SELECT set_config('x', 'y', true)")
        assert out.startswith("SELECT set_config")

    def test_offset_without_limit_is_still_bounded(self):
        """OFFSET alone does not bound rows; the cap must still be applied."""
        assert validate_and_prepare("SELECT id FROM orders OFFSET 10", 500).rstrip().endswith("LIMIT 500")
