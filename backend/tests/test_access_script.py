"""
Unit tests for services/access_script.py -- the generator for the CREATE ROLE /
GRANT script users paste into psql.

Hermetic; no database. The property that matters here is not that the SQL is
*correct* (the integration tests run it for real) but that nothing reaching it
can change the shape of the statements: this is the one place in the product
that hands someone SQL to run with privileges the app itself does not have, and
a table name is the only untrusted-ish value in it.
"""
import pytest

from app.services.access_script import (
    AccessScriptError,
    build_access_script,
    connection_string_hint,
    generate_password,
    role_name_for,
)


def script(**overrides) -> str:
    kwargs = {"database": "shop", "role": "reader", "password": "pw", "tables": ["orders"]}
    kwargs.update(overrides)
    return build_access_script(**kwargs)


# ------------------------------------------------------------------ contents:

class TestScriptContents:
    def test_creates_a_login_role_with_the_password(self):
        assert "CREATE ROLE \"reader\" LOGIN PASSWORD 's3cret';" in script(password="s3cret")

    def test_is_safe_to_run_twice(self):
        # Re-scoping an existing connection regenerates the script for the same
        # role name; a bare CREATE ROLE would fail with "already exists" and
        # strand the user halfway through the flow.
        out = script(role="reader", password="s3cret")
        assert "IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'reader')" in out
        assert "ALTER ROLE \"reader\" LOGIN PASSWORD 's3cret';" in out

    def test_clears_prior_grants_before_granting(self):
        # Without this, narrowing a scope from three tables to two would leave
        # the third grant in place and the UI would quietly overstate the change.
        out = script(tables=["orders"])
        revoke = out.index('REVOKE ALL ON ALL TABLES IN SCHEMA "public" FROM "reader";')
        assert revoke < out.index("GRANT SELECT")

    def test_the_blanket_revoke_targets_only_this_role(self):
        assert 'REVOKE ALL ON ALL TABLES IN SCHEMA "public" FROM "reader";' in script()
        assert "FROM PUBLIC;" not in script().replace("-- REVOKE CREATE ON SCHEMA \"public\" FROM PUBLIC;", "")

    def test_grants_connect_on_the_database(self):
        assert 'GRANT CONNECT ON DATABASE "shop" TO "reader";' in script()

    def test_grants_usage_on_the_schema(self):
        assert 'GRANT USAGE ON SCHEMA "public" TO "reader";' in script()

    def test_grants_select_on_every_requested_table(self):
        out = script(tables=["orders", "customers"])
        assert 'GRANT SELECT ON "public"."orders" TO "reader";' in out
        assert 'GRANT SELECT ON "public"."customers" TO "reader";' in out

    def test_grants_select_on_nothing_else(self):
        assert script(tables=["orders"]).count("GRANT SELECT") == 1

    def test_never_grants_write_privileges(self):
        out = script(tables=["orders", "customers"])
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "ALL PRIVILEGES", "ALL ON"):
            assert f"GRANT {privilege}" not in out

    def test_the_public_revoke_is_commented_out(self):
        # It affects every role on the database, not just the new one, so it is
        # offered rather than applied -- a script that silently re-privileges
        # someone's whole database is not one they can safely paste unread.
        for line in script().splitlines():
            if "REVOKE CREATE ON SCHEMA" in line:
                assert line.strip().startswith("--")

    def test_rejects_an_empty_table_list(self):
        # A role granted nothing connects fine and then fails every query; the
        # useful moment to say so is here, not three steps later.
        with pytest.raises(AccessScriptError):
            script(tables=[])


# ------------------------------------------------------------------- quoting:
# Table names come from the cached schema, but the schema comes from whatever
# database the user connected, so they are not ours to assume anything about.

class TestQuoting:
    def test_identifiers_are_double_quoted(self):
        assert 'GRANT SELECT ON "public"."order_items" TO "reader";' in script(tables=["order_items"])

    def test_embedded_double_quote_in_a_table_name_is_doubled(self):
        out = script(tables=['we"ird'])
        assert '"we""ird"' in out

    def test_a_table_name_cannot_terminate_the_statement(self):
        # The shape an injection would need: close the identifier, add a
        # statement. Doubling the quote keeps it one identifier.
        out = script(tables=['x" TO PUBLIC; DROP TABLE users; --'])
        assert "DROP TABLE users" in out  # present, but inert...
        assert '"x"" TO PUBLIC; DROP TABLE users; --"' in out  # ...because it is one quoted name
        assert out.count("GRANT SELECT") == 1

    def test_mixed_case_and_spaces_survive_as_one_identifier(self):
        assert '"Order Items"' in script(tables=["Order Items"])

    def test_single_quote_in_a_password_is_escaped(self):
        assert "PASSWORD 'a''b'" in script(password="a'b")

    def test_database_name_is_quoted(self):
        assert 'GRANT CONNECT ON DATABASE "my-db" TO "reader";' in script(database="my-db")


# ------------------------------------------------------- passwords and names:

class TestPasswordsAndRoleNames:
    def test_generated_passwords_are_unique(self):
        assert len({generate_password() for _ in range(50)}) == 50

    def test_generated_passwords_have_no_quote_characters(self):
        # token_urlsafe's alphabet is [A-Za-z0-9_-]; asserting it means the
        # single-quoted literal in the script can never be broken out of.
        for _ in range(50):
            password = generate_password()
            assert "'" not in password and '"' not in password and "\\" not in password

    def test_generated_passwords_are_long_enough_to_matter(self):
        assert len(generate_password()) >= 30

    def test_role_names_are_unique_per_connection(self):
        # Postgres roles are cluster-wide, so two scoped connections to
        # different databases on one server would collide on a fixed name.
        assert role_name_for(1) != role_name_for(2)

    def test_role_names_are_stable(self):
        assert role_name_for(7) == role_name_for(7)

    def test_role_names_are_bare_identifiers(self):
        assert role_name_for(42).replace("_", "").isalnum()


class TestConnectionStringHint:
    def test_contains_every_part_the_user_needs(self):
        url = connection_string_hint(
            host="db.example.com", port=5433, database="shop", role="reader", password="pw", ssl_mode="require"
        )
        assert url == "postgresql://reader:pw@db.example.com:5433/shop?sslmode=require"
