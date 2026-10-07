"""
Testes de `revenue/mrr.py` — caso hand-calculado simples (3 clientes, 1 mês).
"""
from __future__ import annotations

import pandas as pd
import pytest

from revenue.mrr import compute_mrr_arr


def test_mrr_arr_hand_calculated():
    panel = pd.DataFrame(
        [
            {"customer_id": "A", "month": pd.Period("2024-01", "M"), "mrr": 100.0},
            {"customer_id": "B", "month": pd.Period("2024-01", "M"), "mrr": 50.0},
            {"customer_id": "C", "month": pd.Period("2024-01", "M"), "mrr": 200.0},
        ]
    )
    result = compute_mrr_arr(panel)
    row = result.iloc[0]

    assert row["mrr"] == pytest.approx(350.0)
    assert row["arr"] == pytest.approx(350.0 * 12)
    assert row["active_customers"] == 3
    assert row["avg_mrr_per_customer"] == pytest.approx(350.0 / 3)


def test_mrr_arr_rejects_missing_columns():
    bad_panel = pd.DataFrame([{"customer_id": "A", "mrr": 100.0}])
    with pytest.raises(ValueError):
        compute_mrr_arr(bad_panel)
