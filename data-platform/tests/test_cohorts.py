"""
Testes de `revenue/cohorts.py` — a invariante determinística é
`retention[cohort, 0] == 1.0` para toda coorte (por definição, é a própria
base). Verificamos isso e também que a matriz tem o shape esperado.
"""
from __future__ import annotations

import numpy as np
import pytest

from revenue.cohorts import compute_cohort_retention
from revenue.synthetic_subscriptions import generate_subscription_panel


def test_month_zero_retention_is_always_100_percent():
    panel = generate_subscription_panel(n_customers=400, n_months=14, seed=42)
    pivot = compute_cohort_retention(panel)
    column_zero = pivot[0].dropna()
    np.testing.assert_allclose(column_zero.to_numpy(), 1.0, atol=1e-9)


def test_cohort_retention_matrix_shape():
    panel = generate_subscription_panel(n_customers=300, n_months=10, seed=3)
    pivot = compute_cohort_retention(panel)
    # número de coortes não pode exceder o número de meses do painel
    assert pivot.shape[0] <= 10
    # months_since_start vai de 0 até, no máximo, n_months-1
    assert pivot.columns.max() <= 9


def test_rejects_missing_columns():
    import pandas as pd

    bad_panel = pd.DataFrame([{"customer_id": 1, "month": pd.Period("2024-01", "M"), "mrr": 10.0}])
    with pytest.raises(ValueError):
        compute_cohort_retention(bad_panel)
