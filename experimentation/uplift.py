"""
RetentIQ — Uplift / CATE (Conditional Average Treatment Effect) via T-learner.

O T-learner é a abordagem mais simples e robusta de meta-learner para
heterogeneidade de efeito de tratamento (Künzel et al., 2019, "Metalearners
for estimating heterogeneous treatment effects using machine learning"):

  1. Treina um modelo `mu0(x)` SÓ com as unidades de controle (treatment=0),
     prevendo o outcome.
  2. Treina um modelo `mu1(x)` SÓ com as unidades de tratamento (treatment=1),
     prevendo o outcome.
  3. CATE(x) = mu1(x) - mu0(x) — o efeito de tratamento estimado para cada
     unidade, individualmente, a partir das features `x`.

Usa `RandomForestRegressor` do scikit-learn (já é dependência do projeto via
`data-platform/ml/churn_model.py`), mas a função aceita qualquer regressor
scikit-learn-compatible via `base_learner`.

Caso de uso no RetentIQ: estimar, por cliente, o efeito esperado de uma ação
de retenção (ex.: cupom de win-back) na receita futura — para priorizar QUAIS
clientes do Kanban de Ações de Retenção devem receber a oferta, em vez de
mandar para todo mundo.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import RegressorMixin, clone
from sklearn.ensemble import RandomForestRegressor


@dataclass
class UpliftModel:
    mu0: RegressorMixin
    mu1: RegressorMixin

    def predict_cate(self, x: np.ndarray) -> np.ndarray:
        """CATE(x) = E[Y|do(T=1), X=x] - E[Y|do(T=0), X=x], estimado."""
        x = np.asarray(x)
        return self.mu1.predict(x) - self.mu0.predict(x)


def fit_t_learner(
    x: np.ndarray,
    treatment: np.ndarray,
    y: np.ndarray,
    base_learner: RegressorMixin | None = None,
) -> UpliftModel:
    """
    Treina um T-learner para estimar CATE.

    `x`: features (n_samples, n_features).
    `treatment`: vetor binário (0 = controle, 1 = tratamento), shape (n_samples,).
    `y`: outcome observado, shape (n_samples,).
    `base_learner`: regressor scikit-learn a clonar para mu0 e mu1
        (default: RandomForestRegressor(n_estimators=200, random_state=42)).
    """
    x = np.asarray(x)
    treatment = np.asarray(treatment)
    y = np.asarray(y)

    if base_learner is None:
        base_learner = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42)

    mask_control = treatment == 0
    mask_treated = treatment == 1
    if mask_control.sum() < 2 or mask_treated.sum() < 2:
        raise ValueError("precisa de pelo menos 2 unidades em cada braço (controle e tratamento)")

    mu0 = clone(base_learner)
    mu1 = clone(base_learner)

    mu0.fit(x[mask_control], y[mask_control])
    mu1.fit(x[mask_treated], y[mask_treated])

    return UpliftModel(mu0=mu0, mu1=mu1)
