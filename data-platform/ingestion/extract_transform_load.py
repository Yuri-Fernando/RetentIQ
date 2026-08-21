"""
RetentIQ — ETL: Online Retail II -> Data Warehouse dimensional (star schema)

Fonte: UCI Machine Learning Repository — "Online Retail II"
https://archive.ics.uci.edu/dataset/502/online+retail+ii
Transações de um varejista online do Reino Unido (2009-2011): pedidos, produtos,
clientes e países. Real, público, sem necessidade de autenticação.

Este script:
  1. Lê o .xlsx bruto (2 abas: 2009-2010 e 2010-2011) de data-platform/datasets/raw/
  2. Limpa e padroniza (nulos, duplicidades, cancelamentos, tipos)
  3. Modela em esquema estrela: dim_customer, dim_product, dim_date, dim_country,
     fact_sales (+ fact_sales_cancelled para devoluções/cancelamentos)
  4. Roda checagens de qualidade (ver data-platform/quality/checks.py)
  5. Grava tudo em um Data Warehouse SQLite local (zero-setup) em
     data-platform/warehouse/retentiq.db — o mesmo schema tem DDL equivalente para
     Postgres em data-platform/warehouse/schema_postgres.sql, usado pelo
     docker-compose (infra/docker/docker-compose.yml) quando o usuário quiser rodar
     a stack completa com Postgres real.

Uso:
    python data-platform/ingestion/extract_transform_load.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_XLSX = ROOT / "data-platform" / "datasets" / "raw" / "online_retail_II.xlsx"
PROCESSED_DIR = ROOT / "data-platform" / "datasets" / "processed"
WAREHOUSE_DIR = ROOT / "data-platform" / "warehouse"
DB_PATH = WAREHOUSE_DIR / "retentiq.db"

sys.path.insert(0, str(ROOT / "data-platform" / "quality"))


def extract() -> pd.DataFrame:
    print(f"[extract] lendo {RAW_XLSX.name} ...", flush=True)
    xl = pd.ExcelFile(RAW_XLSX)
    frames = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        df["source_sheet"] = sheet
        frames.append(df)
        print(f"  -> aba '{sheet}': {len(df):,} linhas".replace(",", "."), flush=True)
    raw = pd.concat(frames, ignore_index=True)
    raw.columns = [
        "invoice", "stock_code", "description", "quantity",
        "invoice_date", "price", "customer_id", "country", "source_sheet",
    ]
    # stock_code mistura números e alfanuméricos (ex.: '79323P') -> força string
    # para evitar erro de tipo misto na exportação parquet (pyarrow) mais adiante.
    raw["stock_code"] = raw["stock_code"].astype(str)
    print(f"[extract] total bruto: {len(raw):,} linhas".replace(",", "."), flush=True)
    return raw


def transform(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    print("[transform] limpando e modelando...", flush=True)
    df = raw.copy()

    # Invoice começando com 'C' = cancelamento/devolução (regra do próprio dataset)
    df["invoice"] = df["invoice"].astype(str)
    df["is_cancelled"] = df["invoice"].str.startswith("C")

    # remove linhas sem cliente identificado (não dá pra atribuir a um dim_customer)
    before = len(df)
    df = df.dropna(subset=["customer_id"])
    df["customer_id"] = df["customer_id"].astype(int)
    print(f"  -> removidas {before - len(df):,} linhas sem customer_id".replace(",", "."), flush=True)

    # remove duplicidades exatas
    before = len(df)
    df = df.drop_duplicates()
    print(f"  -> removidas {before - len(df):,} linhas duplicadas".replace(",", "."), flush=True)

    # descrição/país nulos ou inválidos
    df["description"] = df["description"].fillna("DESCONHECIDO").str.strip()
    df["country"] = df["country"].fillna("Unspecified").str.strip()

    # separa vendas válidas de cancelamentos, e remove preço <= 0 nas vendas válidas
    sales = df[~df["is_cancelled"]].copy()
    cancelled = df[df["is_cancelled"]].copy()

    before = len(sales)
    sales = sales[(sales["price"] > 0) & (sales["quantity"] > 0)]
    print(f"  -> removidas {before - len(sales):,} vendas com preço/quantidade inválidos".replace(",", "."), flush=True)

    sales["revenue"] = sales["quantity"] * sales["price"]
    cancelled["revenue"] = cancelled["quantity"] * cancelled["price"]

    # --- dimensões ---
    dim_customer = (
        sales[["customer_id", "country"]]
        .drop_duplicates(subset=["customer_id"], keep="last")
        .rename(columns={"country": "primary_country"})
        .reset_index(drop=True)
    )

    dim_product = (
        sales[["stock_code", "description"]]
        .drop_duplicates(subset=["stock_code"], keep="last")
        .reset_index(drop=True)
    )

    dim_country = (
        pd.DataFrame({"country": sales["country"].unique()})
        .reset_index(drop=True)
    )
    dim_country.insert(0, "country_id", dim_country.index + 1)

    dates = pd.to_datetime(sales["invoice_date"]).dt.date.unique()
    dim_date = pd.DataFrame({"date": sorted(dates)})
    dim_date["date"] = pd.to_datetime(dim_date["date"])
    dim_date["date_id"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["day"] = dim_date["date"].dt.day
    dim_date["weekday"] = dim_date["date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["date"].dt.weekday >= 5

    # --- fato ---
    fact_sales = sales.merge(dim_country, on="country", how="left")
    fact_sales["date_id"] = pd.to_datetime(fact_sales["invoice_date"]).dt.strftime("%Y%m%d").astype(int)
    fact_sales = fact_sales[[
        "invoice", "stock_code", "customer_id", "country_id", "date_id",
        "invoice_date", "quantity", "price", "revenue",
    ]].reset_index(drop=True)
    fact_sales.insert(0, "sale_id", fact_sales.index + 1)

    fact_sales_cancelled = cancelled.merge(dim_country, on="country", how="left")
    fact_sales_cancelled["date_id"] = pd.to_datetime(
        fact_sales_cancelled["invoice_date"]
    ).dt.strftime("%Y%m%d").astype(int)
    fact_sales_cancelled = fact_sales_cancelled[[
        "invoice", "stock_code", "customer_id", "country_id", "date_id",
        "invoice_date", "quantity", "price", "revenue",
    ]].reset_index(drop=True)
    fact_sales_cancelled.insert(0, "cancel_id", fact_sales_cancelled.index + 1)

    print(
        f"[transform] dim_customer={len(dim_customer):,} dim_product={len(dim_product):,} "
        f"dim_country={len(dim_country):,} dim_date={len(dim_date):,} "
        f"fact_sales={len(fact_sales):,} fact_sales_cancelled={len(fact_sales_cancelled):,}"
        .replace(",", "."),
        flush=True,
    )

    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_country": dim_country,
        "dim_date": dim_date,
        "fact_sales": fact_sales,
        "fact_sales_cancelled": fact_sales_cancelled,
    }


def load(tables: dict[str, pd.DataFrame]) -> None:
    print(f"[load] gravando warehouse SQLite em {DB_PATH} ...", flush=True)
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False, chunksize=5000)
            inserted = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            # verificação pós-insert: to_sql pode "concluir" sem exceção mas gravar
            # menos linhas que o DataFrame de origem (ex.: em runs anteriores,
            # dim_product ficou com 0 linhas mesmo sem erro reportado) — falha alto
            # e cedo em vez de deixar o warehouse silenciosamente incompleto.
            if inserted != len(df):
                raise RuntimeError(
                    f"Divergência ao gravar '{name}': DataFrame tinha {len(df)} linhas, "
                    f"warehouse ficou com {inserted}."
                )
            print(f"  -> tabela '{name}': {inserted:,} linhas".replace(",", "."), flush=True)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON fact_sales(customer_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales(date_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON fact_sales(stock_code)")
        conn.commit()
    finally:
        conn.close()

    # também salva parquet/csv para consumo direto pelos scripts de ML (data-platform/ml/)
    tables["fact_sales"].to_parquet(PROCESSED_DIR / "fact_sales.parquet", index=False)
    tables["dim_customer"].to_parquet(PROCESSED_DIR / "dim_customer.parquet", index=False)
    print("[load] parquet de apoio gravados em data-platform/datasets/processed/", flush=True)


def main() -> None:
    raw = extract()
    tables = transform(raw)
    load(tables)

    try:
        from checks import run_quality_checks  # data-platform/quality/checks.py
        run_quality_checks(DB_PATH)
    except ImportError:
        print("[quality] módulo de checks não encontrado, pulando validação.", flush=True)

    print("\n[OK] Pipeline concluído com sucesso.", flush=True)


if __name__ == "__main__":
    main()
