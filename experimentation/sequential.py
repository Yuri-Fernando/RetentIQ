"""
RetentIQ — Teste sequencial (mSPRT) para parar um experimento antes do N fixo
sem inflar a taxa de falso-positivo.

Implementa o mixture Sequential Probability Ratio Test (mSPRT) de Johari,
Koomen, Pekelis & Walsh, "Always Valid Inference: Continuous Monitoring of
A/B Tests" (2015/2017) — o método usado por empresas como Optimizely para
permitir "peeking" (olhar o resultado do teste a qualquer momento) sem a
inflação de falso-positivo que um teste de hipótese clássico sofre quando
checado repetidamente.

Ideia: em vez de uma razão de verossimilhança simples H1 vs H0 (que exige um
efeito fixo conhecido), usa-se uma distribuição de mistura Normal(0, tau^2)
sobre o possível efeito `theta` sob H1. Isso dá uma estatística de teste
Λ_n em forma fechada que é um martingale sob H0 — e por isso
P(sup_n Λ_n ≥ 1/alpha | H0) ≤ alpha, para QUALQUER regra de parada
(incluindo "parar no primeiro n em que Λ_n ≥ 1/alpha").

Modelo: a sequência de observações `diffs` são as diferenças incrementais
(tratamento - controle) por unidade de tempo/usuário, assumidas ~ N(0, variance)
sob H0. `variance` deve ser estimada a priori (ex.: a partir de dados
históricos/piloto) e `tau2` é a variância da mistura (quanto maior, mais peso
a efeitos grandes — tau2 = variance é uma escolha neutra razoável).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SequentialTestResult:
    n_at_stop: int | None  # None se nunca cruzou o limiar
    lambda_at_stop: float | None
    lambda_path: np.ndarray
    rejected: bool
    alpha: float


def msprt_lambda_path(
    diffs: np.ndarray,
    variance: float,
    tau2: float,
) -> np.ndarray:
    """
    Calcula o caminho completo da estatística mSPRT Λ_n, n = 1..len(diffs).

    Λ_n = sqrt(variance / (variance + n*tau2))
          * exp( tau2 * S_n^2 / (2 * variance * (variance + n*tau2)) )

    onde S_n = soma cumulativa de `diffs` até n.
    """
    diffs = np.asarray(diffs, dtype=float)
    n = np.arange(1, len(diffs) + 1)
    s_n = np.cumsum(diffs)

    denom = variance + n * tau2
    coef = np.sqrt(variance / denom)
    expo = (tau2 * s_n**2) / (2 * variance * denom)
    # clip para evitar overflow em exp quando o efeito acumulado é grande
    expo = np.clip(expo, None, 700)
    lam = coef * np.exp(expo)
    return lam


def msprt_sequential_test(
    diffs: np.ndarray,
    variance: float,
    alpha: float = 0.05,
    tau2: float | None = None,
) -> SequentialTestResult:
    """
    Roda o mSPRT sobre a sequência `diffs` e devolve o primeiro `n` (se algum)
    em que Λ_n ≥ 1/alpha — ponto em que é válido parar e rejeitar H0 (declarar
    efeito estatisticamente significativo) sem inflar o falso-positivo, mesmo
    tendo "espiado" o resultado em cada n.
    """
    if variance <= 0:
        raise ValueError("variance deve ser positiva")
    if tau2 is None:
        tau2 = variance  # escolha neutra padrão

    lam_path = msprt_lambda_path(diffs, variance, tau2)
    threshold = 1.0 / alpha

    crossed = np.where(lam_path >= threshold)[0]
    if len(crossed) == 0:
        return SequentialTestResult(
            n_at_stop=None,
            lambda_at_stop=None,
            lambda_path=lam_path,
            rejected=False,
            alpha=alpha,
        )

    first_idx = int(crossed[0])
    return SequentialTestResult(
        n_at_stop=first_idx + 1,
        lambda_at_stop=float(lam_path[first_idx]),
        lambda_path=lam_path,
        rejected=True,
        alpha=alpha,
    )
