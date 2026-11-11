"""
Benchmark REPRODUTÍVEL de consultas analíticas no PostgreSQL local, antes e
depois de índices candidatos, incluindo o custo de ESCRITA (recarga do fato).

Mede com EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON):
  * Execution Time (mediana de N execuções, após 1 aquecimento)
  * nó raiz/principal do plano e buffers shared hit/read
Tudo roda em um banco DESCARTÁVEL criado e removido pelo script.

Isto é uma demonstração local (1 máquina, cache quente, sem concorrência) —
NÃO é benchmark representativo de produção. O relatório registra hardware,
versão do SGBD e volume.

Uso:
    set RETENTIQ_PG_DSN=postgresql://user:senha@127.0.0.1:55432/postgres
    python data-platform/governance/benchmark_queries.py --sqlite data-platform/warehouse/retentiq.db \
        --runs 7 --out-json bench.json --out-md docs/data-governance/performance-results.md
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from governance import pg_lab  # noqa: E402

QUERIES = pg_lab.WAREHOUSE / "performance" / "queries.sql"

CANDIDATE_INDEXES = [
    # cobre q1/q6: filtro/agrupamento por dia + medida, permite index-only scan
    "CREATE INDEX idx_fact_sales_date_cover ON fact_sales (date_id) INCLUDE (revenue)",
    # cobre q2/q5: agregação por cliente sem visitar o heap
    "CREATE INDEX idx_fact_sales_customer_cover ON fact_sales (customer_id) INCLUDE (invoice, revenue, invoice_date)",
    # cobre q4
    "CREATE INDEX idx_fact_cancelled_date ON fact_sales_cancelled (date_id) INCLUDE (revenue)",
]


def parse_queries(path: Path = QUERIES) -> dict[str, str]:
    blocks = re.split(r"^-- name:\s*", path.read_text(encoding="utf-8"), flags=re.M)[1:]
    out = {}
    for b in blocks:
        name, _, sql = b.partition("\n")
        out[name.strip()] = sql.strip().rstrip(";")
    return out


def _walk(plan: dict):
    yield plan
    for p in plan.get("Plans", []):
        yield from _walk(p)


def explain(cur, sql: str, params: dict) -> dict:
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}", params)
    doc = cur.fetchone()[0][0]
    nodes = [n["Node Type"] + (f" on {n['Relation Name']}" if "Relation Name" in n else "")
             + (f" using {n['Index Name']}" if "Index Name" in n else "")
             for n in _walk(doc["Plan"]) if "Scan" in n["Node Type"]]
    return {
        "execution_ms": doc["Execution Time"],
        "planning_ms": doc["Planning Time"],
        "scans": nodes,
        "shared_hit": doc["Plan"].get("Shared Hit Blocks", 0),
        "shared_read": doc["Plan"].get("Shared Read Blocks", 0),
        "rows": doc["Plan"].get("Actual Rows"),
    }


def run_suite(cur, queries: dict[str, str], params: dict, runs: int) -> dict:
    res = {}
    for name, sql in queries.items():
        explain(cur, sql, params)  # aquecimento
        samples = [explain(cur, sql, params) for _ in range(runs)]
        res[name] = {
            "median_ms": round(statistics.median(s["execution_ms"] for s in samples), 3),
            "min_ms": round(min(s["execution_ms"] for s in samples), 3),
            "max_ms": round(max(s["execution_ms"] for s in samples), 3),
            "scans": samples[-1]["scans"],
            "shared_hit": samples[-1]["shared_hit"],
            "shared_read": samples[-1]["shared_read"],
            "rows": samples[-1]["rows"],
        }
    return res


def reload_fact_seconds(conn, sqlite_path: Path) -> float:
    cur = conn.cursor()
    cur.execute("TRUNCATE fact_sales")
    t0 = time.perf_counter()
    pg_lab.load_from_sqlite(conn, sqlite_path, tables=["fact_sales"])
    return round(time.perf_counter() - t0, 2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Benchmark de consultas antes/depois de índices")
    p.add_argument("--sqlite", type=Path, required=True)
    p.add_argument("--runs", type=int, default=7)
    p.add_argument("--out-json", type=Path)
    args = p.parse_args(argv)
    admin = pg_lab.admin_dsn()
    if not admin:
        print(f"NOT_RUN: defina {pg_lab.DSN_ENV}", file=sys.stderr)
        return 2

    queries = parse_queries()
    with pg_lab.scratch_db(admin, prefix="retentiq_bench") as dsn:
        conn = pg_lab.connect(dsn)
        cur = conn.cursor()
        pg_lab.apply_sql_file(conn, pg_lab.SCHEMA_PG)
        t0 = time.perf_counter()
        counts = pg_lab.load_from_sqlite(conn, args.sqlite)
        load_s = round(time.perf_counter() - t0, 2)
        cur.execute("VACUUM ANALYZE")
        cur.execute("SELECT customer_id FROM vw_customer_kpis ORDER BY total_orders DESC LIMIT 1")
        params = {"customer_id": cur.fetchone()[0]}
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        cur.execute("SELECT current_setting('shared_buffers'), current_setting('work_mem')")
        shared_buffers, work_mem = cur.fetchone()

        baseline = run_suite(cur, queries, params, args.runs)
        reload_base = reload_fact_seconds(conn, args.sqlite)
        cur.execute("VACUUM ANALYZE fact_sales")

        for ddl in CANDIDATE_INDEXES:
            cur.execute(ddl)
        cur.execute("VACUUM ANALYZE")
        cur.execute("""SELECT relname, pg_size_pretty(pg_relation_size(oid)) FROM pg_class
                       WHERE relname LIKE 'idx_%' ORDER BY relname""")
        index_sizes = dict(cur.fetchall())
        with_idx = run_suite(cur, queries, params, args.runs)
        reload_idx = reload_fact_seconds(conn, args.sqlite)
        cur.execute("SELECT pg_size_pretty(pg_total_relation_size('fact_sales'))")
        fact_total = cur.fetchone()[0]
        conn.close()

    report = {
        "environment": {
            "postgres": version, "shared_buffers": shared_buffers, "work_mem": work_mem,
            "host_os": platform.platform(), "python": platform.python_version(),
            "machine": platform.machine(), "processor": platform.processor(),
        },
        "volume": counts, "initial_load_seconds": load_s, "runs_per_query": args.runs,
        "candidate_indexes": CANDIDATE_INDEXES, "index_sizes": index_sizes,
        "fact_sales_total_size_with_indexes": fact_total,
        "baseline": baseline, "with_candidate_indexes": with_idx,
        "write_cost": {"reload_fact_sales_seconds_baseline": reload_base,
                       "reload_fact_sales_seconds_with_indexes": reload_idx},
    }
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out_json:
        args.out_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
