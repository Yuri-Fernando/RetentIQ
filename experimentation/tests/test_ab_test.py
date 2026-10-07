"""
Testes de `ab_test.py` — verificados contra statsmodels (implementação
independente e consolidada) e contra scipy.stats.ttest_ind diretamente.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from experimentation.ab_test import two_proportion_z_test, welch_t_test


def test_two_proportion_z_test_matches_statsmodels():
    # Caso conhecido: controle 200/1000 (20%), tratamento 240/1000 (24%).
    conv_a, n_a = 200, 1000
    conv_b, n_b = 240, 1000

    result = two_proportion_z_test(conv_a, n_a, conv_b, n_b)

    # statsmodels devolve z na ordem (count1, count2) = (b, a) para manter o
    # sinal diff = p_b - p_a igual à nossa convenção.
    z_sm, p_sm = proportions_ztest(
        count=[conv_b, conv_a], nobs=[n_b, n_a], alternative="two-sided"
    )

    assert result.statistic == pytest.approx(z_sm, rel=1e-9)
    assert result.p_value == pytest.approx(p_sm, rel=1e-9)
    assert result.diff == pytest.approx(0.24 - 0.20, rel=1e-9)
    assert result.significant is True  # diferença de 4pp em n=1000 é significativa


def test_two_proportion_z_test_no_difference_is_not_significant():
    result = two_proportion_z_test(conversions_a=500, n_a=1000, conversions_b=503, n_b=1000)
    assert result.significant is False
    assert result.p_value > 0.05


def test_two_proportion_z_test_ci_contains_point_estimate():
    result = two_proportion_z_test(200, 1000, 240, 1000)
    assert result.ci_low < result.diff < result.ci_high


def test_two_proportion_z_test_rejects_invalid_input():
    with pytest.raises(ValueError):
        two_proportion_z_test(0, 0, 0, 10)
    with pytest.raises(ValueError):
        two_proportion_z_test(20, 10, 0, 10)  # conversions > n


def test_welch_t_test_matches_scipy():
    rng = np.random.default_rng(7)
    sample_a = rng.normal(loc=100, scale=15, size=500)
    sample_b = rng.normal(loc=106, scale=20, size=480)  # média maior, variância diferente

    result = welch_t_test(sample_a, sample_b)

    t_sm, p_sm = stats.ttest_ind(sample_b, sample_a, equal_var=False)

    assert result.statistic == pytest.approx(t_sm, rel=1e-9)
    assert result.p_value == pytest.approx(p_sm, rel=1e-9)
    assert result.significant is True  # efeito de ~6 com n grande deve ser significativo


def test_welch_t_test_identical_samples_not_significant():
    rng = np.random.default_rng(3)
    sample = rng.normal(loc=50, scale=10, size=200)
    # mesma distribuição em ambos os braços -> não deve achar diferença
    sample_a = sample[:100]
    sample_b = sample[100:]
    result = welch_t_test(sample_a, sample_b)
    assert result.p_value > 0.01  # não é garantido >0.05, mas não deve ser minúsculo
