"""
Checks de qualidade: passam no warehouse íntegro, DETECTAM adulterações
conhecidas, continuam compatíveis com warehouses legados (v2.1.0, sem
constraints) e estão 100% sincronizados com docs/data-governance/quality-rules.yaml.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from checks import main as checks_main
from checks import run_quality_checks
from extract_transform_load import transform_with_stats
from governance.fixtures import synthetic_raw

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "docs" / "data-governance" / "quality-rules.yaml"


def _by_name(results):
    return {r.name: r for r in results}


def _legacy_warehouse(path: Path) -> Path:
    """Reproduz o warehouse da v2.1.0: pandas.to_sql sem PK/FK/CHECK, sem view e sem auditoria."""
    tables, _ = transform_with_stats(synthetic_raw())
    with sqlite3.connect(path) as c:
        for name, df in tables.items():
            df.to_sql(name, c, if_exists="replace", index=False)
    return path


def test_all_critical_checks_pass_on_fixture(fixture_db, tmp_path):
    res = run_quality_checks(fixture_db, min_fact_rows=100, report_path=tmp_path / "r.json")
    failed = [r.name for r in res if not r.passed and r.severity == "critical"]
    assert failed == []
    assert _by_name(res)["cancelamento.cliente_sem_venda_valida"].passed is False  # warning esperado
    assert _by_name(res)["cancelamento.cliente_sem_venda_valida"].severity == "warning"


def test_detects_cancellation_inside_sales(db_copy, tmp_path):
    with sqlite3.connect(db_copy) as c:
        row = c.execute("SELECT stock_code, customer_id, country_id, date_id, invoice_date FROM fact_sales LIMIT 1").fetchone()
        c.execute("INSERT INTO fact_sales VALUES (999999,'C777',?,?,?,?,?,1,2.0,2.0)", row)
    res = _by_name(run_quality_checks(db_copy, min_fact_rows=100, report_path=tmp_path / "r.json"))
    assert not res["cancelamento.ausente_em_fact_sales"].passed
    assert not res["reconciliacao.contagem_fatos"].passed


def test_detects_revenue_tampering(db_copy, tmp_path):
    with sqlite3.connect(db_copy) as c:
        c.execute("UPDATE fact_sales SET revenue = revenue + 10 WHERE sale_id = 1")
    res = _by_name(run_quality_checks(db_copy, min_fact_rows=100, report_path=tmp_path / "r.json"))
    assert not res["fact_sales.revenue_igual_qtd_x_preco"].passed
    assert not res["reconciliacao.receita_total"].passed


def test_detects_future_and_incoherent_dates(db_copy, tmp_path):
    with sqlite3.connect(db_copy) as c:
        c.execute("UPDATE fact_sales SET invoice_date = '2999-01-01 00:00:00' WHERE sale_id = 1")
    res = _by_name(run_quality_checks(db_copy, min_fact_rows=100, report_path=tmp_path / "r.json"))
    assert not res["datas.sem_venda_futura"].passed
    assert not res["datas.date_id_coerente_com_invoice_date"].passed


def test_detects_fk_orphans_when_constraints_bypassed(db_copy, tmp_path):
    with sqlite3.connect(db_copy) as c:
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute("UPDATE fact_sales SET customer_id = 123 WHERE sale_id = 1")
    res = _by_name(run_quality_checks(db_copy, min_fact_rows=100, report_path=tmp_path / "r.json"))
    assert not res["fk.fact_sales_customer_id"].passed
    assert not res["schema.fk_sem_violacao"].passed


def test_volume_threshold_is_parametrized(fixture_db, tmp_path):
    res = _by_name(run_quality_checks(fixture_db, min_fact_rows=10_000, report_path=tmp_path / "r.json"))
    assert not res["volume.fact_sales_minimo"].passed


def test_cli_exit_codes(fixture_db, db_copy, tmp_path):
    assert checks_main(["--db", str(fixture_db), "--min-rows", "100", "--report", str(tmp_path / "a.json")]) == 0
    with sqlite3.connect(db_copy) as c:
        # revenue < 0 seria barrado pelo CHECK do schema; esta adulteração passa
        # pelo schema e só a regra de consistência detecta
        c.execute("UPDATE fact_sales SET revenue = revenue * 3 WHERE sale_id = 1")
    assert checks_main(["--db", str(db_copy), "--min-rows", "100", "--report", str(tmp_path / "b.json")]) == 1


def test_legacy_warehouse_still_validates_with_warnings(tmp_path):
    db = _legacy_warehouse(tmp_path / "legacy.db")
    res = run_quality_checks(db, min_fact_rows=100, report_path=tmp_path / "r.json")
    by = _by_name(res)
    assert [r.name for r in res if not r.passed and r.severity == "critical"] == []
    assert not by["schema.fk_declaradas_fact_sales"].passed  # v2.1.0 não declarava FKs
    assert "reconciliacao.auditoria_presente" in by
    assert "view.vw_customer_kpis_presente" in by


def test_rule_catalog_matches_implementation(fixture_db, tmp_path):
    implemented = {r.name for r in run_quality_checks(fixture_db, min_fact_rows=100, report_path=tmp_path / "a.json")}
    implemented |= {r.name for r in run_quality_checks(_legacy_warehouse(tmp_path / "l.db"), min_fact_rows=100,
                                                       report_path=tmp_path / "b.json")}
    catalog = yaml.safe_load(RULES.read_text(encoding="utf-8"))["rules"]
    assert implemented == {r["id"] for r in catalog}
    res = run_quality_checks(fixture_db, min_fact_rows=100, report_path=tmp_path / "c.json")
    severities = {r.name: r.severity for r in res}
    for rule in catalog:
        if rule["id"] in severities:
            assert severities[rule["id"]] == rule["severity"], rule["id"]
