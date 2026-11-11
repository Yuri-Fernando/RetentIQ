"""
Fixture sintética e determinística no MESMO formato que o ETL produz após o
extract() do Online Retail II (colunas já renomeadas).

Por que existe:
  * o CI não pode depender do .xlsx de 43 MB (dado de terceiro, não versionado);
  * testes não devem usar identificadores de clientes reais (LGPD — minimização);
  * cada caso de borda observado nos dados reais tem uma linha correspondente
    aqui, para que as regras de limpeza e de qualidade sejam exercitadas de
    verdade (não só o "caminho feliz").

Todos os customer_id ficam na faixa 90001+ e os stock_code começam com 'SYN',
o que torna impossível confundi-los com o dataset real (12346..18287).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RAW_COLUMNS = [
    "invoice", "stock_code", "description", "quantity",
    "invoice_date", "price", "customer_id", "country", "source_sheet",
]

COUNTRIES = ["United Kingdom", "France", "Germany", "Netherlands", "Portugal"]


def synthetic_raw(n_invoices: int = 400, seed: int = 42) -> pd.DataFrame:
    """Gera um DataFrame bruto sintético reprodutível.

    Casos de borda incluídos propositalmente (com contagem conhecida):
      - 5 linhas sem customer_id                     -> removidas pelo ETL
      - 3 linhas duplicadas exatas                   -> removidas pelo ETL
      - 4 vendas com price <= 0 ou quantity <= 0     -> removidas pelo ETL
      - cancelamentos ('C' + quantidade negativa)    -> fact_sales_cancelled
      - 1 cancelamento de cliente/produto sem venda  -> órfão tolerado (warning)
      - mesmo produto 2x na mesma nota               -> prova que não há chave natural
      - 1 cliente comprando de 2 países              -> semântica de primary_country
      - descrição e país nulos                        -> DESCONHECIDO / Unspecified
    """
    rng = np.random.RandomState(seed)
    n_customers = 60
    n_products = 40
    customers = np.arange(90001, 90001 + n_customers)
    products = [f"SYN{i:04d}" for i in range(1, n_products + 1)]
    descriptions = {p: f"PRODUTO SINTETICO {p[-4:]}" for p in products}
    customer_country = {c: COUNTRIES[i % len(COUNTRIES)] for i, c in enumerate(customers)}
    base = pd.Timestamp("2010-01-04 08:00:00")

    rows: list[dict] = []
    for i in range(n_invoices):
        invoice = str(500000 + i)
        cust = int(customers[rng.randint(0, n_customers)])
        when = base + pd.Timedelta(days=int(rng.randint(0, 365)), minutes=int(rng.randint(0, 600)))
        for _ in range(int(rng.randint(1, 5))):
            prod = products[rng.randint(0, n_products)]
            rows.append({
                "invoice": invoice,
                "stock_code": prod,
                "description": descriptions[prod],
                "quantity": int(rng.randint(1, 25)),
                "invoice_date": when,
                "price": float(round(rng.uniform(0.5, 30.0), 2)),
                "customer_id": float(cust),
                "country": customer_country[cust],
                "source_sheet": "Year 2010-2011" if when.year >= 2011 else "Year 2009-2010",
            })

    t = base + pd.Timedelta(days=10)
    edge = [
        # mesmo produto 2x na mesma nota (linhas distintas, preço igual)
        dict(invoice="599001", stock_code="SYN0001", description=descriptions["SYN0001"], quantity=2, invoice_date=t, price=3.0, customer_id=90001.0, country="United Kingdom"),
        dict(invoice="599001", stock_code="SYN0001", description=descriptions["SYN0001"], quantity=5, invoice_date=t, price=3.0, customer_id=90001.0, country="United Kingdom"),
        # cliente 90002 também compra declarando outro país (dado de origem)
        dict(invoice="599002", stock_code="SYN0002", description=descriptions["SYN0002"], quantity=1, invoice_date=t + pd.Timedelta(days=200), price=9.5, customer_id=90002.0, country="Portugal"),
        # descrição e país nulos
        dict(invoice="599003", stock_code="SYN0003", description=None, quantity=3, invoice_date=t, price=1.25, customer_id=90003.0, country=None),
        # vendas inválidas (preço/quantidade <= 0)
        dict(invoice="599004", stock_code="SYN0004", description=descriptions["SYN0004"], quantity=4, invoice_date=t, price=0.0, customer_id=90004.0, country="France"),
        dict(invoice="599005", stock_code="SYN0005", description=descriptions["SYN0005"], quantity=0, invoice_date=t, price=2.0, customer_id=90005.0, country="France"),
        dict(invoice="599006", stock_code="SYN0006", description=descriptions["SYN0006"], quantity=-2, invoice_date=t, price=2.0, customer_id=90006.0, country="Germany"),
        dict(invoice="599007", stock_code="SYN0007", description=descriptions["SYN0007"], quantity=1, invoice_date=t, price=-1.0, customer_id=90007.0, country="Germany"),
        # cancelamentos (prefixo C, quantidade negativa)
        dict(invoice="C599100", stock_code="SYN0001", description=descriptions["SYN0001"], quantity=-2, invoice_date=t + pd.Timedelta(days=1), price=3.0, customer_id=90001.0, country="United Kingdom"),
        dict(invoice="C599101", stock_code="SYN0010", description=descriptions["SYN0010"], quantity=-1, invoice_date=t + pd.Timedelta(days=2), price=4.0, customer_id=90010.0, country="Germany"),
        # cancelamento de cliente e produto que nunca tiveram venda válida
        dict(invoice="C599102", stock_code="SYN9999", description="PRODUTO SO CANCELADO", quantity=-1, invoice_date=t + pd.Timedelta(days=3), price=5.0, customer_id=99999.0, country="Netherlands"),
    ]
    for e in edge:
        e["source_sheet"] = "Year 2009-2010"
        rows.append(e)

    # linhas sem customer_id
    for k in range(5):
        rows.append(dict(invoice=str(598000 + k), stock_code="SYN0011", description=descriptions["SYN0011"], quantity=1,
                         invoice_date=t, price=2.0, customer_id=np.nan, country="United Kingdom", source_sheet="Year 2009-2010"))

    df = pd.DataFrame(rows, columns=RAW_COLUMNS)
    # 3 duplicatas exatas de linhas já existentes
    df = pd.concat([df, df.iloc[[0, 1, 2]]], ignore_index=True)
    df["stock_code"] = df["stock_code"].astype(str)
    return df


EDGE_COUNTS = {
    "missing_customer": 5,
    "exact_duplicates": 3,
    "invalid_sales": 4,
    "cancellations": 3,
    "orphan_cancellations_customer": 1,
    "orphan_cancellations_product": 1,
}
