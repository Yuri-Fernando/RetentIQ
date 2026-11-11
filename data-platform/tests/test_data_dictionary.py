"""
Dicionário de dados: cobertura de 100% das colunas físicas, coerência com o
catálogo do banco e com glossário/regras, e CSV versionado sempre atualizado.
"""
from __future__ import annotations

import copy
import csv
import sqlite3
from pathlib import Path

import yaml

from governance.export_dictionary import METADATA, OUT_CSV, build_rows, main
from governance.reverse_engineer import introspect_sqlite

ROOT = Path(__file__).resolve().parents[2]


def _meta():
    return yaml.safe_load(METADATA.read_text(encoding="utf-8"))


def test_full_coverage_without_errors(fixture_db):
    model = introspect_sqlite(fixture_db)
    rows, errors = build_rows(model, _meta(), None)
    assert errors == []
    physical = sum(len(t["columns"]) for t in model["tables"].values()) + sum(
        len(v["columns"]) for v in model["views"].values())
    assert len(rows) == physical


def test_versioned_csv_is_up_to_date():
    assert main(["--check"]) == 0


def test_new_physical_column_without_metadata_fails(db_copy):
    with sqlite3.connect(db_copy) as c:
        c.execute("ALTER TABLE fact_sales ADD COLUMN discount REAL")
    _, errors = build_rows(introspect_sqlite(db_copy), _meta(), None)
    assert "coluna física sem metadado: fact_sales.discount" in errors


def test_stale_metadata_fails(fixture_db):
    meta = _meta()
    meta["tables"]["fact_sales"]["columns"]["coluna_fantasma"] = copy.deepcopy(
        meta["tables"]["fact_sales"]["columns"]["revenue"])
    _, errors = build_rows(introspect_sqlite(fixture_db), meta, None)
    assert "metadado sem coluna física: fact_sales.coluna_fantasma" in errors


def test_unknown_glossary_term_rule_and_classification_fail(fixture_db):
    meta = _meta()
    col = meta["tables"]["fact_sales"]["columns"]["revenue"]
    col["glossary"] = "Termo Inexistente"
    col["quality_rule"] = "regra.inexistente"
    col["classification"] = "SECRETO"
    _, errors = build_rows(introspect_sqlite(fixture_db), meta, None)
    assert any("termo de glossário inexistente" in e for e in errors)
    assert any("regra de qualidade inexistente" in e for e in errors)
    assert any("classificação inválida" in e for e in errors)


def test_fk_references_match_catalog():
    with open(OUT_CSV, encoding="utf-8") as fh:
        rows = {(r["table"], r["column"]): r for r in csv.DictReader(fh)}
    assert rows[("fact_sales", "customer_id")]["fk_reference"] == "dim_customer.customer_id"
    assert rows[("fact_sales", "date_id")]["fk_reference"] == "dim_date.date_id"
    assert rows[("fact_sales_cancelled", "customer_id")]["fk_reference"] == ""  # decisão de modelo
    assert rows[("fact_sales", "price")]["type_postgres"] == "numeric(12,4)"


def test_customer_identifiers_are_classified_as_personal():
    with open(OUT_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["column"] in {"customer_id", "primary_country"}:
                assert r["classification"] == "PESSOAL_PSEUDONIMIZADO", (r["table"], r["column"])
            assert "SIMULADO" in r["owner_role"]
