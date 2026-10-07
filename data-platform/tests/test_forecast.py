"""
Testes de `revenue/forecast.py`.

`forecast_mrr_linear_trend`: em uma série EXATAMENTE linear (sem ruído), a
regressão deve recuperar slope/intercept exatos e extrapolar exatamente a
reta — caso hand-calculável.

`budget_vs_actual`: caso construído à mão com números redondos.
"""
from __future__ import annotations

import numpy as np
import pytest

from revenue.forecast import budget_vs_actual, forecast_mrr_linear_trend, generate_synthetic_budget


def test_linear_trend_recovers_exact_line_without_noise():
    # y = 100 + 50*t, para t = 0..9
    t = np.arange(10)
    y = 100 + 50 * t

    result = forecast_mrr_linear_trend(y, periods_ahead=5)

    assert result.slope == pytest.approx(50.0, abs=1e-6)
    assert result.intercept == pytest.approx(100.0, abs=1e-6)

    expected_future = 100 + 50 * np.arange(10, 15)
    np.testing.assert_allclose(result.forecast, expected_future, atol=1e-6)


def test_linear_trend_rejects_short_series():
    with pytest.raises(ValueError):
        forecast_mrr_linear_trend([100.0], periods_ahead=3)
    with pytest.raises(ValueError):
        forecast_mrr_linear_trend([100.0, 110.0], periods_ahead=0)


def test_generate_synthetic_budget_compounds_correctly():
    budget = generate_synthetic_budget(first_actual_value=1000.0, n_periods=3, monthly_growth_rate=0.10)
    # 1000*1.1=1100, 1000*1.1^2=1210, 1000*1.1^3=1331
    np.testing.assert_allclose(budget, [1100.0, 1210.0, 1331.0], rtol=1e-9)


def test_budget_vs_actual_hand_calculated():
    actual = np.array([1000.0, 1300.0, 1400.0])
    budget = np.array([1100.0, 1210.0, 1331.0])

    result = budget_vs_actual(actual, budget)

    np.testing.assert_allclose(result["variance"], [-100.0, 90.0, 69.0])
    np.testing.assert_allclose(
        result["variance_pct"], [-100 / 1100, 90 / 1210, 69 / 1331], rtol=1e-9
    )


def test_budget_vs_actual_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        budget_vs_actual(np.array([1, 2, 3]), np.array([1, 2]))
