"""
RetentIQ — Scenario planner de MRR: projeta o MRR futuro sob diferentes
combinações de taxa de churn/expansão e aquisição de novos clientes.

Modelo de projeção (recorrência linear de primeira ordem — padrão em
modelos de planejamento financeiro SaaS):

    mrr[t+1] = mrr[t] * (1 - churn_rate + expansion_rate) + new_mrr_per_month

Fator de crescimento orgânico: g = 1 - churn_rate + expansion_rate.
  - g > 1  -> a base de clientes existente, por si só, já cresce em receita
             (net-negative churn) — cenário ideal.
  - g < 1  -> a base existente encolhe, e só o `new_mrr_per_month` sustenta
             crescimento.

Solução em forma fechada (série geométrica, verificada em teste contra o
cálculo iterativo):

    mrr[t] = mrr0 * g^t + new_mrr_per_month * (g^t - 1) / (g - 1),  se g != 1
    mrr[t] = mrr0 + new_mrr_per_month * t,                          se g == 1
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ScenarioParams:
    name: str
    churn_rate: float
    expansion_rate: float
    new_mrr_per_month: float


def project_mrr(
    current_mrr: float,
    new_mrr_per_month: float,
    churn_rate: float,
    expansion_rate: float,
    months: int = 12,
) -> np.ndarray:
    """
    Projeta `months` meses futuros de MRR (índice 0 = `current_mrr`, o mês
    corrente; índice 1..months = projeção), via recorrência iterativa.
    """
    if months <= 0:
        raise ValueError("months deve ser positivo")
    if not (0 <= churn_rate <= 1):
        raise ValueError("churn_rate deve estar em [0, 1]")
    if expansion_rate < 0:
        raise ValueError("expansion_rate deve ser não-negativo")

    path = np.empty(months + 1)
    path[0] = current_mrr
    growth_factor = 1 - churn_rate + expansion_rate
    for t in range(1, months + 1):
        path[t] = path[t - 1] * growth_factor + new_mrr_per_month
    return path


DEFAULT_SCENARIOS = {
    "pessimista": ScenarioParams("pessimista", churn_rate=0.05, expansion_rate=0.01, new_mrr_per_month=0.0),
    "base": ScenarioParams("base", churn_rate=0.025, expansion_rate=0.02, new_mrr_per_month=0.0),
    "otimista": ScenarioParams("otimista", churn_rate=0.015, expansion_rate=0.04, new_mrr_per_month=0.0),
}


def run_scenarios(
    current_mrr: float,
    months: int = 12,
    scenarios: dict[str, ScenarioParams] | None = None,
) -> pd.DataFrame:
    """
    Roda múltiplos cenários e devolve um DataFrame wide: uma coluna por
    cenário, uma linha por mês (0 = mês corrente).

    `new_mrr_per_month` em `ScenarioParams` costuma ser preenchido com um
    valor absoluto de aquisição mensal planejada (ex.: receita média de novos
    clientes esperados por mês); o default em `DEFAULT_SCENARIOS` usa 0.0
    (cenário "base de clientes existente, sem nova aquisição") — chame com
    `scenarios` customizado para incluir aquisição de novos clientes.
    """
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS

    result = {"month": np.arange(months + 1)}
    for name, params in scenarios.items():
        result[name] = project_mrr(
            current_mrr=current_mrr,
            new_mrr_per_month=params.new_mrr_per_month,
            churn_rate=params.churn_rate,
            expansion_rate=params.expansion_rate,
            months=months,
        )
    return pd.DataFrame(result)
