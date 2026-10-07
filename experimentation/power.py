"""
RetentIQ — Cálculo de tamanho de amostra / poder estatístico.

Duas calculadoras:
  - `sample_size_proportions`: dado baseline (p1), MDE (effect absoluto em pp),
    alpha e poder desejados, devolve o N necessário por grupo (teste de duas
    proporções, grupos de tamanho igual).
  - `sample_size_means`: dado desvio-padrão esperado, MDE (em unidades da
    métrica) e alpha/poder, devolve o N por grupo para uma métrica contínua.

Fórmula padrão (ver Evan Miller's sample size calculator / "Standard deviation
formula" em qualquer livro-texto de experimentação):

    n = (z_alpha/2 + z_beta)^2 * (p1*(1-p1) + p2*(1-p2)) / mde^2

onde `p2 = p1 + mde` e `z_x` é o quantil da normal padrão.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats


@dataclass
class SampleSizeResult:
    n_per_group: int
    alpha: float
    power: float
    mde: float


def _z(alpha_or_power_tail: float) -> float:
    return stats.norm.ppf(alpha_or_power_tail)


def sample_size_proportions(
    baseline_rate: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> SampleSizeResult:
    """
    Tamanho de amostra por grupo para detectar uma diferença absoluta `mde`
    entre duas proporções, partindo de uma taxa baseline `baseline_rate`.

    `mde` é um efeito ABSOLUTO (ex.: 0.02 = 2 pontos percentuais), não relativo.
    """
    if not (0 < baseline_rate < 1):
        raise ValueError("baseline_rate deve estar em (0, 1)")
    if mde <= 0:
        raise ValueError("mde deve ser positivo")
    p1 = baseline_rate
    p2 = baseline_rate + mde
    if not (0 < p2 < 1):
        raise ValueError("baseline_rate + mde deve estar em (0, 1)")

    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)

    numerator = (z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))
    n = numerator / (mde**2)

    return SampleSizeResult(
        n_per_group=math.ceil(n), alpha=alpha, power=power, mde=mde
    )


def sample_size_means(
    std_dev: float,
    mde: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> SampleSizeResult:
    """
    Tamanho de amostra por grupo para detectar uma diferença absoluta `mde`
    na média de uma métrica contínua, dado um desvio-padrão esperado `std_dev`
    (assume variância igual nos dois grupos — aproximação padrão de
    planejamento, antes de qualquer dado real existir).

    n = 2 * (z_alpha/2 + z_beta)^2 * std_dev^2 / mde^2
    """
    if std_dev <= 0:
        raise ValueError("std_dev deve ser positivo")
    if mde <= 0:
        raise ValueError("mde deve ser positivo")

    z_alpha = _z(1 - alpha / 2)
    z_beta = _z(power)

    n = 2 * (z_alpha + z_beta) ** 2 * (std_dev**2) / (mde**2)

    return SampleSizeResult(
        n_per_group=math.ceil(n), alpha=alpha, power=power, mde=mde
    )
