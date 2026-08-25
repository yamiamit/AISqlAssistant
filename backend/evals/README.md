# Text-to-SQL Eval Harness

An offline scorer for the natural-language → SQL pipeline, graded by **execution
match** against the demo database.

This is a **dev-time tool only**. Nothing under `app/` imports it, and it is
deliberately not a Python package (no `__init__.py`) — it puts `backend/` on
`sys.path` when run as a script. The running API cannot reach it, and it should
stay that way.

## Running it

From `backend/`, with the venv active:

```bash
python evals/runner.py                                  # all 40 cases
python evals/runner.py --tag aggregation                # one tag
python evals/runner.py --tag aggregation --tag date_reasoning
python evals/runner.py --case-id hard-05 --case-id join3-01
python evals/runner.py --limit 5                        # cap the run
```

Requires `DEMO_DATABASE_URL` and `GEMINI_API_KEY` (environment or `backend/.env`);
the runner exits loudly if either is missing.

> **Cost**: a full run makes **~40 Gemini calls** (one per case, plus at most one
> retry per case on a transient provider error). It is not free — use `--tag`,
> `--case-id`, or `--limit` while iterating.

Console output gives an overall score, a per-tag table, and every failing case id
with its reason. Full detail — question, generated SQL, gold SQL, both result sets
truncated to 5 rows, pass/fail, failure reason — is written to
`evals/results/<timestamp>.json`. Those result files are gitignored; the harness
and its cases are committed, individual run artifacts are not.

## Checking the harness itself (no AI calls)

A bug in the grader silently corrupts every score it produces, so the grading
path has its own test that stubs the Gemini call and runs everything downstream
for real against the demo database:

```bash
python evals/selftest.py     # costs zero AI calls
```

It asserts that identical-to-gold and differently-aliased-but-equivalent SQL both
`pass`, and that wrong data, hallucinated columns, destructive statements, and
empty results each land in the right failure bucket. Run it when the provider is
down or out of quota, or after touching the comparison logic.

## Splitting the failures (no AI calls)

The runner's headline score is strict: a case fails if the column count differs,
even when the rows are right. That collapses "answered correctly but SELECTed
extra columns" and "got the answer wrong" into one `wrong_result` bucket, and
only the second is a text-to-SQL quality problem.

`analyze_failures.py` separates them by re-executing the SQL already saved in a
results file and asking whether gold's rows can be recovered from some subset of
the generated query's columns:

```bash
python evals/analyze_failures.py evals/results/<timestamp>.json
```

It costs zero AI calls. Quote both numbers it prints, not just one — see
[`BASELINE.md`](BASELINE.md) for the current baseline and why the pair matters.

## What "execution match" means

A case passes when the generated SQL, **actually run against the demo database**,
returns the same rows as the hand-written gold SQL. Specifically:

- Both queries are executed through the same `sql_executor.execute_query` the API
  uses (read-only transaction, statement timeout).
- Rows are compared as **sorted lists of tuples** — order-insensitive.
- Column *names* are ignored (the model may alias however it likes); column
  *count* and per-position values must line up.
- Numbers are normalized to 2 decimal places, so `AVG(x)` and `ROUND(AVG(x), 2)`
  compare equal. A difference in display precision is not a difference in answer.

## Why execution match and not string match

String comparison against a reference query measures the wrong thing. These are
all the same answer:

```sql
SELECT COUNT(*) FROM orders WHERE status = 'pending';
SELECT COUNT(order_id) AS pending_orders FROM orders WHERE status = 'pending';
SELECT COUNT(*) FROM orders o WHERE o.status = 'pending';
```

Any string or AST comparison marks two of those wrong. There are effectively
unlimited correct spellings of a correct query — different aliases, join order,
`WHERE` vs `HAVING`, CTE vs subquery — so a string metric mostly measures
"did the model phrase it the way I happened to phrase it", which is not a
property anyone cares about. Executing both and comparing the data answers the
question that actually matters: *did the user get the right numbers?*

The trade-off is that execution match has known blind spots, and it is worth
being honest about them:

- **Order-insensitive.** "Top 10 customers by revenue" passes as long as the same
  10 rows come back, even if sorted wrong. Catching that would need order-aware
  comparison for the subset of questions where order is part of the answer.
- **Coincidental agreement.** On this dataset a wrong query can occasionally
  return the right rows. A bigger/nastier dataset reduces but never eliminates this.
- **Extra or missing columns fail**, even when the "answer" is arguably present —
  selecting `customer_id, name, total` against a gold of `customer_id, total` is
  scored wrong. This is strict on purpose; loosening it invites false passes.

## Failure reasons

Failures are recorded distinctly, because they mean different things:

| Reason | Meaning |
|---|---|
| `validator_rejected` | `sql_validator` refused the SQL (not SELECT/WITH, blocklisted keyword, stacked statement) |
| `sql_error` | Postgres rejected it — usually a hallucinated table/column |
| `ai_timeout` | Provider did not respond in time, after one retry |
| `ai_rate_limited` | Provider refused on quota/rate limit (`ResourceExhausted`/429), after one retry |
| `ai_error` | Provider returned an error, or unparseable/non-JSON output |
| `schema_error` | Could not introspect the demo database |
| `empty_result` | Ran fine, returned 0 rows, gold returned some |
| `wrong_result` | Ran fine, returned the wrong data |
| `pipeline_error` | Unexpected exception |
| `gold_error` | **Harness bug** — the gold query itself failed. Fix `cases.json`. |

### When the provider is down or out of quota

If the AI provider never answers, the run measures provider availability rather
than SQL quality — a `0%` that really means "out of quota" reads exactly like a
catastrophic model result. The runner therefore counts `ai_rate_limited` /
`ai_timeout` / `ai_error` cases and, when they exceed 20% of the run, prints:

```
!! THIS RUN IS NOT A VALID BASELINE.
```

Treat any run carrying that banner as void and re-run it.

Free-tier quota is granted **per model, per project, per day** — so rotating the
API key changes nothing, but switching models gives you a fresh bucket. This
matters more than it sounds: the app's default `GEMINI_MODEL=gemini-flash-latest`
currently resolves to `gemini-3.7-flash`, whose free tier allows **20 requests
per day**. A 40-case run cannot complete on it even once. Override per-run:

```bash
GEMINI_MODEL=gemini-3.5-flash-lite python evals/runner.py
```

`--limit` or a paid key are the other ways out. Check the model actually resolves
before a long run — `gemini-2.5-flash` and `gemini-2.5-flash-lite` now 404 with
"no longer available to new users" on newly issued keys.

## Retry policy

A case is retried **once**, and only when the provider error looks transient
(timeout, 429/rate-limit, 5xx). That is an API-reliability retry.

It is explicitly **not** SQL self-correction: the same question is re-asked
unchanged, the model never sees the error, and SQL that runs but returns the
wrong answer is never given a second attempt. Adding a correction loop would
change what is being measured, and would contaminate this baseline.

## Cases

40 cases in `cases.json`, each `{id, question, gold_sql, tags}`:

| Tag | Count | What it probes |
|---|---|---|
| `single_table_filter` | 8 | One table, a `WHERE` clause |
| `aggregation` | 8 | `GROUP BY`, `COUNT`/`SUM`/`AVG`/`MIN`/`MAX` |
| `two_table_join` | 8 | One join |
| `multi_table_join` | 6 | Three or more tables |
| `date_reasoning` | 5 | Year, quarter, half-year, month bucketing |
| `hard_ambiguous` | 5 | Deliberately underspecified — **expected to fail** |

Every gold query was verified against the live demo database to run without error
and return a non-empty result under 500 rows (the pipeline's auto-`LIMIT`).

The `hard_ambiguous` cases are the point of the tag, not a bug: "who are our best
customers?" has no single right answer, and `hard-05` ("profit margin by
category") needs the model to know `products.cost` is wholesale cost — which is
documented only in a SQL `COMMENT`, and `schema_to_prompt_text()` does not send
comments to the model. These cases exist to mark the ceiling, and a score of 0/5
on them is an expected result rather than a regression.

### A note on relative dates

The brief asked for a "past 30 days" style case. The demo data ends 2025-12-30, so
any window relative to *today* returns nothing, and a gold query that returns zero
rows cannot distinguish a right answer from a broken one. Date cases therefore use
fixed windows ("last quarter of 2025", "first half of 2023"). Testing genuinely
relative dates needs either a rolling seed or a pinned clock — worth doing, not
done here.

## AI timeout

The API ships `AI_REQUEST_TIMEOUT_SECONDS=30`, tuned for a human watching a
spinner. Provider latency frequently sits right at that boundary, which scores a
large slice of a batch run as `ai_timeout` rather than as SQL mistakes. The runner
therefore waits **120s** by default.

This changes nothing about the prompt or the SQL produced — it only stops network
latency from being counted as model error. To score against the production
timeout instead:

```bash
EVAL_AI_TIMEOUT_SECONDS=30 python evals/runner.py
```
