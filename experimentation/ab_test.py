"""
RetentIQ — Teste de significância para A/B testing.

Duas rotinas:
  - `two_proportion_z_test`: métrica de conversão/taxa (ex.: taxa de churn,
    taxa de clique) — teste z de duas proporções (pooled), com IC da diferença.
  - `welch_t_test`: métrica contínua (ex.: receita por usuário, tempo de sessão)
    — Welch's t-test (não assume variâncias iguais entre os grupos).

Ambas devolvem um `ABTestResult` com estatística, p-valor, IC e decisão de
significância a um nível alpha dado.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class ABTestResult:
    metric: str
    statistic: float
    p_value: float
    diff: float
    ci_low: float
    ci_high: float
    alpha: float
    significant: bool


def two_proportion_z_test(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    alpha: float = 0.05,
) -> ABTestResult:
    """
    Teste z de duas proporções (pooled variance sob H0), bicaudal.

    `a` é o controle, `b` é o tratamento. `diff = p_b - p_a` (positivo = B melhor).
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError("n_a e n_b devem ser positivos")
    if not (0 <= conversions_a <= n_a) or not (0 <= conversions_b <= n_b):
        raise ValueError("conversions deve estar entre 0 e n")

    p_a = conversions_a / n_a
    p_b = conversions_b / n_b
    diff = p_b - p_a

    # Proporção combinada (pooled) usada para o erro padrão sob H0: p_a == p_b.
    p_pool = (conversions_a + conversions_b) / (n_a + n_b)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

    if se_pool == 0:
        z = 0.0
        p_value = 1.0
    else:
        z = diff / se_pool
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    # IC da diferença usa erro padrão NÃO combinado (unpooled) — padrão para
    # intervalo de confiança de p_b - p_a (o pooled SE só vale sob H0).
    se_unpooled = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_low = diff - z_crit * se_unpooled
    ci_high = diff + z_crit * se_unpooled

    return ABTestResult(
        metric="proportion",
        statistic=float(z),
        p_value=float(p_value),
        diff=float(diff),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        alpha=alpha,
        significant=bool(p_value < alpha),
    )


def welch_t_test(
    sample_a: np.ndarray,
    sample_b: np.ndarray,
    alpha: float = 0.05,
) -> ABTestResult:
    """
    Welch's t-test para métrica contínua (variâncias não necessariamente iguais).

    `sample_a` é o controle, `sample_b` é o tratamento.
    """
    sample_a = np.asarray(sample_a, dtype=float)
    sample_b = np.asarray(sample_b, dtype=float)
    if len(sample_a) < 2 or len(sample_b) < 2:
        raise ValueError("cada amostra precisa de pelo menos 2 observações")

    t_stat, p_value = stats.ttest_ind(sample_b, sample_a, equal_var=False)

    mean_a, mean_b = sample_a.mean(), sample_b.mean()
    diff = mean_b - mean_a

    var_a, var_b = sample_a.var(ddof=1), sample_b.var(ddof=1)
    n_a, n_b = len(sample_a), len(sample_b)
    se = np.sqrt(var_a / n_a + var_b / n_b)

    # Graus de liberdade de Welch-Satterthwaite, para o IC usar o mesmo t-crítico
    # que o teste (em vez do z normal).
    df = (var_a / n_a + var_b / n_b) ** 2 / (
        (var_a / n_a) ** 2 / (n_a - 1) + (var_b / n_b) ** 2 / (n_b - 1)
    )
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    ci_low = diff - t_crit * se
    ci_high = diff + t_crit * se

    return ABTestResult(
        metric="continuous",
        statistic=float(t_stat),
        p_value=float(p_value),
        diff=float(diff),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        alpha=alpha,
        significant=bool(p_value < alpha),
    )
