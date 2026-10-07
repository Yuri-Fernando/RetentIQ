"""
RetentIQ — Bridge de movimento de MRR (decomposição mês a mês).

Para cada par de meses consecutivos (m-1 -> m), decompõe a variação total de
MRR em quatro componentes, por cliente:

  - new_mrr:         cliente sem MRR em m-1, com MRR em m (cliente novo).
  - churn_mrr:        cliente com MRR em m-1, sem MRR em m (cancelou) — valor
                      NEGATIVO (remove MRR).
  - expansion_mrr:    cliente ativo nos dois meses, MRR(m) > MRR(m-1) — a
                      diferença positiva (upgrade).
  - contraction_mrr:  cliente ativo nos dois meses, MRR(m) < MRR(m-1) — a
                      diferença (NEGATIVA — downgrade).

Identidade garantida por construção (e verificada em teste):

    ending_mrr = starting_mrr + new_mrr + expansion_mrr + contraction_mrr + churn_mrr
"""
from __future__ import annotations

import pandas as pd


def compute_mrr_bridge(panel: pd.DataFrame) -> pd.DataFrame:
    """
    `panel`: DataFrame (customer_id, month, mrr) — uma linha por (cliente,
    mês) ativo.

    Devolve um DataFrame com uma linha por mês de TRANSIÇÃO (a partir do
    segundo mês presente no painel), colunas:
      month, starting_mrr, new_mrr, expansion_mrr, contraction_mrr,
      churn_mrr, ending_mrr, ending_mrr_check (soma dos componentes — deve
      ser idêntico a `ending_mrr`).
    """
    required = {"customer_id", "month", "mrr"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel está faltando colunas: {missing}")

    wide = panel.pivot_table(
        index="customer_id", columns="month", values="mrr", fill_value=0.0, aggfunc="sum"
    )
    months = sorted(wide.columns)
    if len(months) < 2:
        raise ValueError("precisa de pelo menos 2 meses no painel para montar o bridge")

    rows = []
    for prev_month, curr_month in zip(months[:-1], months[1:]):
        prev_mrr = wide[prev_month]
        curr_mrr = wide[curr_month]

        had_before = prev_mrr > 0
        has_now = curr_mrr > 0

        new_mask = (~had_before) & has_now
        churn_mask = had_before & (~has_now)
        both_active = had_before & has_now

        new_mrr = curr_mrr[new_mask].sum()
        churn_mrr = -prev_mrr[churn_mask].sum()

        delta_active = curr_mrr[both_active] - prev_mrr[both_active]
        expansion_mrr = delta_active[delta_active > 0].sum()
        contraction_mrr = delta_active[delta_active < 0].sum()

        starting_mrr = prev_mrr.sum()
        ending_mrr = curr_mrr.sum()
        ending_check = starting_mrr + new_mrr + expansion_mrr + contraction_mrr + churn_mrr

        rows.append(
            {
                "month": curr_month,
                "starting_mrr": float(starting_mrr),
                "new_mrr": float(new_mrr),
                "expansion_mrr": float(expansion_mrr),
                "contraction_mrr": float(contraction_mrr),
                "churn_mrr": float(churn_mrr),
                "ending_mrr": float(ending_mrr),
                "ending_mrr_check": float(ending_check),
            }
        )

    return pd.DataFrame(rows)
