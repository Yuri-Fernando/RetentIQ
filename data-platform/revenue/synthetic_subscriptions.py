"""
RetentIQ — Gerador de dataset sintético de assinaturas/billing SaaS.

ESTE DATASET É SINTÉTICO — não é o dataset real do UCI Online Retail II
(transacional, sem assinatura recorrente) nem dado de qualquer empresa real.
É gerado com seed fixa (reprodutível) só para sustentar os cálculos de
MRR/ARR/GRR/NRR/cohorts/bridge/forecast deste módulo.

Modelo gerativo (simplificado, mas com dinâmica realista de SaaS B2B/B2C):
  - Clientes entram em coortes mensais, com uma curva de crescimento (mais
    clientes novos nos meses mais recentes, imitando uma empresa em
    crescimento).
  - Cada cliente começa em um plano (tier) com um MRR inicial.
  - A cada mês, um cliente ativo pode: continuar no mesmo plano, fazer
    upgrade (expansão), fazer downgrade (contração), ou cancelar (churn).
    Uma vez cancelado, permanece cancelado (sem reativação — simplificação
    documentada: dados reais frequentemente têm "win-back"/reativação, fora
    de escopo aqui).
  - Não há relação com o dataset de e-commerce do RetentIQ — é um dataset
    paralelo e independente, para o módulo de FP&A/Revenue.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PLAN_TIERS = {
    "starter": 29.0,
    "growth": 59.0,
    "scale": 129.0,
    "enterprise": 299.0,
}
_PLAN_NAMES = list(PLAN_TIERS.keys())
_PLAN_PRICES = np.array(list(PLAN_TIERS.values()))

# Probabilidade de um cliente novo começar em cada plano (maioria entra nos
# planos de entrada, poucos começam direto no enterprise).
_PLAN_START_PROBS = np.array([0.45, 0.30, 0.18, 0.07])

# Probabilidades mensais de transição, por mês ativo (hazard constante —
# simplificação; SaaS real costuma ter churn maior nos primeiros meses).
MONTHLY_CHURN_PROB = 0.025
MONTHLY_EXPANSION_PROB = 0.05
MONTHLY_CONTRACTION_PROB = 0.03


def generate_subscription_panel(
    n_customers: int = 1200,
    n_months: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Gera um painel longo (customer_id, month, cohort_month, plan_tier, mrr)
    com uma linha por (cliente, mês) em que o cliente esteve ATIVO (mrr > 0).
    Meses em que o cliente ainda não existia ou já cancelou simplesmente não
    aparecem — é responsabilidade de quem consome o painel tratar a ausência
    como mrr=0 (ex.: via `pivot_table(..., fill_value=0)`).

    `month` e `cohort_month` são `pandas.Period` de frequência mensal ("M").
    """
    if n_customers <= 0 or n_months <= 0:
        raise ValueError("n_customers e n_months devem ser positivos")

    rng = np.random.default_rng(seed)
    start_period = pd.Period("2023-01", freq="M")
    all_months = pd.period_range(start_period, periods=n_months, freq="M")

    # Curva de crescimento: peso linear crescente -> mais entradas nos meses
    # recentes (empresa em crescimento), com piso para sempre ter alguma
    # entrada em meses iniciais.
    growth_weights = np.linspace(1.0, 3.0, n_months)
    growth_weights = growth_weights / growth_weights.sum()
    cohort_idx = rng.choice(n_months, size=n_customers, p=growth_weights)

    plan_idx0 = rng.choice(len(_PLAN_NAMES), size=n_customers, p=_PLAN_START_PROBS)

    rows = []
    for customer_id in range(n_customers):
        cohort_month = all_months[cohort_idx[customer_id]]
        plan_pos = int(plan_idx0[customer_id])
        mrr = float(_PLAN_PRICES[plan_pos])

        month = cohort_month
        while month <= all_months[-1]:
            rows.append(
                {
                    "customer_id": customer_id,
                    "month": month,
                    "cohort_month": cohort_month,
                    "plan_tier": _PLAN_NAMES[plan_pos],
                    "mrr": mrr,
                }
            )

            draw = rng.random()
            if draw < MONTHLY_CHURN_PROB:
                break  # cancela — não aparece mais nos meses seguintes
            elif draw < MONTHLY_CHURN_PROB + MONTHLY_EXPANSION_PROB and plan_pos < len(_PLAN_NAMES) - 1:
                plan_pos += 1
                mrr = float(_PLAN_PRICES[plan_pos])
            elif (
                draw
                < MONTHLY_CHURN_PROB + MONTHLY_EXPANSION_PROB + MONTHLY_CONTRACTION_PROB
                and plan_pos > 0
            ):
                plan_pos -= 1
                mrr = float(_PLAN_PRICES[plan_pos])
            # senão: continua no mesmo plano

            month = month + 1

    panel = pd.DataFrame(rows)
    return panel
