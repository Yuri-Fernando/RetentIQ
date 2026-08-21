-- RetentIQ — Data Warehouse (esquema estrela) — versão Postgres
--
-- Equivalente ao schema criado automaticamente pelo ETL em SQLite
-- (data-platform/ingestion/extract_transform_load.py). Use este arquivo quando
-- rodar a stack completa via infra/docker/docker-compose.yml (serviço `postgres`).
--
-- Aplicar com:
--   psql -h localhost -U retentiq -d retentiq -f data-platform/warehouse/schema_postgres.sql

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id     INTEGER PRIMARY KEY,
    primary_country TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product (
    stock_code   TEXT PRIMARY KEY,
    description  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_country (
    country_id SERIAL PRIMARY KEY,
    country    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_id    INTEGER PRIMARY KEY,       -- formato YYYYMMDD
    date       DATE NOT NULL,
    year       INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    day        INTEGER NOT NULL,
    weekday    TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id      BIGINT PRIMARY KEY,
    invoice      TEXT NOT NULL,
    stock_code   TEXT NOT NULL REFERENCES dim_product(stock_code),
    customer_id  INTEGER NOT NULL REFERENCES dim_customer(customer_id),
    country_id   INTEGER NOT NULL REFERENCES dim_country(country_id),
    date_id      INTEGER NOT NULL REFERENCES dim_date(date_id),
    invoice_date TIMESTAMP NOT NULL,
    quantity     INTEGER NOT NULL,
    price        NUMERIC(12, 4) NOT NULL,
    revenue      NUMERIC(14, 4) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales_cancelled (
    cancel_id    BIGINT PRIMARY KEY,
    invoice      TEXT NOT NULL,
    stock_code   TEXT NOT NULL,
    customer_id  INTEGER NOT NULL,
    country_id   INTEGER,
    date_id      INTEGER NOT NULL,
    invoice_date TIMESTAMP NOT NULL,
    quantity     INTEGER NOT NULL,
    price        NUMERIC(12, 4) NOT NULL,
    revenue      NUMERIC(14, 4) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date     ON fact_sales(date_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product  ON fact_sales(stock_code);

-- View de apoio: KPIs de negócio prontos para o backend consumir (evita repetir
-- lógica de agregação em várias rotas da API).
CREATE OR REPLACE VIEW vw_customer_kpis AS
SELECT
    c.customer_id,
    c.primary_country,
    COUNT(DISTINCT f.invoice)      AS total_orders,
    SUM(f.revenue)                 AS total_revenue,
    MIN(f.invoice_date)            AS first_purchase,
    MAX(f.invoice_date)            AS last_purchase
FROM dim_customer c
JOIN fact_sales f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.primary_country;
