"""
RetentIQ — Pipeline de geração do relatório de métricas de receita SaaS.

Gera o dataset sintético de assinaturas e roda todos os cálculos do módulo
`revenue/` (MRR/ARR, bridge, GRR/NRR, cohorts, forecast+budget, scenario
planner), salvando os resultados em `data-platform/warehouse/revenue_*`
(mesma convenção de `data-platform/ml/churn_model.py`) — artefatos
recriáveis, não versionados (ver `.gitignore`).

Uso:
    python data-platform/revenue/run_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

from revenue.bridge import compute_mrr_bridge
from revenue.cohorts import compute_cohort_retention
from revenue.forecast import budget_vs_actual, forecast_mrr_linear_trend, generate_synthetic_budget
from revenue.mrr import compute_mrr_arr
from revenue.retention import compute_grr_nrr
from revenue.scenarios import run_scenarios
from revenue.synthetic_subscriptions import generate_subscription_panel

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data-platform" / "warehouse"


def main() -> None:
    print("[revenue] gerando dataset sintético de assinaturas...", flush=True)
    panel = generate_subscription_panel(n_customers=1200, n_months=30, seed=42)
    panel.to_csv(OUT_DIR / "revenue_synthetic_panel.csv", index=False)

    mrr_arr = compute_mrr_arr(panel)
    mrr_arr.to_csv(OUT_DIR / "revenue_mrr_arr.csv", index=False)

    bridge = compute_mrr_bridge(panel)
    bridge.to_csv(OUT_DIR / "revenue_bridge.csv", index=False)

    retention = compute_grr_nrr(panel)
    retention.to_csv(OUT_DIR / "revenue_grr_nrr.csv", index=False)

    cohort_pivot = compute_cohort_retention(panel)
    cohort_pivot.to_csv(OUT_DIR / "revenue_cohort_retention.csv")

    mrr_series = mrr_arr["mrr"].to_numpy()
    forecast = forecast_mrr_linear_trend(mrr_series, periods_ahead=6)
    budget = generate_synthetic_budget(mrr_series[0], n_periods=len(mrr_series), monthly_growth_rate=0.04)
    bva = budget_vs_actual(mrr_series, budget)
    bva.to_csv(OUT_DIR / "revenue_budget_vs_actual.csv", index=False)

    scenarios = run_scenarios(current_mrr=float(mrr_series[-1]), months=12)
    scenarios.to_csv(OUT_DIR / "revenue_scenarios.csv", index=False)

    summary = {
        "n_customers_total": int(panel["customer_id"].nunique()),
        "n_months": int(mrr_arr.shape[0]),
        "mrr_final": float(mrr_series[-1]),
        "arr_final": float(mrr_series[-1] * 12),
        "mrr_growth_total_pct": float((mrr_series[-1] / mrr_series[0]) - 1),
        "avg_grr": float(retention["grr"].mean()),
        "avg_nrr": float(retention["nrr"].mean()),
        "linear_trend_slope_mrr_per_month": forecast.slope,
        "forecast_next_6_months": forecast.forecast.tolist(),
        "scenario_mrr_month_12": {
            name: float(scenarios[name].iloc[-1]) for name in ("pessimista", "base", "otimista")
        },
        "nota_metodologica": (
            "Dataset de assinaturas 100% SINTÉTICO (seed fixa=42), gerado por "
            "revenue/synthetic_subscriptions.py — não representa clientes reais "
            "nem o dataset de e-commerce UCI usado no resto do RetentIQ."
        ),
    }
    (OUT_DIR / "revenue_metrics_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[revenue] MRR final: ${summary['mrr_final']:,.2f} | ARR final: ${summary['arr_final']:,.2f}".replace(",", "."), flush=True)
    print(f"[revenue] GRR médio: {summary['avg_grr']:.1%} | NRR médio: {summary['avg_nrr']:.1%}", flush=True)
    print(f"[revenue] cenário mês 12 — pessimista=${summary['scenario_mrr_month_12']['pessimista']:,.0f} base=${summary['scenario_mrr_month_12']['base']:,.0f} otimista=${summary['scenario_mrr_month_12']['otimista']:,.0f}".replace(",", "."), flush=True)
    print(f"[revenue] relatórios salvos em {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
