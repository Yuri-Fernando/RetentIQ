"""
RetentIQ — ETL: Online Retail II -> Data Warehouse dimensional (star schema)

Fonte: UCI Machine Learning Repository — "Online Retail II"
https://archive.ics.uci.edu/dataset/502/online+retail+ii
Transações de um varejista online do Reino Unido (2009-2011): pedidos, produtos,
clientes e países. Real, público, sem necessidade de autenticação (licença CC BY 4.0
segundo a página do dataset na UCI). O arquivo bruto NÃO é versionado no Git.

Este script:
  1. Lê o .xlsx bruto (2 abas: 2009-2010 e 2010-2011) de data-platform/datasets/raw/
     — ou gera uma fixture sintética determinística (--fixture), usada no CI
  2. Limpa e padroniza (nulos, duplicidades, cancelamentos, tipos)
  3. Modela em esquema estrela: dim_customer, dim_product, dim_date, dim_country,
     fact_sales (+ fact_sales_cancelled para devoluções/cancelamentos)
  4. Cria o schema FÍSICO explícito (data-platform/warehouse/schema_sqlite.sql:
     PK, FK, NOT NULL, CHECK, índices e a view vw_customer_kpis) com
     PRAGMA foreign_keys=ON e carrega dimensões antes dos fatos
  5. Registra a trilha de auditoria da carga (etl_load_audit: hash SHA-256 da
     origem e contagens usadas na reconciliação origem -> warehouse)
  6. Roda as checagens de qualidade (data-platform/quality/checks.py) e termina
     com código != 0 se alguma checagem CRÍTICA falhar
  7. Grava em data-platform/warehouse/retentiq.db (SQLite, zero-setup). O DDL
     equivalente para PostgreSQL fica em data-platform/warehouse/schema_postgres.sql.

Uso:
    python data-platform/ingestion/extract_transform_load.py
    python data-platform/ingestion/extract_transform_load.py --fixture --db-path /tmp/retentiq_fixture.db
"""
from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_XLSX = ROOT / "data-platform" / "datasets" / "raw" / "online_retail_II.xlsx"
PROCESSED_DIR = ROOT / "data-platform" / "datasets" / "processed"
WAREHOUSE_DIR = ROOT / "data-platform" / "warehouse"
DB_PATH = WAREHOUSE_DIR / "retentiq.db"
SCHEMA_SQLITE = WAREHOUSE_DIR / "schema_sqlite.sql"

# ordem de carga: dimensões antes dos fatos (FKs ativas durante o insert)
LOAD_ORDER = [
    "dim_customer", "dim_product", "dim_country", "dim_date",
    "fact_sales", "fact_sales_cancelled",
]

sys.path.insert(0, str(ROOT / "data-platform" / "quality"))
sys.path.insert(0, str(ROOT / "data-platform"))


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(raw_path: Path = RAW_XLSX) -> pd.DataFrame:
    print(f"[extract] lendo {raw_path.name} ...", flush=True)
    xl = pd.ExcelFile(raw_path)
    frames = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        df["source_sheet"] = sheet
        frames.append(df)
        print(f"  -> aba '{sheet}': {_fmt(len(df))} linhas", flush=True)
    raw = pd.concat(frames, ignore_index=True)
    raw.columns = [
        "invoice", "stock_code", "description", "quantity",
        "invoice_date", "price", "customer_id", "country", "source_sheet",
    ]
    # stock_code mistura números e alfanuméricos (ex.: '79323P') -> força string
    # para evitar erro de tipo misto na exportação parquet (pyarrow) mais adiante.
    raw["stock_code"] = raw["stock_code"].astype(str)
    print(f"[extract] total bruto: {_fmt(len(raw))} linhas", flush=True)
    return raw


def transform_with_stats(raw: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    print("[transform] limpando e modelando...", flush=True)
    stats: dict[str, int] = {"source_rows": len(raw)}
    df = raw.copy()

    # Invoice começando com 'C' = cancelamento/devolução (regra do próprio dataset)
    df["invoice"] = df["invoice"].astype(str)
    df["is_cancelled"] = df["invoice"].str.startswith("C")

    # remove linhas sem cliente identificado (não dá pra atribuir a um dim_customer)
    before = len(df)
    df = df.dropna(subset=["customer_id"])
    df["customer_id"] = df["customer_id"].astype(int)
    stats["dropped_missing_customer"] = before - len(df)
    print(f"  -> removidas {_fmt(stats['dropped_missing_customer'])} linhas sem customer_id", flush=True)

    # remove duplicidades exatas
    before = len(df)
    df = df.drop_duplicates()
    stats["dropped_duplicates"] = before - len(df)
    print(f"  -> removidas {_fmt(stats['dropped_duplicates'])} linhas duplicadas", flush=True)

    # descrição/país nulos ou inválidos
    df["description"] = df["description"].fillna("DESCONHECIDO").str.strip()
    df["country"] = df["country"].fillna("Unspecified").str.strip()

    # separa vendas válidas de cancelamentos, e remove preço <= 0 nas vendas válidas
    sales = df[~df["is_cancelled"]].copy()
    cancelled = df[df["is_cancelled"]].copy()

    before = len(sales)
    sales = sales[(sales["price"] > 0) & (sales["quantity"] > 0)]
    stats["dropped_invalid_sales"] = before - len(sales)
    print(f"  -> removidas {_fmt(stats['dropped_invalid_sales'])} vendas com preço/quantidade inválidos", flush=True)

    sales["revenue"] = sales["quantity"] * sales["price"]
    cancelled["revenue"] = cancelled["quantity"] * cancelled["price"]

    # --- dimensões ---
    # primary_country = país da ÚLTIMA linha do cliente na ordem do arquivo de
    # origem (não necessariamente a compra mais recente) — ver logical-model.md.
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

    stats["fact_sales_rows"] = len(fact_sales)
    stats["fact_cancelled_rows"] = len(fact_sales_cancelled)

    print(
        f"[transform] dim_customer={_fmt(len(dim_customer))} dim_product={_fmt(len(dim_product))} "
        f"dim_country={_fmt(len(dim_country))} dim_date={_fmt(len(dim_date))} "
        f"fact_sales={_fmt(len(fact_sales))} fact_sales_cancelled={_fmt(len(fact_sales_cancelled))}",
        flush=True,
    )

    tables = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_country": dim_country,
        "dim_date": dim_date,
        "fact_sales": fact_sales,
        "fact_sales_cancelled": fact_sales_cancelled,
    }
    return tables, stats


def transform(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compatibilidade com a assinatura anterior (só as tabelas)."""
    return transform_with_stats(raw)[0]


def load(
    tables: dict[str, pd.DataFrame],
    db_path: Path = DB_PATH,
    processed_dir: Path | None = PROCESSED_DIR,
    audit: dict | None = None,
) -> None:
    print(f"[load] gravando warehouse SQLite em {db_path} ...", flush=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        # schema físico explícito (DROP + CREATE com PK/FK/CHECK/índices/view)
        conn.executescript(SCHEMA_SQLITE.read_text(encoding="utf-8"))
        conn.execute("PRAGMA foreign_keys = ON")
        for name in LOAD_ORDER:
            df = tables[name]
            df.to_sql(name, conn, if_exists="append", index=False, chunksize=5000)
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
            print(f"  -> tabela '{name}': {_fmt(inserted)} linhas", flush=True)

        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Violação de FK após a carga: {violations[:5]}")

        if audit is not None:
            conn.execute(
                """
                INSERT INTO etl_load_audit (
                    loaded_at_utc, source_name, source_sha256, source_rows,
                    dropped_missing_customer, dropped_duplicates, dropped_invalid_sales,
                    fact_sales_rows, fact_cancelled_rows, fact_sales_revenue
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit["loaded_at_utc"], audit["source_name"], audit.get("source_sha256"),
                    audit["source_rows"], audit["dropped_missing_customer"],
                    audit["dropped_duplicates"], audit["dropped_invalid_sales"],
                    audit["fact_sales_rows"], audit["fact_cancelled_rows"],
                    float(tables["fact_sales"]["revenue"].sum()),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    if processed_dir is not None:
        # também salva parquet para consumo direto pelos scripts de ML (data-platform/ml/)
        processed_dir.mkdir(parents=True, exist_ok=True)
        tables["fact_sales"].to_parquet(processed_dir / "fact_sales.parquet", index=False)
        tables["dim_customer"].to_parquet(processed_dir / "dim_customer.parquet", index=False)
        print(f"[load] parquet de apoio gravados em {processed_dir}", flush=True)


def build_warehouse(
    raw: pd.DataFrame,
    db_path: Path,
    source_name: str,
    source_sha256: str | None,
    processed_dir: Path | None,
) -> dict[str, int]:
    tables, stats = transform_with_stats(raw)
    audit = {
        **stats,
        "loaded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_name": source_name,
        "source_sha256": source_sha256,
    }
    load(tables, db_path=db_path, processed_dir=processed_dir, audit=audit)
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETL Online Retail II -> warehouse SQLite (esquema estrela)")
    p.add_argument("--raw", type=Path, default=RAW_XLSX, help="arquivo .xlsx de origem")
    p.add_argument("--db-path", type=Path, default=DB_PATH, help="destino do warehouse SQLite")
    p.add_argument("--fixture", action="store_true",
                   help="usa fixture sintética determinística (sem dados reais) em vez do .xlsx")
    p.add_argument("--fixture-invoices", type=int, default=400)
    p.add_argument("--no-parquet", action="store_true", help="não grava os parquet de apoio")
    p.add_argument("--min-fact-rows", type=int, default=None,
                   help="limiar do check de volume (padrão: 1000 para dado real, 100 para fixture)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fixture:
        from governance.fixtures import synthetic_raw

        raw = synthetic_raw(n_invoices=args.fixture_invoices)
        source_name, source_sha = "synthetic_fixture(seed=42)", None
        min_rows = args.min_fact_rows if args.min_fact_rows is not None else 100
    else:
        raw = extract(args.raw)
        source_name, source_sha = args.raw.name, sha256_file(args.raw)
        min_rows = args.min_fact_rows if args.min_fact_rows is not None else 1000

    processed = None if (args.no_parquet or args.fixture) else PROCESSED_DIR
    build_warehouse(raw, args.db_path, source_name, source_sha, processed)

    try:
        from checks import run_quality_checks  # data-platform/quality/checks.py
    except ImportError:
        print("[quality] módulo de checks não encontrado — pipeline NÃO validado.", flush=True)
        return 2
    results = run_quality_checks(args.db_path, min_fact_rows=min_rows)
    failed = [r for r in results if not r.passed and r.severity == "critical"]
    if failed:
        print(f"\n[FALHOU] {len(failed)} checagem(ns) crítica(s) de qualidade.", flush=True)
        return 1

    print("\n[OK] Pipeline concluído com sucesso.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
