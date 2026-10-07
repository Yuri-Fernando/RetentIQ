"""
RetentIQ — Forecast de MRR (tendência linear) e comparação Budget vs Actual.

Forecast: regressão linear simples MRR ~ índice do mês (OLS via
`numpy.polyfit`, grau 1). Suficiente para uma série com tendência
predominantemente linear/suave como MRR acumulado de um SaaS em crescimento
estável — não é um modelo de séries temporais sofisticado (ver
`data-platform/ml/demand_forecast.py` para o Holt-Winters usado no forecast
de demanda de vendas, que tem sazonalidade; MRR mensal agregado normalmente
não tem sazonalidade forte o suficiente para justificar o mesmo modelo).

Budget: como não existe um budget real (é um exercício de planejamento
interno, não um dado observável), geramos um budget SINTÉTICO como uma curva
de crescimento composto a partir do primeiro valor observado da série — é o
"quanto a empresa tinha planejado crescer", documentado como sintético.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class LinearTrendForecast:
    slope: float
    intercept: float
    forecast: np.ndarray  # valores previstos para os `periods_ahead` meses seguintes


def forecast_mrr_linear_trend(mrr_series: np.ndarray, periods_ahead: int = 6) -> LinearTrendForecast:
    """
    Ajusta uma regressão linear MRR ~ t (t = 0, 1, 2, ... para cada ponto da
    série) e extrapola `periods_ahead` pontos para frente.
    """
    mrr_series = np.asarray(mrr_series, dtype=float)
    n = len(mrr_series)
    if n < 2:
        raise ValueError("precisa de pelo menos 2 pontos para ajustar uma tendência")
    if periods_ahead <= 0:
        raise ValueError("periods_ahead deve ser positivo")

    t = np.arange(n)
    slope, intercept = np.polyfit(t, mrr_series, deg=1)

    future_t = np.arange(n, n + periods_ahead)
    forecast = slope * future_t + intercept

    return LinearTrendForecast(slope=float(slope), intercept=float(intercept), forecast=forecast)


def generate_synthetic_budget(
    first_actual_value: float,
    n_periods: int,
    monthly_growth_rate: float = 0.03,
) -> np.ndarray:
    """
    Budget SINTÉTICO: crescimento composto `monthly_growth_rate` a partir de
    `first_actual_value`. budget[0] = first_actual_value * (1+g),
    budget[k] = first_actual_value * (1+g)^(k+1).
    """
    if n_periods <= 0:
        raise ValueError("n_periods deve ser positivo")
    k = np.arange(1, n_periods + 1)
    return first_actual_value * (1 + monthly_growth_rate) ** k


def budget_vs_actual(actual: np.ndarray, budget: np.ndarray) -> pd.DataFrame:
    """
    Compara série realizada (`actual`) contra planejada (`budget`), mesmo
    tamanho e mesma ordem temporal. Devolve DataFrame com variance (absoluta)
    e variance_pct (relativa ao budget).
    """
    actual = np.asarray(actual, dtype=float)
    budget = np.asarray(budget, dtype=float)
    if actual.shape != budget.shape:
        raise ValueError("actual e budget devem ter o mesmo tamanho")

    variance = actual - budget
    with np.errstate(divide="ignore", invalid="ignore"):
        variance_pct = np.where(budget != 0, variance / budget, np.nan)

    return pd.DataFrame(
        {
            "actual": actual,
            "budget": budget,
            "variance": variance,
            "variance_pct": variance_pct,
        }
    )
