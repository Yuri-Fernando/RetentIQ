"""
RetentIQ — data-platform/revenue/

Módulo de métricas de receita SaaS (gap "10 — SaaS / FP&A / Revenue" da
auditoria de portfólio): MRR/ARR, GRR/NRR, cohorts de receita, bridge de
movimento de MRR (new/expansion/contraction/churn), forecast + budget vs
actual, e scenario planner.

Dataset: o RetentIQ real (UCI Online Retail II) é um dataset de e-commerce
transacional, SEM estrutura de assinatura/billing recorrente — não existe
"MRR" de verdade para extrair dele. Para este módulo, geramos um dataset
SINTÉTICO de assinaturas (`synthetic_subscriptions.py`), com seed fixa e
reprodutível, claramente documentado como sintético (não é dado real do UCI
nem de qualquer empresa real). Isso segue a mesma convenção já usada no
resto do portfólio para gaps sem dataset real disponível.

Decisão de stack: Python (não TypeScript), mesma justificativa do pacote
`experimentation/` — é cálculo analítico sobre uma tabela de dados, não um
endpoint HTTP, e usa pandas/numpy, já dependências do `data-platform/`.
NÃO foi conectado à API Express/dashboard Next.js existentes (ver
`docs/HISTORICO.md` para a decisão de escopo completa) — os resultados
(DataFrames/CSVs) são o produto final deste módulo, análogo a
`data-platform/ml/churn_model.py` gerando `churn_scores.csv` sem que isso
signifique uma rota HTTP nova.
"""
