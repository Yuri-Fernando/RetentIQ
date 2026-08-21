"""
RetentIQ — Modelo preditivo de Churn (RFM + Random Forest)

Combina duas ideias do repertório de dados:
  - "6. Análise de churn de clientes" (segmentação de risco por regras)
  - "11. Modelo preditivo de churn" (ML supervisionado com avaliação crítica)

Estratégia de rotulagem (evita vazamento de dados):
  1. Define snapshot_date = última data do dataset - CHURN_WINDOW_DAYS.
  2. Calcula features RFM (Recência, Frequência, Monetário) usando SOMENTE
     transações ANTERIORES ao snapshot_date.
  3. Rotula como "churn = 1" o cliente que NÃO comprou nada no período
     [snapshot_date, snapshot_date + CHURN_WINDOW_DAYS] (o holdout futuro).
  4. Treina/testa com split estratificado, e reporta precision/recall/F1/matriz
     de confusão — não apenas acurácia (conforme recomendado no material fonte).

Saídas:
  - data-platform/warehouse/churn_scores.csv      (score de risco por cliente)
  - data-platform/warehouse/churn_metrics.json    (métricas do modelo)
  - data-platform/warehouse/churn_model.joblib    (modelo treinado)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data-platform" / "warehouse" / "retentiq.db"
OUT_DIR = ROOT / "data-platform" / "warehouse"

CHURN_WINDOW_DAYS = 90
RISK_THRESHOLDS = {"alto": 0.66, "medio": 0.33}  # score >= alto -> Alto risco, etc.


def load_sales() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT customer_id, invoice, invoice_date, revenue FROM fact_sales", conn
    )
    conn.close()
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    return df


def build_features(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    past = df[df["invoice_date"] < snapshot_date]

    rfm = past.groupby("customer_id").agg(
        recency_days=("invoice_date", lambda s: (snapshot_date - s.max()).days),
        frequency=("invoice", "nunique"),
        monetary=("revenue", "sum"),
        avg_order_value=("revenue", "mean"),
        tenure_days=("invoice_date", lambda s: (snapshot_date - s.min()).days),
    ).reset_index()

    return rfm


def label_churn(df: pd.DataFrame, snapshot_date: pd.Timestamp, window_end: pd.Timestamp) -> pd.Series:
    future = df[(df["invoice_date"] >= snapshot_date) & (df["invoice_date"] < window_end)]
    active_customers = set(future["customer_id"].unique())
    return active_customers


def main() -> None:
    print("[churn] carregando fact_sales...", flush=True)
    df = load_sales()

    max_date = df["invoice_date"].max()
    snapshot_date = max_date - pd.Timedelta(days=CHURN_WINDOW_DAYS)
    window_end = max_date + pd.Timedelta(days=1)
    print(f"[churn] snapshot_date={snapshot_date.date()} (janela de avaliação de {CHURN_WINDOW_DAYS} dias até {max_date.date()})", flush=True)

    features = build_features(df, snapshot_date)
    active_in_future = label_churn(df, snapshot_date, window_end)
    features["churned"] = (~features["customer_id"].isin(active_in_future)).astype(int)

    print(f"[churn] clientes analisados: {len(features):,} | taxa de churn observada: {features['churned'].mean():.1%}".replace(",", "."), flush=True)

    X = features[["recency_days", "frequency", "monetary", "avg_order_value", "tenure_days"]]
    y = features["churned"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300, max_depth=8, class_weight="balanced", random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    metrics = {
        "snapshot_date": str(snapshot_date.date()),
        "churn_window_days": CHURN_WINDOW_DAYS,
        "n_customers": int(len(features)),
        "churn_rate_observada": float(features["churned"].mean()),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "feature_importance": dict(zip(X.columns, model.feature_importances_.tolist())),
        "nota_metodologica": (
            "Métricas de negócio: falso negativo (cliente marcado como ativo mas que na "
            "verdade some) custa mais caro que falso positivo (contatar um cliente que "
            "ainda ficaria ativo) — por isso o modelo usa class_weight='balanced' e a "
            "priorização de recall deve ser revisada com o time de negócio antes de "
            "definir o threshold final de ação."
        ),
    }

    (OUT_DIR / "churn_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    joblib.dump(model, OUT_DIR / "churn_model.joblib")

    # score todos os clientes (não só o holdout de teste) para popular o dashboard
    features["risk_score"] = model.predict_proba(X)[:, 1]
    features["risk_segment"] = pd.cut(
        features["risk_score"],
        bins=[-0.01, RISK_THRESHOLDS["medio"], RISK_THRESHOLDS["alto"], 1.0],
        labels=["Baixo", "Médio", "Alto"],
    )
    features.sort_values("risk_score", ascending=False).to_csv(
        OUT_DIR / "churn_scores.csv", index=False
    )

    print(f"[churn] precision={metrics['precision']:.3f} recall={metrics['recall']:.3f} f1={metrics['f1']:.3f} roc_auc={metrics['roc_auc']:.3f}", flush=True)
    print(f"[churn] scores salvos em {OUT_DIR / 'churn_scores.csv'}", flush=True)
    print(f"[churn] métricas salvas em {OUT_DIR / 'churn_metrics.json'}", flush=True)


if __name__ == "__main__":
    main()
