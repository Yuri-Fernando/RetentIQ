"""
Testes de `power.py` — verificados contra statsmodels.stats.power
(implementação independente) e contra o valor publicado pela calculadora de
amostra de Evan Miller para o caso clássico baseline=20%, MDE=5pp.
"""
from __future__ import annotations

import pytest
from statsmodels.stats.power import TTestIndPower

from experimentation.power import sample_size_means, sample_size_proportions


def test_sample_size_proportions_known_case():
    # Caso publicado (Evan Miller's sample size calculator): baseline 20%,
    # MDE absoluto 5pp (de 20% para 25%), alpha=0.05, power=0.80
    # -> calculadoras padrão convergem para n ≈ 1091 por grupo (fórmula
    # normal padrão, sem correção de continuidade).
    result = sample_size_proportions(baseline_rate=0.20, mde=0.05, alpha=0.05, power=0.80)
    assert result.n_per_group == pytest.approx(1091, abs=5)


def test_sample_size_proportions_larger_mde_needs_fewer_samples():
    small_mde = sample_size_proportions(baseline_rate=0.20, mde=0.02)
    large_mde = sample_size_proportions(baseline_rate=0.20, mde=0.10)
    assert large_mde.n_per_group < small_mde.n_per_group


def test_sample_size_proportions_rejects_invalid_input():
    with pytest.raises(ValueError):
        sample_size_proportions(baseline_rate=0.0, mde=0.05)
    with pytest.raises(ValueError):
        sample_size_proportions(baseline_rate=0.98, mde=0.05)  # p2 > 1


def test_sample_size_means_matches_statsmodels_effect_size():
    # Para métricas contínuas, statsmodels parametriza por "effect size"
    # padronizado (Cohen's d = mde / std_dev), não por mde/std_dev bruto.
    # Verificamos que nossa fórmula de amostra converge para o mesmo n que
    # TTestIndPower.solve_power ao converter mde/std_dev em d.
    std_dev = 15.0
    mde = 3.0
    alpha = 0.05
    power = 0.80

    result = sample_size_means(std_dev=std_dev, mde=mde, alpha=alpha, power=power)

    effect_size = mde / std_dev
    analysis = TTestIndPower()
    n_statsmodels = analysis.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=1.0, alternative="two-sided"
    )

    # Nossa fórmula usa a aproximação normal (z), statsmodels usa a
    # distribuição t exata — convergem a menos de ~5% para n grande.
    assert result.n_per_group == pytest.approx(n_statsmodels, rel=0.05)


def test_sample_size_means_rejects_invalid_input():
    with pytest.raises(ValueError):
        sample_size_means(std_dev=0, mde=1)
    with pytest.raises(ValueError):
        sample_size_means(std_dev=1, mde=0)
