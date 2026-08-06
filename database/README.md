# Sample E-Commerce Database

A ready-to-load demo Postgres database so you can try the AI SQL Assistant without connecting your own data first.

## Schema

| Table | Description |
|---|---|
| `customers` | Registered shoppers |
| `categories` | Product categories |
| `products` | Items for sale, each belongs to a category |
| `orders` | One order per customer checkout |
| `order_items` | Line items linking orders to products (many-to-many) |
| `payments` | Payment attempts against an order |

Relationships: `orders.customer_id -> customers.customer_id`, `products.category_id -> categories.category_id`, `order_items.order_id -> orders.order_id`, `order_items.product_id -> products.product_id`, `payments.order_id -> orders.order_id`.

## Load it

### Option A — Neon (production target)

1. Create a free project at [neon.tech](https://neon.tech).
2. Grab the connection string from the Neon dashboard.
3. Run:
   ```bash
   psql "postgresql://<user>:<password>@<host>/<db>?sslmode=require" -f schema.sql
   psql "postgresql://<user>:<password>@<host>/<db>?sslmode=require" -f seed_data.sql
   ```

### Option B — Local Postgres (dev/testing)

```bash
createdb demo_ecommerce
psql -d demo_ecommerce -f schema.sql
psql -d demo_ecommerce -f seed_data.sql
```

Then use this database's host/port/name/username/password (or its connection string) on the **Connect Database** page in the app.

## Try these prompts once connected

- "Show the top 10 customers by total revenue"
- "What are the 5 best-selling products by quantity?"
- "Show monthly revenue for 2024"
- "Which orders are still pending?"
- "List customers who haven't placed an order in the last 90 days"
