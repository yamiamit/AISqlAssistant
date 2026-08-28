# Text-to-SQL Eval Baseline

First valid baseline for the natural-language → SQL pipeline, graded by
**execution match** against the demo database.

| | |
|---|---|
| **Run** | `evals/results/20260825T222915.json` |
| **Date** | 2026-08-25 |
| **Model** | `gemini-3.5-flash-lite` (temperature 0.1, JSON mode) |
| **Cases** | 40, across 6 tags |
| **Grader** | execution match — order-insensitive, column-names ignored, numbers to 2dp |
| **Provider failures** | 0/40 — **this run is a valid baseline** |
| **Wall clock** | ~7 min, 4 workers, 40 AI calls, 0 retries |

## Headline numbers

```
exact execution match (runner PASS)    11 / 40    27.5%
right rows, extra columns              20 / 40    50.0%
genuinely wrong answer                  9 / 40    22.5%
never produced runnable SQL             0 / 40     0.0%
---------------------------------------------------------
ANSWER-CORRECT (exact + over-selected) 31 / 40    77.5%
```

Two numbers, because they measure different things and only quoting one of them
is misleading:

- **27.5% strict execution match** is what `runner.py` prints. A case passes only
  if the result set matches gold exactly — column *count* included.
- **77.5% answer-correct** additionally counts cases where the model returned
  **exactly the right rows** but selected extra columns. Reproduce with
  `python evals/analyze_failures.py evals/results/<run>.json` (zero AI calls).

The gap between them is one behaviour, not twenty different bugs: the model
answers "which orders are still pending?" with the right 100 rows but also
returns `status` and `shipped_date`, which gold does not select. The rows are
right; the projection is wider. 20 of the 29 failures are exactly this.

Both numbers are honest. Which to quote depends on the question being asked:
*"does the generated query match a reference query?"* → 27.5%.
*"did the user get the right data back?"* → 77.5%.

## Second model: `openai/gpt-oss-120b` (Groq), 2026-08-28

Run `evals/results/20260828T194837.json` — 40 cases, 0 provider failures, ~6 min,
4 workers paced to one AI call / 8.5s. **This is a valid run.**

```
exact execution match (runner PASS)    16 / 40    40.0%
right rows, extra columns              15 / 40    37.5%
genuinely wrong answer                  9 / 40    22.5%
never produced runnable SQL             0 / 40     0.0%
---------------------------------------------------------
ANSWER-CORRECT (exact + over-selected) 31 / 40    77.5%
```

**Both models land on exactly 77.5% answer-correct, and on exactly 9 genuinely
wrong — via completely different cases.**

| Tag | Gemini 3.5-flash-lite | Groq gpt-oss-120b |
|---|---|---|
| `aggregation` | 75% | **100%** |
| `date_reasoning` | 80% | **100%** |
| `two_table_join` | 100% | 100% |
| `multi_table_join` | 50% | **67%** |
| `single_table_filter` | 88% | 75% |
| `hard_ambiguous` | 60% | **0%** |
| **overall answer-correct** | **77.5%** | **77.5%** |

What the comparison settles:

- **The weak spot was partly capability.** `multi_table_join` improved 50% → 67%
  and `aggregation`/`date_reasoning` went to 100% on the larger model. Join depth
  does track difficulty, as suspected.
- **But the ceiling is not capability.** A substantially larger model moved cases
  around without moving the total at all. What it gained on aggregation and joins
  it gave back on `hard_ambiguous` (3/5 → 0/5) and `single_table_filter`.
- **`hard_ambiguous` is doing its job.** gpt-oss-120b answers those questions far
  more expansively — 190 rows where gold returns 10, 189 where gold returns 59.
  Neither reading is wrong; the questions have no single right answer, which is
  the entire point of the tag.
- **Strict match is the more model-sensitive metric** (27.5% → 40.0%) because it
  partly measures projection style, which differs sharply between models.

Caveat: n=1 per model, and the Gemini pair alone varies ±2.5% run to run (see
below). Treat 77.5% ≈ 77.5% as "indistinguishable", not "identical".

## Per-tag breakdown

| Tag | exact | +cols | wrong | total | answer-correct |
|---|---|---|---|---|---|
| `two_table_join` | 2 | 6 | 0 | 8 | **100%** |
| `single_table_filter` | 0 | 7 | 1 | 8 | **88%** |
| `date_reasoning` | 2 | 2 | 1 | 5 | **80%** |
| `aggregation` | 5 | 1 | 2 | 8 | **75%** |
| `hard_ambiguous` | 0 | 3 | 2 | 5 | **60%** |
| `multi_table_join` | 2 | 1 | 3 | 6 | **50%** |

`single_table_filter` scores **0% strict / 88% answer-correct** — the single
clearest illustration of why the strict number alone misleads. Every one of those
8 questions ("list all customers based in India") names a filter but never says
which columns to show, so the model's choice of projection is guesswork against
a gold query that made one specific choice.

`multi_table_join` is the genuine weak spot: 3 of 6 wrong on the answer itself,
not the projection. Difficulty tracks join depth, which is the expected shape.

`hard_ambiguous` scoring 0% strict is **an expected result, not a regression** —
the tag exists to mark the ceiling. See the note in `README.md`.

## The 9 genuinely wrong cases

Worth reading individually, because they are not all the same kind of error:

| Case | What happened |
|---|---|
| `filter-03` | **Real error.** "Products that cost more than 100 dollars" → filtered on `cost > 100` instead of `price > 100`. Read the wholesale-cost column as the customer-facing price. |
| `agg-04` | Added an unasked `WHERE status = 'completed'` to payments — defensible reading, different answer. |
| `agg-06` | Grouped by `category_name` (joining `categories`) instead of `category_id`. Arguably the *better* answer; still not gold's. |
| `date-01` | Read "order revenue" off `payments.amount` rather than `orders.total_amount`. |
| `join3-02`, `join3-03`, `join3-05` | Correct shape, differ at the `LIMIT` boundary / tie-breaking on a top-N. |
| `hard-03`, `hard-04` | `hard_ambiguous` by design — "month-over-month growth", "customers at risk of churning" have no single right answer. |

Only `filter-03` is unambiguously a model mistake. The rest are interpretation
differences on underspecified questions — which is itself the finding: at this
model size the failure mode is *reading the question differently*, not producing
broken SQL. **Zero cases produced invalid SQL, zero were rejected by the
validator, and zero hallucinated a table or column.**

## Harness integrity

`python evals/selftest.py` — all 6 grading paths correct, zero AI calls:

| Scenario | Expected | Actual |
|---|---|---|
| identical to gold | `pass` | `pass` |
| equivalent, different aliases | `pass` | `pass` |
| wrong data | `wrong_result` | `wrong_result` |
| hallucinated column | `sql_error` | `sql_error` |
| destructive statement (`DROP TABLE`) | `validator_rejected` | `validator_rejected` |
| empty result | `empty_result` | `empty_result` |

The grader was verified **before** the baseline was run, which is the order that
matters: a scoring bug found afterwards invalidates every number above it.

## Why the three earlier runs are void

| Run | Scored as | What the `detail` field actually says |
|---|---|---|
| `20260825T140340` | 0/2, `ai_timeout` ×2 | 2× "took too long" — genuine 120s timeouts |
| `20260825T155245` | 0/40, `ai_timeout` ×40 | **34× "ResourceExhausted"** + 6× "took too long" |
| `20260825T162646` | 0/1, `ai_rate_limited` ×1 | 1× "ResourceExhausted" |

All three carried the runner's `THIS RUN IS NOT A VALID BASELINE` banner. They
measure provider availability, not SQL quality. **Do not quote 0%.**

Note the second row: 34 of those 40 cases were **rate limits mislabelled as
timeouts**. The current classifier checks rate-limit markers before timeout
markers and maps that exact string to `ai_rate_limited` —

```python
>>> _ai_failure_reason("The AI service returned an error: ResourceExhausted.")
'ai_rate_limited'
```

— so the run must predate that fix. (No git history here to date it precisely.)
This is why the problem read as latency for hours: the harness said "the provider
is slow", so the response was to *raise* the timeout, when the provider was
actually saying "you are out of quota" and the fix was to change model.

**A wrong failure label sends you to the wrong fix.** The taxonomy in
`README.md` is load-bearing, not decoration.

### The retry doubled the burn rate

Every case in all three void runs shows `attempts: 2` — the transient-error retry
fired on all of them. Against a **20-request/day** cap, a 40-case run therefore
requested **80 calls**, exhausting a day's quota 4× over and guaranteeing that
every subsequent case failed too. The retry is correct policy for a flaky
provider and wrong for an exhausted quota: a per-day 429 is not transient, and
re-asking immediately (there is no backoff) cannot succeed. Worth gating the
retry on rate-limit errors, or honouring the `retry_delay` the API returns.

Both valid runs below show `attempts: 1` across every case.

The cause was not the API key. `GEMINI_MODEL=gemini-flash-latest` resolves to
`gemini-3.7-flash`, whose free tier allows **20 requests per day** — a 40-case
run cannot complete on it even once, and rotating the key does not help because
the quota is per *project*, not per key:

```
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests
limit: 20, model: gemini-3.7-flash
quota_id: GenerateRequestsPerDayPerProjectPerModel-FreeTier
```

Free-tier quota is **per model**, so `gemini-3.5-flash-lite` draws from its own
bucket and completed all 40 calls without a single rate-limit. Note that
`gemini-2.5-flash` and `gemini-2.5-flash-lite` now return 404 `no longer
available to new users` on this key.

## Reproducing

```bash
cd backend
python evals/selftest.py                                    # verify grader, 0 AI calls
GEMINI_MODEL=gemini-3.5-flash-lite python evals/runner.py   # 40 cases, ~7 min
python evals/analyze_failures.py evals/results/<run>.json    # split failures, 0 AI calls
```

`backend/.env` still ships `GEMINI_MODEL=gemini-flash-latest` for the API, where
a 20/day cap is survivable for interactive use. The eval overrides it per-run
rather than changing app config.

## Known limits of this baseline

Stated so the numbers are not over-read:

- **Single run, no variance.** Temperature is 0.1, not 0 — these are point
  estimates, not means. n=1.
- **40 cases on one schema.** Enough to rank tags, not enough for tight
  confidence intervals on any single tag (5–8 cases each).
- **One model.** No cross-model comparison; the 27.5/77.5 pair characterizes
  `gemini-3.5-flash-lite`, not the pipeline's ceiling.
- **Execution match's own blind spots** — order-insensitivity, coincidental
  agreement — are documented in `README.md` and apply here unchanged.
