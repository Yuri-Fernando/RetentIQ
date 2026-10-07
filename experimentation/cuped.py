"""
RetentIQ — CUPED (Controlled-experiment Using Pre-Experiment Data).

Reduz a variância da métrica de interesse `y` usando uma covariável
pré-experimento `x` (ex.: receita do cliente nos 30 dias ANTES do teste,
usada para ajustar a receita DURANTE o teste).

Referência: Deng, Xu, Kohavi & Walker (2013), "Improving the Sensitivity of
Online Controlled Experiments by Utilizing Pre-Experiment Data".

Ajuste:
    y_cuped = y - theta * (x - mean(x))
    theta   = Cov(x, y) / Var(x)

Resultado teórico conhecido (usado para verificar a implementação em teste):
    Var(y_cuped) / Var(y) ≈ 1 - corr(x, y)^2

Ou seja, quanto mais `x` for correlacionado com `y`, maior a redução de
variância — e a redução é aproximadamente o quadrado da correlação.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class CupedResult:
    theta: float
    y_adjusted: np.ndarray
    var_before: float
    var_after: float
    variance_reduction: float  # 1 - var_after/var_before


def cuped_adjust(y: np.ndarray, x: np.ndarray) -> CupedResult:
    """
    Aplica CUPED a `y` usando a covariável pré-experimento `x`.

    `y` e `x` devem ter o mesmo tamanho e vir da MESMA unidade experimental
    (ex.: mesmo cliente), pareados por índice.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if y.shape != x.shape:
        raise ValueError("y e x devem ter o mesmo shape")
    if len(y) < 2:
        raise ValueError("precisa de pelo menos 2 observações")

    var_x = np.var(x, ddof=1)
    if var_x == 0:
        theta = 0.0
    else:
        cov_xy = np.cov(x, y, ddof=1)[0, 1]
        theta = cov_xy / var_x

    y_adjusted = y - theta * (x - x.mean())

    var_before = np.var(y, ddof=1)
    var_after = np.var(y_adjusted, ddof=1)
    reduction = 1 - (var_after / var_before) if var_before > 0 else 0.0

    return CupedResult(
        theta=float(theta),
        y_adjusted=y_adjusted,
        var_before=float(var_before),
        var_after=float(var_after),
        variance_reduction=float(reduction),
    )
