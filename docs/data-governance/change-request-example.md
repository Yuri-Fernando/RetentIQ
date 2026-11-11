# CR-001 — Restrições de domínio nos fatos do warehouse PostgreSQL

> **Simulação de processo corporativo — laboratório de portfólio.** Aprovações e
> papéis abaixo são fictícios. A parte técnica (scripts, testes, medições) é real e
> reproduzível.

| Campo | Valor |
|---|---|
| ID | CR-001 |
| Tipo | restritiva (novas CHECK constraints) |
| Solicitante (simulado) | Data Steward |
| Data | 2026-11-10 |
| Scripts | [`CR-001_fact_sales_checks.up.sql`](../../data-platform/warehouse/migrations/postgres/CR-001_fact_sales_checks.up.sql) · [`down.sql`](../../data-platform/warehouse/migrations/postgres/CR-001_fact_sales_checks.down.sql) |
| Teste | `test_cr001_forward_rollback_and_idempotency` em [`test_postgres_lab.py`](../../data-platform/tests/test_postgres_lab.py) |

## Requisito

O warehouse SQLite rejeita `quantity <= 0`, `price <= 0`, `revenue < 0` em vendas e
nota sem prefixo `C` em cancelamentos (CHECK no DDL). O PostgreSQL só tem essas
regras garantidas pelo ETL. Uma carga manual ou outro processo poderia gravar
receita negativa como venda e distorcer a receita bruta.

## Impacto

| Dimensão | Análise |
|---|---|
| Dados existentes | o dado real completo já satisfaz as regras (0 violações no SQLite com os mesmos CHECKs; carga real de 793.609 linhas) |
| ETL | nenhuma mudança: o ETL já filtra essas linhas antes da carga |
| API | nenhuma: só leitura; nenhuma coluna alterada |
| Schema diff | `checks` de `fact_sales` 0 → 3, `fact_sales_cancelled` 0 → 1; nenhuma mudança de coluna/PK/FK |
| Performance | validação varre a tabela uma vez; INSERT ganha avaliação de 3 expressões por linha (custo desprezível frente ao COPY; não medido isoladamente) |
| Lock | `ADD CONSTRAINT ... NOT VALID` pega `ACCESS EXCLUSIVE` por instante; `VALIDATE` usa `SHARE UPDATE EXCLUSIVE` (não bloqueia leitura/escrita). `lock_timeout = 5s` evita fila atrás de consulta longa |
| PII / LGPD | nenhuma coluna pessoal envolvida |

## Plano

1. Forward: `psql -v ON_ERROR_STOP=1 -f CR-001_fact_sales_checks.up.sql`
2. Verificação: `SELECT conname, convalidated FROM pg_constraint WHERE conname LIKE 'ck_fact_sales%'` → 4 linhas, todas `true`
3. Rollback (se necessário): `CR-001_fact_sales_checks.down.sql` — ver [rollback-plan.md](rollback-plan.md)

## Homologação (executada no laboratório)

| Verificação | Resultado |
|---|---|
| up aplicado em banco descartável com dados da fixture | ✅ |
| up reaplicado (idempotência) | ✅ sem erro |
| constraints validadas (`convalidated = true`) | ✅ |
| `UPDATE fact_sales SET quantity = 0` rejeitado | ✅ `CheckViolation` |
| down restaura exatamente o snapshot anterior (diff vazio) | ✅ |
| CI (`data-model-postgres`) executa o mesmo teste em `postgres:16` | configurado; resultado no GitHub Actions após o push |

## Aprovação (simulada)

| Papel (simulado) | Decisão |
|---|---|
| Data Owner Comercial | aprovado |
| DBA / Steward | aprovado com condição: aplicar fora do horário de carga |

## Decisão sobre o DDL base

`schema_postgres.sql` continua sendo o baseline e a CR-001 fica como migração
versionada separada, para demonstrar forward/rollback. Incorporar as constraints
ao baseline é passo da próxima versão.
