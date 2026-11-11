# Engenharia reversa e ferramenta CASE — RetentIQ

## 1. Engenharia reversa própria (catálogo do banco)

[`data-platform/governance/reverse_engineer.py`](../../data-platform/governance/reverse_engineer.py)
lê o **catálogo** do SGBD, não o texto do DDL:

| SGBD | Fonte | Extrai |
|---|---|---|
| SQLite | `PRAGMA table_xinfo`, `foreign_key_list`, `index_list`, `index_info` | colunas, tipo declarado, nulidade, default, PK, FK, UNIQUE, índices, views |
| PostgreSQL | `information_schema.tables/columns` + `pg_constraint`, `pg_index`, `pg_attribute` | o mesmo + precisão de `NUMERIC`, contagem de CHECKs, índices parciais |

Saídas: JSON canônico ordenado ([`model/`](model/)), DBML e Mermaid.

```bash
python data-platform/governance/reverse_engineer.py --sqlite data-platform/warehouse/retentiq.db \
  --out-json model.json --out-dbml model.dbml --out-mermaid model.mmd
python data-platform/governance/reverse_engineer.py --postgres "$RETENTIQ_PG_DSN" --out-json pg.json
```

Limitação honesta: o SQLite não expõe CHECK no catálogo; o script só **conta**
`CHECK (` no DDL armazenado em `sqlite_master` (informativo, não usado no diff).

## 2. Ferramenta CASE usada de verdade: `@dbml/cli` 3.14.1 (open source)

Executada em 2026-11-10, instalada fora do repositório
(`D:\Claude Temp\staging\dbmlcli`, Node.js). Não houve uso de SAP PowerDesigner,
ERwin ou similares.

| Fluxo | Comando | Resultado | Evidência |
|---|---|---|---|
| **Importar DDL** (SQL → modelo) | `sql2dbml --postgres schema_postgres.sql` | ❌ falhou: `Cannot read properties of undefined (reading 'pathName')`. Diagnóstico: o parser PostgreSQL do `@dbml/core` 3.14.1 não aceita `CREATE TABLE IF NOT EXISTS`. Removendo `IF NOT EXISTS` (e a view): ✅ 7 tabelas, 4 refs | [`evidence/case-tool/imported_from_ddl.dbml`](evidence/case-tool/imported_from_ddl.dbml) |
| **Validar modelo lógico** | `dbml2sql --postgres retentiq-logical.dbml` | ✅ 6 `CREATE TABLE` (sintaxe DBML válida) | — |
| **Forward engineering** (modelo → DDL → banco) | `dbml2sql --postgres retentiq-physical-postgres.dbml`, aplicado em PostgreSQL 16 descartável, depois engenharia reversa + diff contra o modelo versionado | ✅ tabelas, colunas, nulidade, PK, FK, UNIQUE e índices idênticos; única diferença: `view_removed:vw_customer_kpis` (DBML não modela views) | [`evidence/case-tool/forward.sql`](evidence/case-tool/forward.sql) |
| **Engenharia reversa pela ferramenta** (banco vivo → modelo) | `db2dbml postgres <dsn>` | ✅ 7 tabelas, 4 refs — igual à extração própria | [`evidence/case-tool/db2dbml_live.dbml`](evidence/case-tool/db2dbml_live.dbml) |

Os `.dbml` também abrem no [dbdiagram.io](https://dbdiagram.io) (colar o conteúdo)
para visualização; isso não foi feito nesta sessão e não há captura de tela.

## 3. Cenário "sistema legado" (banco descartável)

Automatizado em [`test_reverse_engineering.py`](../../data-platform/tests/test_reverse_engineering.py)
— nunca toca no warehouse do usuário:

1. **gerar** o schema (ETL com fixture → SQLite temporário);
2. **alterar** de propósito, uma mudança por caso: coluna nova, coluna removida,
   view removida, índice removido, mudança de tipo (reconstrução de tabela);
3. **extrair** o schema pelo catálogo;
4. **detectar** o drift e classificar (`compatible` / `review` / `breaking`);
5. **restaurar** recriando a partir do DDL versionado e provar diff vazio.

Caso real (não simulado): o warehouse v2.1.0 que já existia na máquina do autor foi
comparado com o modelo v2.2.0 →
[`evidence/baseline-v2.1.0-schema-diff.md`](evidence/baseline-v2.1.0-schema-diff.md)
(13 incompatibilidades: sem PK/FK/UNIQUE/view).
