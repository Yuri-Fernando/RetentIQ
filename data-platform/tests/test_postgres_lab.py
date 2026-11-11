"""
Laboratório PostgreSQL (executa só com RETENTIQ_PG_DSN definido — CI sobe um
serviço postgres:16; localmente: docker). Cada teste usa um banco DESCARTÁVEL.

Cobre: DDL PostgreSQL x modelo versionado, carga, integridade (FK/CHECK),
CR-001 forward/rollback/idempotência, menor privilégio por papel e DML de exemplo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from governance import pg_lab
from governance.reverse_engineer import introspect_postgres
from governance.schema_diff import diff_models

psycopg2 = pytest.importorskip("psycopg2")
ADMIN = pg_lab.admin_dsn()
pytestmark = pytest.mark.skipif(not ADMIN, reason="RETENTIQ_PG_DSN não definido (laboratório PostgreSQL)")

ROOT = Path(__file__).resolve().parents[2]
WH = ROOT / "data-platform" / "warehouse"
EXPECTED_PG = ROOT / "docs" / "data-governance" / "model" / "retentiq_postgres.schema.json"
CR_UP = WH / "migrations" / "postgres" / "CR-001_fact_sales_checks.up.sql"
CR_DOWN = WH / "migrations" / "postgres" / "CR-001_fact_sales_checks.down.sql"


@pytest.fixture()
def pg(fixture_db):
    with pg_lab.scratch_db(ADMIN) as dsn:
        conn = pg_lab.connect(dsn)
        pg_lab.apply_sql_file(conn, pg_lab.SCHEMA_PG)
        pg_lab.load_from_sqlite(conn, fixture_db)
        try:
            yield dsn, conn
        finally:
            conn.close()


def _count(conn, sql):
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchone()[0]


def test_postgres_ddl_matches_versioned_model(pg):
    dsn, _ = pg
    expected = json.loads(EXPECTED_PG.read_text(encoding="utf-8"))
    assert diff_models(expected, introspect_postgres(dsn)) == []


def test_load_preserves_counts_and_revenue(pg, fixture_db):
    import sqlite3

    _, conn = pg
    with sqlite3.connect(fixture_db) as s:
        n, rev = s.execute("SELECT COUNT(*), ROUND(SUM(revenue), 2) FROM fact_sales").fetchone()
    assert _count(conn, "SELECT COUNT(*) FROM fact_sales") == n
    assert float(_count(conn, "SELECT ROUND(SUM(total_revenue), 2) FROM vw_customer_kpis")) == pytest.approx(rev)


def test_foreign_key_enforced_in_postgres(pg):
    _, conn = pg
    with pytest.raises(psycopg2.errors.ForeignKeyViolation):
        conn.cursor().execute("""INSERT INTO fact_sales VALUES (990000099,'X','SYN0001',123,1,20100104,
                                 '2010-01-04 10:00','1','1.0','1.0')""")


def test_cr001_forward_rollback_and_idempotency(pg):
    dsn, conn = pg
    baseline = introspect_postgres(dsn)
    pg_lab.apply_sql_file(conn, CR_UP)
    pg_lab.apply_sql_file(conn, CR_UP)  # reaplicação não falha
    after = introspect_postgres(dsn)
    assert after["tables"]["fact_sales"]["checks"] == baseline["tables"]["fact_sales"]["checks"] + 3
    assert _count(conn, """SELECT COUNT(*) FROM pg_constraint
                          WHERE conname LIKE 'ck_fact_sales%' AND NOT convalidated""") == 0
    with pytest.raises(psycopg2.errors.CheckViolation):
        conn.cursor().execute("UPDATE fact_sales SET quantity = 0 WHERE sale_id = 1")
    pg_lab.apply_sql_file(conn, CR_DOWN)
    assert diff_models(baseline, introspect_postgres(dsn)) == []
    assert introspect_postgres(dsn)["tables"]["fact_sales"]["checks"] == baseline["tables"]["fact_sales"]["checks"]


def test_least_privilege_roles(pg):
    _, conn = pg
    pg_lab.apply_sql_file(conn, WH / "security" / "roles_postgres.sql")
    cur = conn.cursor()
    try:
        cur.execute("SET ROLE retentiq_analyst")
        cur.execute("SELECT COUNT(*) FROM vw_customer_kpis")
        assert cur.fetchone()[0] > 0
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM fact_sales LIMIT 1")
        cur.execute("RESET ROLE")
        cur.execute("SET ROLE retentiq_analyst")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT * FROM dim_customer LIMIT 1")
        cur.execute("RESET ROLE")
        cur.execute("SET ROLE retentiq_engineer")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("CREATE TABLE intruso (id int)")
        cur.execute("RESET ROLE")
        cur.execute("SET ROLE retentiq_steward")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("DELETE FROM fact_sales WHERE sale_id = 1")
    finally:
        cur.execute("RESET ROLE")


def test_dml_examples_run_and_leave_no_residue(pg):
    _, conn = pg
    before = _count(conn, "SELECT COUNT(*) FROM fact_sales")
    pg_lab.apply_sql_file(conn, WH / "dml_examples.sql")
    assert _count(conn, "SELECT COUNT(*) FROM fact_sales") == before
    assert _count(conn, "SELECT COUNT(*) FROM dim_customer WHERE customer_id = 99000001") == 0
