"""
RetentIQ — Previsão de demanda (receita diária) com Holt-Winters

Implementa a ideia "12. Previsão de demanda" do repertório de dados: série
histórica -> tendência/sazonalidade -> modelo de referência -> modelo de
previsão -> comparação previsto x realizado -> métricas de erro.

Modelo: Exponential Smoothing (Holt-Winters) com sazonalidade semanal — simples,
interpretável e sem dependências pesadas (só statsmodels, já usado no projeto).
Serve como baseline sólido para depois evoluir para SARIMAX/Prophet se o
usuário quiser.

Saídas:
  - data-platform/warehouse/demand_forecast.csv    (histórico + previsão)
  - data-platform/warehouse/demand_forecast_metrics.json
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data-platform" / "warehouse" / "retentiq.db"
OUT_DIR = ROOT / "data-platform" / "warehouse"

FORECAST_HORIZON_DAYS = 30
TEST_HOLDOUT_DAYS = 30


def load_daily_revenue() -> pd.Series:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT invoice_date, revenue FROM fact_sales", conn)
    conn.close()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"]).dt.date
    daily = df.groupby("invoice_date")["revenue"].sum()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.asfreq("D").fillna(0.0)  # preenche dias sem venda com 0
    return daily


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def main() -> None:
    print("[forecast] carregando série diária de receita...", flush=True)
    daily = load_daily_revenue()
    print(f"[forecast] série com {len(daily)} dias, de {daily.index.min().date()} a {daily.index.max().date()}", flush=True)

    train = daily.iloc[: -TEST_HOLDOUT_DAYS]
    test = daily.iloc[-TEST_HOLDOUT_DAYS:]

    print("[forecast] treinando Holt-Winters (tendência aditiva + sazonalidade semanal)...", flush=True)
    model = ExponentialSmoothing(
        train, trend="add", seasonal="add", seasonal_periods=7, initialization_method="estimated"
    ).fit()

    test_pred = model.forecast(len(test))
    mae = float(np.mean(np.abs(test.values - test_pred.values)))
    rmse = float(np.sqrt(np.mean((test.values - test_pred.values) ** 2)))
    mape_val = mape(test.values, test_pred.values)

    # modelo final treinado com TODA a série, para prever o futuro real
    full_model = ExponentialSmoothing(
        daily, trend="add", seasonal="add", seasonal_periods=7, initialization_method="estimated"
    ).fit()
    future = full_model.forecast(FORECAST_HORIZON_DAYS)

    result = pd.concat([
        daily.rename("revenue_actual"),
        test_pred.rename("revenue_predicted_holdout"),
        future.rename("revenue_forecast_future"),
    ], axis=1)
    result.index.name = "date"
    result.to_csv(OUT_DIR / "demand_forecast.csv")

    metrics = {
        "train_days": len(train),
        "test_holdout_days": len(test),
        "forecast_horizon_days": FORECAST_HORIZON_DAYS,
        "mae": mae,
        "rmse": rmse,
        "mape_percent": mape_val,
        "nota_metodologica": (
            "Baseline Holt-Winters com sazonalidade semanal (dia da semana). Datas "
            "incompletas foram preenchidas com receita 0 (sem venda), o que é razoável "
            "para um varejista com operação contínua mas pode distorcer feriados "
            "atípicos — próximo passo natural é adicionar regressoras de feriados/"
            "promoções (ex.: SARIMAX com exog) quando esses dados existirem."
        ),
    }
    (OUT_DIR / "demand_forecast_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"[forecast] MAE={mae:.2f} RMSE={rmse:.2f} MAPE={mape_val:.1f}%", flush=True)
    print(f"[forecast] previsão salva em {OUT_DIR / 'demand_forecast.csv'}", flush=True)


if __name__ == "__main__":
    main()
