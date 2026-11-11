-- CR-001 (simulação de processo — laboratório de portfólio) — forward
-- Ver docs/data-governance/change-request-example.md
--
-- Objetivo: levar para o PostgreSQL as mesmas regras de domínio que o warehouse
-- SQLite já aplica (schema_sqlite.sql), hoje garantidas só pelo ETL.
--
-- Estratégia de baixo bloqueio:
--   1) ADD CONSTRAINT ... NOT VALID  -> lock curto (ACCESS EXCLUSIVE breve), não varre a tabela;
--      já passa a valer para INSERT/UPDATE novos;
--   2) VALIDATE CONSTRAINT           -> varre linhas existentes com SHARE UPDATE EXCLUSIVE
--      (leituras e escritas continuam).
-- Idempotente: pode ser reaplicado sem erro.

BEGIN;
SET LOCAL lock_timeout = '5s';

ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_quantity_positive;
ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_price_positive;
ALTER TABLE fact_sales DROP CONSTRAINT IF EXISTS ck_fact_sales_revenue_non_negative;
ALTER TABLE fact_sales_cancelled DROP CONSTRAINT IF EXISTS ck_fact_sales_cancelled_invoice_prefix;

ALTER TABLE fact_sales ADD CONSTRAINT ck_fact_sales_quantity_positive CHECK (quantity > 0) NOT VALID;
ALTER TABLE fact_sales ADD CONSTRAINT ck_fact_sales_price_positive CHECK (price > 0) NOT VALID;
ALTER TABLE fact_sales ADD CONSTRAINT ck_fact_sales_revenue_non_negative CHECK (revenue >= 0) NOT VALID;
ALTER TABLE fact_sales_cancelled
    ADD CONSTRAINT ck_fact_sales_cancelled_invoice_prefix CHECK (left(invoice, 1) = 'C') NOT VALID;
COMMIT;

ALTER TABLE fact_sales VALIDATE CONSTRAINT ck_fact_sales_quantity_positive;
ALTER TABLE fact_sales VALIDATE CONSTRAINT ck_fact_sales_price_positive;
ALTER TABLE fact_sales VALIDATE CONSTRAINT ck_fact_sales_revenue_non_negative;
ALTER TABLE fact_sales_cancelled VALIDATE CONSTRAINT ck_fact_sales_cancelled_invoice_prefix;
