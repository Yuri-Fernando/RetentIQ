# Catálogo de dados — RetentIQ

> Catálogo **leve, versionado em Markdown** (não há ferramenta de catálogo como
> DataHub/OpenMetadata neste projeto). O nível de coluna está no
> [dicionário](data-dictionary.csv), gerado do banco. Papéis de owner/steward são
> **responsabilidades simuladas** de laboratório.

## Conjuntos de dados

| Ativo | Tipo | Grão | Linhas (dado real) | Classificação máx. | Owner (simulado) | Atualização | Consumidores |
|---|---|---|---|---|---|---|---|
| `online_retail_II.xlsx` | arquivo bruto (terceiro, UCI) | linha de nota | 1.067.371 | PESSOAL_PSEUDONIMIZADO | Plataforma de Dados | estático (dataset histórico 2009–2011) | ETL |
| `dim_customer` | dimensão | cliente | 5.878 | PESSOAL_PSEUDONIMIZADO | Comercial | full refresh por carga | view, ML |
| `dim_product` | dimensão | produto | 4.631 | INTERNO | Catálogo | full refresh | API, ML (recomendação) |
| `dim_country` | dimensão | país | 41 | INTERNO | Comercial | full refresh | API |
| `dim_date` | dimensão | dia com venda | 604 | PUBLICO | Plataforma de Dados | full refresh | API, ML (demanda) |
| `fact_sales` | fato | linha de venda válida | 793.609 | PESSOAL_PSEUDONIMIZADO | Comercial | full refresh | view, ML, API |
| `fact_sales_cancelled` | fato | linha de cancelamento | 18.688 | PESSOAL_PSEUDONIMIZADO | Comercial | full refresh | análises de cancelamento |
| `etl_load_audit` | técnica / auditoria | carga | 1 por execução | INTERNO | Plataforma de Dados | append por carga | steward, checks |
| `vw_customer_kpis` | view de consumo | cliente | 5.878 | PESSOAL_PSEUDONIMIZADO | Comercial | sob demanda (view) | export pseudonimizado, papel `retentiq_analyst` (a API atual **não** usa a view: agrega direto em `fact_sales` — dívida DT-05) |
| `datasets/processed/*.parquet` | extrato para ML | = fato/dimensão | = origem | PESSOAL_PSEUDONIMIZADO | Plataforma de Dados | por carga | `data-platform/ml/` |
| export de KPIs (`governance/privacy.py`) | arquivo derivado | cliente | = view | PESSOAL_PSEUDONIMIZADO (token HMAC) | Comercial | sob demanda | compartilhamento fora do time de dados |

## Proveniência e uso permitido do dado de origem

| Item | Registro |
|---|---|
| Fonte | UCI Machine Learning Repository — *Online Retail II*, https://archive.ics.uci.edu/dataset/502/online+retail+ii |
| Licença | CC BY 4.0, conforme a página do dataset (verificar a página antes de redistribuir) |
| Versionado no Git? | **Não.** `.gitignore` exclui `datasets/raw/*`, `*.db` e `*.parquet` |
| Dados pessoais | apenas `Customer ID` (pseudônimo do varejista) + país; nenhum nome/e-mail/endereço |
| Testes e CI | usam **fixture sintética** (`governance/fixtures.py`, IDs 90001+), nunca o dado real |
| Retenção | ver [retention-policy-example.md](retention-policy-example.md) |

## Como encontrar o que procura

| Pergunta | Onde |
|---|---|
| O que significa a coluna X? | [data-dictionary.csv](data-dictionary.csv) |
| Como se calcula receita líquida? | [business-glossary.md](business-glossary.md#venda-líquida) |
| De onde vem o valor? | [data-lineage.md](data-lineage.md) |
| Que regra de qualidade protege a coluna? | coluna `quality_rule` do dicionário → [quality-rules.yaml](quality-rules.yaml) |
| Quem pode acessar? | [access-matrix.md](access-matrix.md) |
