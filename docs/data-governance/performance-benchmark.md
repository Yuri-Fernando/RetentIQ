# Benchmark de consultas e índices — RetentIQ

> **Demonstração local, não benchmark de produção.** Uma máquina, PostgreSQL em
> Docker Desktop, cache quente, sem concorrência. Números brutos:
> [`evidence/benchmark-2026-11-10.json`](evidence/benchmark-2026-11-10.json).

## Como reproduzir

```bash
docker run -d --name retentiq-pg -e POSTGRES_USER=retentiq -e POSTGRES_PASSWORD=<senha-local> \
  -p 127.0.0.1:55432:5432 postgres:16-alpine
export RETENTIQ_PG_DSN="postgresql://retentiq:<senha-local>@127.0.0.1:55432/postgres"
python data-platform/ingestion/extract_transform_load.py            # warehouse do dado real
python data-platform/governance/benchmark_queries.py --sqlite data-platform/warehouse/retentiq.db \
  --runs 7 --out-json bench.json
```

O script cria um banco descartável, aplica `schema_postgres.sql`, carrega via
`COPY`, roda `VACUUM ANALYZE`, executa cada consulta de
[`warehouse/performance/queries.sql`](../../data-platform/warehouse/performance/queries.sql)
com `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` (1 aquecimento + 7 medições, mediana),
cria os índices candidatos, repete e mede a recarga do fato.

## Ambiente (2026-11-10)

| Item | Valor |
|---|---|
| SGBD | PostgreSQL 16.15 (imagem `postgres:16-alpine`), `shared_buffers=128MB`, `work_mem=4MB` (padrão) |
| Host | Windows 11, Intel Core família 6 modelo 158; VM do Docker com 4 vCPU e 11,7 GiB |
| Volume | dado real: `fact_sales` 793.609 · `fact_sales_cancelled` 18.688 · `dim_customer` 5.878 · `dim_product` 4.631 |
| Carga inicial (COPY via Python, todas as tabelas) | 283 s |

## Índices candidatos testados

```sql
CREATE INDEX idx_fact_sales_date_cover     ON fact_sales (date_id) INCLUDE (revenue);
CREATE INDEX idx_fact_sales_customer_cover ON fact_sales (customer_id) INCLUDE (invoice, revenue, invoice_date);
CREATE INDEX idx_fact_cancelled_date       ON fact_sales_cancelled (date_id) INCLUDE (revenue);
```

## Resultados (mediana de 7 execuções, ms)

| Consulta | Antes | Depois | Plano antes → depois | Buffers (hit) |
|---|---:|---:|---|---|
| q1 receita por mês | 469,2 | 471,1 | Seq Scan → Seq Scan | 9.539 → 9.534 |
| q2 top 20 clientes | 344,4 | 340,9 | Seq Scan → Seq Scan | 9.504 → 9.499 |
| q3 top 20 produtos | 754,9 | 780,8 | Seq Scan → Seq Scan | 9.624 → 9.619 |
| q4 cancelamentos por mês | 6,3 | 6,2 | Seq Scan → Seq Scan | 226 → 226 |
| q5 KPI de um cliente (view) | 19,8 | **9,2** | Bitmap Heap Scan (`idx_fact_sales_customer`) → **Index Only Scan** (`_cover`) | 516 → 72 |
| q6 receita de um mês | 38,3 | **23,1** | Index Scan (`idx_fact_sales_date`) → **Index Only Scan** (`_cover`) | 821 → 246 |

## Custo

| Item | Valor |
|---|---|
| Tamanho dos índices novos | `customer_cover` 36 MB · `date_cover` 24 MB · `cancelled_date` 592 kB (os 3 originais somam ≈ 21 MB) |
| `fact_sales` total com índices | 183 MB |
| Recarga de `fact_sales` (TRUNCATE + COPY) | 242,6 s sem × 241,0 s com os índices novos |

## Leitura dos resultados

1. **Agregações sobre a tabela inteira (q1–q4) não melhoram com índice.** Ler
   793 mil linhas por Seq Scan já é o plano mais barato; as variações (±3%) são
   ruído.
2. **Consultas seletivas melhoram com índice cobrindo**: q5 2,2× e q6 1,7×, porque
   o Index Only Scan evita visitar o heap (buffers caem 7× e 3×). Exige `VACUUM`
   recente (visibility map), o que o ETL de full refresh + `ANALYZE` já favorece.
3. **Custo de escrita: inconclusivo.** A recarga é dominada pela geração do CSV em
   Python e pela rede do Docker Desktop (~240 s); o custo de manter 2 índices a
   mais ficou abaixo do ruído desta medição. Medir de verdade exigiria COPY a
   partir de arquivo local ao servidor.
4. **Decisão:** **não** alterar o DDL. Os ganhos são em consultas que levam
   ~20-40 ms e não são gargalo do produto; os índices custam +60 MB (+33% do
   tamanho do fato). Reavaliar se a API passar a consultar a view por cliente em
   alto volume (ver dívida DT-05).
