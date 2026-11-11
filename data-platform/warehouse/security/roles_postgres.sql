-- RetentIQ — controle de acesso por PAPEL (menor privilégio) no warehouse PostgreSQL.
-- Laboratório de portfólio: papéis de exemplo, sem usuários reais nem senhas.
-- Ver docs/data-governance/access-matrix.md e docs/security/controls-mapping.md.
--
-- Modelo:
--   retentiq_analyst  -> só lê a camada de consumo (view de KPIs + dimensões não pessoais)
--   retentiq_engineer -> lê tudo, escreve fatos/dimensões (carga do ETL), sem DDL
--   retentiq_steward  -> lê tudo + trilha de auditoria (qualidade/metadados), sem escrita
--   (DDL fica com o dono do schema / DBA, fora destes papéis)
--
-- Logins reais seriam criados com `CREATE ROLE <pessoa> LOGIN IN ROLE retentiq_analyst`
-- e senha/credencial gerenciada fora do repositório.
-- Idempotente. Aplica sobre o schema corrente (search_path).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'retentiq_analyst') THEN
        CREATE ROLE retentiq_analyst NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'retentiq_engineer') THEN
        CREATE ROLE retentiq_engineer NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'retentiq_steward') THEN
        CREATE ROLE retentiq_steward NOLOGIN;
    END IF;
END
$$;

-- ninguém herda acesso por padrão
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO retentiq_analyst, retentiq_engineer, retentiq_steward;

-- analista: camada de consumo. NÃO lê fact_sales/fact_sales_cancelled linha a linha
-- (minimização: KPI agregado basta para a finalidade de retenção).
GRANT SELECT ON vw_customer_kpis, dim_product, dim_country, dim_date TO retentiq_analyst;

-- engenheiro: carga (DML), sem DDL
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON dim_customer, dim_product, dim_country, dim_date, fact_sales, fact_sales_cancelled
    TO retentiq_engineer;
GRANT SELECT, INSERT ON etl_load_audit TO retentiq_engineer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO retentiq_engineer;
GRANT SELECT ON vw_customer_kpis TO retentiq_engineer;

-- steward: leitura ampla para qualidade/metadados + auditoria; sem escrita
GRANT SELECT ON ALL TABLES IN SCHEMA public TO retentiq_steward;
