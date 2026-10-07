# Roadmap

Próximos passos do RetentIQ, consolidados aqui (antes espalhados entre o README e
`docs/HISTORICO.md`). Ver [`CHANGELOG.md`](CHANGELOG.md) para o que já foi entregue.

## Pendente

### Infraestrutura / Deploy

- **Deploy em produção** — nenhum provedor foi escolhido/configurado ainda
  (Vercel/Render/Fly.io etc.); hoje a aplicação roda validada localmente.
- **PostgreSQL em produção** — schema já pronto
  (`data-platform/warehouse/schema_postgres.sql`) e stack Docker já configurada;
  falta subir e apontar a aplicação para lá.
- **Provedor de e-mail real** para a fila de win-back — hoje o envio é simulado (log
  local, `apps/api/src/queue/winbackWorker.ts`); plugar um provedor como
  Resend/SendGrid.

### Dados

- **Dataset Olist (opcional)** — trocar o dataset do Reino Unido (UCI Online Retail
  II) pelo dataset brasileiro Olist, mais comum em portfólios de dados nacionais.
  Requer conta Kaggle + token `kaggle.json` (credenciais pessoais, não incluídas).

### `experimentation/` — possíveis extensões futuras

Escopo atual (v2.1.0): A/B testing (z-test/t-test), power/sample size, CUPED,
sequential testing (mSPRT), A/B bayesiano, uplift/CATE (T-learner). Ficou de fora
deliberadamente (ver `experimentation/__init__.py` para a decisão de escopo):

- **X-learner** para CATE — o T-learner implementado é mais simples e já cobre o
  caso de uso do Kanban de retenção; X-learner tende a performar melhor com braços de
  tamanho desbalanceado, mas adiciona complexidade (precisa de um modelo de
  propensão) sem um ganho claro no dataset sintético atual.
- **Multi-armed bandits** (ex.: Thompson Sampling online) — fora de escopo porque o
  gap da auditoria pedia "A/B, power, CUPED, sequential, Bayesian, uplift", não
  alocação adaptativa de tráfego.
- **Integração com o dashboard Next.js** — hoje `experimentation/` é uma biblioteca
  Python standalone, não uma rota HTTP; conectar ao dashboard exigiria uma camada de
  API nova (fora do escopo desta entrega, que priorizou profundidade estatística
  correta sobre superfície de produto).

### `data-platform/revenue/` — possíveis extensões futuras

Escopo atual (v2.1.0): MRR/ARR, GRR/NRR, cohorts de receita, bridge de movimento
(new/expansion/contraction/churn), forecast de tendência linear + budget sintético
vs. actual, scenario planner. Ficou de fora deliberadamente:

- **Dataset de billing real** — hoje é 100% sintético (seed fixa, documentado em
  `revenue/synthetic_subscriptions.py`); não há dataset público de assinatura SaaS
  tão acessível quanto o UCI Online Retail II usado no resto do projeto. Trocar por
  um dataset real (ex.: exportação de um Stripe/Chargebee de demonstração) é a
  melhoria mais valiosa se o módulo crescer.
- **Reativação/win-back no modelo de assinatura** — o gerador sintético não modela
  cliente que cancela e depois reativa; dados reais de SaaS frequentemente têm isso.
  Simplificação documentada em `synthetic_subscriptions.py`.
- **Forecast com sazonalidade** (Holt-Winters, como em
  `data-platform/ml/demand_forecast.py`) — o forecast atual é tendência linear
  simples; MRR agregado mensal normalmente não tem sazonalidade forte o suficiente
  para justificar o modelo mais complexo, mas poderia ser revisado se o dataset
  crescer para incluir sazonalidade de verdade (ex.: planos anuais renovando no
  mesmo mês).
- **Conectar ao dashboard Next.js** (`apps/web`) — mesma decisão de escopo do
  `experimentation/`: os resultados hoje são CSVs/JSON em
  `data-platform/warehouse/revenue_*`, não uma rota `GET /revenue/*` na API Express
  nem um componente no dashboard. Caminho natural se o módulo for promovido a
  funcionalidade de produto: replicar o padrão de
  `apps/api/src/services/metricsService.ts` + `apps/api/src/routes/metrics.ts`.
