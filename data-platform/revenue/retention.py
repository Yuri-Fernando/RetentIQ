"""
RetentIQ — GRR (Gross Revenue Retention) e NRR (Net Revenue Retention)
mês a mês, calculados em cima do bridge de MRR.

Definições padrão de mercado (SaaS):

    GRR_m = (starting_mrr + churn_mrr + contraction_mrr) / starting_mrr
    NRR_m = (starting_mrr + churn_mrr + contraction_mrr + expansion_mrr) / starting_mrr

`churn_mrr` e `contraction_mrr` já são negativos no bridge (ver
`bridge.compute_mrr_bridge`), então a soma acima já SUBTRAI a receita
perdida — não precisa de sinal adicional.

GRR nunca pode exceder 100% (churn/contração só diminuem receita de clientes
existentes; novos clientes não entram na conta). NRR PODE exceder 100% se a
expansão compensar o churn+contração — isso é o sinal "bom" de um SaaS
saudável (net-negative churn).
"""
from __future__ import annotations

import pandas as pd

from .bridge import compute_mrr_bridge


def compute_grr_nrr(panel: pd.DataFrame) -> pd.DataFrame:
    """
    `panel`: mesmo formato aceito por `bridge.compute_mrr_bridge`.

    Devolve DataFrame com: month, starting_mrr, grr, nrr (grr/nrr como
    fração, ex. 0.97 = 97%).
    """
    bridge = compute_mrr_bridge(panel)

    bridge = bridge[bridge["starting_mrr"] > 0].copy()
    bridge["grr"] = (
        bridge["starting_mrr"] + bridge["churn_mrr"] + bridge["contraction_mrr"]
    ) / bridge["starting_mrr"]
    bridge["nrr"] = bridge["grr"] + bridge["expansion_mrr"] / bridge["starting_mrr"]

    return bridge[["month", "starting_mrr", "grr", "nrr"]]
