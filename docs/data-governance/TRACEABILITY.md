# Matriz de rastreabilidade — Administração e Modelagem de Dados

> Requisito (perfil de vaga de AD/modelagem) → o que já existia → o que foi feito →
> arquivo → teste/evidência → status. Status usa o vocabulário:
> **VALIDADO** (testado e verificado sobre dado real ou banco real) · **TESTADO**
> (teste automatizado verde) · **DOCUMENTADO** · **NOT_RUN** (com motivo).

| Requisito | Evidência anterior (v2.1.0) | Melhoria (v2.2.0) | Arquivo final | Teste / evidência | Status |
|---|---|---|---|---|---|
| Modelagem conceitual | — | entidades, cardinalidades, OLTP inferido × analítico | [conceptual-model.md](conceptual-model.md), [diagrams/retentiq-conceptual.mmd](diagrams/retentiq-conceptual.mmd) | revisão manual contra o dado real | DOCUMENTADO |
| Modelagem lógica (relacional + dimensional) | estrela implícita no ETL | chaves natural×substituta justificadas, grão, medidas, SCD, double counting | [logical-model.md](logical-model.md), [diagrams/retentiq-logical.dbml](diagrams/retentiq-logical.dbml) | DBML validado por `@dbml/cli` (`dbml2sql`) | TESTADO |
| Modelagem física | DDL PG declarado "equivalente" ao SQLite (não era) | DDL SQLite explícito com PK/FK/CHECK/view; mapeamento de tipos | [physical-model.md](physical-model.md), `data-platform/warehouse/schema_sqlite.sql` | carga real 793.609 linhas sem violação; [baseline diff](evidence/baseline-v2.1.0-schema-diff.md) | VALIDADO |
| Normalização / desnormalização | — | DFs medidas, 1FN/2FN/3FN, anomalia real, trade-offs | [normalization-analysis.md](normalization-analysis.md), [ADR-004](../adr/ADR-004-dimensional-model.md) | números medidos no bruto (1.232 SKUs com >1 descrição) | DOCUMENTADO |
| Padrões de nomenclatura | — | regras + auditoria + dívidas DT-01..05 | [naming-standards.md](naming-standards.md) | — | DOCUMENTADO |
| SQL DDL/DML | DDL PG | DML executável (UPSERT, UPDATE, DELETE, SELECT em transação) | `data-platform/warehouse/dml_examples.sql` | `test_dml_examples_run_and_leave_no_residue` (PostgreSQL 16) | TESTADO |
| PK/FK/integridade | só checks por LEFT JOIN | FKs declaradas e aplicadas no SQLite; CHECKs | `schema_sqlite.sql` | `test_foreign_key_is_enforced`, `test_check_constraints_are_enforced` | TESTADO |
| Dicionário de dados | — | gerado do catálogo + YAML semântico; 50 colunas | [data-dictionary.csv](data-dictionary.csv), `governance/export_dictionary.py` | `test_data_dictionary.py`, `--check` no CI | TESTADO |
| Glossário de negócio | — | 10 termos com regra de cálculo e limitações | [business-glossary.md](business-glossary.md) | termos validados contra o dicionário | TESTADO |
| Catálogo e linhagem | — | catálogo por ativo; linhagem por etapa e por coluna (5 KPIs) | [data-catalog.md](data-catalog.md), [data-lineage.md](data-lineage.md) | reconciliação origem→warehouse | VALIDADO |
| Engenharia reversa | — | catálogo SQLite (PRAGMA) e PostgreSQL (pg_catalog) → JSON/DBML/Mermaid | `governance/reverse_engineer.py`, [reverse-engineering.md](reverse-engineering.md) | `test_reverse_engineering.py`; PG em `test_postgres_lab.py` | TESTADO |
| Ferramenta CASE | — | `@dbml/cli` 3.14.1: import DDL, forward engineering, `db2dbml` | [evidence/case-tool/](evidence/case-tool/) | round trip com diff vazio (exceto view) | VALIDADO |
| SAP PowerDesigner / ERwin | — | **não usados** | — | — | NOT_RUN (ferramentas não disponíveis; não alegado) |
| Schema drift / comparação de modelos | — | diff classificado, aprovações, exit 1 | `governance/schema_diff.py`, [schema-diff.md](schema-diff.md) | 5 cenários de drift + restauração | TESTADO |
| Controle de mudanças / homologação | — | CR-001 com up/down idempotentes, checklist, rollback (aprovação **simulada**) | [change-control.md](change-control.md), [change-request-example.md](change-request-example.md), `migrations/postgres/` | `test_cr001_forward_rollback_and_idempotency` | TESTADO |
| Qualidade de dados | 7 checks; **CI pulava** | 30 regras com severidade, catálogo YAML, fixture no CI, exit 1 real | `quality/checks.py`, [quality-rules.yaml](quality-rules.yaml) | `test_quality_checks.py`; carga real 28 OK + 1 aviso esperado | VALIDADO |
| Classificação / LGPD | — | 4 níveis, por coluna; RIPD simplificado | [data-classification.md](data-classification.md), [privacy-impact-notes.md](privacy-impact-notes.md) | `test_customer_identifiers_are_classified_as_personal` | TESTADO |
| Controle de acesso | — | papéis de menor privilégio | `security/roles_postgres.sql`, [access-matrix.md](access-matrix.md) | `test_least_privilege_roles` | TESTADO |
| Pseudonimização / minimização | — | HMAC-SHA256 + k-anonimato + precisão reduzida | `governance/privacy.py` | `test_privacy.py` | TESTADO |
| Performance e índices | 3 índices sem medição | EXPLAIN (ANALYZE, BUFFERS) antes/depois, custo de espaço | [performance-benchmark.md](performance-benchmark.md) | [evidence/benchmark-2026-11-10.json](evidence/benchmark-2026-11-10.json) | VALIDADO (local, não produção) |
| ITSM / Kanban | — | tickets de mudança e incidente, backlog (laboratório) | [sample-*.md](sample-backlog.md) | — | DOCUMENTADO |
| Segurança (vulnerabilidades, ameaças, riscos, incidentes) | — | pip-audit + Trivy no CI; STRIDE; registro de riscos; runbook; mapeamento ISO/NIST/LGPD/GDPR | [../security/](../security/) | pyarrow corrigido (PYSEC-2026-113) | TESTADO |
| Segunda evidência (OLTP multitenant) | FleetCam V1..V11 | laboratório Flyway real, 23 verificações, dicionário, revisão DDL | [FleetCam/docs/data-model](https://github.com/Yuri-Fernando/FleetCam-IoT-Video-Platform/tree/main/docs/data-model) | `migration_lab.py --check` no CI | VALIDADO |
| Experiência profissional de 3 anos | — | **não se aplica**: portfólio não substitui experiência | [PORTFOLIO_CASE.md](PORTFOLIO_CASE.md#o-que-posso-e-não-posso-afirmar) | — | — |
