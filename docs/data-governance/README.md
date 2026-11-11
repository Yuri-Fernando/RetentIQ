# Governança e modelagem de dados — RetentIQ

Pacote da v2.2.0: modelagem em três níveis, schema físico íntegro, dicionário
gerado do banco, glossário, linhagem, engenharia reversa, schema diff, controle
de mudanças, qualidade no CI, classificação/LGPD, controle de acesso e benchmark.
Comece pela [matriz de rastreabilidade](TRACEABILITY.md) ou pelo
[caso de portfólio](PORTFOLIO_CASE.md).

## Mapa

| Tema | Documentos | Código / dados |
|---|---|---|
| Modelagem | [conceitual](conceptual-model.md) · [lógico](logical-model.md) · [físico](physical-model.md) · [normalização](normalization-analysis.md) · [nomes](naming-standards.md) · [ADR-004](../adr/ADR-004-dimensional-model.md) | `data-platform/warehouse/schema_sqlite.sql`, `schema_postgres.sql` |
| Diagramas | [diagrams/](diagrams/README.md) | `.mmd` (Mermaid), `.dbml` |
| Metadados | [dicionário](data-dictionary.csv) · [glossário](business-glossary.md) · [catálogo](data-catalog.md) · [linhagem](data-lineage.md) | `metadata/columns.yaml`, `governance/export_dictionary.py` |
| Engenharia reversa | [engenharia reversa + CASE](reverse-engineering.md) · [schema diff](schema-diff.md) | `governance/reverse_engineer.py`, `schema_diff.py`, [model/](model/) |
| Mudanças | [processo](change-control.md) · [checklist](review-checklist.md) · [CR-001](change-request-example.md) · [rollback](rollback-plan.md) | `warehouse/migrations/postgres/` |
| Qualidade | [regras](quality-rules.yaml) | `quality/checks.py` |
| Privacidade e acesso | [classificação](data-classification.md) · [impacto](privacy-impact-notes.md) · [acesso](access-matrix.md) · [retenção](retention-policy-example.md) | `governance/privacy.py`, `warehouse/security/roles_postgres.sql` |
| Performance | [benchmark](performance-benchmark.md) | `governance/benchmark_queries.py`, `warehouse/performance/queries.sql` |
| Processo (laboratório) | [ticket de mudança](sample-data-change-ticket.md) · [incidente](sample-incident-ticket.md) · [backlog](sample-backlog.md) | — |
| Segurança | [ameaças](../security/threat-model.md) · [riscos](../security/risk-register.md) · [incidentes](../security/incident-response.md) · [vulnerabilidades](../security/vulnerability-assessment.md) · [controles](../security/controls-mapping.md) | job `security` no CI |
| Evidências | [evidence/](evidence/) | diffs, benchmark, saídas da ferramenta CASE |

## Reproduzir

```bash
pip install -r data-platform/requirements.txt
python -m pytest data-platform/tests -q                       # sem PostgreSQL: testes PG são pulados
python data-platform/ingestion/extract_transform_load.py --fixture --db-path /tmp/fx.db
python data-platform/quality/checks.py --db /tmp/fx.db --min-rows 100
python data-platform/governance/schema_diff.py --expected docs/data-governance/model/retentiq_sqlite.schema.json --sqlite /tmp/fx.db
python data-platform/governance/export_dictionary.py --check

# laboratório PostgreSQL (Docker)
docker run -d --name retentiq-pg -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1:55432:5432 postgres:16
RETENTIQ_PG_DSN=postgresql://postgres@127.0.0.1:55432/postgres python -m pytest data-platform/tests/test_postgres_lab.py -v
```
