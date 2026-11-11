"""
Utilitários para o laboratório PostgreSQL DESCARTÁVEL (testes, CI e benchmark).

  * create_scratch_db / drop_scratch_db : banco temporário isolado (nunca reaproveita
    um banco existente — protege ambiente compartilhado)
  * apply_sql_file                      : executa DDL/DML versionado (autocommit, respeita BEGIN/COMMIT do arquivo)
  * load_from_sqlite                    : copia o warehouse SQLite para o PostgreSQL via COPY

A DSN administrativa vem de RETENTIQ_PG_DSN (ex.: postgresql://user:senha@127.0.0.1:55432/postgres).
Nada aqui guarda credencial.
"""
from __future__ import annotations

import csv
import io
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
WAREHOUSE = ROOT / "data-platform" / "warehouse"
SCHEMA_PG = WAREHOUSE / "schema_postgres.sql"
DSN_ENV = "RETENTIQ_PG_DSN"

LOAD_ORDER = [
    "dim_customer", "dim_product", "dim_country", "dim_date",
    "fact_sales", "fact_sales_cancelled", "etl_load_audit",
]
SEQUENCES = {"dim_country": ("country_id", "dim_country_country_id_seq"),
             "etl_load_audit": ("load_id", "etl_load_audit_load_id_seq")}


def admin_dsn() -> str | None:
    return os.environ.get(DSN_ENV)


def _with_db(dsn: str, dbname: str) -> str:
    parts = urlsplit(dsn)
    return urlunsplit(parts._replace(path=f"/{dbname}"))


def connect(dsn: str):
    import psycopg2

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    return conn


def create_scratch_db(dsn: str, prefix: str = "retentiq_t") -> str:
    name = f"{prefix}_{secrets.token_hex(4)}"
    # sem `with conn:` — no psycopg2 2.9 ele abre transação e CREATE DATABASE não pode rodar nela
    conn = connect(dsn)
    try:
        conn.cursor().execute(f'CREATE DATABASE "{name}"')
    finally:
        conn.close()
    return _with_db(dsn, name)


def drop_scratch_db(admin: str, scratch_dsn: str) -> None:
    name = urlsplit(scratch_dsn).path.lstrip("/")
    assert name.startswith("retentiq_t_") or name.startswith("retentiq_bench_"), "recusa dropar banco não descartável"
    conn = connect(admin)
    try:
        conn.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    finally:
        conn.close()


@contextmanager
def scratch_db(admin: str, prefix: str = "retentiq_t"):
    dsn = create_scratch_db(admin, prefix)
    try:
        yield dsn
    finally:
        drop_scratch_db(admin, dsn)


def apply_sql_file(conn, path: Path) -> None:
    conn.cursor().execute(Path(path).read_text(encoding="utf-8"))


def load_from_sqlite(conn, sqlite_path: Path, tables: list[str] | None = None) -> dict[str, int]:
    src = sqlite3.connect(f"{Path(sqlite_path).resolve().as_uri()}?mode=ro", uri=True)
    counts: dict[str, int] = {}
    cur = conn.cursor()
    try:
        for t in tables or LOAD_ORDER:
            exists = src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()
            if not exists:
                continue
            q = src.execute(f"SELECT * FROM {t}")
            cols = [d[0] for d in q.description]
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            n = 0
            for row in q:
                w.writerow(["" if v is None else v for v in row])
                n += 1
            buf.seek(0)
            cur.copy_expert(f"COPY {t} ({', '.join(cols)}) FROM STDIN WITH (FORMAT csv)", buf)
            counts[t] = n
            if t in SEQUENCES:
                col, seq = SEQUENCES[t]
                cur.execute(f"SELECT setval('{seq}', COALESCE((SELECT MAX({col}) FROM {t}), 0) + 1, false)")
        cur.execute("ANALYZE")
        return counts
    finally:
        src.close()
