# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
versionamento segue [SemVer](https://semver.org/lang/pt-BR/).

Histórico completo de decisões, bugs encontrados/corrigidos e resultados reais de
cada execução: [`docs/HISTORICO.md`](docs/HISTORICO.md). Este arquivo resume apenas
o que mudou, versão a versão.

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
