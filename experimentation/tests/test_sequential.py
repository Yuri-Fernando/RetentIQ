"""
Testes de `sequential.py` — a propriedade central do mSPRT não é "acertar um
valor calculado à mão", é uma garantia estatística: a taxa de falso-positivo
sob H0 (efeito verdadeiro = 0), mesmo parando no primeiro cruzamento do
limiar em QUALQUER n, não deve exceder alpha. Verificamos isso por simulação
(a forma padrão de validar um teste sequencial), com N de simulações grande
o suficiente para o intervalo de confiança binomial não conter valores muito
acima de alpha.
"""
from __future__ import annotations

import numpy as np
import pytest

from experimentation.sequential import msprt_lambda_path, msprt_sequential_test


def test_msprt_lambda_path_starts_near_one_with_no_signal():
    # Com diffs = 0 em todos os pontos, Λ_n = sqrt(variance/(variance+n*tau2)),
    # que é < 1 e decrescente — nunca deveria cruzar 1/alpha.
    diffs = np.zeros(500)
    lam = msprt_lambda_path(diffs, variance=1.0, tau2=1.0)
    assert np.all(lam <= 1.0)
    assert np.all(np.diff(lam) <= 1e-12)  # monotonicamente não-crescente


def test_msprt_false_positive_rate_under_null_is_controlled():
    alpha = 0.05
    variance = 1.0
    n_per_stream = 300
    n_simulations = 2000

    rng = np.random.default_rng(123)
    rejections = 0
    for _ in range(n_simulations):
        diffs = rng.normal(loc=0.0, scale=np.sqrt(variance), size=n_per_stream)
        result = msprt_sequential_test(diffs, variance=variance, alpha=alpha)
        if result.rejected:
            rejections += 1

    false_positive_rate = rejections / n_simulations

    # Garantia teórica: FPR <= alpha para QUALQUER regra de parada. Damos uma
    # margem para erro de simulação (IC binomial de ~2000 amostras em p=0.05
    # tem desvio padrão ≈ sqrt(0.05*0.95/2000) ≈ 0.0049, então 3 desvios ≈ 0.015).
    assert false_positive_rate <= alpha + 0.02


def test_msprt_detects_real_effect_eventually():
    # Com um efeito real e grande, o teste deve rejeitar H0 bem antes do fim
    # da sequência (essa é a vantagem de parar antecipadamente).
    rng = np.random.default_rng(99)
    true_effect = 0.5
    diffs = rng.normal(loc=true_effect, scale=1.0, size=1000)

    result = msprt_sequential_test(diffs, variance=1.0, alpha=0.05)

    assert result.rejected is True
    assert result.n_at_stop is not None
    assert result.n_at_stop < 1000  # parou antes do N fixo


def test_msprt_rejects_invalid_variance():
    with pytest.raises(ValueError):
        msprt_sequential_test(np.zeros(10), variance=0)
