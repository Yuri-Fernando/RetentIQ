# 📈 RetentIQ — inteligência de receita e retenção de clientes, do dado bruto à decisão de negócio

### Python · Node.js · TypeScript · Next.js · Express · GraphQL · Kafka · RabbitMQ · CQRS · scikit-learn · statsmodels · SQLite/PostgreSQL · Redis · Docker · Prometheus

[![ci](https://github.com/Yuri-Fernando/retentiq/actions/workflows/ci.yml/badge.svg)](https://github.com/Yuri-Fernando/retentiq/actions/workflows/ci.yml)
![testes](https://img.shields.io/badge/testes%20python-56%2F56-0a8a0a)
![MRR](https://img.shields.io/badge/MRR%20final-%2482.787-c8742a)
![versão](https://img.shields.io/badge/vers%C3%A3o-v2.1.0-4a5563) ![licença](https://img.shields.io/badge/licen%C3%A7a-n%C3%A3o%20definida-4a5563)

## Status

🟡 **Em desenvolvimento — v2.1.0** — aplicação completa e funcional localmente (API,
dashboard, pipeline de dados e modelos de ML todos rodando e testados de ponta a ponta,
mais os dois módulos novos de Data Science/FP&A desta versão); falta o deploy em um
provedor de nuvem para ficar acessível publicamente.

Posicionamento no portfólio: **Event-Driven SaaS** — produto distribuído com
arquitetura orientada a eventos (Kafka + RabbitMQ) e **CQRS**. Ver
[`docs/event-driven-architecture.md`](docs/event-driven-architecture.md) e
`docs/adr/`. (Frontend segue Next.js — decisão deliberada, ADR-003.)

### Status das capacidades

| Capacidade | Status |
|---|---|
| ETL → Data Warehouse dimensional (Python) | ✅ |
| ML: churn · previsão de demanda · recomendação | ✅ |
| API REST + GraphQL + WebSocket (Node/TS) | ✅ |
| Dashboard Next.js + Kanban de retenção | ✅ |
| Observabilidade (Prometheus/Grafana) | ✅ |
| Testes E2E (Playwright) | ✅ |
| Event-Driven Architecture — abstração de bus + demo | ✅ `platform/messaging/` (InMemoryBus + demo + testes, Node puro) |
| Schemas de domain events (JSON Schema) | ✅ `platform/messaging/schemas/` |
| ADRs (Kafka vs RabbitMQ · CQRS · manter Next.js) | ✅ `docs/adr/` |
| Kafka/RabbitMQ com broker real | ✅ testado — `KafkaBus.roundtrip()` / `RabbitBus.consumeOnce()` verdes contra Redpanda + RabbitMQ (Docker); job `platform-integration` no CI |
| Read models CQRS materializados | ✅ `platform/read-models/` — `ChurnReadModel` (SQLite embutido do Node) + teste de equivalência replay ↔ incremental |
| **Experimentação de produto** (A/B, power, CUPED, sequential, Bayesian, uplift) | ✅ `experimentation/` (Python) — **30 testes**, verificados contra `statsmodels`/`scipy`, Monte Carlo e casos hand-calculados |
| **Métricas de receita SaaS** (MRR/ARR/GRR/NRR, cohorts, bridge, forecast, scenarios) | ✅ `data-platform/revenue/` (Python, dataset sintético) — **26 testes**, bridge reconciliado exatamente mês a mês |
| Deploy em nuvem pública | 🗺️ planejado — nenhum provedor escolhido ainda (ver `ROADMAP.md`) |

---

## Descrição / Contexto

RetentIQ é uma plataforma full-stack de inteligência de receita e retenção de clientes
para e-commerce: ingestão de dados → Data Warehouse dimensional → modelos de Machine
Learning (churn, previsão de demanda, recomendação) → API (REST + GraphQL + WebSocket)
→ dashboard web → observabilidade (Prometheus) → testes automatizados (unitários e
E2E), mais dois módulos de Data Science/FP&A adicionados na v2.1.0: experimentação de
produto (`experimentation/`) e métricas de receita recorrente (`data-platform/revenue/`).

É um projeto de portfólio, construído para demonstrar competência tanto na construção
do sistema (autenticação, tempo real, filas, APIs, event-driven/CQRS, testes, CI/CD)
quanto na extração de inteligência de negócio a partir de dados reais (ETL, modelagem
dimensional, ML, experimentação estatística, métricas de FP&A, validação de qualidade).

---

## 🧭 Origem do Projeto

O projeto nasceu da fusão de dois repertórios de estudo — um de projetos de
desenvolvimento full-stack (30 ideias) e outro de projetos de engenharia/ciência de
dados (20 ideias) — num único produto de dados ponta a ponta, em vez de dois projetos
isolados e mais rasos (raciocínio completo em `docs/MENTORIA.md`). As conclusões que
definiram a construção:

1. Os dois repertórios convergem naturalmente num domínio comum de
   e-commerce/receita/clientes — fundir em vez de escolher um de cada lista.
2. **Dataset real, não sintético**, para o núcleo do produto — UCI Online Retail II,
   por ser público, sem exigir credenciais/API key, e rico o suficiente para sustentar
   todas as análises sem inventar colunas.
3. "Funil de recrutamento" (ideia do repertório dev) reformulado como **funil de
   retenção** (alto risco → contatado → em andamento → resolvido) — mesmo conceito,
   aplicado ao domínio certo do produto.
4. "Análise de vagas de emprego" descartada deliberadamente — sem ponte honesta com
   e-commerce/retenção; forçar essa peça seria o anti-padrão que os materiais de origem
   alertam (ferramenta sem finalidade explicável).
5. **v2.1.0**: uma auditoria externa de portfólio apontou dois gaps atribuídos a este
   repositório — "Data Science / Experimentation" e "SaaS / FP&A / Revenue". Os dois
   módulos novos (`experimentation/`, `data-platform/revenue/`) foram implementados em
   **Python**, não TypeScript, por serem bibliotecas de cálculo estatístico/financeiro
   puro (entram arrays/DataFrames, saem números) — o mesmo padrão já usado em
   `data-platform/ml/`, documentado nos próprios `__init__.py` dos módulos.

Histórico completo de decisões e sessões em [`docs/HISTORICO.md`](docs/HISTORICO.md).

---

## 🎯 Objetivo

- Demonstrar um pipeline de dados completo, com dataset real, do bruto à decisão de
  negócio (não um dashboard estático sobre dados sintéticos).
- Responder perguntas de negócio concretas de um lojista de e-commerce: quanto estou
  faturando, quais clientes têm risco de cancelar, quanto devo esperar vender, quais
  produtos/países geram mais receita, e o que fazer com um cliente em risco.
- Construir a aplicação inteira (frontend, backend, ML, infraestrutura) com o mesmo
  nível de cuidado que um sistema em produção: validação de dados, testes automatizados,
  tratamento de erro, observabilidade — não só o "caminho feliz".
- Demonstrar rigor estatístico de experimentação de produto (A/B testing que não infla
  falso-positivo, redução de variância, inferência bayesiana, uplift) e de métricas de
  receita recorrente (MRR/ARR/GRR/NRR com bridge que reconcilia exatamente).

---

## 🔬 Linha de Desenvolvimento

- ETL e modelagem dimensional (esquema estrela) sobre dataset real de e-commerce.
- Machine Learning aplicado a negócio (churn, séries temporais, recomendação).
- Arquitetura orientada a eventos e CQRS (Kafka/RabbitMQ, read models materializados).
- Experimentação de produto / inferência causal (A/B, power analysis, CUPED, testes
  sequenciais, Bayesian, uplift/CATE).
- FP&A de SaaS (MRR/ARR, GRR/NRR, cohorts de receita, revenue bridge, forecast, cenários).
- Engenharia full-stack de produto (API, dashboard, filas, PWA, observabilidade).

---

## 🏗️ Arquitetura

```text
UCI Online Retail II (dataset real, 2009–2011)
              │
              ▼
   ETL (Python/pandas) — limpeza, deduplicação,
   modelagem em esquema estrela
              │
              ▼
   Data Warehouse (SQLite / PostgreSQL)
   fact_sales · dim_customer · dim_product · dim_country · dim_date
              │
      ┌───────┼────────────────┐
      ▼       ▼                ▼
   Churn   Previsão de      Motor de
  (RF/RFM)   Demanda      Recomendação
  (sklearn)  (Holt-Winters)  (coocorrência)
      │       │                │
      └───────┴────────┬───────┘
                        ▼
        API (Node.js + Express + TypeScript)
        REST · GraphQL (/graphql) · WebSocket (Socket.io)
        Fila assíncrona (BullMQ + Redis) · /metrics (Prometheus)
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
        Web (Next.js)         platform/ (event-driven + CQRS)
        Dashboard · Kanban    bus (Kafka/RabbitMQ) · read models

(standalone, paralelos ao pipeline acima — bibliotecas Python, não rotas HTTP)
   experimentation/            data-platform/revenue/
   A/B · power · CUPED ·       MRR/ARR · GRR/NRR · cohorts ·
   sequential · Bayesian ·     bridge · forecast · scenarios
   uplift/CATE                 (dataset sintético de assinaturas)
```

| Módulo | Função | Teste |
|---|---|---|
| `data-platform/ingestion/` | ETL xlsx → Data Warehouse dimensional | `quality/checks.py` (7 checagens) |
| `data-platform/ml/` | Churn (RF/RFM), previsão de demanda (Holt-Winters), recomendação | métricas reais (precision/recall/MAE/RMSE) |
| `experimentation/` | A/B testing, power, CUPED, sequential (mSPRT), Bayesian, uplift (T-learner) | 30 testes vs. `statsmodels`/`scipy`/Monte Carlo |
| `data-platform/revenue/` | MRR/ARR, GRR/NRR, cohorts, bridge, forecast, scenarios | 26 testes, bridge reconciliado exatamente mês a mês |
| `apps/api` | REST + GraphQL + WebSocket + fila (BullMQ) | Vitest + testes manuais (login/JWT/CRUD) |
| `apps/web` | Dashboard + Kanban de retenção + PWA | `next build`/`next lint` + Playwright E2E |
| `platform/messaging` | Bus event-driven (InMemory/Kafka/Rabbit) | testes contra Redpanda + RabbitMQ reais (Docker) |
| `platform/read-models` | CQRS — `ChurnReadModel` (node:sqlite) | teste de equivalência replay ↔ incremental |

---

## ⚙️ Funcionamento

1. ETL lê o xlsx do UCI Online Retail II, limpa/deduplica e carrega o Data Warehouse
   dimensional (SQLite ou PostgreSQL).
2. `quality/checks.py` roda 7 checagens (schema, nulos, integridade referencial,
   duplicidade, volume mínimo) com exit code para plugar em CI.
3. Os modelos de ML (`data-platform/ml/`) leem do warehouse e geram CSVs de churn,
   previsão de demanda e recomendações.
4. A API (`apps/api`) expõe os dados via REST/GraphQL, emite alertas de churn em tempo
   real via WebSocket, e processa a fila de win-back (BullMQ/Redis) em background.
5. O dashboard (`apps/web`) consome a API, exibe KPIs, gráficos e o Kanban de Ações de
   Retenção (chat em tempo real por card, notas em blocos, funil por estágio).
6. Em paralelo, `platform/messaging` publica/consome domain events (Kafka ou RabbitMQ)
   e `platform/read-models` materializa um read model CQRS a partir desses eventos.
7. `experimentation/` e `data-platform/revenue/` são bibliotecas Python standalone:
   rodam via `run_report.py`/scripts próprios e geram CSVs/JSON em
   `data-platform/warehouse/`, sem rota HTTP própria (decisão de escopo documentada nos
   `__init__.py` de cada módulo).

Fluxo ponta a ponta de alerta de churn (validado de verdade nesta revisão):

```text
Cliente classificado como alto risco (score do modelo RF)
      ↓
API detecta e emite evento via WebSocket (Socket.io)
      ↓
Dashboard recebe alerta em tempo real
      ↓
Analista cria card no Kanban de retenção → chat → nota → win-back (fila BullMQ)
```

---

## 🧠 Validação / Verificação

| Camada | O que prova | Resultado |
|---|---|---|
| Qualidade de dados (`quality/checks.py`) | Schema, nulos, integridade referencial, duplicidade, volume | 7/7 checagens passando |
| Modelo de churn | Classificação sem vazamento de dados (snapshot + holdout futuro) | precision 0,782 / recall 0,791 / F1 0,787 / ROC-AUC 0,813 |
| Previsão de demanda | Série temporal com holdout real de 30 dias | MAE 13.758 / RMSE 28.347 / MAPE 24,1% |
| `experimentation/` (30 testes) | Testes estatísticos contra implementações independentes | `two_proportion_z_test` reproduz `proportions_ztest` do `statsmodels` a `rel=1e-9`; mSPRT validado com 2.000 streams Monte Carlo sob H0 (falso-positivo ≤ alpha+margem); sample size (baseline 20%, MDE 5pp) converge para n≈1.091, valor publicado pela calculadora de Evan Miller |
| `data-platform/revenue/` (26 testes) | Identidade do bridge (`ending = starting + new + expansion + contraction + churn`) | Verificada **exatamente** (não aproximadamente) mês a mês, mais casos hand-calculados (3 clientes, 2 meses) e invariantes (GRR ≤ 100%, NRR ≥ GRR) |
| `platform/messaging` | Bus event-driven contra broker real | `KafkaBus.roundtrip()` / `RabbitBus.consumeOnce()` verdes contra Redpanda + RabbitMQ via Docker |
| `platform/read-models` | Read model CQRS | Equivalência replay ↔ incremental confirmada por teste |
| Testes E2E (Playwright) | Fluxo crítico de login, dashboard, Kanban | Suíte verde |

Re-executado nesta auditoria: `pytest experimentation/tests data-platform/tests` →
**56 passed** (Python 3.10 canônico).

---

## 🧪 Desenvolvimento Experimental

**Achados reais (não plantados):**

| Bug / hipótese | O que foi testado | Causa real | Correção |
|---|---|---|---|
| `dim_product` reportava 4.631 linhas no log mas ficava com 0 no banco | Carga inicial do Data Warehouse | Falha silenciosa do `pandas.to_sql` (reporta sucesso com a tabela vazia) | Checagem pós-insert (`SELECT COUNT(*)` vs. tamanho do DataFrame) adicionada ao ETL — motivo concreto do módulo de qualidade de dados |
| `DELETE` de card do Kanban quebrava para clientes com comentário | Teste de ponta a ponta do Kanban (criar → comentar → deletar) | `FOREIGN KEY constraint failed` — schema tinha `REFERENCES` real bloqueando o comportamento documentado ("não apaga em cascata") | `REFERENCES` removida do schema; vínculo lógico mantido sem a constraint |
| Build da API falhava (`tsc`) | `npm run build` | `jwt.sign()` não compilava contra os tipos do `jsonwebtoken` v9 (`expiresIn` genérico) | Cast explícito para `jwt.SignOptions["expiresIn"]` |
| Build do dashboard falhava | `next build` | `useSWR(path, fetcher)` sem generic inferia `{}`, quebrando acesso a campos | Interfaces + generics explícitos em cada `useSWR<T>()`, nomes de campo conferidos contra a API real |
| Teste de bridge de receita falhava com valores idênticos | `pivot[0].dropna() == pytest.approx(1.0)` | Comparação elemento-a-elemento numa `Series` do pandas contra `pytest.approx` de um escalar retorna `False` mesmo com valores iguais | Substituído por `np.testing.assert_allclose` |
| `npm install` travava com `TAR_ENTRY_ERROR`/`EINVAL` | Instalação direta na pasta sincronizada por Google Drive | Cliente do Drive não aguenta a criação rápida de milhares de arquivos pequenos | Instalar fora (`C:\tmp`) e copiar `node_modules` de volta via `robocopy` — regra permanente em `~/.claude/rules/node-env.md` |

Log detalhado, cronológico, de cada sessão (incluindo os bugs de integração entre os
dois subagentes da v2.0.0) em [`docs/HISTORICO.md`](docs/HISTORICO.md).

---

## 🛠️ Tecnologias

| Categoria | Tecnologia |
|---|---|
| **Dados / ML** | Python, pandas, scikit-learn (Random Forest, T-learner), statsmodels (Holt-Winters, testes estatísticos), scipy, pyarrow |
| **Experimentação** | `experimentation/` — testes z/t, power analysis, CUPED, mSPRT, A/B bayesiano, uplift/CATE |
| **FP&A / Revenue** | `data-platform/revenue/` — MRR/ARR, GRR/NRR, cohorts, bridge, forecast, scenario planner |
| **Data Warehouse** | SQLite (dev) / PostgreSQL (schema pronto para produção) |
| **Backend** | Node.js, TypeScript, Express, GraphQL (`graphql-yoga`), Socket.io, BullMQ, Zod |
| **Frontend** | Next.js 14 (App Router), React, Tailwind CSS, Recharts, SWR |
| **Event-driven / CQRS** | Kafka (via `kafkajs`), RabbitMQ (via `amqplib`), `node:sqlite` (read models) |
| **Autenticação** | JWT |
| **Fila / cache** | Redis |
| **Observabilidade** | Prometheus, Grafana |
| **Infraestrutura** | Docker, Docker Compose |
| **Testes** | pytest, Vitest, Playwright, testes contra broker real (Redpanda/RabbitMQ) |
| **CI/CD** | GitHub Actions (`ci.yml`, incluindo job `platform-integration`) |
| **Conceitos** | ETL, modelagem dimensional, RFM, séries temporais, sistemas de recomendação, event-driven architecture, CQRS, A/B testing, power analysis, CUPED, testes sequenciais, inferência bayesiana, uplift/CATE, MRR/ARR/GRR/NRR, cohort analysis, revenue bridge |

---

## 📊 Resultados

**Pipeline principal (dataset real, UCI Online Retail II):**
- Data Warehouse: 793.609 linhas em `fact_sales`, 5.878 clientes, 4.631 produtos,
  41 países.
- Qualidade de dados: 7/7 checagens automatizadas passando.
- Churn: precision 0,782 / recall 0,791 / F1 0,787 / ROC-AUC 0,813 (janela de 90 dias,
  5.281 clientes analisados).
- Previsão de demanda: MAE 13.758 / RMSE 28.347 / MAPE 24,1% (série de 739 dias,
  holdout de 30 dias).
- Recomendação: 18.742 pares produto→produto, 17.603 recomendações para 5.878 clientes.

**`experimentation/` (v2.1.0, dataset de simulação/Monte Carlo):**
- 30 testes passando, verificados contra `statsmodels`/`scipy`, simulação Monte Carlo
  (mSPRT, 2.000 streams sob H0) e casos hand-calculados (sample size baseline 20%/MDE
  5pp → n≈1.091, igual à calculadora de Evan Miller).

**`data-platform/revenue/` (v2.1.0, dataset sintético de assinaturas, seed fixa=42,
1.200 clientes, 30 meses):**
- **MRR final ≈ $82.787** · **ARR ≈ $993.444**.
- **GRR médio 95,7%** · **NRR médio 99,4%**.
- Scenario planner, mês 12: pessimista **$50.724** / base **$77.954** / otimista
  **$111.339**.
- 26 testes passando, com a identidade do bridge de MRR
  (`ending = starting + new + expansion + contraction + churn`) verificada
  **exatamente** (não aproximadamente) em todo mês do dataset, não só num caso isolado.

**Total de testes Python re-executados nesta auditoria:** `pytest experimentation/tests
data-platform/tests` → **56 passed** em 19,35s (Python 3.10 canônico).

Todos os números de `experimentation/` e `data-platform/revenue/` vêm de dados
**sintéticos** (gerados com seed fixa, documentados como tal) — não representam receita
real de nenhuma empresa. Ver `## ⚠️ Limitações`.

---

## 🖼️ Evidências

Sem screenshots do dashboard ou dos painéis capturados nesta revisão (ambiente sem
browser interativo durante a sessão de auditoria). As evidências de funcionamento real
são as saídas de teste/execução citadas em `## 📊 Resultados` e `## 🧠 Validação`: os
793.609 registros do Data Warehouse, as métricas de ML calculadas sobre o dataset real,
os 56 testes Python re-executados nesta sessão, e os testes de `platform/messaging`
contra brokers reais (Redpanda/RabbitMQ via Docker).

---

## 🚀 Aplicações

- Referência de pipeline de dados ponta a ponta para e-commerce (ETL → DW → ML → API →
  dashboard), com o mesmo rigor de um sistema em produção.
- Material de estudo/demonstração de arquitetura orientada a eventos e CQRS aplicados a
  um domínio de negócio real.
- Biblioteca de referência para experimentação de produto (A/B testing que não infla
  falso-positivo, CUPED, inferência bayesiana, uplift) e para métricas de FP&A de SaaS
  (MRR/ARR/GRR/NRR, revenue bridge).

---

## 🔭 Visão de Longo Prazo

```text
Hoje: aplicação completa validada localmente, nunca implantada em nuvem pública
      ↓
Deploy em produção (provedor a escolher) + PostgreSQL real
      ↓
Provedor de e-mail real para a fila de win-back (hoje simulado em log local)
      ↓
experimentation/ e data-platform/revenue/ conectados ao dashboard Next.js
(hoje bibliotecas Python standalone gerando CSV/JSON)
      ↓
Dataset de billing real (revenue/) e dataset Olist opcional (pipeline principal)
      ↓
Extensões de experimentação (X-learner, multi-armed bandits) se o escopo justificar
```

---

## 🗺️ Roadmap

- **F0 — Escopo inicial (v1.0.0)** ✅ Concluída — ETL, Data Warehouse, churn/forecast,
  API REST, dashboard, Docker/CI/E2E básico.
- **F1 — Ações de Retenção (v2.0.0 → v2.0.2)** ✅ Concluída — Kanban, chat tempo real,
  recomendação, GraphQL, fila assíncrona, PWA, `/metrics`; hardening de `npm
  install`/TypeScript/bugs reais nas versões `.1`/`.2`.
- **F2 — Event-driven + CQRS (`platform/`)** ✅ Concluída — bus Kafka/RabbitMQ testado
  contra broker real, read models CQRS com equivalência replay ↔ incremental.
- **F3 — Experimentação + Revenue (v2.1.0)** ✅ Concluída — `experimentation/` (30
  testes) e `data-platform/revenue/` (26 testes), fechando gaps de auditoria de
  portfólio.
- **F4 — Deploy em produção** ⏳ Planejada — provedor de nuvem, PostgreSQL real,
  provedor de e-mail real (ver `ROADMAP.md`).
- **F5 — Conectar `experimentation/`/`revenue/` ao produto** ⏳ Planejada — hoje são
  bibliotecas Python standalone, não rotas HTTP/componentes de dashboard.

---

## 🕓 Histórico e Mudanças

| Versão | Data | O que mudou |
|---|---|---|
| v1.0.0 | 2026-08-19 | ETL → Data Warehouse → churn/forecast → API REST → dashboard → Docker/CI/E2E básico |
| v2.0.0 | 2026-08-19 | Kanban de Ações de Retenção, chat em tempo real, recomendação, GraphQL, fila assíncrona (BullMQ), PWA offline, `/metrics` |
| v2.0.1 | 2026-08-20 | 2 bugs reais de TypeScript corrigidos, ESLint configurado nas duas apps, teste unitário real adicionado, `.env`/ícones PWA gerados |
| v2.0.2 | 2026-08-21 | `node_modules` materializado dentro das pastas reais do projeto, bug real do `DELETE` do Kanban corrigido, cache do webpack desabilitado, error handler JSON global |
| v2.1.0 | 2026-10-07 | `experimentation/` (A/B, power, CUPED, sequential, Bayesian, uplift — 30 testes) e `data-platform/revenue/` (MRR/ARR/GRR/NRR, cohorts, bridge, forecast, scenarios — 26 testes); `ROADMAP.md` criado |

Changelog completo em [`CHANGELOG.md`](CHANGELOG.md); histórico de decisões e sessões em
[`docs/HISTORICO.md`](docs/HISTORICO.md).

---

## 🔮 Próximos Passos

**Concluído nesta versão (v2.1.0):**
- ✅ `experimentation/` e `data-platform/revenue/`, 56 testes novos passando
  (re-verificado nesta auditoria), `ROADMAP.md` consolidado.

**Dependem de terceiros/decisão do usuário:**
- [ ] Escolher e configurar um provedor de deploy (Vercel/Render/Fly.io etc.).
- [ ] Subir PostgreSQL em produção (schema já pronto em
  `data-platform/warehouse/schema_postgres.sql`).
- [ ] Plugar um provedor de e-mail real (Resend/SendGrid) na fila de win-back — hoje
  simulado em log local.
- [ ] Dataset Olist (opcional) — requer conta Kaggle + token pessoal.

**Próximos técnicos (o que faria numa v2.2):**
- Conectar `experimentation/` e `data-platform/revenue/` ao dashboard Next.js (hoje
  geram CSV/JSON, não uma rota `GET /revenue/*`/`GET /experiments/*`).
- Trocar o dataset sintético de `revenue/` por um dataset de billing real (ex.:
  exportação de demonstração de Stripe/Chargebee).
- Modelar reativação/win-back no gerador sintético de assinaturas.
- Avaliar X-learner (CATE) e multi-armed bandits em `experimentation/` se o escopo do
  Kanban de retenção justificar.

---

## ▶️ Como rodar localmente

Pré-requisitos: Python 3.10, Node.js 18+, Docker Desktop (Postgres/Redis/Prometheus/
Grafana/Kafka/RabbitMQ via `infra/docker/docker-compose.yml`).

```bash
# Testes Python (experimentação + revenue — 56 testes)
python -m pytest experimentation/tests data-platform/tests -v

# Pipeline de dados principal (ETL + ML + qualidade)
python data-platform/ingestion/extract_transform_load.py
python data-platform/quality/checks.py
python data-platform/ml/churn_model.py

# Relatório de receita SaaS (gera MRR/ARR/GRR/NRR/bridge/forecast/scenarios)
python data-platform/revenue/run_report.py

# API + Web (dentro de cada pasta, node_modules já materializado localmente)
cd apps/api && npm run build && npm test && npm run dev
cd apps/web && npm run build && npm run dev

# Testes E2E
npx playwright test
```

| Ambiente | Observação |
|---|---|
| Pasta sincronizada (Google Drive) | `npm install` direto na pasta falha (`TAR_ENTRY_ERROR`) — instalar em `C:\tmp\<nome>` e copiar `node_modules` de volta via `robocopy`; cache do webpack do Next.js desabilitado (`config.cache = false`) pelo mesmo motivo |
| Docker Compose (`infra/docker/`) | Sobe Postgres, Redis, API, Web, Prometheus, Grafana — copiar `.env.example` para `.env` antes |
| CI (GitHub Actions) | `ci.yml` valida `data-platform` (qualidade), `api`/`web` (lint/build/test) e `platform-integration` (bus contra Kafka/RabbitMQ real) a cada push/PR |

---

## 📁 Estrutura do repositório

```text
data-platform/     Engenharia e Ciência de Dados (Python)
  ingestion/          ETL: xlsx → Data Warehouse dimensional
  quality/             Checagens automatizadas de qualidade de dados
  warehouse/            Schema SQL, Data Warehouse e relatórios gerados
  ml/                  Churn, previsão de demanda, motor de recomendação
  revenue/             MRR/ARR, GRR/NRR, cohorts, bridge, forecast, scenarios
                       (dataset sintético de assinaturas — ver docs/HISTORICO.md)
  tests/               26 testes de data-platform/revenue/

experimentation/   A/B testing, power/sample size, CUPED, sequential testing (mSPRT),
                   A/B bayesiano, uplift/CATE (Python, standalone)
  tests/               30 testes

apps/
  api/                Node.js + TypeScript + Express — REST + GraphQL + WebSocket
  web/                Next.js + Tailwind + Recharts — dashboard + Kanban de retenção

platform/
  messaging/          Event-driven: bus (InMemory/Kafka/Rabbit) + schemas + demo + testes
  read-models/        CQRS: ChurnReadModel (node:sqlite) + teste replay ↔ incremental

infra/
  docker/              docker-compose.yml (Postgres, Redis, API, Web, Prometheus, Grafana)
  monitoring/          Configuração do Prometheus

tests/e2e/           Testes Playwright (login, dashboard, Kanban de retenção)
docs/                 HISTORICO.md, MENTORIA.md, ADRs (docs/adr/), event-driven-architecture.md
.github/workflows/    CI (lint, build, testes, qualidade de dados, integração platform/)
```

---

## 📚 Documentação

| Documento | Conteúdo |
|---|---|
| [`CHANGELOG.md`](CHANGELOG.md) | O que mudou em cada versão (Keep a Changelog) |
| [`ROADMAP.md`](ROADMAP.md) | Próximos passos consolidados (deploy, dados, extensões de `experimentation/`/`revenue/`) |
| [`docs/HISTORICO.md`](docs/HISTORICO.md) | Log cronológico completo: decisões, bugs encontrados/corrigidos, resultados reais de cada execução |
| [`docs/MENTORIA.md`](docs/MENTORIA.md) | Racional completo de cada decisão técnica e como defender o projeto em entrevista |
| [`docs/adr/`](docs/adr/) | ADR-001 (Kafka vs. RabbitMQ), ADR-002 (CQRS/read models), ADR-003 (manter Next.js) |
| [`docs/event-driven-architecture.md`](docs/event-driven-architecture.md) | Arquitetura orientada a eventos da camada `platform/` |

---

## ⚠️ Limitações

- Deploy em produção ainda não realizado — aplicação validada apenas localmente.
- `experimentation/` e `data-platform/revenue/` são bibliotecas Python standalone,
  **não** conectadas à API Express nem ao dashboard Next.js — geram CSV/JSON, não rotas
  HTTP.
- `data-platform/revenue/` usa um dataset **100% sintético** (seed fixa), sem relação
  com o UCI Online Retail II nem com dados de empresas reais; não modela
  reativação/win-back de clientes.
- Provedor de e-mail da fila de win-back é simulado (log local), não um envio real.
- `ansible`/dependências nativas não se aplicam aqui, mas o PostgreSQL de produção
  ainda não foi testado com a aplicação (schema pronto, nunca usado em runtime real).
- X-learner e multi-armed bandits ficaram deliberadamente fora do escopo de
  `experimentation/` (ver `ROADMAP.md` para o racional).
- Sem screenshots do dashboard/Kanban capturados nesta revisão (ver `## 🖼️ Evidências`).

---

## Status

🟡 **Em desenvolvimento — v2.1.0**, deploy público ainda pendente.

A aplicação está completa e funcional localmente: pipeline de dados, ML, API, dashboard,
event-driven/CQRS, e os dois módulos novos de experimentação e receita SaaS (56 testes
re-verificados nesta auditoria). O que falta para "concluído" é o deploy em um provedor
de nuvem e a conexão dos módulos novos ao produto — ambos documentados em
`ROADMAP.md`.

---

## Contexto / Observações

- Projeto de portfólio, 100% público, sem dados ou credenciais reais de terceiros —
  dataset público (UCI Online Retail II) para o pipeline principal; `data-platform/
  revenue/` usa um dataset sintético próprio (seed fixa), sem relação com empresas
  reais.
- Números de MRR/ARR/GRR/NRR e das métricas de `experimentation/` são medições reais
  sobre dados de laboratório/simulação (não estimativas de ferramenta), com seus limites
  declarados em `## ⚠️ Limitações`.
- Log técnico completo de decisões, bugs encontrados/corrigidos e resultados reais de
  cada execução em [`docs/HISTORICO.md`](docs/HISTORICO.md).

---

## 🔗 Projetos Relacionados

Nenhuma dependência técnica direta com outros repositórios do portfólio foi
estabelecida nesta revisão — RetentIQ é um produto standalone.

---

## 🤖 Autor

**Yuri Fernando Dubbern**

Engenharia Elétrica · Ciência da Computação · Inteligência Artificial ·
Sistemas Embarcados · Projeto de Hardware · Pesquisa e Desenvolvimento

[LinkedIn](https://www.linkedin.com/in/yuridubbern) · [GitHub](https://github.com/Yuri-Fernando) · [Lattes](http://lattes.cnpq.br/7151392692642166) · [Linktree](https://linktr.ee/yuri.f.dubbern)

---

## Licença

Sem arquivo `LICENSE` nesta revisão do repositório — código publicado publicamente no
GitHub, sem licença formal declarada. Recomendação registrada em `ROADMAP.md`/pendências
futuras: adicionar uma licença explícita (ex.: MIT) antes de qualquer uso por terceiros.
