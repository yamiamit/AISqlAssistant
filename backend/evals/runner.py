#!/usr/bin/env python3
"""
Offline eval harness for the text-to-SQL pipeline, scored by execution match
against the demo database.

DEV-TIME TOOL ONLY. Nothing under app/ imports this package, and this package
is deliberately not importable as one (no __init__.py) -- it reaches into the
app by putting backend/ on sys.path when run as a script. Keep it that way:
the running API must never be able to reach eval code.

It calls the SAME pipeline the API calls -- app.services.nl_to_sql.run_nl_to_sql,
which api/routes/chat.py is now a thin wrapper over -- so a score here reflects
what the product actually does, not a parallel reimplementation of it.

Usage (from backend/):
    python evals/runner.py
    python evals/runner.py --tag aggregation --limit 5
    python evals/runner.py --case-id hard-05 --case-id join3-01
"""
import argparse
import json
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = EVALS_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# The API ships a 30s AI timeout, which is tuned for "a human is watching a
# spinner". Provider latency routinely sits right at that boundary, so a batch
# run scores a large slice of cases as timeouts rather than as SQL mistakes --
# infrastructure noise, not model quality. The eval therefore waits longer by
# default. This changes NOTHING about the prompt or the SQL produced; override
# with EVAL_AI_TIMEOUT_SECONDS to score against the production timeout instead.
os.environ["AI_REQUEST_TIMEOUT_SECONDS"] = os.environ.get("EVAL_AI_TIMEOUT_SECONDS", "120")

from app.config import settings  # noqa: E402
from app.services.nl_to_sql import STAGE_AI, STAGE_VALIDATION, run_nl_to_sql  # noqa: E402
from app.services.schema_introspector import discover_schema  # noqa: E402
from app.services.sql_executor import QueryExecutionError, execute_query  # noqa: E402

MAX_WORKERS = 4

# --- Provider rate limiting -------------------------------------------------
# Groq's free tier caps *tokens per minute*, not requests per day: 8000 TPM
# against ~1040 tokens per case (887 prompt + ~150 completion) allows only
# ~7.7 calls/min. Four unthrottled workers spend the whole minute's budget in
# seconds, and every remaining case then 429s -- which is exactly how the first
# 40-case Groq run scored 26/40 `ai_rate_limited` and voided itself.
#
# So calls are paced to a minimum interval. Workers still overlap on the
# Postgres side; only the AI call is serialized. Override for a paid key or a
# different provider:
#   EVAL_MIN_CALL_INTERVAL_SECONDS=0 python evals/runner.py
AI_CALL_MIN_INTERVAL = float(os.environ.get("EVAL_MIN_CALL_INTERVAL_SECONDS", "8.5"))

# A per-day/per-minute 429 is not transient in the way a blip is: re-asking
# immediately cannot succeed. Wait out the window before the one retry.
RATE_LIMIT_BACKOFF_SECONDS = float(os.environ.get("EVAL_RATE_LIMIT_BACKOFF_SECONDS", "62"))

_throttle_lock = threading.Lock()
_last_call_at = 0.0


def _throttle() -> None:
    """Block until enough time has passed since the last AI call."""
    global _last_call_at
    if AI_CALL_MIN_INTERVAL <= 0:
        return
    with _throttle_lock:
        wait = _last_call_at + AI_CALL_MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_call_at = time.monotonic()
GOLD_TIMEOUT_MS = 15_000

# Grading outcomes. Everything that isn't PASS is a failure, but they are
# recorded distinctly because they mean very different things about the model.
PASS = "pass"
VALIDATOR_REJECTED = "validator_rejected"
AI_TIMEOUT = "ai_timeout"
AI_RATE_LIMITED = "ai_rate_limited"
AI_ERROR = "ai_error"
SCHEMA_ERROR = "schema_error"
SQL_ERROR = "sql_error"
EMPTY_RESULT = "empty_result"
WRONG_RESULT = "wrong_result"
PIPELINE_ERROR = "pipeline_error"
GOLD_ERROR = "gold_error"

# ai_service.py normalizes every provider exception into a friendly string, so
# the only signal available out here is that string. These substrings identify
# errors worth ONE retry as an API-reliability measure. This is explicitly NOT
# SQL self-correction -- the same question is re-asked unchanged, and a model
# that returns runnable-but-wrong SQL is never given a second attempt.
#
# Timeout and rate-limit are tracked separately because they mean different
# things to whoever reads the report: "the provider was slow" is a latency
# problem, "the key is out of quota" means the run measured nothing at all.
_TIMEOUT_MARKERS = ("took too long", "DeadlineExceeded")
_RATE_LIMIT_MARKERS = ("ResourceExhausted", "TooManyRequests", "429", "quota", "RateLimitError", "rate limit")
_OTHER_TRANSIENT_MARKERS = ("ServiceUnavailable", "InternalServerError", "Aborted", "RetryError", "Unavailable")


def _matches(message: str | None, markers: tuple[str, ...]) -> bool:
    return bool(message) and any(marker.lower() in message.lower() for marker in markers)


def _is_transient(message: str | None) -> bool:
    return (
        _matches(message, _TIMEOUT_MARKERS)
        or _matches(message, _RATE_LIMIT_MARKERS)
        or _matches(message, _OTHER_TRANSIENT_MARKERS)
    )


def _ai_failure_reason(message: str | None) -> str:
    if _matches(message, _RATE_LIMIT_MARKERS):
        return AI_RATE_LIMITED
    if _matches(message, _TIMEOUT_MARKERS):
        return AI_TIMEOUT
    return AI_ERROR


def _norm_value(value):
    """
    Make two result sets comparable without being pedantic about types.

    Postgres hands back Decimal for SUM/AVG and int for COUNT; sql_executor
    already turns Decimal into float and dates into ISO strings. Rounding
    numbers to 2dp additionally means `AVG(x)` and `ROUND(AVG(x), 2)` compare
    equal -- a difference in display precision is not a difference in answer.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return value


def _as_row_tuples(columns: list[str], rows: list[dict]) -> list[tuple]:
    return [tuple(_norm_value(row.get(col)) for col in columns) for row in rows]


def _sort_key(row: tuple):
    # Result rows mix None, str and float, which don't compare against each
    # other; sort on a stringified surrogate so the ordering is total.
    return [(value is None, str(value)) for value in row]


def _results_match(gold_columns, gold_rows, gen_columns, gen_rows) -> bool:
    """
    EXECUTION MATCH: same rows, order-insensitive, after value normalization.
    Column *names* are ignored (the model is free to alias differently) but
    column count and per-position values must line up.
    """
    left = sorted(_as_row_tuples(gold_columns, gold_rows), key=_sort_key)
    right = sorted(_as_row_tuples(gen_columns, gen_rows), key=_sort_key)
    return left == right


def _truncate(rows: list[dict] | None, limit: int = 5) -> list[dict]:
    return list(rows or [])[:limit]


def _run_case(case: dict, cached_schema: dict) -> dict:
    """Run one case end to end and grade it. Never raises."""
    record = {
        "id": case["id"],
        "question": case["question"],
        "tags": case["tags"],
        "gold_sql": case["gold_sql"],
        "generated_sql": None,
        "passed": False,
        "reason": None,
        "detail": None,
        "attempts": 1,
        "gold_rows": [],
        "generated_rows": [],
        "gold_row_count": None,
        "generated_row_count": None,
    }

    _throttle()
    outcome = run_nl_to_sql(
        connection_url=settings.DEMO_DATABASE_URL,
        prompt=case["question"],
        cached_schema=cached_schema,
        history=None,
        row_limit=settings.SQL_DEFAULT_ROW_LIMIT,
        statement_timeout_ms=settings.SQL_STATEMENT_TIMEOUT_MS,
    )

    # One retry, only for transient provider errors -- never for a bad answer.
    if outcome.failure_stage == STAGE_AI and _is_transient(outcome.error_message):
        # Rate limits need the window to actually roll over; retrying inside it
        # just burns the second attempt too.
        if _matches(outcome.error_message, _RATE_LIMIT_MARKERS):
            time.sleep(RATE_LIMIT_BACKOFF_SECONDS)
        record["attempts"] = 2
        _throttle()
        outcome = run_nl_to_sql(
            connection_url=settings.DEMO_DATABASE_URL,
            prompt=case["question"],
            cached_schema=cached_schema,
            history=None,
            row_limit=settings.SQL_DEFAULT_ROW_LIMIT,
            statement_timeout_ms=settings.SQL_STATEMENT_TIMEOUT_MS,
        )

    record["generated_sql"] = outcome.generated_sql

    if not outcome.ok:
        record["detail"] = outcome.error_message
        if outcome.failure_stage == STAGE_VALIDATION:
            record["reason"] = VALIDATOR_REJECTED
        elif outcome.failure_stage == STAGE_AI:
            record["reason"] = _ai_failure_reason(outcome.error_message)
        elif outcome.failure_stage == "schema":
            record["reason"] = SCHEMA_ERROR
        elif outcome.failure_stage == "execution":
            record["reason"] = SQL_ERROR
        else:
            record["reason"] = PIPELINE_ERROR
        return record

    try:
        gold = execute_query(settings.DEMO_DATABASE_URL, case["gold_sql"], GOLD_TIMEOUT_MS)
    except QueryExecutionError as exc:
        # The harness's own SQL is broken -- surfaced loudly, never counted as
        # a model failure.
        record["reason"] = GOLD_ERROR
        record["detail"] = str(exc)
        return record

    record["gold_row_count"] = gold.row_count
    record["generated_row_count"] = outcome.row_count
    record["gold_rows"] = _truncate(gold.rows)
    record["generated_rows"] = _truncate(outcome.result_rows)

    if outcome.row_count == 0 and gold.row_count > 0:
        record["reason"] = EMPTY_RESULT
        record["detail"] = f"generated returned 0 rows, gold returned {gold.row_count}"
        return record

    if _results_match(gold.columns, gold.rows, outcome.result_columns, outcome.result_rows):
        record["passed"] = True
        record["reason"] = PASS
    else:
        record["reason"] = WRONG_RESULT
        record["detail"] = (
            f"generated {outcome.row_count} rows x {len(outcome.result_columns or [])} cols, "
            f"gold {gold.row_count} rows x {len(gold.columns)} cols"
        )
    return record


def _load_cases(args) -> list[dict]:
    cases = json.loads((EVALS_DIR / "cases.json").read_text())
    if args.tag:
        cases = [c for c in cases if any(t in args.tag for t in c["tags"])]
    if args.case_id:
        cases = [c for c in cases if c["id"] in args.case_id]
    if args.limit:
        cases = cases[: args.limit]
    return cases


def _check_env() -> None:
    missing = []
    if not settings.DEMO_DATABASE_URL:
        missing.append("DEMO_DATABASE_URL")
    if not settings.AI_API_KEY:
        missing.append(settings.AI_API_KEY_NAME)
    if missing:
        sys.exit(
            f"ERROR: missing required setting(s): {', '.join(missing)}.\n"
            f"Set them in the environment or in backend/.env, then re-run."
        )


def _print_summary(records: list[dict]) -> None:
    total = len(records)
    passed = sum(1 for r in records if r["passed"])
    pct = (passed / total * 100) if total else 0.0

    print("\n" + "=" * 62)
    print(f"OVERALL: {passed}/{total} passed  ({pct:.1f}%)   [execution match]")
    print("=" * 62)

    by_tag = defaultdict(lambda: [0, 0])
    for record in records:
        for tag in record["tags"]:
            by_tag[tag][1] += 1
            if record["passed"]:
                by_tag[tag][0] += 1

    print(f"\n{'tag':<22}{'passed':>10}{'total':>8}{'score':>9}")
    print("-" * 49)
    for tag in sorted(by_tag):
        hit, tot = by_tag[tag]
        print(f"{tag:<22}{hit:>10}{tot:>8}{(hit / tot * 100):>8.0f}%")

    failures = [r for r in records if not r["passed"]]
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for record in failures:
            detail = (record["detail"] or "").replace("\n", " ")[:88]
            print(f"  {record['id']:<12} {record['reason']:<18} {detail}")

    reasons = Counter(r["reason"] for r in records if not r["passed"])
    if reasons:
        print("\nFAILURE REASONS:")
        for reason, count in reasons.most_common():
            print(f"  {reason:<20} {count}")

    if any(r["reason"] == GOLD_ERROR for r in records):
        print("\n!! GOLD_ERROR present: a gold query is broken. Fix cases.json -- "
              "these are harness bugs, not model failures.")

    # A run where the provider never answered measured nothing about SQL
    # quality. Say so loudly -- a 0% that actually means "out of quota" is
    # worse than no number at all, because it reads like a model result.
    provider_dead = sum(1 for r in records if r["reason"] in (AI_RATE_LIMITED, AI_TIMEOUT, AI_ERROR))
    if provider_dead:
        share = provider_dead / total * 100
        print(f"\n!! {provider_dead}/{total} case(s) ({share:.0f}%) never produced SQL because the AI "
              f"provider failed (rate limit / timeout / error).")
        if share >= 20:
            print("   THIS RUN IS NOT A VALID BASELINE. The score above reflects provider")
            print("   availability, not text-to-SQL quality. Re-run once quota recovers.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the text-to-SQL pipeline by execution match.")
    parser.add_argument("--tag", action="append", help="only run cases with this tag (repeatable)")
    parser.add_argument("--case-id", action="append", help="only run this case id (repeatable)")
    parser.add_argument("--limit", type=int, help="cap the number of cases run")
    args = parser.parse_args()

    _check_env()

    cases = _load_cases(args)
    if not cases:
        sys.exit("No cases matched the given filters.")

    print(f"Introspecting demo database schema ...")
    try:
        schema = discover_schema(settings.DEMO_DATABASE_URL)
    except Exception as exc:
        sys.exit(f"ERROR: could not introspect DEMO_DATABASE_URL ({exc.__class__.__name__}): {exc}")

    print(f"Running {len(cases)} case(s) with {MAX_WORKERS} workers "
          f"(~{len(cases)} AI calls, plus retries) ...")
    print(f"Provider: {settings.AI_PROVIDER} | Model: {settings.AI_MODEL} "
          f"| AI timeout: {settings.AI_REQUEST_TIMEOUT_SECONDS}s")
    if AI_CALL_MIN_INTERVAL > 0:
        print(f"Pacing: {AI_CALL_MIN_INTERVAL}s between AI calls "
              f"(~{len(cases) * AI_CALL_MIN_INTERVAL / 60:.1f} min for {len(cases)} case(s))\n")
    else:
        print()

    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for record in pool.map(lambda c: _run_case(c, schema), cases):
            status = "PASS" if record["passed"] else f"FAIL ({record['reason']})"
            print(f"  {record['id']:<12} {status}")
            records.append(record)

    records.sort(key=lambda r: r["id"])
    _print_summary(records)

    results_dir = EVALS_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    out_path.write_text(json.dumps(
        {
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "provider": settings.AI_PROVIDER,
            "model": settings.AI_MODEL,
            "total": len(records),
            "passed": sum(1 for r in records if r["passed"]),
            "cases": records,
        },
        indent=2,
        default=str,
    ))
    print(f"\nFull detail written to {out_path.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
