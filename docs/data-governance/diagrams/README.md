# Diagramas versionados

| Arquivo | Nível | Origem | Como visualizar |
|---|---|---|---|
| `retentiq-conceptual.mmd` | conceitual | escrito à mão | GitHub renderiza Mermaid em `.md`; ou [mermaid.live](https://mermaid.live) |
| `retentiq-logical.dbml` | lógico dimensional | escrito à mão (intenção do modelo) | [dbdiagram.io](https://dbdiagram.io) (colar) ou `npx @dbml/cli dbml2sql` |
| `reverse-engineered.dbml` / `.mmd` | físico SQLite | **gerado** do catálogo (`reverse_engineer.py`) | idem |
| `retentiq-physical-postgres.dbml` | físico PostgreSQL | **gerado** do catálogo de um PostgreSQL 16 com `schema_postgres.sql` | idem |

Os gerados não devem ser editados à mão. `test_versioned_dbml_is_regenerated_from_catalog`
falha se `reverse-engineered.dbml` divergir do schema real produzido pelo ETL.

Regerar:

```bash
python data-platform/ingestion/extract_transform_load.py --fixture --db-path /tmp/fx.db
python data-platform/governance/reverse_engineer.py --sqlite /tmp/fx.db \
  --out-json docs/data-governance/model/retentiq_sqlite.schema.json \
  --out-dbml docs/data-governance/diagrams/reverse-engineered.dbml \
  --out-mermaid docs/data-governance/diagrams/reverse-engineered.mmd
```
