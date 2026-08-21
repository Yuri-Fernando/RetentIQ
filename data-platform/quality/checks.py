"""
RetentIQ — Validação de qualidade do Data Warehouse.

Implementa, sem dependências externas (sqlite3 + regras próprias), o mesmo
espírito de ferramentas como dbt tests / Great Expectations, citadas no material
de referência: checagem de schema, nulos, duplicidade e integridade referencial
entre fato e dimensões.

Gera um relatório em data-platform/warehouse/quality_report.json e retorna um
código de saída != 0 se alguma checagem crítica falhar — pronto para ser
plugado num step de CI/CD (ver .github/workflows/ci.yml).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _fetch_one(conn: sqlite3.Connection, sql: str) -> int:
    return conn.execute(sql).fetchone()[0]


def run_quality_checks(db_path: Path) -> list[CheckResult]:
    print(f"[quality] rodando checks de qualidade em {db_path} ...", flush=True)
    conn = sqlite3.connect(db_path)
    results: list[CheckResult] = []

    def check(name: str, passed: bool, detail: str) -> None:
        results.append(CheckResult(name, passed, detail))
        status = "OK" if passed else "FALHOU"
        print(f"  [{status}] {name} — {detail}", flush=True)

    # 1. tabelas esperadas existem
    expected_tables = {
        "dim_customer", "dim_product", "dim_country", "dim_date",
        "fact_sales", "fact_sales_cancelled",
    }
    existing = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    missing = expected_tables - existing
    check(
        "schema.tabelas_esperadas",
        not missing,
        "todas as tabelas presentes" if not missing else f"faltando: {missing}",
    )

    # 2. fact_sales não pode ter customer_id nulo
    nulls_customer = _fetch_one(
        conn, "SELECT COUNT(*) FROM fact_sales WHERE customer_id IS NULL"
    )
    check(
        "fact_sales.customer_id_nao_nulo",
        nulls_customer == 0,
        f"{nulls_customer} linhas com customer_id nulo",
    )

    # 3. fact_sales não pode ter revenue negativo (vendas válidas)
    negative_revenue = _fetch_one(
        conn, "SELECT COUNT(*) FROM fact_sales WHERE revenue < 0"
    )
    check(
        "fact_sales.revenue_nao_negativo",
        negative_revenue == 0,
        f"{negative_revenue} linhas com receita negativa",
    )

    # 4. integridade referencial: todo customer_id em fact_sales existe em dim_customer
    orphan_customers = _fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_customer d ON f.customer_id = d.customer_id
        WHERE d.customer_id IS NULL
        """,
    )
    check(
        "fk.fact_sales_customer_id",
        orphan_customers == 0,
        f"{orphan_customers} vendas com cliente inexistente na dimensão",
    )

    # 5. integridade referencial: todo stock_code em fact_sales existe em dim_product
    orphan_products = _fetch_one(
        conn,
        """
        SELECT COUNT(*) FROM fact_sales f
        LEFT JOIN dim_product d ON f.stock_code = d.stock_code
        WHERE d.stock_code IS NULL
        """,
    )
    check(
        "fk.fact_sales_stock_code",
        orphan_products == 0,
        f"{orphan_products} vendas com produto inexistente na dimensão",
    )

    # 6. sem duplicidade de chave primária em fact_sales
    dup_sales = _fetch_one(
        conn,
        "SELECT COUNT(*) - COUNT(DISTINCT sale_id) FROM fact_sales",
    )
    check("pk.fact_sales_sale_id_unico", dup_sales == 0, f"{dup_sales} sale_id duplicados")

    # 7. volume mínimo de dados (sanity check de negócio)
    total_rows = _fetch_one(conn, "SELECT COUNT(*) FROM fact_sales")
    check(
        "volume.fact_sales_minimo",
        total_rows > 1000,
        f"{total_rows} linhas em fact_sales (esperado > 1000)",
    )

    conn.close()

    report_path = db_path.parent / "quality_report.json"
    report_path.write_text(
        json.dumps(
            {
                "checks": [asdict(r) for r in results],
                "all_passed": all(r.passed for r in results),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[quality] relatório salvo em {report_path}", flush=True)

    return results


if __name__ == "__main__":
    db = Path(__file__).resolve().parents[1] / "warehouse" / "retentiq.db"
    res = run_quality_checks(db)
    if not all(r.passed for r in res):
        sys.exit(1)
