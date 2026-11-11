# Padrões de nomenclatura — RetentIQ (warehouse)

> Padrão para objetos **novos**. Objetos existentes que divergem foram mantidos
> para não quebrar a API, os scripts de ML e o ETL (regra de compatibilidade) — a
> divergência fica registrada como dívida técnica no fim deste documento.

## Regras

| Objeto | Padrão | Exemplo |
|---|---|---|
| Geral | `snake_case`, ASCII, inglês, sem abreviação ambígua | `invoice_date` |
| Tabela fato | `fact_<processo>` no singular do processo | `fact_sales`, `fact_sales_cancelled` |
| Dimensão | `dim_<entidade>` no singular | `dim_customer` |
| View de consumo | `vw_<assunto>` | `vw_customer_kpis` |
| Tabela técnica | `<domínio>_<assunto>` | `etl_load_audit` |
| PK substituta | `<entidade>_id` | `sale_id`, `country_id` |
| PK natural | nome de negócio da origem | `stock_code`, `customer_id` |
| FK | mesmo nome da PK referenciada | `fact_sales.customer_id → dim_customer.customer_id` |
| Chave de data | `date_id` (inteiro AAAAMMDD) | `20111209` |
| Timestamp | sufixo `_date` para data de negócio da origem; `_at` para instante técnico; `_utc` quando com fuso UTC explícito | `invoice_date`, `loaded_at_utc` |
| Booleano | prefixo `is_` / `has_` | `is_weekend` |
| Contagem/medida | substantivo + unidade quando houver ambiguidade | `quantity`, `revenue`, `fact_sales_revenue` |
| Índice | `idx_<tabela>_<colunas>` | `idx_fact_sales_customer` |
| CHECK nomeado | `ck_<tabela>_<regra>` | `ck_fact_sales_price_positive` |
| UNIQUE nomeado | `uq_<tabela>_<colunas>` | — |
| FK nomeada | `fk_<tabela>_<referenciada>` | — |
| Migração / mudança | `CR-<nnn>_<assunto>.(up|down).sql` | `CR-001_fact_sales_checks.up.sql` |
| Versão de schema | SemVer do projeto no CHANGELOG + snapshot em `model/*.schema.json` | v2.2.0 |

## Inconsistências reais encontradas (auditoria do schema atual)

| Achado | Onde | Risco de corrigir | Decisão |
|---|---|---|---|
| `primary_country` é texto, não FK para `dim_country` | `dim_customer` | API lê a coluna pelo nome | mantido; dívida DT-01 |
| Coluna `date` usa palavra reservada/genérica | `dim_date.date` | lida por scripts; exige aspas em alguns SGBDs | mantido; dívida DT-02 |
| Constraints anônimas (nome gerado pelo SGBD, ex.: `fact_sales_customer_id_fkey`) | DDL PostgreSQL | renomear constraint é barato, mas muda o diff de todo o histórico | novas constraints já nomeadas (CR-001); dívida DT-03 |
| `price`/`revenue` sem sufixo de moeda | fatos | ambiguidade se surgir outra moeda | mantido; moeda documentada no glossário (GBP) |
| `weekday` em inglês (`Monday`) | `dim_date` | relatórios em português precisam traduzir | mantido; tradução é responsabilidade da camada de apresentação |

## Dívidas técnicas registradas

| ID | Descrição | Proposta | Status |
|---|---|---|---|
| DT-01 | `dim_customer.primary_country` texto | adicionar `primary_country_id` FK + manter a coluna antiga por 1 versão (expand/contract) | planejado |
| DT-02 | `dim_date.date` | adicionar `calendar_date` e depreciar `date` | planejado |
| DT-03 | constraints PostgreSQL sem nome explícito | nomear na próxima mudança estrutural de cada tabela | planejado |
| DT-04 | carga não atômica (por tabela) | gravar em arquivo temporário e `os.replace` no final | planejado |
| DT-05 | API agrega KPIs direto em `fact_sales` (`metrics.ts`, `metricsService.ts`) em vez de usar `vw_customer_kpis` — mesma regra de negócio em dois lugares | migrar as rotas para a view, com teste de igualdade de resultado | planejado |
