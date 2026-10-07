"""
RetentIQ — MRR / ARR mês a mês, a partir do painel de assinaturas.
"""
from __future__ import annotations

import pandas as pd


def compute_mrr_arr(panel: pd.DataFrame) -> pd.DataFrame:
    """
    `panel`: DataFrame com colunas (customer_id, month, mrr) — uma linha por
    (cliente, mês) ativo, como devolvido por
    `synthetic_subscriptions.generate_subscription_panel`.

    Devolve DataFrame indexado por `month` com: mrr, arr (= mrr * 12),
    active_customers, avg_mrr_per_customer.
    """
    required = {"customer_id", "month", "mrr"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel está faltando colunas: {missing}")

    grouped = panel.groupby("month").agg(
        mrr=("mrr", "sum"),
        active_customers=("customer_id", "nunique"),
    )
    grouped["arr"] = grouped["mrr"] * 12
    grouped["avg_mrr_per_customer"] = grouped["mrr"] / grouped["active_customers"]
    grouped = grouped.sort_index()
    return grouped.reset_index()
