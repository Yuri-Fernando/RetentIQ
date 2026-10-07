"""
Testes de `revenue/retention.py` (GRR/NRR) — verificados contra o caso
construído à mão de `test_bridge.py` (mesmos números, cálculo manual de
GRR/NRR) e contra as invariantes conhecidas: GRR <= 100% sempre; NRR >= GRR
sempre (porque NRR soma a expansão de volta).
"""
from __future__ import annotations

import pandas as pd
import pytest

from revenue.retention import compute_grr_nrr
from revenue.synthetic_subscriptions import generate_subscription_panel


def test_grr_nrr_hand_calculated_case():
    panel = pd.DataFrame(
        [
            {"customer_id": "A", "month": pd.Period("2024-01", "M"), "mrr": 100.0},
            {"customer_id": "B", "month": pd.Period("2024-01", "M"), "mrr": 50.0},
            {"customer_id": "C", "month": pd.Period("2024-01", "M"), "mrr": 200.0},
            {"customer_id": "A", "month": pd.Period("2024-02", "M"), "mrr": 120.0},
            {"customer_id": "B", "month": pd.Period("2024-02", "M"), "mrr": 30.0},
            {"customer_id": "D", "month": pd.Period("2024-02", "M"), "mrr": 80.0},
        ]
    )
    result = compute_grr_nrr(panel)
    row = result.iloc[0]

    # starting=350, churn=-200, contraction=-20, expansion=+20 (do teste do bridge)
    # GRR = (350 - 200 - 20) / 350 = 130/350
    # NRR = GRR + 20/350 = 150/350
    assert row["grr"] == pytest.approx(130 / 350)
    assert row["nrr"] == pytest.approx(150 / 350)


def test_grr_never_exceeds_100_percent():
    panel = generate_subscription_panel(n_customers=600, n_months=15, seed=42)
    result = compute_grr_nrr(panel)
    assert (result["grr"] <= 1.0 + 1e-9).all()


def test_nrr_is_always_at_least_grr():
    panel = generate_subscription_panel(n_customers=600, n_months=15, seed=42)
    result = compute_grr_nrr(panel)
    assert (result["nrr"] >= result["grr"] - 1e-9).all()
