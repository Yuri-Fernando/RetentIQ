-- CR-001 (simulação de processo — laboratório de portfólio) — rollback
-- Remove apenas as constraints criadas pelo forward. Não toca em dados.
-- Idempotente.
BEGIN;
SET LOCAL lock_timeout = '5s';
ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_quantity_positive;
ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_price_positive;
ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_revenue_non_negative;
ALTER TABLE fact_sales_cancelled DROP CONSTRAINT IF EXISTS ck_fact_sales_cancelled_invoice_prefix;
COMMIT;
