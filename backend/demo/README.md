# Live Demo Database

Backs the **"Try with sample data"** button on the Connect Database page
(`POST /api/connections/demo`) — a shared, read-only e-commerce dataset so a
visitor can start chatting immediately, with no credentials of their own.

This is a separate, larger dataset from [`database/`](../../database) (the
manual getting-started sample in the main README) — sized so filter,
aggregation, join, and date-range questions all have something non-trivial to
return. See [`schema.sql`](schema.sql) for the full 8-table schema and
column comments, and [`seed.sql`](seed.sql) for exactly how the data is
built (every value is a literal or a deterministic expression — no
`random()` anywhere, so re-running this against a fresh database always
produces byte-identical data).

| Table | Rows |
|---|---|
| `categories` | 8 |
| `suppliers` | 12 |
| `customers` | 200 |
| `products` | 80 |
| `orders` | 1,000 (spread 2023-01-01 – 2025-12-31) |
| `order_items` | ~2,500 |
| `payments` | 1,000 |
| `reviews` | ~360 (covers all 80 products) |

## Load it into a fresh Neon database

1. Create a **second** Neon project (or a second database in an existing
   project) — keep this separate from `APP_DATABASE_URL`, since this is data
   every visitor's demo connection points at, not the app's own metadata.
2. Copy its connection string from the Neon dashboard.
3. Run, in order (`seed.sql` depends on the tables `schema.sql` creates):
   ```bash
   psql "postgresql://<user>:<password>@<host>/<db>?sslmode=require" -f backend/demo/schema.sql
   psql "postgresql://<user>:<password>@<host>/<db>?sslmode=require" -f backend/demo/seed.sql
   ```
4. Set `DEMO_DATABASE_URL` on the backend to that same connection string (see
   `backend/.env.example`) and restart/redeploy the backend.

Re-running step 3 against the same database is safe and idempotent —
`schema.sql` starts with `DROP TABLE ... CASCADE` for all 8 tables, so it
always rebuilds from empty.

## Local Postgres (dev/testing)

```bash
createdb ai_sql_assistant_demo
psql -d ai_sql_assistant_demo -f backend/demo/schema.sql
psql -d ai_sql_assistant_demo -f backend/demo/seed.sql
```

Then point `DEMO_DATABASE_URL` at it, e.g.
`postgresql://postgres:postgres@localhost:5432/ai_sql_assistant_demo`.

## How it's wired up

`POST /api/connections/demo` parses `DEMO_DATABASE_URL` and inserts a normal
`DBConnection` row for the current user with `is_demo=True` — it goes through
the exact same `target_db.py` / `schema_introspector.py` / `sql_executor.py`
path as any user-supplied connection. `is_demo` only gates two things at the
API layer: `PUT`/`DELETE` on that connection are rejected (403), and the
frontend shows example-question chips instead of connection details. The
underlying SQL safety model (`sql_validator.py`'s SELECT/WITH allow-list,
read-only transaction, forced `LIMIT`) already makes every connection
read-only regardless of this flag — `is_demo` protects the *connection
row*, not the query path.

## Try these prompts once connected

These are the same 5 prompts shown as clickable chips in the chat view when
the active connection is the demo (`frontend/src/components/chat/ExampleQuestionChips.tsx`) — picked to exercise different query shapes:

- "Which orders are still pending?" — simple filter
- "What's the average order value by year?" — aggregation
- "Show the top 10 customers by total amount spent" — 2-table join
- "Which product categories have generated the most revenue?" — 3-table join
- "Show monthly revenue for 2024" — date-range aggregation
