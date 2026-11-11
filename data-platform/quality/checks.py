"""
RetentIQ — Validação de qualidade do Data Warehouse.

Implementa, sem dependências externas (sqlite3 + regras próprias), o mesmo
espírito de ferramentas como dbt tests / Great Expectations: schema, nulos,
duplicidade, integridade referencial, domínios/ranges, datas, consistência de
cancelamentos, reconciliação origem -> warehouse e ausência de double counting.

Cada regra tem um ID estável, documentado em
docs/data-governance/quality-rules.yaml (o teste
data-platform/tests/test_quality_checks.py garante que código e catálogo de regras
não divergem). Severidade:
  * critical -> falha o pipeline/CI (exit != 0)
  * warning  -> é reportada, não bloqueia (ex.: órfãos tolerados por decisão de modelo)

Gera um relatório JSON (padrão: <pasta do banco>/quality_report.json).

Uso:
    python data-platform/quality/checks.py
    python data-platform/quality/checks.py --db /tmp/fixture.db --min-rows 100
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_TABLES = {
    "dim_customer", "dim_product", "dim_country", "dim_date",
    "fact_sales", "fact_sales_cancelled",
}

# tolerância para comparação de somas em ponto flutuante (REAL no SQLite)
REVENUE_TOLERANCE = 0.01


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "critical"


def _fetch_one(conn: sqlite3.Connection, sql: str):
    return conn.execute(sql).fetchone()[0]


def _objects(conn: sqlite3.Connection, kind: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type=?", (kind,))}


def run_quality_checks(
    db_path: Path,
    min_fact_rows: int = 1000,
    report_path: Path | None = None,
    now_utc: datetime | None = None,
) -> list[CheckResult]:
    print(f"[quality] rodando checks de qualidade em {db_path} ...", flush=True)
    # somente leitura: os checks nunca alteram o warehouse
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    results: list[CheckResult] = []
    now = (now_utc or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M:%S")

    def check(name: str, passed: bool, detail: str, severity: str = "critical") -> None:
        results.append(CheckResult(name, bool(passed), detail, severity))
        status = "OK" if passed else ("FALHOU" if severity == "critical" else "AVISO")
        print(f"  [{status}] {name} — {detail}", flush=True)

    tables = _objects(conn, "table")
    views = _objects(conn, "view")

    # --- schema --------------------------------------------------------------
    missing = EXPECTED_TABLES - tables
    check("schema.tabelas_esperadas", not missing,
          "todas as tabelas presentes" if not missing else f"faltando: {sorted(missing)}")
    if missing:
        conn.close()
        return _write_report(results, db_path, report_path)

    declared_fks = conn.execute("SELECT COUNT(*) FROM pragma_foreign_key_list('fact_sales')").fetchone()[0]
    check("schema.fk_declaradas_fact_sales", declared_fks >= 4,
          f"{declared_fks} FKs declaradas em fact_sales (esperado 4)",
          severity="warning")
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    check("schema.fk_sem_violacao", not fk_violations,
          f"{len(fk_violations)} violações em PRAGMA foreign_key_check")

    # --- nulos / domínio ----------------------------------------------------
    nulls_customer = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales WHERE customer_id IS NULL")
    check("fact_sales.customer_id_nao_nulo", nulls_customer == 0,
          f"{nulls_customer} linhas com customer_id nulo")

    negative_revenue = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales WHERE revenue < 0")
    check("fact_sales.revenue_nao_negativo", negative_revenue == 0,
          f"{negative_revenue} linhas com receita negativa")

    bad_qty_price = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales WHERE quantity <= 0 OR price <= 0")
    check("fact_sales.quantidade_preco_positivos", bad_qty_price == 0,
          f"{bad_qty_price} vendas com quantidade ou preço <= 0")

    bad_revenue = _fetch_one(
        conn, f"SELECT COUNT(*) FROM fact_sales WHERE abs(revenue - quantity * price) > {REVENUE_TOLERANCE}"
    )
    check("fact_sales.revenue_igual_qtd_x_preco", bad_revenue == 0,
          f"{bad_revenue} linhas com revenue != quantity * price")

    # --- integridade referencial -------------------------------------------
    for col, dim, key in [
        ("customer_id", "dim_customer", "customer_id"),
        ("stock_code", "dim_product", "stock_code"),
        ("country_id", "dim_country", "country_id"),
        ("date_id", "dim_date", "date_id"),
    ]:
        orphans = _fetch_one(conn, f"""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN {dim} d ON f.{col} = d.{key}
            WHERE d.{key} IS NULL
        """)
        check(f"fk.fact_sales_{col}", orphans == 0,
              f"{orphans} vendas com {col} inexistente em {dim}")

    # --- unicidade de chaves -------------------------------------------------
    dup_sales = _fetch_one(conn, "SELECT COUNT(*) - COUNT(DISTINCT sale_id) FROM fact_sales")
    check("pk.fact_sales_sale_id_unico", dup_sales == 0, f"{dup_sales} sale_id duplicados")
    for dim, key in [("dim_customer", "customer_id"), ("dim_product", "stock_code"),
                     ("dim_country", "country_id"), ("dim_date", "date_id")]:
        dup = _fetch_one(conn, f"SELECT COUNT(*) - COUNT(DISTINCT {key}) FROM {dim}")
        check(f"pk.{dim}_{key}_unico", dup == 0, f"{dup} {key} duplicados em {dim}")

    # --- datas ---------------------------------------------------------------
    future = _fetch_one(conn, f"SELECT COUNT(*) FROM fact_sales WHERE invoice_date > '{now}'")
    check("datas.sem_venda_futura", future == 0, f"{future} vendas com data no futuro (> {now} UTC)")
    date_mismatch = _fetch_one(conn, """
        SELECT COUNT(*) FROM fact_sales
        WHERE CAST(strftime('%Y%m%d', invoice_date) AS INTEGER) <> date_id
    """)
    check("datas.date_id_coerente_com_invoice_date", date_mismatch == 0,
          f"{date_mismatch} linhas com date_id diferente da data de invoice_date")

    # --- cancelamentos ---------------------------------------------------------
    not_c = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales_cancelled WHERE substr(invoice,1,1) <> 'C'")
    check("cancelamento.invoice_prefixo_c", not_c == 0,
          f"{not_c} linhas em fact_sales_cancelled sem prefixo 'C'")
    c_in_sales = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales WHERE substr(invoice,1,1) = 'C'")
    check("cancelamento.ausente_em_fact_sales", c_in_sales == 0,
          f"{c_in_sales} notas de cancelamento dentro de fact_sales (double counting de receita)")
    positive_cancel = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales_cancelled WHERE quantity > 0")
    check("cancelamento.quantidade_negativa", positive_cancel == 0,
          f"{positive_cancel} cancelamentos com quantidade positiva", severity="warning")
    orphan_cancel_cust = _fetch_one(conn, """
        SELECT COUNT(*) FROM fact_sales_cancelled f
        LEFT JOIN dim_customer d ON f.customer_id = d.customer_id WHERE d.customer_id IS NULL
    """)
    check("cancelamento.cliente_sem_venda_valida", orphan_cancel_cust == 0,
          f"{orphan_cancel_cust} cancelamentos de clientes sem venda válida (tolerado: sem FK por decisão de modelo)",
          severity="warning")

    # --- volume ----------------------------------------------------------------
    total_rows = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales")
    check("volume.fact_sales_minimo", total_rows > min_fact_rows,
          f"{total_rows} linhas em fact_sales (esperado > {min_fact_rows})")

    # --- reconciliação origem -> warehouse ------------------------------------
    if "etl_load_audit" in tables and _fetch_one(conn, "SELECT COUNT(*) FROM etl_load_audit"):
        a = conn.execute("""
            SELECT source_rows, dropped_missing_customer, dropped_duplicates, dropped_invalid_sales,
                   fact_sales_rows, fact_cancelled_rows, fact_sales_revenue
            FROM etl_load_audit ORDER BY load_id DESC LIMIT 1
        """).fetchone()
        src, d_cust, d_dup, d_inv, a_sales, a_canc, a_rev = a
        accounted = d_cust + d_dup + d_inv + a_sales + a_canc
        check("reconciliacao.linhas_origem", accounted == src,
              f"origem={src} vs removidas({d_cust}+{d_dup}+{d_inv}) + vendas({a_sales}) + cancelamentos({a_canc}) = {accounted}")
        cancel_rows = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales_cancelled")
        check("reconciliacao.contagem_fatos", total_rows == a_sales and cancel_rows == a_canc,
              f"warehouse vendas={total_rows}/canc={cancel_rows} vs auditoria vendas={a_sales}/canc={a_canc}")
        rev = _fetch_one(conn, "SELECT COALESCE(SUM(revenue), 0) FROM fact_sales")
        check("reconciliacao.receita_total", abs(rev - a_rev) <= REVENUE_TOLERANCE,
              f"SUM(revenue) warehouse={rev:.2f} vs calculado na transformação={a_rev:.2f}")
    else:
        check("reconciliacao.auditoria_presente", False,
              "etl_load_audit ausente (warehouse gerado por ETL anterior à v2.2.0) — reconciliação não executada",
              severity="warning")

    # --- view analítica: sem double counting ----------------------------------
    if "vw_customer_kpis" in views:
        kpi_rev, kpi_rows = conn.execute(
            "SELECT COALESCE(SUM(total_revenue),0), COUNT(*) FROM vw_customer_kpis").fetchone()
        rev = _fetch_one(conn, "SELECT COALESCE(SUM(revenue), 0) FROM fact_sales")
        check("view.vw_customer_kpis_sem_double_counting", abs(kpi_rev - rev) <= REVENUE_TOLERANCE,
              f"SUM(total_revenue) view={kpi_rev:.2f} vs SUM(revenue) fato={rev:.2f}")
        buyers = _fetch_one(conn, "SELECT COUNT(DISTINCT customer_id) FROM fact_sales")
        check("view.vw_customer_kpis_um_por_cliente", kpi_rows == buyers,
              f"{kpi_rows} linhas na view vs {buyers} clientes com venda")
    else:
        check("view.vw_customer_kpis_presente", False,
              "view ausente (warehouse gerado por ETL anterior à v2.2.0)", severity="warning")

    conn.close()
    return _write_report(results, db_path, report_path)


def _write_report(results: list[CheckResult], db_path: Path, report_path: Path | None) -> list[CheckResult]:
    report_path = report_path or (Path(db_path).parent / "quality_report.json")
    critical_failed = [r.name for r in results if not r.passed and r.severity == "critical"]
    report_path.write_text(
        json.dumps(
            {
                "checks": [asdict(r) for r in results],
                "all_passed": not critical_failed,
                "critical_failed": critical_failed,
                "warnings": [r.name for r in results if not r.passed and r.severity == "warning"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[quality] relatório salvo em {report_path}", flush=True)
    return results


def main(argv: list[str] | None = None) -> int:
    default_db = Path(__file__).resolve().parents[1] / "warehouse" / "retentiq.db"
    p = argparse.ArgumentParser(description="Checks de qualidade do warehouse RetentIQ")
    p.add_argument("--db", type=Path, default=default_db)
    p.add_argument("--min-rows", type=int, default=1000,
                   help="volume mínimo de fact_sales (1000 p/ dado real; a fixture do CI usa 100)")
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args(argv)
    res = run_quality_checks(args.db, min_fact_rows=args.min_rows, report_path=args.report)
    return 1 if any(not r.passed and r.severity == "critical" for r in res) else 0


if __name__ == "__main__":
    sys.exit(main())
