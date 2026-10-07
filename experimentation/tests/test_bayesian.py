"""
Testes de `bayesian.py`.

Verificação: com amostras grandes o suficiente, a posterior bayesiana e o
teste frequentista devem CONCORDAR na direção e magnitude do efeito (ambos
estimam a mesma coisa, só a interpretação de incerteza muda) — então
comparamos contra `ab_test.two_proportion_z_test` / `welch_t_test` como
checagem cruzada independente, além de um caso extremo onde a resposta é
analiticamente óbvia (nenhuma sobreposição real -> P(B>A) ≈ 1).
"""
from __future__ import annotations

import numpy as np
import pytest

from experimentation.ab_test import two_proportion_z_test, welch_t_test
from experimentation.bayesian import bayesian_ab_beta, bayesian_ab_normal


def test_bayesian_beta_obvious_winner_has_probability_near_one():
    # B muito melhor que A, amostra grande -> quase certeza de que B > A.
    result = bayesian_ab_beta(conversions_a=100, n_a=1000, conversions_b=400, n_b=1000)
    assert result.prob_b_better > 0.999
    assert result.diff_mean == pytest.approx(0.30, abs=0.01)


def test_bayesian_beta_agrees_with_frequentist_point_estimate():
    conv_a, n_a, conv_b, n_b = 200, 1000, 240, 1000
    bayes = bayesian_ab_beta(conv_a, n_a, conv_b, n_b)
    freq = two_proportion_z_test(conv_a, n_a, conv_b, n_b)

    # Com prior Beta(1,1) (quase não-informativo) e n=1000, a média da
    # posterior da diferença deve ficar muito próxima do diff observado.
    assert bayes.diff_mean == pytest.approx(freq.diff, abs=0.01)
    # diferença estatisticamente significativa no frequentista -> alta
    # probabilidade bayesiana de B ser melhor.
    assert bayes.prob_b_better > 0.95


def test_bayesian_beta_no_difference_gives_probability_near_half():
    result = bayesian_ab_beta(conversions_a=500, n_a=1000, conversions_b=502, n_b=1000)
    assert 0.35 < result.prob_b_better < 0.65


def test_bayesian_normal_agrees_with_welch_direction():
    rng = np.random.default_rng(5)
    sample_a = rng.normal(loc=100, scale=15, size=1000)
    sample_b = rng.normal(loc=110, scale=15, size=1000)

    bayes = bayesian_ab_normal(sample_a, sample_b)
    freq = welch_t_test(sample_a, sample_b)

    assert bayes.diff_mean == pytest.approx(freq.diff, abs=1.0)
    assert bayes.prob_b_better > 0.99
    assert freq.significant is True


def test_bayesian_credible_interval_contains_diff_mean():
    result = bayesian_ab_beta(conversions_a=200, n_a=1000, conversions_b=240, n_b=1000)
    assert result.diff_ci_low < result.diff_mean < result.diff_ci_high
