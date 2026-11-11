"""
ETL ponta a ponta sobre a fixture sintética: regras de limpeza, schema físico
(PK/FK/CHECK realmente aplicados pelo SQLite), grão e semântica das dimensões.
"""
from __future__ import annotations

import hashlib
import sqlite3

import pandas as pd
import pytest

from extract_transform_load import main, transform_with_stats
from governance.fixtures import EDGE_COUNTS, synthetic_raw


def test_cleaning_counts_match_planted_edge_cases(fixture_build):
    _, stats = fixture_build
    assert stats["dropped_missing_customer"] == EDGE_COUNTS["missing_customer"]
    assert stats["dropped_duplicates"] == EDGE_COUNTS["exact_duplicates"]
    assert stats["dropped_invalid_sales"] == EDGE_COUNTS["invalid_sales"]
    assert stats["fact_cancelled_rows"] == EDGE_COUNTS["cancellations"]
    accounted = (stats["dropped_missing_customer"] + stats["dropped_duplicates"]
                 + stats["dropped_invalid_sales"] + stats["fact_sales_rows"] + stats["fact_cancelled_rows"])
    assert accounted == stats["source_rows"]


def test_transform_is_deterministic():
    def digest() -> str:
        tables, _ = transform_with_stats(synthetic_raw())
        return hashlib.sha256(pd.util.hash_pandas_object(tables["fact_sales"], index=True).values.tobytes()).hexdigest()

    assert digest() == digest()


def test_physical_schema_declares_keys(fixture_db):
    with sqlite3.connect(fixture_db) as c:
        fks = {(r[3], r[2]) for r in c.execute("PRAGMA foreign_key_list('fact_sales')")}
        assert fks == {("stock_code", "dim_product"), ("customer_id", "dim_customer"),
                       ("country_id", "dim_country"), ("date_id", "dim_date")}
        pk = [r[1] for r in c.execute("PRAGMA table_info('fact_sales')") if r[5]]
        assert pk == ["sale_id"]
        assert c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='vw_customer_kpis' AND type='view'").fetchone()[0] == 1


def test_foreign_key_is_enforced(db_copy):
    with sqlite3.connect(db_copy) as c:
        c.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            c.execute("""INSERT INTO fact_sales VALUES (999999,'1','SYN0001',123,1,20100104,
                         '2010-01-04 10:00:00',1,1.0,1.0)""")


@pytest.mark.parametrize("qty,price,revenue", [(0, 1.0, 0.0), (1, 0.0, 0.0), (1, 1.0, -1.0)])
def test_check_constraints_are_enforced(db_copy, qty, price, revenue):
    with sqlite3.connect(db_copy) as c:
        row = c.execute("SELECT stock_code, customer_id, country_id, date_id FROM fact_sales LIMIT 1").fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            c.execute("INSERT INTO fact_sales VALUES (999999,'1',?,?,?,?,'2010-01-04 10:00:00',?,?,?)",
                      (*row, qty, price, revenue))


def test_grain_has_no_natural_key(fixture_db):
    """Mesmo invoice+produto+preço em 2 linhas: a chave precisa ser substituta."""
    with sqlite3.connect(fixture_db) as c:
        n = c.execute("SELECT COUNT(*) FROM fact_sales WHERE invoice='599001' AND stock_code='SYN0001'").fetchone()[0]
    assert n == 2


def test_primary_country_is_last_row_in_file_order(fixture_db):
    with sqlite3.connect(fixture_db) as c:
        primary = c.execute("SELECT primary_country FROM dim_customer WHERE customer_id=90002").fetchone()[0]
        countries = {r[0] for r in c.execute("""SELECT DISTINCT d.country FROM fact_sales f
                     JOIN dim_country d USING(country_id) WHERE f.customer_id=90002""")}
    assert primary == "Portugal"
    assert {"France", "Portugal"} <= countries


def test_cancellations_are_separated_and_orphans_tolerated(fixture_db):
    with sqlite3.connect(fixture_db) as c:
        assert c.execute("SELECT COUNT(*) FROM fact_sales WHERE invoice LIKE 'C%'").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM fact_sales_cancelled WHERE customer_id=99999").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM dim_customer WHERE customer_id=99999").fetchone()[0] == 0


def test_null_description_and_country_are_standardized(fixture_db):
    with sqlite3.connect(fixture_db) as c:
        assert c.execute("SELECT COUNT(*) FROM dim_country WHERE country='Unspecified'").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM dim_country WHERE country IS NULL").fetchone()[0] == 0


def test_load_audit_records_provenance(fixture_db):
    with sqlite3.connect(fixture_db) as c:
        name, sha, rows = c.execute("SELECT source_name, source_sha256, source_rows FROM etl_load_audit").fetchone()
    assert name.startswith("synthetic_fixture")
    assert sha is None  # fixture não tem arquivo de origem
    assert rows == len(synthetic_raw())


def test_cli_fixture_mode_exits_zero(tmp_path):
    assert main(["--fixture", "--db-path", str(tmp_path / "cli.db")]) == 0
