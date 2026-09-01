"""
The half of scoped access that cannot be tested without a real server: whether
Postgres actually refuses a non-granted table, and whether the catalog query in
schema_introspector actually filters by privilege.

These skip unless TEST_DATABASE_URL is set, and they need a role that can
CREATE ROLE and CREATE TABLE. Point them at a throwaway database -- the fixture
creates and drops tables and a login role in `public`. It refuses to run against
DEMO_DATABASE_URL, which is shared.

    TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/scratch \
        .venv/bin/python -m pytest tests/test_scoped_access_integration.py -v

Why these are worth the setup cost: every other test in this suite asserts what
*our* code does. The premise of the whole feature is what *Postgres* does, and
the one belief that turned out to be wrong -- that reflecting as a restricted
role would hide non-granted tables -- was a belief about Postgres, not about us.
"""
import os
import secrets

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.services import access_script
from app.services.schema_introspector import detect_write_access, discover_schema
from app.services.sql_executor import QueryExecutionError, execute_query

ADMIN_URL = os.getenv("TEST_DATABASE_URL")
DEMO_URL = os.getenv("DEMO_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_URL, reason="Set TEST_DATABASE_URL to a throwaway Postgres database to run these."
)

GRANTED_TABLE = "scoped_access_granted"
DENIED_TABLE = "scoped_access_denied"
ROLE = "scoped_access_reader"


@pytest.fixture(scope="module")
def restricted_url():
    """
    Build the world the feature assumes: two tables, a login role granted SELECT
    on exactly one of them, and a connection URL for that role.
    """
    if DEMO_URL and make_url(ADMIN_URL).database == make_url(DEMO_URL).database:
        pytest.skip("TEST_DATABASE_URL points at the shared demo database; use a throwaway one.")

    password = secrets.token_urlsafe(24)
    admin = create_engine(ADMIN_URL, connect_args={"connect_timeout": 5})
    database = make_url(ADMIN_URL).database

    with admin.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{GRANTED_TABLE}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{DENIED_TABLE}"'))
        conn.execute(text(f'CREATE TABLE "{GRANTED_TABLE}" (id integer PRIMARY KEY, label text)'))
        conn.execute(text(f'CREATE TABLE "{DENIED_TABLE}" (id integer PRIMARY KEY, secret text)'))
        conn.execute(text(f"""INSERT INTO "{GRANTED_TABLE}" VALUES (1, 'visible')"""))
        conn.execute(text(f"""INSERT INTO "{DENIED_TABLE}" VALUES (1, 'hidden')"""))

    # Role creation is its own transaction: if the server won't allow it, that's
    # a skip (wrong privileges for this test), not a failure of the feature.
    try:
        with admin.begin() as conn:
            conn.execute(text(f'DROP ROLE IF EXISTS "{ROLE}"'))
            conn.execute(text(f"""CREATE ROLE "{ROLE}" LOGIN PASSWORD '{password}'"""))
    except Exception as exc:  # noqa: BLE001
        admin.dispose()
        pytest.skip(f"TEST_DATABASE_URL's role cannot CREATE ROLE: {exc.__class__.__name__}")

    with admin.begin() as conn:
        conn.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO "{ROLE}"'))
        conn.execute(text(f'GRANT USAGE ON SCHEMA public TO "{ROLE}"'))
        conn.execute(text(f'GRANT SELECT ON public."{GRANTED_TABLE}" TO "{ROLE}"'))

    url = make_url(ADMIN_URL).set(
        drivername="postgresql+psycopg2", username=ROLE, password=password
    )
    yield url.render_as_string(hide_password=False)

    with admin.begin() as conn:
        conn.execute(text(f'REVOKE ALL ON public."{GRANTED_TABLE}" FROM "{ROLE}"'))
        conn.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{ROLE}"'))
        conn.execute(text(f'REVOKE ALL ON DATABASE "{database}" FROM "{ROLE}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{GRANTED_TABLE}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{DENIED_TABLE}"'))
    with admin.begin() as conn:
        conn.execute(text(f'DROP ROLE IF EXISTS "{ROLE}"'))
    admin.dispose()


def test_select_on_a_granted_table_succeeds(restricted_url):
    result = execute_query(restricted_url, f'SELECT id, label FROM "{GRANTED_TABLE}" LIMIT 10')
    assert result.rows == [{"id": 1, "label": "visible"}]


def test_select_on_a_non_granted_table_is_refused(restricted_url):
    # The query is a valid SELECT, so all three app-layer guards pass it. Only
    # the grant stops it -- this is the case the feature exists for.
    with pytest.raises(QueryExecutionError) as exc:
        execute_query(restricted_url, f'SELECT secret FROM "{DENIED_TABLE}" LIMIT 10')
    assert str(exc.value) == "That table isn't in your connection's allowed set."


def test_introspection_returns_only_granted_tables(restricted_url):
    # The regression this feature was built around: pg_catalog.pg_class is
    # world-readable, so a reflection that doesn't filter by privilege lists
    # DENIED_TABLE here and feeds it to the model.
    names = {table["name"] for table in discover_schema(restricted_url)["tables"]}
    assert GRANTED_TABLE in names
    assert DENIED_TABLE not in names


def test_admin_role_still_sees_both_tables(restricted_url):
    # Parity check: the filter must be invisible to an unrestricted connection,
    # or every user who skips scoping silently loses their schema.
    names = {table["name"] for table in discover_schema(ADMIN_URL)["tables"]}
    assert {GRANTED_TABLE, DENIED_TABLE} <= names


def test_write_access_is_detected_on_an_unrestricted_role(restricted_url):
    # The banner's premise: an ordinary connection can write, and we can tell.
    assert detect_write_access(ADMIN_URL) is True


def test_write_access_is_not_detected_on_a_select_only_role(restricted_url):
    assert detect_write_access(restricted_url) is False


def test_the_generated_script_actually_produces_a_scoped_role():
    """
    The end-to-end claim of the whole feature: run the script we hand the user,
    connect as the role it creates, and the boundary holds.

    Every other test here builds the restricted role with hand-written GRANTs.
    This one builds it with the *generated* ones, which is the only way to know
    the generator emits SQL Postgres actually accepts.
    """
    admin = create_engine(ADMIN_URL, connect_args={"connect_timeout": 5})
    database = make_url(ADMIN_URL).database
    role = access_script.role_name_for(4242)
    password = access_script.generate_password()

    with admin.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS script_granted'))
        conn.execute(text('DROP TABLE IF EXISTS script_denied'))
        conn.execute(text('CREATE TABLE script_granted (id integer PRIMARY KEY, label text)'))
        conn.execute(text('CREATE TABLE script_denied (id integer PRIMARY KEY, secret text)'))
        conn.execute(text("INSERT INTO script_granted VALUES (1, 'ok')"))
    with admin.begin() as conn:
        conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))

    script = access_script.build_access_script(
        database=database, role=role, password=password, tables=["script_granted"]
    )

    try:
        # Executed exactly as pasted — the whole script in one go, the way psql
        # would take it. Splitting on ';' would cut the DO block in half, and
        # psycopg2 refuses CREATE ROLE inside an explicit transaction block, so
        # this runs in autocommit rather than wrapped.
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql(script)

        url = make_url(ADMIN_URL).set(
            drivername="postgresql+psycopg2", username=role, password=password
        ).render_as_string(hide_password=False)

        assert execute_query(url, "SELECT label FROM script_granted LIMIT 5").rows == [{"label": "ok"}]

        with pytest.raises(QueryExecutionError) as exc:
            execute_query(url, "SELECT secret FROM script_denied LIMIT 5")
        assert str(exc.value) == "That table isn't in your connection's allowed set."

        names = {t["name"] for t in discover_schema(url)["tables"]}
        assert names == {"script_granted"}

        # And the role the script creates is one the banner will call scoped.
        assert detect_write_access(url) is False
    finally:
        # Tolerant of a failure before the role was created, so a real assertion
        # failure isn't buried under an UndefinedObject from cleanup.
        with admin.begin() as conn:
            exists = conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role})
            if exists:
                conn.execute(text(f'REVOKE ALL ON public.script_granted FROM "{role}"'))
                conn.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{role}"'))
                conn.execute(text(f'REVOKE ALL ON DATABASE "{database}" FROM "{role}"'))
            conn.execute(text('DROP TABLE IF EXISTS script_granted'))
            conn.execute(text('DROP TABLE IF EXISTS script_denied'))
        with admin.begin() as conn:
            conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        admin.dispose()


def test_the_generated_script_can_be_re_run_to_change_the_scope():
    """
    Re-scoping is an ordinary thing to want: narrow to three tables, then to two.
    The script is generated for the same role name each time, so it has to cope
    with the role already existing *and* has to actually drop the grant that is
    no longer wanted.
    """
    admin = create_engine(ADMIN_URL, connect_args={"connect_timeout": 5})
    database = make_url(ADMIN_URL).database
    role = access_script.role_name_for(9999)

    with admin.begin() as conn:
        for name in ("rescope_a", "rescope_b"):
            conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            conn.execute(text(f"CREATE TABLE {name} (id integer PRIMARY KEY)"))
    with admin.begin() as conn:
        conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))

    def run(tables):
        password = access_script.generate_password()
        script = access_script.build_access_script(
            database=database, role=role, password=password, tables=tables
        )
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.exec_driver_sql(script)
        return make_url(ADMIN_URL).set(
            drivername="postgresql+psycopg2", username=role, password=password
        ).render_as_string(hide_password=False)

    try:
        url = run(["rescope_a", "rescope_b"])
        assert {t["name"] for t in discover_schema(url)["tables"]} >= {"rescope_a", "rescope_b"}

        # Second run, narrower: must not error, and must actually revoke the
        # grant it no longer lists.
        url = run(["rescope_a"])
        names = {t["name"] for t in discover_schema(url)["tables"]}
        assert "rescope_a" in names
        assert "rescope_b" not in names

        with pytest.raises(QueryExecutionError):
            execute_query(url, "SELECT id FROM rescope_b LIMIT 1")
    finally:
        with admin.begin() as conn:
            if conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}):
                conn.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role}"'))
                conn.execute(text(f'REVOKE ALL ON SCHEMA public FROM "{role}"'))
                conn.execute(text(f'REVOKE ALL ON DATABASE "{database}" FROM "{role}"'))
            conn.execute(text("DROP TABLE IF EXISTS rescope_a"))
            conn.execute(text("DROP TABLE IF EXISTS rescope_b"))
        with admin.begin() as conn:
            conn.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
        admin.dispose()
