#!/usr/bin/env python3
"""
Classify the failures in an eval run. Costs ZERO AI calls -- it re-executes the
already-generated SQL saved in a results file against the demo database.

The runner's headline number is strict execution match: a case passes only if the
generated result set matches gold exactly, column count included. That is the
right primary metric (loosening it invites false passes), but it collapses two
very different failures into one `wrong_result` bucket:

  * the model answered the question correctly but SELECTed extra columns
    ("which orders are pending?" -> it also returns status and shipped_date), and
  * the model actually got the answer wrong.

Only the second is a text-to-SQL quality problem. This script separates them by
asking: can gold's result be recovered by picking some subset of the generated
query's columns? If yes, the rows are right and only the projection is wider.

Usage (from backend/):
    python evals/analyze_failures.py evals/results/<timestamp>.json
"""
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.services.sql_executor import QueryExecutionError, execute_query  # noqa: E402

GOLD_TIMEOUT_MS = 15_000

PASSED = "exact_match"
OVER_SELECTED = "over_selected"
WRONG = "genuinely_wrong"
NO_SQL = "no_sql"

# Guard against combinatorial blowup on wide generated result sets.
MAX_GEN_COLUMNS = 9


def _norm(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return value


def _rows_as(columns, rows):
    return sorted(
        [tuple(_norm(row.get(col)) for col in columns) for row in rows],
        key=lambda row: [(v is None, str(v)) for v in row],
    )


def _classify(case) -> tuple[str, list | None]:
    if not case.get("generated_sql"):
        return NO_SQL, None
    try:
        gold = execute_query(settings.DEMO_DATABASE_URL, case["gold_sql"], GOLD_TIMEOUT_MS)
        gen = execute_query(settings.DEMO_DATABASE_URL, case["generated_sql"], GOLD_TIMEOUT_MS)
    except QueryExecutionError:
        return WRONG, None

    # Different row counts means a different answer, never just a wider SELECT.
    if gold.row_count != gen.row_count:
        return WRONG, None

    target = _rows_as(gold.columns, gold.rows)
    width = len(gold.columns)
    if width <= len(gen.columns) <= MAX_GEN_COLUMNS:
        for combo in itertools.permutations(gen.columns, width):
            if _rows_as(list(combo), gen.rows) == target:
                return OVER_SELECTED, list(combo)
    return WRONG, None


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if not settings.DEMO_DATABASE_URL:
        sys.exit("ERROR: DEMO_DATABASE_URL is required (environment or backend/.env).")

    data = json.loads(Path(sys.argv[1]).read_text())
    cases = data["cases"]

    buckets = defaultdict(list)
    by_tag = defaultdict(lambda: defaultdict(int))

    for case in cases:
        if case["passed"]:
            label = PASSED
        else:
            label, _ = _classify(case)
        buckets[label].append(case["id"])
        for tag in case["tags"]:
            by_tag[tag][label] += 1
            by_tag[tag]["total"] += 1

    total = len(cases)
    exact = len(buckets[PASSED])
    over = len(buckets[OVER_SELECTED])
    wrong = len(buckets[WRONG])
    no_sql = len(buckets[NO_SQL])

    print(f"\nrun_at {data['run_at']} | model {data['model']} | {total} cases")
    print("=" * 66)
    print(f"  exact execution match (runner PASS)   {exact:>3}   {exact / total * 100:5.1f}%")
    print(f"  right rows, extra columns             {over:>3}   {over / total * 100:5.1f}%")
    print(f"  genuinely wrong answer                {wrong:>3}   {wrong / total * 100:5.1f}%")
    print(f"  never produced runnable SQL           {no_sql:>3}   {no_sql / total * 100:5.1f}%")
    print("-" * 66)
    print(f"  ANSWER-CORRECT (exact + over-selected) {exact + over:>2}   "
          f"{(exact + over) / total * 100:5.1f}%")
    print("=" * 66)

    print(f"\n{'tag':<22}{'exact':>8}{'+cols':>8}{'wrong':>8}{'total':>8}{'ans-ok':>9}")
    print("-" * 63)
    for tag in sorted(by_tag):
        row = by_tag[tag]
        ok = row[PASSED] + row[OVER_SELECTED]
        print(f"{tag:<22}{row[PASSED]:>8}{row[OVER_SELECTED]:>8}{row[WRONG]:>8}"
              f"{row['total']:>8}{ok / row['total'] * 100:>8.0f}%")

    if buckets[OVER_SELECTED]:
        print(f"\nover-selected ({over}): {', '.join(sorted(buckets[OVER_SELECTED]))}")
    if buckets[WRONG]:
        print(f"\ngenuinely wrong ({wrong}): {', '.join(sorted(buckets[WRONG]))}")


if __name__ == "__main__":
    main()
