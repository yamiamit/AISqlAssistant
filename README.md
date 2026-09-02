# AI SQL Assistant

Ask your PostgreSQL database questions in plain English. Connect your own database, get AI-generated SQL you can trust (validated, read-only, explained), see results as tables and charts, and keep a full history of every conversation.

Built as a full-stack portfolio project to demonstrate practical AI integration, backend/database engineering, authentication, and secure SQL execution — deliberately scoped to stay understandable end-to-end rather than reaching for infrastructure it doesn't need.

## Features

- **Auth** — register/login with JWT, bcrypt-hashed passwords, each user's data (connections, chats, saved queries) fully isolated.
- **Bring your own database** — connect any PostgreSQL database by host/port/credentials or a connection string; schema (tables, columns, primary keys, foreign keys) is discovered automatically and cached — filtered to the tables the connecting role can actually `SELECT`, so a restricted role yields a restricted schema.
- **Natural language → SQL** — every prompt is turned into SQL grounded in your actual schema, explained in plain English, and shown with copy/collapse controls.
- **Secure SQL execution** — an allow-list validator permits only `SELECT`/`WITH` queries, blocks stacked statements and a keyword blocklist (`INSERT`, `DROP`, `pg_sleep`, ...), and forces a row `LIMIT`; execution itself runs inside a read-only transaction with a hard statement timeout.
- **Scoped access** — those layers control what *kind* of query runs, never what data it touches. Tick the tables a connection should expose (with warnings when you'd sever a foreign key the AI needs for joins) and the app generates the `CREATE ROLE`/`GRANT` script for you to run yourself; paste the new connection string back and the boundary holds end to end — introspection hides the rest, the AI is never shown them, and a query that reaches one is refused by Postgres. Connections that can still write are detected and flagged.
- **Results, charts, exports** — a result table plus an auto-suggested bar/line/pie chart (switchable), with CSV, PNG, and formatted-PDF-report export.
- **Chat history & saved queries** — every turn (prompt, SQL, explanation, results, chart, timestamp) is persisted; search and delete conversations, or bookmark a query to re-run later.
- **Schema Viewer** — a dedicated page listing every table's columns, primary keys, and foreign keys.
- **Polished UX** — responsive SaaS-style dashboard, dark mode, loading states, and a typing indicator while the AI responds.

## Live demo

Click **"Try with sample data"** on the Connect Database page to start chatting instantly, without connecting your own Postgres database. It attaches a shared, read-only e-commerce dataset (200 customers, 80 products, 1,000 orders across 2023–2025) to your account and drops you straight into chat with 5 example questions to try. See [`backend/demo/README.md`](backend/demo/README.md) for the dataset itself and how to stand it up.

## Screenshots

| Chat | Schema Viewer |
|---|---|
| ![Chat](docs/screenshots/chat.jpg) | ![Schema Viewer](docs/screenshots/schema-viewer.jpg) |

| Database Connections | Register (light mode) |
|---|---|
| ![Database Connections](docs/screenshots/database-connection.jpg) | ![Register](docs/screenshots/register-light.jpg) |

## Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router, Recharts |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL (Neon in production) |
| Auth | JWT (PyJWT) + bcrypt (passlib) |
| AI | Groq (`openai/gpt-oss-120b`, JSON-mode); Gemini selectable via `AI_PROVIDER` |
| PDF | ReportLab + Matplotlib (report generation) |
| Deployment | Vercel (frontend), Render (backend), Neon (database) |

No Docker, Kubernetes, microservices, Kafka, or Redis — this is a standard three-tier app, kept intentionally simple to build in 2-3 weeks and explain confidently in an interview. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system diagram and the reasoning behind it.

## Folder Structure

```
AISqlAssistant/
  frontend/     React + TypeScript + Vite + Tailwind
    src/
      api/           axios client + one module per resource
      context/        Auth, Theme, Connection (React Context, no Redux)
      pages/          one file per route
      components/     grouped by feature (chat, connections, schema, savedQueries, common)
  backend/      FastAPI + SQLAlchemy
    app/
      models/         SQLAlchemy ORM models
      schemas/        Pydantic request/response models
      core/           security (hashing, JWT) + shared dependencies
      services/       AI, SQL validation/execution, schema discovery, encryption, export
      utils/          prompt templates + the chart-suggestion heuristic
      api/routes/      one router per resource
    demo/          shared read-only dataset behind "Try with sample data"
    evals/         offline text-to-SQL eval harness (dev-time only, not imported by app/)
    tests/         pytest suite — hermetic by default; the grant tests skip without TEST_DATABASE_URL
  database/     sample e-commerce schema + seed data + load instructions
  docs/         architecture diagram, API reference, deployment guide, screenshots
```

## Architecture

```mermaid
flowchart LR
    FE["React SPA"] -- "JWT" --> API["FastAPI backend"]
    API --> AppDB[("App DB (Neon)")]
    API -- "dynamic, per-connection" --> TargetDB[("Your Postgres DB")]
    API --> AI["AI provider<br/>Groq (default) or Gemini<br/>via ai_service.py"]
```

The backend maintains its own metadata database (users, connections, chats, saved queries) separately from the arbitrary external databases users connect to — those are reached through short-lived, per-request connections built from encrypted stored credentials.

The AI provider sits behind a single module (`services/ai_service.py`): every call goes through one `_chat_json()` choke point, so switching providers is a one-file change and `AI_PROVIDER` selects between them at startup. Full write-up: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Endpoint reference: [`docs/API.md`](docs/API.md).

## Evaluation

Natural-language → SQL is the part of this app most likely to be wrong in ways that
*look* right, so it is measured rather than asserted. [`backend/evals/`](backend/evals/README.md)
is an offline harness that runs 40 hand-written questions through the real pipeline
and grades them by **execution match**: both the generated SQL and a hand-written
gold query are executed against the demo database and their rows compared. Any
correct spelling of a correct query therefore counts as correct — aliases, join
order, `WHERE` vs `HAVING`, and CTE vs subquery are not penalised, because "did the
user get the right numbers?" is the only property worth scoring.

### Benchmark

Two models, same 40 cases, same grader, 0 provider failures on both runs — full
detail in [`BASELINE.md`](backend/evals/BASELINE.md):

| Metric | Gemini 3.5-flash-lite | Groq `gpt-oss-120b` | What it answers |
|---|---|---|---|
| Strict execution match | 27.5% (11/40) | **40.0%** (16/40) | Does the result set match the reference query *exactly*, column count included? |
| Right rows, extra columns | 50.0% (20/40) | 37.5% (15/40) | Correct answer, wider `SELECT`. |
| **Answer-correct** | **77.5%** (31/40) | **77.5%** (31/40) | **Did the user get the right rows back?** |
| Genuinely wrong answer | 22.5% (9/40) | 22.5% (9/40) | Wrong data, not just a wider `SELECT`. |
| Invalid / rejected / hallucinated SQL | **0%** (0/40) | **0%** (0/40) | Every case produced valid SQL the validator accepted and Postgres ran. |

Per tag, by answer-correct:

| Tag | Cases | Gemini | Groq | What it probes |
|---|---|---|---|---|
| `two_table_join` | 8 | 100% | 100% | One join |
| `aggregation` | 8 | 75% | **100%** | `GROUP BY`, `COUNT`/`SUM`/`AVG` |
| `date_reasoning` | 5 | 80% | **100%** | Year/quarter/month bucketing |
| `single_table_filter` | 8 | 88% | 75% | One table, a `WHERE` clause |
| `multi_table_join` | 6 | 50% | **67%** | Three or more tables |
| `hard_ambiguous` | 5 | 60% | 0% † | Deliberately underspecified — *expected to fail* |
| **Overall** | **40** | **77.5%** | **77.5%** | |

† 2 of these 5 are a harness defect, not a model failure — see the caveats below.

Beyond accuracy, the two providers differ in ways that decide which is actually
usable:

| | Gemini 3.5-flash-lite | Groq `gpt-oss-120b` |
|---|---|---|
| Latency per call | ~4.2s | **~1.3s** |
| Free-tier limit | 20 requests **/day** on some models | 1000 requests/day, 8000 tokens/**minute** |
| Can a 40-case run finish? | **No** — quota dies first | Yes, ~6 min with pacing |

### What the comparison shows

**Both models land on exactly 77.5% answer-correct, and on exactly 9 genuinely
wrong — from completely different cases.** That coincidence is the most useful
result in the table:

- **The headline number is not where the improvement is.** Answer-correct did not
  move at all. The +12.5 points of strict match are largely Groq picking narrower
  projections that happened to match gold more often — style, not skill.
- **The real quality win is one case the score barely registers.** `filter-03`,
  *"which products cost more than 100 dollars?"*, is the only genuinely dangerous
  answer either model produced: Gemini filtered wholesale `cost` instead of retail
  `price` and returned **2 products instead of 7** — a user would believe that was
  the whole list. Groq gets it right. One case in a 40-case benchmark, worth more
  than the twelve points.
- **Capability matters, up to a point.** The larger model fixed the known weak
  spot — `multi_table_join` 50% → 67% — and took `aggregation` and
  `date_reasoning` to 100%. Difficulty does track join depth.
- **But capability is not the ceiling.** A substantially larger model moved cases
  around without moving the total at all: what it gained on joins and aggregation
  it gave back on `single_table_filter` and `hard_ambiguous`.
- **Zero invalid SQL on either model.** No syntax errors, no hallucinated tables
  or columns, nothing caught by the validator, across 80 generations. The failure
  mode at both model sizes is *reading the question differently*, not writing
  broken SQL.

Two caveats on the numbers above, both found while investigating them:

- **`hard_ambiguous` 0% overstates the drop.** 2 of those 5 (`hard-01`, `hard-02`)
  are a harness defect, not a model failure: the prompt rule says *"do NOT invent a
  top-N cutoff"*, the questions ("who are our best customers?") name no number, and
  the gold queries end in `LIMIT 10` anyway. The model is marked wrong for obeying
  its instructions.
- **The over-selection gap is not fixable in the prompt.** Tested directly: adding
  an explicit "select the minimum columns" rule *and* narrowing the few-shot
  example left strict match at exactly 16/40, but dropped answer-correct from
  **77.5% → 45.0%** — the model began under-selecting, and a missing column is
  unrecoverable where an extra one is not. Gold itself is inconsistent (it wants
  `product_name` for products, all five name/contact fields for customers, and no
  name at all for top-10-customers), so there is no rule that satisfies all three.
  Over-selection is the safer failure mode; it was left alone deliberately.

### Why two numbers

Either one alone misleads. The gap between strict and answer-correct is a single
behaviour, not twenty separate bugs — asked "which orders are still pending?",
the model returns the right 100 rows *plus* `status` and `shipped_date`, which
the gold query does not select. The rows are right; the projection is wider.

Strict match stays the primary metric because loosening it invites false passes;
[`analyze_failures.py`](backend/evals/analyze_failures.py) splits the two apart
afterwards without spending an AI call. Note that strict match is also the far
more model-sensitive number (27.5% → 40.0% between models, versus no change in
answer-correct), because it partly measures projection *style*.

⚠️ **n=1 per model.** Temperature is 0.1, not 0, and repeat Gemini runs vary by
about ±2.5%. Treat 77.5% ≈ 77.5% as *indistinguishable*, not identical.

### Reproducing

```bash
cd backend
python evals/selftest.py                                    # verify the grader itself, 0 AI calls
python evals/runner.py                                      # 40 cases on Groq, ~6 min
python evals/analyze_failures.py evals/results/<run>.json   # split the failures, 0 AI calls

# the Gemini column, for comparison:
AI_PROVIDER=gemini GEMINI_MODEL=gemini-3.5-flash-lite python evals/runner.py
```

Groq's free tier caps **tokens per minute** (8000) rather than requests per day,
and one case costs ~1040 tokens — so the runner paces itself to one AI call every
8.5s and backs off a full window on a 429. Unthrottled, a 40-case run spends the
minute's budget in seconds and voids itself. Override with
`EVAL_MIN_CALL_INTERVAL_SECONDS=0` on a paid key.

The grader has its own test (`selftest.py`, zero AI calls) that was run *before* the
baseline — a scoring bug found afterwards would invalidate every number above it.
The runner also refuses to be quoted when the provider is unavailable: if more than
20% of a run fails on timeouts or quota, it prints `THIS RUN IS NOT A VALID
BASELINE`, so "out of quota" can never be mistaken for "the model scored 0%".
Grading rules, known blind spots, and the failure taxonomy are in
[`backend/evals/README.md`](backend/evals/README.md).

## Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- A PostgreSQL database (local install, Docker, or a free [Neon](https://neon.tech) project) — you need **two**: one for the app's own data, one to use as the "connected" target database (or reuse the [sample e-commerce database](database/README.md))
- A [Groq API key](https://console.groq.com/keys) (only required for AI SQL generation — everything else works without one). Groq is the default because its free tier allows enough requests per day to run the eval harness repeatedly; set `AI_PROVIDER=gemini` with a [Gemini key](https://aistudio.google.com/app/apikey) to use Gemini instead.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in APP_DATABASE_URL, JWT_SECRET_KEY, ENCRYPTION_KEY, GROQ_API_KEY, etc.
                       # the app refuses to start on a placeholder secret — see app/config.py
uvicorn app.main:app --reload
```

Tables are created automatically on startup. API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

App available at `http://localhost:5173`.

### Sample database (optional but recommended)

```bash
createdb demo_ecommerce
psql -d demo_ecommerce -f database/schema.sql
psql -d demo_ecommerce -f database/seed_data.sql
```

Then connect to it from the app's "Connect Database" page. See [`database/README.md`](database/README.md) for Neon instructions and example prompts to try.

### Running the tests

`pytest` is installed by `backend/requirements.txt`:

```bash
cd backend
python -m pytest tests -q     # 114 hermetic cases; the 8 grant tests skip

# to run the grant integration tests too, against a throwaway database:
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/scratch \
  python -m pytest tests -q
```

## Environment Variables

**Backend** (`backend/.env`, see `backend/.env.example`):

| Variable | Purpose |
|---|---|
| `APP_DATABASE_URL` | Postgres connection string for the app's own data |
| `JWT_SECRET_KEY` | Signs auth tokens |
| `ENCRYPTION_KEY` | Fernet key encrypting stored target-DB passwords at rest |
| `AI_PROVIDER` | `groq` (default) or `gemini` |
| `GROQ_API_KEY` / `GROQ_MODEL` | Groq config — used when `AI_PROVIDER=groq` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Gemini config — used when `AI_PROVIDER=gemini` |
| `SQL_STATEMENT_TIMEOUT_MS` / `SQL_DEFAULT_ROW_LIMIT` | SQL execution safety limits |
| `CORS_ORIGINS` | Allowed frontend origin(s) |
| `DEMO_DATABASE_URL` | Backs the "Try with sample data" button — see [`backend/demo/README.md`](backend/demo/README.md). Leave empty to disable it. |

**Frontend** (`frontend/.env`, see `frontend/.env.example`):

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend API base URL |

## Deployment

Frontend → Vercel, backend → Render, app database → Neon. Config files (`frontend/vercel.json`, `backend/render.yaml`) are already in the repo — full step-by-step in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Code Quality

- **Clean architecture**: routes stay thin — all business logic (SQL validation, AI calls, schema discovery, exports) lives in single-purpose `services/` modules that are independently testable and independently explainable.
- **Security by construction**: passwords bcrypt-hashed; target-DB credentials Fernet-encrypted at rest; SQL allow-listed, forced-`LIMIT`, read-only-transaction, and statement-timeout as layered defenses.
- **Typed end-to-end**: Pydantic schemas on the backend, TypeScript interfaces on the frontend mirroring them.
- **Every failure mode has a home**: invalid SQL, empty results, bad credentials, AI timeouts, and an offline database each produce a specific, human-readable message instead of a generic error.
- **The AI step is measured, not assumed**: a 40-case execution-match eval harness with a tested grader, two models benchmarked side by side, and honestly stated blind spots — see [Evaluation](#evaluation).
- **The security-critical modules are unit-tested**: 114 hermetic pytest cases — no database, no network — over `sql_validator` (stacked statements, data-modifying CTEs, keyword-in-literal false positives, the outer-vs-subquery row cap) and the scoped-access helpers (`access_script`, the foreign-key pruning in `schema_introspector`, the `42501` translation in `sql_executor`) — plus tests that pin each module's *documented* limitations, so a future change can't widen them silently. Eight further integration tests assert what Postgres itself does about grants, and skip unless `TEST_DATABASE_URL` points at a throwaway database (`backend/tests/`).

## Future Improvements

- Refresh tokens / server-side session invalidation (current auth is stateless JWT — simple, but "logout" only clears the client-side token)
- Streaming AI responses instead of a single request/response round trip
- Multi-database "join across connections" queries
- Extend the test suite to the remaining services (AI, export, schema discovery) — `sql_validator` and the scoped-access helpers are covered today — plus Vitest/RTL for frontend components
- Harden the baseline: repeat runs for variance (currently n=1 per model), order-aware grading for top-N questions, and more cases per tag

## Interview Talking Points

This project is designed so each of these is a two-minute answer, not a slide:

- **Auth flow** — registration → bcrypt hash → JWT issuance → Bearer-token verification on every request (`core/security.py`, `core/deps.py`)
- **Dynamic database connections** — why the app maintains two separate Postgres roles (its own metadata DB vs. arbitrary target DBs) and how credentials are encrypted at rest and decrypted only to open a short-lived connection (`services/target_db.py`, `services/encryption.py`)
- **Schema discovery** — `SQLAlchemy.inspect()` for columns and constraints, but one hand-written catalog query for the table list: `pg_catalog.pg_class` is world-readable, so reflecting as a restricted role still returns every table unless you filter on `has_table_privilege()` (`services/schema_introspector.py`)
- **Prompt engineering** — how the schema gets serialized into the AI prompt, why JSON-mode + a few-shot example keeps output parseable (`utils/prompt_templates.py`)
- **SQL validation** — the layered defense between "AI-generated text" and "SQL that actually runs", and why the app layer can only ever police the *shape* of a query while table-level access has to come from Postgres grants (`services/sql_validator.py`, `services/sql_executor.py`)
- **Chart selection** — a small rule-based heuristic instead of another AI call (`utils/chart_suggester.py`) — a deliberate simplicity trade-off
- **Evaluating the AI** — why execution match beats string comparison, why the benchmark reports strict *and* answer-correct rather than one number, and what it means that two very different models both land on 77.5% answer-correct from different cases (`backend/evals/`)
- **Reading a benchmark honestly** — why a run can be *void* rather than bad (the `NOT A VALID BASELINE` guard), why a rate limit mislabelled as a timeout sent hours of debugging at the wrong fix, and why the harness paces itself against a tokens-per-minute cap
