"""
RetentIQ — A/B testing bayesiano.

Duas rotinas:
  - `bayesian_ab_beta`: métrica de conversão. Prior Beta em cada braço,
    posterior Beta (conjugado), P(B > A) e intervalo de credibilidade da
    diferença via Monte Carlo (amostragem direta das Betas — exato o
    suficiente para decisão de produto, sem precisar de MCMC).
  - `bayesian_ab_normal`: métrica contínua. Posterior aproximada por
    Normal(mean, se^2) por braço (aproximação padrão com prior não-informativo
    — equivalente ao erro padrão da média amostral), P(B > A) e IC da diferença
    via Monte Carlo.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class BayesianABResult:
    prob_b_better: float
    diff_mean: float
    diff_ci_low: float
    diff_ci_high: float
    credibility: float


def bayesian_ab_beta(
    conversions_a: int,
    n_a: int,
    conversions_b: int,
    n_b: int,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    n_samples: int = 200_000,
    credibility: float = 0.95,
    seed: int | None = 42,
) -> BayesianABResult:
    """
    A/B bayesiano para métrica de conversão (Beta-Binomial conjugado).

    Prior Beta(prior_alpha, prior_beta) em cada braço (Beta(1,1) = uniforme,
    não-informativo, é o default). Posterior de cada braço:
        Beta(prior_alpha + conversions, prior_beta + (n - conversions))
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError("n_a e n_b devem ser positivos")

    rng = np.random.default_rng(seed)

    post_a = rng.beta(prior_alpha + conversions_a, prior_beta + (n_a - conversions_a), n_samples)
    post_b = rng.beta(prior_alpha + conversions_b, prior_beta + (n_b - conversions_b), n_samples)

    diff = post_b - post_a
    prob_b_better = float(np.mean(diff > 0))

    lower_q = (1 - credibility) / 2
    upper_q = 1 - lower_q
    ci_low, ci_high = np.quantile(diff, [lower_q, upper_q])

    return BayesianABResult(
        prob_b_better=prob_b_better,
        diff_mean=float(diff.mean()),
        diff_ci_low=float(ci_low),
        diff_ci_high=float(ci_high),
        credibility=credibility,
    )


def bayesian_ab_normal(
    sample_a: np.ndarray,
    sample_b: np.ndarray,
    n_samples: int = 200_000,
    credibility: float = 0.95,
    seed: int | None = 42,
) -> BayesianABResult:
    """
    A/B bayesiano para métrica contínua, com prior não-informativo.

    Aproxima a posterior da média de cada braço por
    Normal(mean_amostral, se_amostral^2) — a aproximação padrão usada quando
    não há prior informativo definido (converge para a mesma resposta que o
    teste frequentista, mas devolve uma distribuição de probabilidade sobre
    "B é melhor que A", que é a pergunta que o Bayesiano responde direto).
    """
    sample_a = np.asarray(sample_a, dtype=float)
    sample_b = np.asarray(sample_b, dtype=float)
    if len(sample_a) < 2 or len(sample_b) < 2:
        raise ValueError("cada amostra precisa de pelo menos 2 observações")

    rng = np.random.default_rng(seed)

    mean_a, se_a = sample_a.mean(), sample_a.std(ddof=1) / np.sqrt(len(sample_a))
    mean_b, se_b = sample_b.mean(), sample_b.std(ddof=1) / np.sqrt(len(sample_b))

    post_a = rng.normal(mean_a, se_a, n_samples)
    post_b = rng.normal(mean_b, se_b, n_samples)

    diff = post_b - post_a
    prob_b_better = float(np.mean(diff > 0))

    lower_q = (1 - credibility) / 2
    upper_q = 1 - lower_q
    ci_low, ci_high = np.quantile(diff, [lower_q, upper_q])

    return BayesianABResult(
        prob_b_better=prob_b_better,
        diff_mean=float(diff.mean()),
        diff_ci_low=float(ci_low),
        diff_ci_high=float(ci_high),
        credibility=credibility,
    )
