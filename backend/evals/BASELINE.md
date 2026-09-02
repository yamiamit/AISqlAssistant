# Text-to-SQL Eval Baseline

First valid baseline for the natural-language → SQL pipeline, graded by
**execution match** against the demo database.

> **Re-graded after a gold-query fix.** `hard-01` and `hard-02` had gold queries
> ending in `LIMIT 10` while the system prompt forbids inventing a top-N cutoff,
> so the harness scored the model that obeyed as wrong. Both runs below were
> re-graded from their stored `generated_sql` at zero AI calls. Strict match is
> unchanged (11/40, 16/40); answer-correct moved **Gemini 77.5% → 75.0%** and
> **Groq 77.5% → 82.5%**. See [The gold-query correction](#the-gold-query-correction).

| | |
|---|---|
| **Run** | `evals/results/20260826T192000.json` |
| **Date** | 2026-08-25 |
| **Model** | `gemini-3.5-flash-lite` (temperature 0.1, JSON mode) |
| **Cases** | 40, across 6 tags |
| **Grader** | execution match — order-insensitive, column-names ignored, numbers to 2dp |
| **Provider failures** | 0/40 — **this run is a valid baseline** |
| **Wall clock** | ~7 min, 4 workers, 40 AI calls, 0 retries |

## Headline numbers

```
exact execution match (runner PASS)    11 / 40    27.5%
right rows, extra columns              19 / 40    47.5%
genuinely wrong answer                 10 / 40    25.0%
never produced runnable SQL             0 / 40     0.0%
---------------------------------------------------------
ANSWER-CORRECT (exact + over-selected) 30 / 40    75.0%
```

Two numbers, because they measure different things and only quoting one of them
is misleading:

- **27.5% strict execution match** is what `runner.py` prints. A case passes only
  if the result set matches gold exactly — column *count* included.
- **75.0% answer-correct** additionally counts cases where the model returned
  **exactly the right rows** but selected extra columns. Reproduce with
  `python evals/analyze_failures.py evals/results/<run>.json` (zero AI calls).

The gap between them is one behaviour, not twenty different bugs: the model
answers "which orders are still pending?" with the right 100 rows but also
returns `status` and `shipped_date`, which gold does not select. The rows are
right; the projection is wider. 20 of the 29 failures are exactly this.

Both numbers are honest. Which to quote depends on the question being asked:
*"does the generated query match a reference query?"* → 27.5%.
*"did the user get the right data back?"* → 75.0%.

## Second model: `openai/gpt-oss-120b` (Groq), 2026-08-28

Run `evals/results/20260828T194837.json` — 40 cases, 0 provider failures, ~6 min,
4 workers paced to one AI call / 8.5s. **This is a valid run.**

```
exact execution match (runner PASS)    16 / 40    40.0%
right rows, extra columns              17 / 40    42.5%
genuinely wrong answer                  7 / 40    17.5%
never produced runnable SQL             0 / 40     0.0%
---------------------------------------------------------
ANSWER-CORRECT (exact + over-selected) 33 / 40    82.5%
```

**Groq leads by 7.5 points on answer-correct (82.5% vs 75.0%) and by 12.5 on
strict match.**

| Tag | Gemini 3.5-flash-lite | Groq gpt-oss-120b |
|---|---|---|
| `aggregation` | 75% | **100%** |
| `date_reasoning` | 80% | **100%** |
| `two_table_join` | 100% | 100% |
| `multi_table_join` | 67% | 67% |
| `single_table_filter` | 88% | 75% |
| `hard_ambiguous` | 20% | **40%** |
| **overall answer-correct** | **75.0%** | **82.5%** |

What the comparison settles:

- **Capability moves the total.** `aggregation`, `date_reasoning` and
  `two_table_join` all reach 100% on the larger model, and it leads answer-correct
  by 7.5 points. Join depth does track difficulty, as suspected.
- **`multi_table_join` is the shared ceiling.** Both models sit at 67% — the only
  tag the larger model does not improve.
- **`hard_ambiguous` is still doing its job.** Even with gold corrected, both
  models trail badly there (20% / 40%). `hard-03`, `hard-04` and `hard-05` have no
  single right answer, which is the entire point of the tag.
- **Strict match is the more model-sensitive metric** (27.5% → 40.0%) because it
  partly measures projection style, which differs sharply between models.

Caveat: n=1 per model, the Gemini pair alone varies ±2.5% run to run (see below),
and tie-broken top-N cases like `join3-03` add roughly ±1 case. The 7.5-point gap
is wider than that noise, but it rests on one run per model — a direction, not a
measurement.

## Per-tag breakdown

| Tag | exact | +cols | wrong | total | answer-correct |
|---|---|---|---|---|---|
| `two_table_join` | 3 | 5 | 0 | 8 | **100%** |
| `single_table_filter` | 0 | 7 | 1 | 8 | **88%** |
| `date_reasoning` | 2 | 2 | 1 | 5 | **80%** |
| `aggregation` | 5 | 1 | 2 | 8 | **75%** |
| `multi_table_join` | 1 | 3 | 2 | 6 | **67%** |
| `hard_ambiguous` | 0 | 1 | 4 | 5 | **20%** |

`single_table_filter` scores **0% strict / 88% answer-correct** — the single
clearest illustration of why the strict number alone misleads. Every one of those
8 questions ("list all customers based in India") names a filter but never says
which columns to show, so the model's choice of projection is guesswork against
a gold query that made one specific choice.

`multi_table_join` is the genuine weak spot: 3 of 6 wrong on the answer itself,
not the projection. Difficulty tracks join depth, which is the expected shape.

`hard_ambiguous` scoring 0% strict is **an expected result, not a regression** —
the tag exists to mark the ceiling. Its answer-correct number fell from 60% to 20%
when the invented `LIMIT 10` was removed from gold; see
[The gold-query correction](#the-gold-query-correction).

## The 10 genuinely wrong cases (Gemini)

Worth reading individually, because they are not all the same kind of error:

| Case | What happened |
|---|---|
| `filter-03` | **Real error.** "Products that cost more than 100 dollars" → filtered on `cost > 100` instead of `price > 100`. Read the wholesale-cost column as the customer-facing price. |
| `agg-04` | Added an unasked `WHERE status = 'completed'` to payments — defensible reading, different answer. |
| `agg-06` | Grouped by `category_name` (joining `categories`) instead of `category_id`. Arguably the *better* answer; still not gold's. |
| `date-01` | Read "order revenue" off `payments.amount` rather than `orders.total_amount`. |
| `join3-02`, `join3-05` | Correct shape, differ at the `LIMIT` boundary / tie-breaking on a top-N. (`join3-03` is the same shape but grades either way between executions — it is the ±1 of run-to-run noise.) |
| `hard-01`, `hard-02` | Answered the *un*cut question ("best customers", "underperforming products") with 10 rows where corrected gold returns all of them — Gemini invented the top-N cutoff the prompt forbids. |
| `hard-03`, `hard-04` | `hard_ambiguous` by design — "month-over-month growth", "customers at risk of churning" have no single right answer. |

Only `filter-03` is unambiguously a model mistake. The rest are interpretation
differences on underspecified questions — which is itself the finding: at this
model size the failure mode is *reading the question differently*, not producing
broken SQL. **Zero cases produced invalid SQL, zero were rejected by the
validator, and zero hallucinated a table or column.**

## The gold-query correction

Found while investigating why `hard_ambiguous` collapsed to 0% on Groq.

`hard-01` ("Who are our best customers?") and `hard-02` ("Which products are
underperforming?") name no cutoff, and the system prompt is explicit:

> Do NOT invent a top-N cutoff. Only add `LIMIT n` / `ORDER BY ... LIMIT n` for
> ranking when the question actually asks for one ("top 10", "best 5").

Both gold queries nevertheless ended in `LIMIT 10`. **Gold contradicted the rule
the model was graded against.** The effect was asymmetric, which is why it went
unnoticed for a whole model comparison:

| | hard-01 | hard-02 | Effect |
|---|---|---|---|
| Groq (obeyed the rule) | returned all 190 | returned all 80 | marked **wrong** |
| Gemini (invented a cutoff) | returned 10 | returned 50 | marked **right** |

The harness was rewarding the model that ignored its instructions and penalising
the one that followed them — and that, not model quality, produced the striking
"both models score exactly 77.5%" result in the first version of this document.

The fix removes the two invented `LIMIT`s from `cases.json`. Both runs were then
re-graded from their stored `generated_sql`, so the corrected numbers cost **zero
AI calls**:

| | strict (before → after) | answer-correct (before → after) |
|---|---|---|
| Gemini | 11/40 → **11/40** | 31/40 → **30/40** (77.5% → 75.0%) |
| Groq | 16/40 → **16/40** | 31/40 → **33/40** (77.5% → 82.5%) |

Strict match is unchanged for both, because neither case was ever an exact match.
That the re-grade reproduces both recorded strict counts exactly is the check that
makes the new answer-correct numbers quotable — a re-grade that could not
reproduce them would be measuring its own bugs.

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
- **Two models, one run each.** The 27.5/75.0 pair characterizes
  `gemini-3.5-flash-lite` and 40.0/82.5 characterizes `gpt-oss-120b` — neither is
  the pipeline's ceiling, and neither has a variance estimate.
- **Tie-broken top-N cases grade either way.** `join3-03` flips between
  executions; budget ±1 case on any answer-correct total.
- **Execution match's own blind spots** — order-insensitivity, coincidental
  agreement — are documented in `README.md` and apply here unchanged.
