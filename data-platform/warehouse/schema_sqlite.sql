-- RetentIQ — Data Warehouse (esquema estrela) — modelo FÍSICO SQLite
--
-- Fonte da verdade do warehouse local criado pelo ETL
-- (data-platform/ingestion/extract_transform_load.py). Até a v2.1.0 o ETL criava
-- as tabelas via pandas.to_sql(if_exists="replace"), o que produzia tabelas SEM
-- PK, FK, NOT NULL, CHECK e SEM a view vw_customer_kpis — divergindo do DDL
-- PostgreSQL declarado em schema_postgres.sql (ver
-- docs/data-governance/schema-diff.md, seção "Baseline v2.1.0").
--
-- Decisões de compatibilidade:
--   * nomes de tabelas/colunas e tipos declarados (INTEGER/TEXT/REAL/TIMESTAMP)
--     são os mesmos que o pandas gerava, para não mudar o que a API
--     (apps/api/src/lib/db.ts) e os scripts de ML leem;
--   * só foram ADICIONADAS restrições que os dados reais já satisfazem
--     (verificado sobre o Online Retail II completo, 793.609 vendas);
--   * fact_sales_cancelled NÃO tem FK para dim_customer/dim_product: nos dados
--     reais 129 cancelamentos têm cliente e 37 têm produto que nunca aparecem em
--     vendas válidas (as dimensões são derivadas das vendas). Mesma decisão do DDL
--     PostgreSQL. A órfandade é monitorada por check de qualidade (warning).
--   * SQLite não tem tipo decimal exato: price/revenue ficam REAL (IEEE-754). O
--     PostgreSQL usa NUMERIC(12,4)/NUMERIC(14,4). Ver physical-model.md.
--
-- Este arquivo é aplicado pelo ETL a cada carga completa (DROP + CREATE).

PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS vw_customer_kpis;
DROP TABLE IF EXISTS etl_load_audit;
DROP TABLE IF EXISTS fact_sales_cancelled;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_country;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;

CREATE TABLE dim_customer (
    customer_id     INTEGER NOT NULL PRIMARY KEY CHECK (customer_id > 0),
    primary_country TEXT    NOT NULL
);

CREATE TABLE dim_product (
    stock_code  TEXT NOT NULL PRIMARY KEY CHECK (LENGTH(stock_code) > 0),
    description TEXT NOT NULL
);

CREATE TABLE dim_country (
    country_id INTEGER NOT NULL PRIMARY KEY,
    country    TEXT    NOT NULL UNIQUE
);

CREATE TABLE dim_date (
    date       TIMESTAMP NOT NULL,
    date_id    INTEGER   NOT NULL PRIMARY KEY CHECK (date_id BETWEEN 19000101 AND 29991231),
    year       INTEGER   NOT NULL,
    month      INTEGER   NOT NULL CHECK (month BETWEEN 1 AND 12),
    day        INTEGER   NOT NULL CHECK (day BETWEEN 1 AND 31),
    weekday    TEXT      NOT NULL,
    is_weekend INTEGER   NOT NULL CHECK (is_weekend IN (0, 1))
);

-- Grão: 1 linha = 1 linha de nota fiscal (invoice line) de venda válida.
-- Não há chave natural confiável na origem (o mesmo invoice+stock_code+price
-- aparece em linhas distintas), por isso sale_id é chave substituta.
CREATE TABLE fact_sales (
    sale_id      INTEGER   NOT NULL PRIMARY KEY,
    invoice      TEXT      NOT NULL,
    stock_code   TEXT      NOT NULL REFERENCES dim_product (stock_code),
    customer_id  INTEGER   NOT NULL REFERENCES dim_customer (customer_id),
    country_id   INTEGER   NOT NULL REFERENCES dim_country (country_id),
    date_id      INTEGER   NOT NULL REFERENCES dim_date (date_id),
    invoice_date TIMESTAMP NOT NULL,
    quantity     INTEGER   NOT NULL CHECK (quantity > 0),
    price        REAL      NOT NULL CHECK (price > 0),
    revenue      REAL      NOT NULL CHECK (revenue >= 0)
);

-- Grão: 1 linha = 1 linha de nota de cancelamento/devolução (invoice 'C...').
CREATE TABLE fact_sales_cancelled (
    cancel_id    INTEGER   NOT NULL PRIMARY KEY,
    invoice      TEXT      NOT NULL CHECK (SUBSTR(invoice, 1, 1) = 'C'),
    stock_code   TEXT      NOT NULL,
    customer_id  INTEGER   NOT NULL,
    country_id   INTEGER,
    date_id      INTEGER   NOT NULL,
    invoice_date TIMESTAMP NOT NULL,
    quantity     INTEGER   NOT NULL,
    price        REAL      NOT NULL,
    revenue      REAL      NOT NULL
);

-- Trilha de auditoria da carga (1 linha por execução do ETL): origem, hash do
-- arquivo bruto e contagens usadas na reconciliação origem -> warehouse.
CREATE TABLE etl_load_audit (
    load_id                  INTEGER NOT NULL PRIMARY KEY,
    loaded_at_utc            TEXT    NOT NULL,
    source_name              TEXT    NOT NULL,
    source_sha256            TEXT,
    source_rows              INTEGER NOT NULL CHECK (source_rows >= 0),
    dropped_missing_customer INTEGER NOT NULL CHECK (dropped_missing_customer >= 0),
    dropped_duplicates       INTEGER NOT NULL CHECK (dropped_duplicates >= 0),
    dropped_invalid_sales    INTEGER NOT NULL CHECK (dropped_invalid_sales >= 0),
    fact_sales_rows          INTEGER NOT NULL CHECK (fact_sales_rows >= 0),
    fact_cancelled_rows      INTEGER NOT NULL CHECK (fact_cancelled_rows >= 0),
    fact_sales_revenue       REAL    NOT NULL
);

CREATE INDEX idx_fact_sales_customer ON fact_sales (customer_id);
CREATE INDEX idx_fact_sales_date     ON fact_sales (date_id);
CREATE INDEX idx_fact_sales_product  ON fact_sales (stock_code);

-- Mesma definição da view do PostgreSQL (schema_postgres.sql).
CREATE VIEW vw_customer_kpis AS
SELECT
    c.customer_id,
    c.primary_country,
    COUNT(DISTINCT f.invoice) AS total_orders,
    SUM(f.revenue)            AS total_revenue,
    MIN(f.invoice_date)       AS first_purchase,
    MAX(f.invoice_date)       AS last_purchase
FROM dim_customer c
JOIN fact_sales f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.primary_country;
