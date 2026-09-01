"""
Unit tests for the two pieces that make scoped access true rather than
aspirational: the foreign-key pruning in services/schema_introspector.py, and
the 42501 translation in services/sql_executor.py.

Hermetic, like test_sql_validator.py -- no database, no network. Both behaviours
are decidable from data already in hand: pruning is set membership over the
reflected schema, and the executor's message choice is decidable from the error
object alone.

The grant-dependent half of this feature (does Postgres actually refuse a
non-granted table? does the catalog query actually filter?) cannot be asserted
without a live server and two roles -- those live in
test_scoped_access_integration.py and skip unless TEST_DATABASE_URL is set.
"""
from sqlalchemy.exc import ProgrammingError

from app.services.schema_introspector import prune_unreadable_foreign_keys
from app.services.sql_executor import rejection_message


def table(name: str, *references: str) -> dict:
    """A minimal reflected-table dict carrying only what pruning looks at."""
    return {
        "name": name,
        "columns": [],
        "primary_keys": [],
        "foreign_keys": [
            {"column": f"{ref}_id", "references_table": ref, "references_column": f"{ref}_id"}
            for ref in references
        ],
    }


def references(tables: list[dict], name: str) -> list[str]:
    return [fk["references_table"] for t in tables if t["name"] == name for fk in t["foreign_keys"]]


class FakePgError(Exception):
    """Stands in for a psycopg2 error, which carries the SQLSTATE on .pgcode."""

    def __init__(self, message: str, pgcode: str | None):
        super().__init__(message)
        self.pgcode = pgcode


def db_error(message: str, pgcode: str | None) -> ProgrammingError:
    return ProgrammingError("SELECT 1", {}, FakePgError(message, pgcode))


# ------------------------------------------------------- foreign-key pruning:
# An FK pointing at a table the role can't read teaches the model to write a
# join that dies at execution. The schema must only promise what it can deliver.

class TestForeignKeyPruning:
    def test_drops_fk_to_a_table_not_in_the_readable_set(self):
        tables = [table("orders", "customers")]  # customers was never granted
        assert references(prune_unreadable_foreign_keys(tables), "orders") == []

    def test_keeps_fk_when_both_ends_are_readable(self):
        tables = [table("orders", "customers"), table("customers")]
        assert references(prune_unreadable_foreign_keys(tables), "orders") == ["customers"]

    def test_keeps_only_the_readable_end_of_a_mixed_table(self):
        # order_items references both orders (granted) and products (not).
        tables = [table("order_items", "orders", "products"), table("orders")]
        assert references(prune_unreadable_foreign_keys(tables), "order_items") == ["orders"]

    def test_full_access_is_unchanged(self):
        # The whole graph is readable, so pruning must be a no-op -- this is what
        # keeps the filter invisible to users who skip scoping entirely.
        tables = [table("orders", "customers"), table("customers"), table("payments", "orders")]
        pruned = prune_unreadable_foreign_keys(tables)
        assert references(pruned, "orders") == ["customers"]
        assert references(pruned, "payments") == ["orders"]

    def test_self_referencing_fk_survives(self):
        tables = [table("employees", "employees")]
        assert references(prune_unreadable_foreign_keys(tables), "employees") == ["employees"]

    def test_table_with_no_foreign_keys_is_untouched(self):
        tables = [table("categories")]
        assert prune_unreadable_foreign_keys(tables) == [table("categories")]

    def test_empty_schema(self):
        assert prune_unreadable_foreign_keys([]) == []

    def test_columns_and_primary_keys_are_not_disturbed(self):
        tables = [table("orders", "customers")]
        tables[0]["columns"] = [{"name": "order_id", "type": "INTEGER", "nullable": False, "is_primary_key": True}]
        tables[0]["primary_keys"] = ["order_id"]
        pruned = prune_unreadable_foreign_keys(tables)
        assert pruned[0]["primary_keys"] == ["order_id"]
        assert pruned[0]["columns"][0]["name"] == "order_id"


# ------------------------------------------------------------ 42501 messages:
# "permission denied for table users" reads like an app bug. It isn't -- it's
# the access boundary doing its job, and the message should say so.

class TestRejectionMessage:
    def test_insufficient_privilege_names_the_allowed_set(self):
        message = rejection_message(db_error("permission denied for table users", "42501"))
        assert message == "That table isn't in your connection's allowed set."

    def test_insufficient_privilege_does_not_leak_the_table_name(self):
        # The role couldn't read it, so the user learning it exists is a small
        # disclosure the friendly message avoids for free.
        assert "users" not in rejection_message(db_error("permission denied for table users", "42501"))

    def test_other_postgres_errors_are_surfaced_verbatim(self):
        # 42703 = undefined_column. Postgres already says this well; a generic
        # rewrite here would cost the user the column name they need.
        message = rejection_message(db_error('column "foo" does not exist', "42703"))
        assert 'column "foo" does not exist' in message

    def test_syntax_error_is_surfaced_verbatim(self):
        message = rejection_message(db_error('syntax error at or near "FROM"', "42601"))
        assert 'syntax error at or near "FROM"' in message

    def test_error_without_a_pgcode_falls_through(self):
        message = rejection_message(db_error("something odd happened", None))
        assert "something odd happened" in message

    def test_error_without_an_orig_falls_through(self):
        # A SQLAlchemy-level error that never reached the driver has no .orig;
        # the message must still be produced rather than raising in the handler.
        assert rejection_message(ProgrammingError("SELECT 1", {}, None))
