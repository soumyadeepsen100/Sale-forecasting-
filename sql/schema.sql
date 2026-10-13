-- Normalized schema (3NF) for the Superstore Furniture data
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS locations;

CREATE TABLE customers (
    customer_id   TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    segment       TEXT NOT NULL
);

CREATE TABLE locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    city        TEXT NOT NULL,
    state       TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    region      TEXT NOT NULL,
    UNIQUE (city, state, postal_code)
);

CREATE TABLE products (
    product_id   TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    sub_category TEXT NOT NULL
);

CREATE TABLE orders (
    order_id    TEXT PRIMARY KEY,
    order_date  DATE NOT NULL,          -- stored as YYYY-MM-DD
    ship_date   DATE NOT NULL,
    ship_mode   TEXT NOT NULL,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    location_id INTEGER NOT NULL REFERENCES locations(location_id)
);

CREATE TABLE order_items (
    row_id     INTEGER PRIMARY KEY,
    order_id   TEXT NOT NULL REFERENCES orders(order_id),
    product_id TEXT NOT NULL REFERENCES products(product_id),
    sales      REAL NOT NULL,
    quantity   INTEGER NOT NULL,
    discount   REAL NOT NULL,
    profit     REAL NOT NULL
);

CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_items_order ON order_items(order_id);
