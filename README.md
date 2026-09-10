# RetentIQ

Python · Node.js · TypeScript · Next.js · Express · GraphQL · Kafka · RabbitMQ · CQRS · Machine Learning · SQLite/PostgreSQL · Redis · Docker · Prometheus

## Status

🟡 **Em desenvolvimento** — aplicação completa e funcional localmente (API, dashboard,
pipeline de dados e modelos de ML todos rodando e testados de ponta a ponta); falta o
deploy em um provedor de nuvem para ficar acessível publicamente.

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
| Event-Driven Architecture — abstração de bus + demo | ✅ `platform/messaging/` (InMemoryBus + demo + 4 testes, Node puro) |
| Schemas de domain events (JSON Schema) | ✅ `platform/messaging/schemas/` |
| ADRs (Kafka vs RabbitMQ · CQRS · manter Next.js) | ✅ `docs/adr/` |
| Kafka/RabbitMQ com broker real | ✅ testado — `KafkaBus.roundtrip()` / `RabbitBus.consumeOnce()` verdes contra Redpanda + RabbitMQ (Docker). `platform/package.json` declara `kafkajs`/`amqplib`; job `platform-integration` no CI |
| Read models CQRS materializados | ✅ `platform/read-models/` — `ChurnReadModel` (SQLite embutido do Node) + teste de equivalência **replay ↔ incremental** |
| CI da camada platform | ✅ job `platform-messaging` no `.github/workflows/ci.yml` (bus + read models) |

## Descrição geral

RetentIQ é uma plataforma full-stack de inteligência de receita e retenção de clientes
para e-commerce: ingestão de dados → Data Warehouse dimensional → modelos de Machine
Learning (churn, previsão de demanda, recomendação) → API (REST + GraphQL + WebSocket)
→ dashboard web → observabilidade (Prometheus) → testes automatizados (unitários e
E2E).

O projeto nasceu da fusão de dois repertórios de estudo — um de projetos de
desenvolvimento full-stack e outro de projetos de engenharia/ciência de dados — num
único produto de dados ponta a ponta, em vez de dois projetos isolados e mais rasos.
É um projeto de portfólio, construído para demonstrar competência tanto na construção
do sistema (autenticação, tempo real, filas, APIs, testes, CI/CD) quanto na extração de
inteligência de negócio a partir de dados reais (ETL, modelagem dimensional, ML,
validação de qualidade).

## Objetivo

- Demonstrar um pipeline de dados completo, com dataset real, do bruto à decisão de
  negócio (não um dashboard estático sobre dados sintéticos).
- Responder perguntas de negócio concretas de um lojista de e-commerce: quanto estou
  faturando, quais clientes têm risco de cancelar, quanto devo esperar vender, quais
  produtos/países geram mais receita, e o que fazer com um cliente em risco.
- Construir a aplicação inteira (frontend, backend, ML, infraestrutura) com o mesmo
  nível de cuidado que um sistema em produção: validação de dados, testes automatizados,
  tratamento de erro, observabilidade — não só o "caminho feliz".

## Principais funcionalidades

- **Dashboard de métricas** — receita diária, pedidos, ticket médio, ranking de
  produtos e países por receita.
- **Predição de churn** — modelo de classificação (Random Forest sobre features RFM)
  com score de 0 a 1 e segmentação Alto/Médio/Baixo risco, com alerta em tempo real via
  WebSocket quando novos clientes de alto risco são identificados.
- **Previsão de demanda** — série temporal (Holt-Winters com sazonalidade semanal) para
  os próximos 30 dias de receita.
- **Kanban de Ações de Retenção** — cards por cliente em risco, editor de notas em
  blocos (estilo bloco de texto/checklist), chat em tempo real por card (Socket.io) e
  funil de retenção (alto risco → contatado → em andamento → resolvido).
- **Motor de recomendação** — coocorrência de produtos por nota fiscal, usado para
  montar ofertas de win-back personalizadas.
- **Fila assíncrona de win-back** — disparo de e-mail de retenção processado em
  background (BullMQ/Redis), sem bloquear a requisição HTTP.
- **API GraphQL** — alternativa de leitura à API REST, mesma camada de autenticação.
- **PWA offline** — cache-first das rotas principais do dashboard.
- **Observabilidade** — endpoint `/metrics` (Prometheus) e stack de monitoramento via
  Docker Compose (Prometheus + Grafana).
- **Qualidade de dados automatizada** — 7 checagens (schema, nulos, integridade
  referencial, duplicidade, volume mínimo) com relatório e exit code para plugar em CI.

## Arquitetura / Pipeline

```
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
                        ▼
        Web (Next.js + Tailwind + Recharts)
        Dashboard · Kanban de Retenção · PWA offline
```

## Tecnologias e conceitos

| Categoria | Tecnologia |
|---|---|
| Dados / ML | Python, pandas, scikit-learn (Random Forest), statsmodels (Holt-Winters), pyarrow |
| Data Warehouse | SQLite (dev) / PostgreSQL (schema pronto para produção) |
| Backend | Node.js, TypeScript, Express, GraphQL (graphql-yoga), Socket.io, BullMQ, Zod |
| Frontend | Next.js 14 (App Router), React, Tailwind CSS, Recharts, SWR |
| Autenticação | JWT |
| Fila / cache | Redis |
| Observabilidade | Prometheus, Grafana |
| Infraestrutura | Docker, Docker Compose |
| Testes | Vitest (unitário), Playwright (E2E) |
| CI/CD | GitHub Actions |
| Conceitos | ETL, modelagem dimensional (esquema estrela), validação de qualidade de dados, RFM, séries temporais, sistemas de recomendação, filas assíncronas, WebSocket, GraphQL, PWA, observabilidade |

## Desenvolvimento

O projeto foi construído em duas grandes entregas, registradas com versionamento
semântico e log técnico detalhado de decisões, bugs encontrados/corrigidos e
resultados reais de cada execução:

```
v1.0.0 — Escopo inicial
  ETL → Data Warehouse → churn/forecast → API REST → dashboard → Docker/CI/E2E básico
              ↓
v2.0.0 — Módulo de Ações de Retenção
  Kanban + chat em tempo real + notas em blocos, motor de recomendação,
  GraphQL, fila assíncrona, PWA offline, /metrics
              ↓
v2.x — Hardening
  bugs reais corrigidos (tipagem, integridade referencial, tratamento de erro
  global), suíte de testes e lint configuradas nas duas apps, validação de
  ponta a ponta (build/lint/test/dev) rodando de verdade
```

Decisões técnicas relevantes:

- **Dataset real, não sintético** — UCI Online Retail II (~1,07M linhas brutas,
  varejista online do Reino Unido, 2009–2011), escolhido por ser público, sem exigir
  credenciais/API key, e rico o suficiente para sustentar todas as análises sem
  precisar inventar nenhuma coluna.
- **Checagem pós-carga no ETL** — o pipeline verifica `SELECT COUNT(*)` contra o
  tamanho do DataFrame após cada `INSERT`, porque uma falha silenciosa real
  (`pandas.to_sql` reportando sucesso com a tabela vazia) foi encontrada durante o
  desenvolvimento — é o motivo concreto por trás do módulo de qualidade de dados.
- **Degradação graciosa de infraestrutura opcional** — se o Redis não estiver
  disponível, o rate limiter cai para memória e a fila de win-back fica desabilitada
  sem derrubar a API; se os CSVs de ML ainda não foram gerados, as rotas dependentes
  devolvem `[]`/erro tratado em vez de 500.
- **Conversão de tipo centralizada, não espalhada** — valores lidos de CSV chegam como
  string; a conversão para número acontece uma única vez no backend (não em cada tela
  do frontend), depois de um bug real de tipagem ter sido encontrado por essa razão.

## Resultados / Aplicação

Pipeline de dados executado de ponta a ponta neste dataset real:

- **Data Warehouse:** 793.609 linhas em `fact_sales`, 5.878 clientes, 4.631 produtos,
  41 países.
- **Qualidade de dados:** 7/7 checagens automatizadas passando.
- **Modelo de churn:** precision 0,782 / recall 0,791 / F1 0,787 / ROC-AUC 0,813
  (janela de avaliação de 90 dias, 5.281 clientes analisados).
- **Previsão de demanda:** MAE 13.758 / RMSE 28.347 / MAPE 24,1% (série de 739 dias,
  holdout de 30 dias).
- **Motor de recomendação:** 18.742 pares produto→produto, 17.603 recomendações
  geradas para 5.878 clientes.

Aplicação validada rodando de ponta a ponta (não só compilando): build, lint e testes
automatizados limpos na API e no web; servidor da API testado com login real, emissão
de JWT, CRUD completo do Kanban de retenção e leitura do Data Warehouse; `next build`
e `next dev` do dashboard testados servindo a aplicação real.

## Estrutura do projeto

```
data-platform/     Engenharia e Ciência de Dados (Python)
  ingestion/          ETL: xlsx → Data Warehouse dimensional
  quality/             Checagens automatizadas de qualidade de dados
  warehouse/            Schema SQL, Data Warehouse e relatórios gerados
  ml/                  Churn, previsão de demanda, motor de recomendação

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
docs/                 Log técnico, histórico, ADRs (docs/adr/), event-driven-architecture.md
.github/workflows/    CI (lint, build, testes, checagem de qualidade de dados)
```

## Próximos passos

O que falta para considerar o projeto encerrado:

- **Deploy em produção** — nenhum provedor foi escolhido/configurado ainda
  (Vercel/Render/Fly.io etc.); hoje a aplicação roda validada localmente.
- **Provedor de e-mail real** para a fila de win-back — hoje o envio é simulado (log
  local); plugar um provedor como Resend/SendGrid.
- **PostgreSQL em produção** — schema já pronto (`data-platform/warehouse/schema_postgres.sql`)
  e stack Docker já configurada; falta subir e apontar a aplicação para lá.
- **Dataset Olist (opcional)** — trocar o dataset do Reino Unido pelo dataset
  brasileiro Olist, mais comum em portfólios de dados nacionais.

## Contexto / Observações

- Projeto de portfólio, 100% público, sem dados ou credenciais reais de terceiros —
  dataset público (UCI), credenciais de demonstração geradas localmente.
- Log técnico completo de decisões, bugs encontrados/corrigidos e resultados reais de
  cada execução em [`docs/HISTORICO.md`](docs/HISTORICO.md).

## Autor
Engenheiro de Dados · AI Engineer · Enterprise Automation · IaC · DevOps · Robótica e Automação

[LinkedIn](https://www.linkedin.com/in/yuridubbern) · [GitHub](https://github.com/Yuri-Fernando) · [Lattes](http://lattes.cnpq.br/7151392692642166) · [Linktree](https://linktr.ee/yuri.f.dubbern)

