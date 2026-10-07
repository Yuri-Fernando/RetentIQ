"""
Testes de `cuped.py` — dataset sintético com correlação controlada entre a
covariável pré-experimento `x` e a métrica `y`, verificando o resultado
teórico conhecido: Var(y_cuped)/Var(y) ≈ 1 - corr(x,y)^2.
"""
from __future__ import annotations

import numpy as np
import pytest

from experimentation.cuped import cuped_adjust


def _correlated_pair(rho: float, n: int = 20_000, seed: int = 11):
    """Gera (x, y) com correlação populacional ≈ rho, via método Cholesky 2D."""
    rng = np.random.default_rng(seed)
    z1 = rng.normal(size=n)
    z2 = rng.normal(size=n)
    x = z1
    y = rho * z1 + np.sqrt(1 - rho**2) * z2
    # escala para parecer uma métrica de negócio (receita), não padrão N(0,1)
    x = 100 + 20 * x
    y = 500 + 80 * y
    return x, y


@pytest.mark.parametrize("rho", [0.3, 0.6, 0.9])
def test_variance_reduction_matches_theoretical_rho_squared(rho):
    x, y = _correlated_pair(rho)
    result = cuped_adjust(y, x)

    expected_reduction = rho**2
    assert result.variance_reduction == pytest.approx(expected_reduction, abs=0.02)


def test_cuped_preserves_mean():
    x, y = _correlated_pair(0.7)
    result = cuped_adjust(y, x)
    # CUPED é projetado para não enviesar a média: E[y_cuped] == E[y]
    assert result.y_adjusted.mean() == pytest.approx(y.mean(), abs=1e-6)


def test_cuped_no_correlation_means_no_reduction():
    x, y = _correlated_pair(0.0)
    result = cuped_adjust(y, x)
    assert result.variance_reduction == pytest.approx(0.0, abs=0.02)


def test_cuped_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        cuped_adjust(np.array([1, 2, 3]), np.array([1, 2]))
