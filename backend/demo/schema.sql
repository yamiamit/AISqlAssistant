-- =============================================================================
-- AI SQL Assistant — Live Demo Database
-- =============================================================================
-- Backs the "Try with sample data" button (POST /api/connections/demo). This
-- is a separate, larger dataset from database/schema.sql (the manual
-- getting-started sample) — sized so natural-language questions that filter,
-- aggregate, join across 2-3 tables, or reason over a date range all have
-- something non-trivial to return.
--
-- Relationships:
--   suppliers  1---* products *---1 categories
--   customers  1---* orders 1---* order_items *---1 products
--   orders     1---* payments
--   customers  1---* reviews *---1 products
-- =============================================================================

DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE categories (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL UNIQUE,
    description   TEXT
);

CREATE TABLE suppliers (
    supplier_id     SERIAL PRIMARY KEY,
    supplier_name   VARCHAR(120) NOT NULL,
    country         VARCHAR(60) NOT NULL,
    contact_email   VARCHAR(160),
    lead_time_days  INTEGER NOT NULL DEFAULT 7 CHECK (lead_time_days > 0)
);

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    first_name    VARCHAR(50)  NOT NULL,
    last_name     VARCHAR(50)  NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    phone         VARCHAR(20),
    city          VARCHAR(60),
    country       VARCHAR(60)  NOT NULL,
    signup_date   DATE NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE products (
    product_id     SERIAL PRIMARY KEY,
    product_name   VARCHAR(120) NOT NULL,
    category_id    INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    supplier_id    INTEGER REFERENCES suppliers(supplier_id) ON DELETE SET NULL,
    price          NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    cost           NUMERIC(10, 2) NOT NULL CHECK (cost >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    created_at     DATE NOT NULL
);

CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_date    DATE NOT NULL,
    shipped_date  DATE,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                  CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
    total_amount  NUMERIC(10, 2) NOT NULL DEFAULT 0
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id    INTEGER NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE payments (
    payment_id     SERIAL PRIMARY KEY,
    order_id       INTEGER NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_date   DATE NOT NULL,
    amount         NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(30) NOT NULL
                   CHECK (payment_method IN ('credit_card', 'debit_card', 'paypal', 'bank_transfer', 'upi')),
    status         VARCHAR(20) NOT NULL DEFAULT 'completed'
                   CHECK (status IN ('completed', 'failed', 'refunded', 'pending'))
);

CREATE TABLE reviews (
    review_id     SERIAL PRIMARY KEY,
    product_id    INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text   TEXT,
    review_date   DATE NOT NULL
);

-- Helpful indexes for the GROUP BY / JOIN shapes the AI is likely to generate
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_supplier_id ON products(supplier_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_customer_id ON reviews(customer_id);

-- Non-obvious columns, documented so both a human and the AI's schema prompt
-- (schema_introspector.py only surfaces name/type/nullable, not comments —
-- these are for anyone reading the SQL directly) understand them at a glance.
COMMENT ON COLUMN products.cost IS
    'Wholesale cost the store pays the supplier — distinct from price (what the customer pays). price - cost = gross margin per unit.';
COMMENT ON COLUMN suppliers.lead_time_days IS
    'Typical days between placing a restock order with this supplier and receiving it. Not tied to any one order.';
COMMENT ON COLUMN customers.is_active IS
    'False means the customer account is deactivated/closed, independent of order history — an inactive customer can still have past orders.';
COMMENT ON COLUMN orders.status IS
    'Lifecycle stage of the order: pending -> processing -> shipped -> delivered, or cancelled at any point before shipped.';
COMMENT ON COLUMN orders.shipped_date IS
    'NULL until the order reaches shipped/delivered status; always NULL for pending, processing, or cancelled orders.';
COMMENT ON COLUMN order_items.unit_price IS
    'Price per unit at the time the order was placed — copied from products.price then, so it stays correct even if the product price changes later.';
COMMENT ON COLUMN payments.status IS
    'completed = money captured; pending = awaiting settlement; failed = attempt did not go through; refunded = captured then returned.';
COMMENT ON COLUMN reviews.rating IS '1 (worst) to 5 (best), customer-submitted.';
