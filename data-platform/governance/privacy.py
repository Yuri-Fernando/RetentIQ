"""
Controles técnicos de privacidade para EXPORTS do warehouse (minimização).

O warehouse guarda `customer_id` (pseudônimo do varejista). Para compartilhar
KPIs fora do time de dados (ex.: planilha para a área comercial, dataset de
estudo), este módulo:

  1. troca customer_id por um token HMAC-SHA256 com chave secreta
     (RETENTIQ_PSEUDONYMIZATION_KEY, nunca versionada): o token é estável para a
     mesma chave (permite joins entre exports) e não é reversível sem a chave;
  2. generaliza o país quando o grupo tem menos de k clientes (k-anonimato sobre
     o quase-identificador país) — países raros viram "OUTROS";
  3. reduz a precisão temporal (data -> mês) e monetária (2 casas);
  4. descarta colunas não necessárias para a finalidade declarada.

Limites (registrados em docs/data-governance/privacy-impact-notes.md):
  * pseudonimização NÃO é anonimização (LGPD art. 13 §4; GDPR considerando 26):
    o export continua sendo dado pessoal enquanto a chave existir;
  * k-anonimato só sobre país não protege contra ataques por outros atributos
    (ex.: receita total muito alta e única). Por isso o export arredonda e não
    inclui datas exatas.

Uso:
    set RETENTIQ_PSEUDONYMIZATION_KEY=<segredo>   (PowerShell: $env:RETENTIQ_PSEUDONYMIZATION_KEY="...")
    python data-platform/governance/privacy.py --db data-platform/warehouse/retentiq.db --out kpis_export.csv
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

KEY_ENV = "RETENTIQ_PSEUDONYMIZATION_KEY"
MIN_KEY_BYTES = 16


def load_key(env: dict | None = None) -> bytes:
    env = os.environ if env is None else env
    key = env.get(KEY_ENV, "")
    if len(key.encode()) < MIN_KEY_BYTES:
        raise RuntimeError(
            f"{KEY_ENV} ausente ou curta (mínimo {MIN_KEY_BYTES} bytes). "
            "Defina a chave fora do repositório (cofre/variável de ambiente)."
        )
    return key.encode()


def pseudonymize(value: object, key: bytes, length: int = 24) -> str:
    """Token determinístico HMAC-SHA256(key, str(value)), truncado em `length` hex."""
    digest = hmac.new(key, str(value).encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:length]


def generalize_rare(series: pd.Series, k: int, other: str = "OUTROS") -> pd.Series:
    counts = series.value_counts()
    rare = set(counts[counts < k].index)
    return series.where(~series.isin(rare), other)


def build_kpi_export(db_path: Path, key: bytes, k: int = 10) -> pd.DataFrame:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        df = pd.read_sql_query(
            "SELECT customer_id, primary_country, total_orders, total_revenue, last_purchase "
            "FROM vw_customer_kpis", conn)
    out = pd.DataFrame({
        "customer_token": df["customer_id"].map(lambda v: pseudonymize(v, key)),
        "country_group": generalize_rare(df["primary_country"], k),
        "total_orders": df["total_orders"].astype(int),
        "total_revenue_gbp": df["total_revenue"].round(2),
        "last_purchase_month": pd.to_datetime(df["last_purchase"]).dt.strftime("%Y-%m"),
    })
    return out.sort_values("customer_token").reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export pseudonimizado de KPIs por cliente")
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--k", type=int, default=10, help="tamanho mínimo de grupo por país")
    args = p.parse_args(argv)
    out = build_kpi_export(args.db, load_key(), args.k)
    out.to_csv(args.out, index=False)
    print(f"[privacy] {len(out)} clientes exportados (pseudonimizados, k={args.k}) em {args.out}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
