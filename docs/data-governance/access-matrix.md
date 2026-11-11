# Matriz de acesso por papel — RetentIQ (warehouse PostgreSQL)

> Implementada em [`data-platform/warehouse/security/roles_postgres.sql`](../../data-platform/warehouse/security/roles_postgres.sql)
> e **testada** em PostgreSQL 16 descartável (`test_least_privilege_roles`).
> Papéis de laboratório: não há pessoas reais vinculadas.

| Objeto | `retentiq_analyst` | `retentiq_engineer` | `retentiq_steward` | dono do schema / DBA |
|---|---|---|---|---|
| `vw_customer_kpis` | SELECT | SELECT | SELECT | ALL |
| `dim_product`, `dim_country`, `dim_date` | SELECT | SELECT, DML | SELECT | ALL |
| `dim_customer` | — | SELECT, DML | SELECT | ALL |
| `fact_sales`, `fact_sales_cancelled` | — | SELECT, DML, TRUNCATE | SELECT | ALL |
| `etl_load_audit` | — | SELECT, INSERT | SELECT | ALL |
| DDL (CREATE/ALTER/DROP) | — | — | — | sim |

## Verificado por teste

| Cenário | Esperado | Resultado |
|---|---|---|
| analista lê a view de KPIs | permitido | ✅ |
| analista lê `fact_sales` linha a linha | `InsufficientPrivilege` | ✅ |
| analista lê `dim_customer` | `InsufficientPrivilege` | ✅ |
| engenheiro cria tabela no schema | `InsufficientPrivilege` | ✅ |
| steward apaga linha de fato | `InsufficientPrivilege` | ✅ |

## Princípios aplicados

- **Menor privilégio** (ISO/IEC 27001:2022 controle 8.3; LGPD art. 46): o analista
  vê agregado, não transação.
- **Segregação de funções**: quem carrega (engineer) não altera estrutura; quem
  audita (steward) não escreve.
- **`REVOKE ALL ... FROM PUBLIC`**: nada é herdado por padrão.
- Logins individuais herdariam um papel (`CREATE ROLE fulano LOGIN IN ROLE ...`);
  credenciais ficariam em cofre, nunca no repositório.

## Trilha de auditoria

| O quê | Como | Status |
|---|---|---|
| Cargas (quem/quando/de onde) | `etl_load_audit` | implementado (sem identidade do executor) |
| Consultas e alterações de privilégio | `log_statement = 'ddl'` / extensão `pgaudit` | **planejado** — não configurado |

## Warehouse SQLite (modo local)

SQLite não tem usuários/papéis. Controles nesse modo: arquivo fora do Git,
API abre em `readonly: true` (`apps/api/src/lib/db.ts`), checks abrem com `mode=ro`.
