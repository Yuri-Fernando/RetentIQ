"""
Testes de `revenue/synthetic_subscriptions.py` — garante que o gerador é
determinístico (mesma seed -> mesmo dataset) e produz um painel consistente
(cada cliente aparece em meses contíguos a partir da própria coorte, sem
"buracos" nem reativação após churn).
"""
from __future__ import annotations

from revenue.synthetic_subscriptions import generate_subscription_panel


def test_generation_is_deterministic_given_seed():
    panel_1 = generate_subscription_panel(n_customers=200, n_months=12, seed=42)
    panel_2 = generate_subscription_panel(n_customers=200, n_months=12, seed=42)
    assert panel_1.equals(panel_2)


def test_different_seed_gives_different_dataset():
    panel_1 = generate_subscription_panel(n_customers=200, n_months=12, seed=42)
    panel_2 = generate_subscription_panel(n_customers=200, n_months=12, seed=7)
    assert not panel_1.equals(panel_2)


def test_every_customer_has_contiguous_months_from_cohort():
    panel = generate_subscription_panel(n_customers=150, n_months=10, seed=1)
    for customer_id, rows in panel.groupby("customer_id"):
        months = sorted(rows["month"].tolist())
        cohort = rows["cohort_month"].iloc[0]
        assert months[0] == cohort
        # meses contíguos: nenhum "buraco" (ativo, inativo, ativo de novo)
        expected = [cohort + k for k in range(len(months))]
        assert months == expected


def test_mrr_is_always_a_valid_plan_price():
    from revenue.synthetic_subscriptions import PLAN_TIERS

    panel = generate_subscription_panel(n_customers=100, n_months=8, seed=5)
    valid_prices = set(PLAN_TIERS.values())
    assert set(panel["mrr"].unique()).issubset(valid_prices)


def test_rejects_invalid_input():
    import pytest

    with pytest.raises(ValueError):
        generate_subscription_panel(n_customers=0, n_months=10)
    with pytest.raises(ValueError):
        generate_subscription_panel(n_customers=10, n_months=0)
