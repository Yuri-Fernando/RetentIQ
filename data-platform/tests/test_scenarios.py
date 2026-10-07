"""
Testes de `revenue/scenarios.py` — verifica a recorrência iterativa contra a
fórmula fechada de série geométrica (cálculo independente), e um caso
hand-calculado de 2 passos.
"""
from __future__ import annotations

import numpy as np
import pytest

from revenue.scenarios import DEFAULT_SCENARIOS, ScenarioParams, project_mrr, run_scenarios


def _closed_form(mrr0: float, new_mrr: float, growth_factor: float, months: int) -> np.ndarray:
    t = np.arange(months + 1)
    if growth_factor == 1.0:
        return mrr0 + new_mrr * t
    return mrr0 * growth_factor**t + new_mrr * (growth_factor**t - 1) / (growth_factor - 1)


def test_project_mrr_matches_closed_form_geometric_series():
    mrr0 = 10_000.0
    new_mrr = 500.0
    churn_rate = 0.03
    expansion_rate = 0.01
    growth_factor = 1 - churn_rate + expansion_rate

    path = project_mrr(mrr0, new_mrr, churn_rate, expansion_rate, months=24)
    expected = _closed_form(mrr0, new_mrr, growth_factor, 24)

    np.testing.assert_allclose(path, expected, rtol=1e-9)


def test_project_mrr_hand_calculated_two_steps():
    # mrr0=1000, new=100/mês, churn=5%, expansion=0%
    # t=1: 1000*0.95 + 100 = 1050
    # t=2: 1050*0.95 + 100 = 1097.5
    path = project_mrr(1000.0, 100.0, churn_rate=0.05, expansion_rate=0.0, months=2)
    np.testing.assert_allclose(path, [1000.0, 1050.0, 1097.5])


def test_pessimistic_scenario_grows_slower_than_optimistic():
    result = run_scenarios(current_mrr=10_000.0, months=12)
    assert result["otimista"].iloc[-1] > result["base"].iloc[-1] > result["pessimista"].iloc[-1]


def test_run_scenarios_default_set_has_three_scenarios():
    assert set(DEFAULT_SCENARIOS.keys()) == {"pessimista", "base", "otimista"}


def test_project_mrr_rejects_invalid_churn_rate():
    with pytest.raises(ValueError):
        project_mrr(1000.0, 0.0, churn_rate=1.5, expansion_rate=0.0, months=5)
    with pytest.raises(ValueError):
        project_mrr(1000.0, 0.0, churn_rate=0.05, expansion_rate=-0.1, months=5)
