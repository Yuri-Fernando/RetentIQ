# Modelo físico — RetentIQ

> Nível físico: como o modelo lógico é **realmente** implementado em cada SGBD.
> Fontes da verdade (DDL versionado):
>
> - SQLite (warehouse local criado pelo ETL): [`data-platform/warehouse/schema_sqlite.sql`](../../data-platform/warehouse/schema_sqlite.sql)
> - PostgreSQL (stack Docker): [`data-platform/warehouse/schema_postgres.sql`](../../data-platform/warehouse/schema_postgres.sql)
>
> Diagramas **extraídos do catálogo** (não desenhados à mão):
> [`diagrams/reverse-engineered.dbml`](diagrams/reverse-engineered.dbml) (SQLite) e
> [`diagrams/retentiq-physical-postgres.dbml`](diagrams/retentiq-physical-postgres.dbml).
> Snapshots JSON usados no diff de schema: [`model/`](model/).

## 1. O que mudou na v2.2.0 (drift corrigido)

Até a v2.1.0 o ETL criava as tabelas SQLite com `pandas.to_sql(if_exists="replace")`.
O diff do warehouse antigo contra o modelo
([evidence/baseline-v2.1.0-schema-diff.md](evidence/baseline-v2.1.0-schema-diff.md))
mostrou **13 diferenças incompatíveis**: nenhuma PK, nenhuma FK, nenhum UNIQUE, sem a
view `vw_customer_kpis` (que só existia no DDL PostgreSQL) e 34 colunas aceitando
NULL. O DDL PostgreSQL dizia "equivalente ao SQLite", mas não era.

Agora o ETL aplica `schema_sqlite.sql` (DROP + CREATE) com `PRAGMA foreign_keys=ON`
e carrega dimensões antes dos fatos. Validado sobre o **dataset real completo**:
793.609 vendas e 18.688 cancelamentos carregados sem nenhuma violação de PK/FK/CHECK.

## 2. Mapeamento de tipos

| Lógico | SQLite (declarado) | PostgreSQL | Observação |
|---|---|---|---|
| id inteiro | `INTEGER` | `INTEGER` / `BIGINT` (`sale_id`, `cancel_id`) | `INTEGER PRIMARY KEY` no SQLite é alias do `rowid` (busca por PK sem índice extra) |
| id sequencial | `INTEGER PRIMARY KEY` (valor vem do ETL) | `SERIAL` (`country_id`), `BIGSERIAL` (`load_id`) | no PG a carga externa precisa de `setval` depois do `COPY` (feito em `pg_lab.load_from_sqlite`) |
| código/texto | `TEXT` | `TEXT` | sem `VARCHAR(n)`: o tamanho não é regra de negócio e `TEXT` não tem custo extra no PG |
| moeda | `REAL` (IEEE-754 binário) | `NUMERIC(12,4)` preço · `NUMERIC(14,4)` receita · `NUMERIC(16,4)` total auditado | ver §3 |
| data | `TIMESTAMP` (texto ISO) | `DATE` | nome de tipo mantido como o pandas gerava, para não mudar o que a API lê |
| timestamp | `TIMESTAMP` (texto `YYYY-MM-DD HH:MM:SS`) | `TIMESTAMP` (sem fuso) | origem não tem fuso; `loaded_at_utc` é `TIMESTAMPTZ` no PG |
| booleano | `INTEGER` + `CHECK (IN (0,1))` | `BOOLEAN` | SQLite não tem booleano nativo |

Diff entre os dois dialetos (gerado por `schema_diff.py --actual-json`,
[evidence/sqlite-vs-postgres-diff.md](evidence/sqlite-vs-postgres-diff.md)): as 17
diferenças são **todas de tipo** (`real`↔`numeric`, `timestamp`↔`date`,
`integer`↔`boolean`/`bigint`, `text`↔`timestamptz`). Tabelas, colunas, nulidade,
PKs, FKs, UNIQUEs, índices e a view coincidem. CHECKs não entram no diff (o SQLite
não os expõe no catálogo); no PostgreSQL os dos fatos chegam com a
[CR-001](change-request-example.md).

## 3. Por que NUMERIC para valores financeiros

`REAL`/`double` não representa `0,10` exatamente; somas de milhões de linhas
acumulam erro de arredondamento. No PostgreSQL, `NUMERIC(p,s)` é decimal exato.

- `price NUMERIC(12,4)`: até 99.999.999,9999 — a origem tem preço com até 2 casas, 4
  casas dão folga para preço médio/rateio;
- `revenue NUMERIC(14,4)`: maior receita de linha real = £ 168.469,60 (folga de 6
  ordens de grandeza).

No SQLite (modo local zero-setup) a receita fica `REAL`. Medido no dado real:
`SUM(revenue)` = £ 17.685.460,64, igual a `SUM(quantity*price)` arredondado a 2 casas.
As regras de qualidade usam tolerância de 0,01 justamente por isso. Para valores
financeiros oficiais, a fonte deve ser o PostgreSQL.

## 4. Restrições físicas

| Restrição | SQLite | PostgreSQL |
|---|---|---|
| PK em todas as tabelas | ✅ | ✅ |
| 4 FKs de `fact_sales` | ✅ (`PRAGMA foreign_keys=ON` na carga + `foreign_key_check`) | ✅ |
| `dim_country.country` UNIQUE | ✅ | ✅ |
| NOT NULL conforme modelo lógico | ✅ | ✅ |
| CHECK de domínio (`quantity>0`, `price>0`, `revenue>=0`, prefixo `C`, `month 1-12`...) | ✅ | parcial: só `etl_load_audit`; fatos ganham com a CR-001 (`NOT VALID` + `VALIDATE`) |
| FKs de `fact_sales_cancelled` | ❌ por decisão de modelo | ❌ por decisão de modelo |

## 5. Índices

| Índice | Colunas | Justificativa |
|---|---|---|
| `idx_fact_sales_customer` | `customer_id` | KPI/histórico de um cliente (API) e join com `dim_customer` |
| `idx_fact_sales_date` | `date_id` | filtros por período |
| `idx_fact_sales_product` | `stock_code` | detalhe por produto |

Índices **cobrindo** (`INCLUDE`) foram medidos no
[benchmark](performance-benchmark.md) e **não** foram adotados no DDL: só ajudam
consultas pontuais/faixa (2,2× e 1,7×), não as agregações completas, e somam 60 MB.

## 6. Convenções de nomes

Ver [naming-standards.md](naming-standards.md) (inclui inconsistências reais
herdadas e por que não foram renomeadas).

## 7. Estratégia de carga e atualização

| Aspecto | Implementação atual | Consequência |
|---|---|---|
| Tipo de carga | **full refresh** (DROP + CREATE + INSERT) | simples e idempotente; sem histórico (SCD tipo 1) |
| Ordem | dimensões → fatos (FKs ativas) | falha cedo em órfão |
| Atomicidade | por tabela (`to_sql` commita por chamada) | uma falha no meio deixa o warehouse incompleto até a próxima carga. Item de backlog: gravar em arquivo temporário e trocar (`os.replace`) ao final |
| Verificação | contagem pós-insert, `foreign_key_check`, 30 regras de qualidade, `etl_load_audit` | o processo termina com código 1 se uma regra crítica falhar (antes imprimia "[OK]" mesmo com falha) |
| Tempo medido (dado real, notebook local, arquivo no Google Drive) | 8 min 53 s ponta a ponta | a leitura do `.xlsx` domina; o ETL não foi otimizado para tempo |
