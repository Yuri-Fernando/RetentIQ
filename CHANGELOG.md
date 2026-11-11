# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

Histórico completo de decisões, bugs encontrados/corrigidos e resultados reais de
cada execução: [`docs/HISTORICO.md`](docs/HISTORICO.md). Este arquivo resume apenas
o que mudou, versão a versão.

## [2.2.0] — 2026-11-10

### Added

- **Modelo físico SQLite explícito** (`data-platform/warehouse/schema_sqlite.sql`):
  PK em todas as tabelas, 4 FKs em `fact_sales`, `UNIQUE`, `NOT NULL`, `CHECK` de
  domínio, índices e a view `vw_customer_kpis` (antes só no PostgreSQL). Validado na
  carga completa do Online Retail II sem nenhuma violação.
- `etl_load_audit` (SQLite e PostgreSQL): trilha da carga com SHA-256 da origem e
  contagens para reconciliação.
- `data-platform/governance/`: fixture sintética determinística, engenharia reversa
  (PRAGMA / `pg_catalog` → JSON/DBML/Mermaid), schema diff classificado com
  aprovações e exit 1, gerador/validador do dicionário, pseudonimização HMAC +
  k-anonimato, laboratório PostgreSQL descartável e benchmark com
  `EXPLAIN (ANALYZE, BUFFERS)`.
- `docs/data-governance/`: modelos conceitual/lógico/físico, diagramas versionados,
  normalização, padrões de nomes, dicionário (50 colunas, gerado), glossário,
  catálogo, linhagem, engenharia reversa e ferramenta CASE (`@dbml/cli` 3.14.1),
  controle de mudanças, CR-001, checklist, rollback, classificação, RIPD
  simplificado, matriz de acesso, retenção, benchmark, tickets/backlog de
  laboratório, rastreabilidade, caso técnico e Q&A de entrevista.
- `docs/adr/ADR-004-dimensional-model.md`.
- `docs/security/`: STRIDE, registro de riscos, runbook de incidentes, avaliação de
  vulnerabilidades, mapeamento ISO 27001 / NIST CSF 2.0 / LGPD / GDPR.
- `data-platform/warehouse/migrations/postgres/CR-001_*` (up/down idempotentes),
  `security/roles_postgres.sql` (menor privilégio), `dml_examples.sql`,
  `performance/queries.sql`; `.sqlfluff`.
- 50 testes novos (ETL fixture, qualidade, dicionário, engenharia reversa, drift,
  privacidade, 6 contra PostgreSQL 16).
- CI: jobs `data-model-postgres` e `security` (pip-audit + Trivy).

### Changed

- ETL aplica o DDL explícito com `PRAGMA foreign_keys=ON`, carrega dimensões antes
  dos fatos, roda `foreign_key_check`, aceita `--fixture/--db-path/--raw` e
  **retorna 1 se uma regra crítica falhar** (antes imprimia "[OK]" de qualquer forma).
- `quality/checks.py`: 7 → 30 regras com severidade (critical/warning), limiar de
  volume parametrizável, abertura somente leitura, reconciliação origem→warehouse e
  anti-double-counting; catálogo em `docs/data-governance/quality-rules.yaml`.
- CI `data-platform`: deixa de **pular** os checks; lint SQL, testes, ETL com fixture,
  schema drift e `export_dictionary.py --check`.
- `schema_postgres.sql`: + `etl_load_audit` (aditivo).

### Security

- `pyarrow` 22.0.0 → 23.0.1 (PYSEC-2026-113, apontado pelo pip-audit).
- Dockerfiles da API e do web passam a rodar como usuário `node` (Trivy DS-0002).

## [2.1.0] — 2026-10-07

### Added

- **`experimentation/`** — pacote de experimentação de produto (Python): A/B testing
  (teste z de duas proporções + Welch's t-test), calculadora de tamanho de
  amostra/poder estatístico, CUPED (redução de variância via covariável
  pré-experimento), teste sequencial mSPRT ("always valid inference", permite parar
  antes do N fixo sem inflar falso-positivo), A/B bayesiano (Beta-Binomial e
  Normal), e uplift/CATE via T-learner (scikit-learn). 30 testes, verificados contra
  `statsmodels`/`scipy` (implementações independentes), simulação Monte Carlo (mSPRT)
  e casos hand-calculados.
- **`data-platform/revenue/`** — módulo de métricas de receita SaaS/FP&A (Python):
  gerador de dataset sintético de assinaturas (seed fixa), MRR/ARR, GRR/NRR, cohort de
  retenção de receita, bridge de movimento de MRR (new/expansion/contraction/churn
  reconciliando exatamente com o MRR observado), forecast de tendência linear +
  budget sintético vs. actual, e scenario planner (pessimista/base/otimista). 26
  testes, com reconciliação exata do bridge verificada em cada mês e casos
  hand-calculados.
- `data-platform/revenue/run_report.py` — pipeline que gera o dataset sintético e
  todos os relatórios (`data-platform/warehouse/revenue_*.csv`/`.json`), seguindo a
  mesma convenção de `data-platform/ml/churn_model.py`.
- `ROADMAP.md` — próximos passos do projeto, consolidado num único arquivo (antes
  espalhado entre o README e `docs/HISTORICO.md`).

### Changed

- `data-platform/requirements.txt` — adiciona `scipy` (dependência explícita, antes
  só transitiva via scikit-learn/statsmodels) e `pytest` (testes de
  `experimentation/` e `data-platform/revenue/`).

## [2.0.2] — 2026-08-21

### Fixed

- `node_modules` de `apps/api` e `apps/web` materializado dentro das pastas reais do
  projeto (antes só existia na pasta de staging local) — `npm run build/lint/test/dev`
  validados rodando direto da pasta sincronizada.
- Bug real: `DELETE` de card do Kanban de retenção quebrava para clientes com
  comentário associado.
- Cache do webpack do Next.js desabilitado (causava crash de build na pasta
  sincronizada pelo Google Drive).
- Error handler JSON global adicionado na API.

## [2.0.1] — 2026-08-20

### Fixed

- 2 bugs reais de TypeScript corrigidos (`auth.ts`, `dashboard/page.tsx`).
- Configuração de ESLint criada para `apps/api` e `apps/web` (não existia).
- `npm install` das duas apps validado de ponta a ponta fora do caminho sincronizado
  (Google Drive) — causa raiz do bloqueio documentada em `docs/HISTORICO.md`.

### Added

- Teste unitário real (`csv.test.ts`).
- `.env`/ícones PWA gerados para uso local/demo.

## [2.0.0] — 2026-08-19

### Added

- Módulo "Ações de Retenção": Kanban de clientes em risco, chat em tempo real
  (Socket.io), editor de notas em blocos.
- Motor de recomendação (coocorrência de produtos por nota fiscal).
- API GraphQL (graphql-yoga), alternativa de leitura à API REST.
- Fila assíncrona de win-back (BullMQ/Redis).
- PWA offline (cache-first das rotas principais do dashboard).
- Endpoint `/metrics` (Prometheus) + stack de observabilidade (Docker Compose).

## [1.0.0] — 2026-08-19

### Added

- ETL (Python/pandas) do UCI Online Retail II → Data Warehouse dimensional
  (SQLite/PostgreSQL).
- Modelo de churn (Random Forest sobre features RFM).
- Previsão de demanda (Holt-Winters, séries temporais).
- API REST (Node/Express/TypeScript).
- Dashboard Next.js (métricas de receita, produtos, países).
- Docker Compose básico, CI (GitHub Actions), testes E2E (Playwright).
