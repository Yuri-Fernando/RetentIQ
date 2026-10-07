"""
RetentIQ — Análise de cohort de receita: curva de retenção de receita por
coorte de aquisição (cohort de mês de entrada x meses desde a entrada).
"""
from __future__ import annotations

import pandas as pd


def compute_cohort_retention(panel: pd.DataFrame) -> pd.DataFrame:
    """
    `panel`: DataFrame (customer_id, month, cohort_month, mrr).

    Devolve uma matriz (pivot) com `cohort_month` nas linhas e
    `months_since_start` (0, 1, 2, ...) nas colunas, onde cada célula é a
    RETENÇÃO DE RECEITA da coorte naquele mês relativo, isto é:

        retention[cohort, k] = MRR da coorte no mês (cohort + k)
                                / MRR da coorte no mês 0 (cohort + 0)

    Por definição, a coluna `months_since_start == 0` é sempre 1.0 (100%) —
    é o próprio denominador. Valores > 1.0 em meses seguintes indicam
    expansão líquida dentro da coorte (upgrades superando churn+contração).
    """
    required = {"customer_id", "month", "cohort_month", "mrr"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel está faltando colunas: {missing}")

    df = panel.copy()
    df["months_since_start"] = (df["month"] - df["cohort_month"]).apply(lambda off: off.n)

    cohort_mrr = (
        df.groupby(["cohort_month", "months_since_start"])["mrr"].sum().reset_index()
    )

    base = cohort_mrr[cohort_mrr["months_since_start"] == 0][
        ["cohort_month", "mrr"]
    ].rename(columns={"mrr": "base_mrr"})

    merged = cohort_mrr.merge(base, on="cohort_month", how="left")
    merged["retention"] = merged["mrr"] / merged["base_mrr"]

    pivot = merged.pivot_table(
        index="cohort_month", columns="months_since_start", values="retention"
    )
    return pivot.sort_index()
