"""
RetentIQ — Motor de recomendação por coprodutos (market basket)

Implementa a ideia "17 — Sistema de recomendação" do repertório dev, cruzada
com o caso de uso de retenção: quando um cliente de Alto risco entra no board
de ações (ver apps/api/src/routes/retention.ts), o time de retenção precisa
de uma oferta concreta de win-back — este script gera essas recomendações.

Abordagem: contagem de coocorrência de produtos na mesma nota fiscal
(association rules simplificadas / item-item collaborative filtering). Não
precisa de biblioteca extra — só pandas, já usado no projeto.

Saídas:
  - data-platform/warehouse/product_recommendations.csv
      (stock_code, recommended_stock_code, co_purchase_count, score)
  - data-platform/warehouse/customer_recommendations.csv
      (customer_id, recommended_stock_code, recommended_description, score)
      -> top 3 produtos recomendados por cliente, excluindo o que ele já comprou
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data-platform" / "warehouse" / "retentiq.db"
OUT_DIR = ROOT / "data-platform" / "warehouse"

TOP_N_PER_PRODUCT = 5
TOP_N_PER_CUSTOMER = 3
MIN_CO_PURCHASE = 3  # ignora pares muito raros (ruído)


def load_baskets() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT invoice, customer_id, stock_code FROM fact_sales", conn)
    conn.close()
    return df


def build_product_pairs(df: pd.DataFrame) -> Counter:
    """Conta quantas vezes cada par de produtos aparece na mesma nota fiscal."""
    pair_counts: Counter = Counter()
    for _invoice, group in df.groupby("invoice")["stock_code"]:
        items = sorted(set(group))
        if len(items) < 2 or len(items) > 50:  # ignora notas gigantes (ruído/atacado)
            continue
        for a, b in combinations(items, 2):
            pair_counts[(a, b)] += 1
    return pair_counts


def main() -> None:
    print("[recommend] carregando cestas de compra (fact_sales)...", flush=True)
    df = load_baskets()
    print(f"[recommend] {df['invoice'].nunique():,} notas fiscais, {df['stock_code'].nunique():,} produtos".replace(",", "."), flush=True)

    print("[recommend] contando coocorrência de produtos por nota fiscal...", flush=True)
    pair_counts = build_product_pairs(df)
    print(f"[recommend] {len(pair_counts):,} pares de produtos coocorrentes".replace(",", "."), flush=True)

    # transforma em matriz simétrica: produto -> [(vizinho, contagem), ...]
    neighbors: dict[str, Counter] = {}
    for (a, b), count in pair_counts.items():
        if count < MIN_CO_PURCHASE:
            continue
        neighbors.setdefault(a, Counter())[b] = count
        neighbors.setdefault(b, Counter())[a] = count

    rows = []
    for product, counter in neighbors.items():
        for neighbor, count in counter.most_common(TOP_N_PER_PRODUCT):
            rows.append({"stock_code": product, "recommended_stock_code": neighbor, "co_purchase_count": count})
    product_recs = pd.DataFrame(rows)
    product_recs.to_csv(OUT_DIR / "product_recommendations.csv", index=False)
    print(f"[recommend] recomendações produto->produto salvas ({len(product_recs):,} linhas)".replace(",", "."), flush=True)

    # recomendação por cliente: olha os produtos que ele já comprou, soma o
    # score dos vizinhos, remove o que ele já tem, pega o top N.
    print("[recommend] gerando recomendações por cliente...", flush=True)
    customer_products = df.groupby("customer_id")["stock_code"].apply(set)

    conn = sqlite3.connect(DB_PATH)
    descriptions = dict(
        pd.read_sql("SELECT stock_code, description FROM dim_product", conn).values
    )
    conn.close()

    customer_rows = []
    for customer_id, owned in customer_products.items():
        scores: Counter = Counter()
        for product in owned:
            for neighbor, count in neighbors.get(product, {}).items():
                if neighbor not in owned:
                    scores[neighbor] += count
        for neighbor, score in scores.most_common(TOP_N_PER_CUSTOMER):
            customer_rows.append({
                "customer_id": customer_id,
                "recommended_stock_code": neighbor,
                "recommended_description": descriptions.get(neighbor, ""),
                "score": score,
            })

    customer_recs = pd.DataFrame(customer_rows)
    customer_recs.to_csv(OUT_DIR / "customer_recommendations.csv", index=False)
    print(f"[recommend] recomendações por cliente salvas ({len(customer_recs):,} linhas, {customer_products.shape[0]:,} clientes)".replace(",", "."), flush=True)
    print("[recommend] OK", flush=True)


if __name__ == "__main__":
    main()
