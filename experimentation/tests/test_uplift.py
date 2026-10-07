"""
Testes de `uplift.py` — dataset sintético com efeito de tratamento
heterogêneo CONHECIDO (função de `x`), verificando que o CATE estimado pelo
T-learner se correlaciona fortemente com o CATE verdadeiro (padrão de
verificação para modelos de uplift, já que não há "valor exato" fechado como
em um teste estatístico — é um problema de ML supervisionado).
"""
from __future__ import annotations

import numpy as np
import pytest

from experimentation.uplift import fit_t_learner


def _synthetic_uplift_data(n: int = 4000, seed: int = 21):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 10, size=(n, 1))
    treatment = rng.integers(0, 2, size=n)

    # Efeito de tratamento verdadeiro cresce com x (heterogêneo por desenho):
    # clientes com x alto (ex.: tempo de vida/engajamento) respondem mais à
    # ação de retenção.
    true_cate = 2.0 * x[:, 0]
    baseline = 50 + 3 * x[:, 0]
    noise = rng.normal(scale=5.0, size=n)

    y = baseline + treatment * true_cate + noise
    return x, treatment, y, true_cate


def test_t_learner_cate_correlates_with_true_effect():
    x, treatment, y, true_cate = _synthetic_uplift_data()

    model = fit_t_learner(x, treatment, y)
    estimated_cate = model.predict_cate(x)

    corr = np.corrcoef(estimated_cate, true_cate)[0, 1]
    assert corr > 0.85


def test_t_learner_cate_mean_close_to_true_average_effect():
    x, treatment, y, true_cate = _synthetic_uplift_data()
    model = fit_t_learner(x, treatment, y)
    estimated_cate = model.predict_cate(x)

    assert estimated_cate.mean() == pytest.approx(true_cate.mean(), rel=0.15)


def test_t_learner_rejects_too_few_units_per_arm():
    x = np.array([[1.0], [2.0], [3.0]])
    treatment = np.array([0, 0, 1])  # só 1 unidade tratada
    y = np.array([10.0, 11.0, 15.0])
    with pytest.raises(ValueError):
        fit_t_learner(x, treatment, y)


def test_t_learner_zero_effect_when_no_true_difference():
    rng = np.random.default_rng(31)
    n = 2000
    x = rng.uniform(0, 10, size=(n, 1))
    treatment = rng.integers(0, 2, size=n)
    y = 50 + 3 * x[:, 0] + rng.normal(scale=5.0, size=n)  # sem efeito de tratamento

    model = fit_t_learner(x, treatment, y)
    estimated_cate = model.predict_cate(x)

    assert abs(estimated_cate.mean()) < 2.0  # próximo de zero, dentro do ruído
