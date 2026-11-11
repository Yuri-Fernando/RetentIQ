"""
Engenharia reversa + schema diff. Inclui o cenário "legado" pedido no plano:
(a) gerar schema, (b) aplicar alteração proposital isolada em banco DESCARTÁVEL,
(c) fazer reverse engineering, (d) demonstrar drift e restauração.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from extract_transform_load import build_warehouse
from governance.fixtures import synthetic_raw
from governance.reverse_engineer import introspect_sqlite, to_dbml, to_mermaid
from governance.schema_diff import diff_models
from governance.schema_diff import main as diff_main

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "docs" / "data-governance" / "model"
EXPECTED = MODEL_DIR / "retentiq_sqlite.schema.json"
DBML = ROOT / "docs" / "data-governance" / "diagrams" / "reverse-engineered.dbml"


def test_catalog_introspection(fixture_db):
    m = introspect_sqlite(fixture_db)
    assert set(m["tables"]) == {"dim_customer", "dim_product", "dim_country", "dim_date",
                                "fact_sales", "fact_sales_cancelled", "etl_load_audit"}
    assert set(m["views"]) == {"vw_customer_kpis"}
    fs = m["tables"]["fact_sales"]
    assert fs["primary_key"] == ["sale_id"]
    assert len(fs["foreign_keys"]) == 4
    assert {i["name"] for i in fs["indexes"]} == {"idx_fact_sales_customer", "idx_fact_sales_date", "idx_fact_sales_product"}
    assert m["tables"]["dim_country"]["unique"] == [{"columns": ["country"]}]
    assert m["tables"]["fact_sales_cancelled"]["foreign_keys"] == []


def test_versioned_model_matches_real_schema(fixture_db):
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert diff_models(expected, introspect_sqlite(fixture_db)) == []


def test_versioned_dbml_is_regenerated_from_catalog(fixture_db):
    assert DBML.read_text(encoding="utf-8") == to_dbml(introspect_sqlite(fixture_db))


def test_dbml_and_mermaid_outputs(fixture_db):
    m = introspect_sqlite(fixture_db)
    dbml = to_dbml(m)
    assert "Ref: fact_sales.customer_id > dim_customer.customer_id" in dbml
    assert "sale_id integer [pk]" in dbml
    mer = to_mermaid(m)
    assert mer.startswith("erDiagram")
    assert 'dim_customer ||--o{ fact_sales : "customer_id"' in mer


def _drift(db: Path, sql: list[str]) -> None:
    with sqlite3.connect(db) as c:
        c.execute("PRAGMA foreign_keys = OFF")
        for s in sql:
            c.execute(s)


@pytest.mark.parametrize("sql,expected_id,severity", [
    (["ALTER TABLE fact_sales ADD COLUMN discount REAL"], "column_added:fact_sales.discount", "compatible"),
    (["ALTER TABLE dim_product DROP COLUMN description"], "column_removed:dim_product.description", "breaking"),
    (["DROP VIEW vw_customer_kpis"], "view_removed:vw_customer_kpis", "breaking"),
    (["DROP INDEX idx_fact_sales_date"], "index_removed:fact_sales.idx_fact_sales_date", "review"),
    ([  # mudança de tipo: SQLite exige reconstrução da tabela
        "CREATE TABLE etl_new AS SELECT * FROM etl_load_audit",
        "DROP TABLE etl_load_audit",
        """CREATE TABLE etl_load_audit (load_id INTEGER NOT NULL PRIMARY KEY, loaded_at_utc TEXT NOT NULL,
           source_name TEXT NOT NULL, source_sha256 TEXT, source_rows TEXT NOT NULL,
           dropped_missing_customer INTEGER NOT NULL, dropped_duplicates INTEGER NOT NULL,
           dropped_invalid_sales INTEGER NOT NULL, fact_sales_rows INTEGER NOT NULL,
           fact_cancelled_rows INTEGER NOT NULL, fact_sales_revenue REAL NOT NULL)""",
        "INSERT INTO etl_load_audit SELECT * FROM etl_new", "DROP TABLE etl_new",
    ], "type_changed:etl_load_audit.source_rows", "breaking"),
])
def test_drift_is_detected_and_classified(db_copy, sql, expected_id, severity):
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    _drift(db_copy, sql)
    changes = {c.id: c for c in diff_models(expected, introspect_sqlite(db_copy))}
    assert expected_id in changes
    assert changes[expected_id].severity == severity


def test_breaking_drift_fails_cli_unless_approved(db_copy, tmp_path):
    _drift(db_copy, ["ALTER TABLE dim_product DROP COLUMN description"])
    args = ["--expected", str(EXPECTED), "--sqlite", str(db_copy), "--out-json", str(tmp_path / "d.json")]
    assert diff_main(args) == 1
    approvals = tmp_path / "approvals.json"
    approvals.write_text(json.dumps({"approved": ["column_removed:dim_product.description"]}), encoding="utf-8")
    assert diff_main(args + ["--approvals", str(approvals)]) == 0


def test_drift_restoration_by_rebuilding_from_versioned_ddl(db_copy):
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    _drift(db_copy, ["DROP VIEW vw_customer_kpis", "ALTER TABLE fact_sales ADD COLUMN discount REAL"])
    assert diff_models(expected, introspect_sqlite(db_copy)) != []
    # restauração: recarga completa a partir do DDL versionado (schema_sqlite.sql)
    build_warehouse(synthetic_raw(), db_copy, "synthetic_fixture(seed=42)", None, None)
    assert diff_models(expected, introspect_sqlite(db_copy)) == []
