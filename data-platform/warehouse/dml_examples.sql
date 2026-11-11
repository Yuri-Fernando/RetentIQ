-- RetentIQ — exemplos executáveis de DML (PostgreSQL) sobre dados SINTÉTICOS.
--
-- Roda inteiro dentro de UMA transação que termina em ROLLBACK: é seguro
-- executar contra qualquer banco de laboratório, quantas vezes quiser, sem
-- deixar resíduo. Executado pelo teste data-platform/tests/test_postgres_lab.py.
--
--   psql "$RETENTIQ_PG_DSN" -v ON_ERROR_STOP=1 -f data-platform/warehouse/dml_examples.sql

BEGIN;

-- 1) INSERT com UPSERT idempotente nas dimensões (chave natural / substituta)
INSERT INTO dim_customer (customer_id, primary_country) VALUES (99000001, 'Portugal')
ON CONFLICT (customer_id) DO UPDATE SET primary_country = EXCLUDED.primary_country;

INSERT INTO dim_product (stock_code, description) VALUES ('SYNDML1', 'PRODUTO SINTETICO DML')
ON CONFLICT (stock_code) DO NOTHING;

INSERT INTO dim_country (country) VALUES ('Portugal')
ON CONFLICT (country) DO NOTHING;

INSERT INTO dim_date (date_id, date, year, month, day, weekday, is_weekend)
VALUES (20111231, DATE '2011-12-31', 2011, 12, 31, 'Saturday', TRUE)
ON CONFLICT (date_id) DO NOTHING;

-- 2) INSERT no fato respeitando as FKs (dimensões antes do fato)
INSERT INTO fact_sales (sale_id, invoice, stock_code, customer_id, country_id, date_id,
                        invoice_date, quantity, price, revenue)
SELECT 990000001, 'DML0001', 'SYNDML1', 99000001, c.country_id, 20111231,
       TIMESTAMP '2011-12-31 10:00:00', 3, 2.5000, 3 * 2.5000
FROM dim_country c WHERE c.country = 'Portugal';

-- 3) UPDATE mantendo a medida derivada coerente (revenue = quantity * price)
UPDATE fact_sales
SET quantity = 4, revenue = 4 * price
WHERE sale_id = 990000001;

-- 4) SELECT: a view de consumo reflete a alteração dentro da transação
SELECT customer_id, total_orders, total_revenue
FROM vw_customer_kpis
WHERE customer_id = 99000001;

-- 5) DELETE na ordem inversa das FKs (fato antes da dimensão)
DELETE FROM fact_sales WHERE sale_id = 990000001;
DELETE FROM dim_customer WHERE customer_id = 99000001;
DELETE FROM dim_product WHERE stock_code = 'SYNDML1';

ROLLBACK;
