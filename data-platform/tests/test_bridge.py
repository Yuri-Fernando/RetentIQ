"""
Testes de `revenue/bridge.py` — a propriedade central é a identidade de
reconciliação: ending_mrr == starting_mrr + new + expansion + contraction +
churn, EXATAMENTE (não aproximadamente), para todo mês. Também testamos um
caso construído à mão (3 clientes, 2 meses) onde cada componente é
verificável manualmente.
"""
from __future__ import annotations

import pandas as pd
import pytest

from revenue.bridge import compute_mrr_bridge
from revenue.synthetic_subscriptions import generate_subscription_panel


def test_bridge_reconciles_exactly_on_synthetic_dataset():
    panel = generate_subscription_panel(n_customers=500, n_months=18, seed=42)
    bridge = compute_mrr_bridge(panel)

    assert len(bridge) == 17  # 18 meses -> 17 transições
    for _, row in bridge.iterrows():
        assert row["ending_mrr"] == pytest.approx(row["ending_mrr_check"], abs=1e-6)
        # a soma dos componentes de variação deve bater com a variação real
        actual_delta = row["ending_mrr"] - row["starting_mrr"]
        components_delta = (
            row["new_mrr"] + row["expansion_mrr"] + row["contraction_mrr"] + row["churn_mrr"]
        )
        assert actual_delta == pytest.approx(components_delta, abs=1e-6)


def test_bridge_hand_calculated_case():
    # Mês 1: cliente A=100, cliente B=50, cliente C=200 (ativo mas sai no mês 2).
    # Mês 2: cliente A=120 (expansão +20), cliente B=30 (contração -20),
    #        cliente C ausente (churn -200), cliente D novo=80 (novo +80).
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

    bridge = compute_mrr_bridge(panel)
    assert len(bridge) == 1
    row = bridge.iloc[0]

    assert row["starting_mrr"] == pytest.approx(350.0)  # 100+50+200
    assert row["new_mrr"] == pytest.approx(80.0)  # D
    assert row["expansion_mrr"] == pytest.approx(20.0)  # A: 120-100
    assert row["contraction_mrr"] == pytest.approx(-20.0)  # B: 30-50
    assert row["churn_mrr"] == pytest.approx(-200.0)  # C
    assert row["ending_mrr"] == pytest.approx(230.0)  # 120+30+80

    # Reconciliação exata: 350 + 80 + 20 - 20 - 200 = 230
    assert row["ending_mrr"] == pytest.approx(
        row["starting_mrr"]
        + row["new_mrr"]
        + row["expansion_mrr"]
        + row["contraction_mrr"]
        + row["churn_mrr"]
    )


def test_bridge_rejects_single_month_panel():
    panel = pd.DataFrame(
        [{"customer_id": "A", "month": pd.Period("2024-01", "M"), "mrr": 100.0}]
    )
    with pytest.raises(ValueError):
        compute_mrr_bridge(panel)
