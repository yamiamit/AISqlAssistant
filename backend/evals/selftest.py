#!/usr/bin/env python3
"""
Self-test for the eval harness itself -- runs WITHOUT calling the AI provider.

The harness grades model output, so a bug in the grader silently corrupts every
score it produces. This stubs out the one non-deterministic piece (the Gemini
call) and drives the rest of the grading path for real: validator, executor,
gold execution against the live demo database, and result comparison.

Use it to check the harness still works when the provider is unavailable or out
of quota -- it costs zero AI calls. It does NOT test the provider integration
itself; that is exercised by runner.py.

Usage (from backend/):
    python evals/selftest.py
"""
import importlib.util
import json
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVALS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import app.services.nl_to_sql as nl  # noqa: E402
from app.config import settings  # noqa: E402
from app.services.schema_introspector import discover_schema  # noqa: E402

_spec = importlib.util.spec_from_file_location("runner", EVALS_DIR / "runner.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)

# Each scenario pins what the "model" returns, then asserts how the harness
# grades it. agg-01's gold is: SELECT status, COUNT(*) FROM orders GROUP BY status
SCENARIOS = [
    ("identical to gold", None, runner.PASS),
    (
        "equivalent, different aliases",
        "SELECT o.status AS s, COUNT(o.order_id) AS n FROM orders o GROUP BY o.status",
        runner.PASS,
    ),
    (
        "wrong data",
        "SELECT status, COUNT(*) FROM orders WHERE status = 'pending' GROUP BY status",
        runner.WRONG_RESULT,
    ),
    ("hallucinated column", "SELECT nonexistent_col FROM orders", runner.SQL_ERROR),
    ("destructive statement", "DROP TABLE orders", runner.VALIDATOR_REJECTED),
    (
        "empty result",
        "SELECT status, COUNT(*) FROM orders WHERE status = 'nope' GROUP BY status",
        runner.EMPTY_RESULT,
    ),
]


def main() -> None:
    if not settings.DEMO_DATABASE_URL:
        sys.exit("ERROR: DEMO_DATABASE_URL is required (environment or backend/.env).")

    case = {c["id"]: c for c in json.loads((EVALS_DIR / "cases.json").read_text())}["agg-01"]
    schema = discover_schema(settings.DEMO_DATABASE_URL)
    original_generate_sql = nl.generate_sql

    print(f"{'scenario':<32}{'expected':<20}{'actual':<20}ok")
    print("-" * 78)
    failures = 0
    try:
        for label, fake_sql, expected in SCENARIOS:
            sql = case["gold_sql"] if fake_sql is None else fake_sql
            nl.generate_sql = lambda _schema, _prompt, _history, _sql=sql: {"sql": _sql, "explanation": "stub"}
            actual = runner._run_case(case, schema)["reason"]
            ok = actual == expected
            failures += not ok
            print(f"{label:<32}{expected:<20}{actual:<20}{'OK' if ok else 'MISMATCH'}")
    finally:
        nl.generate_sql = original_generate_sql

    if failures:
        sys.exit(f"\n*** {failures} grading path(s) wrong -- the harness itself is buggy. ***")
    print("\nAll grading paths correct (no AI calls used).")


if __name__ == "__main__":
    main()
