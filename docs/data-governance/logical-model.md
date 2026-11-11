# Modelo lógico — RetentIQ

> Nível lógico: tabelas, atributos, chaves, domínios e regras de integridade,
> **independente de SGBD**. Diagrama versionado:
> [`diagrams/retentiq-logical.dbml`](diagrams/retentiq-logical.dbml) (DBML, importável
> no dbdiagram.io / `@dbml/cli`).

## 1. Visão relacional

| Tabela | PK | Tipo de chave | FKs | Unicidade adicional |
|---|---|---|---|---|
| `dim_customer` | `customer_id` | natural (origem) | — | — |
| `dim_product` | `stock_code` | natural (origem) | — | — |
| `dim_country` | `country_id` | substituta | — | `country` (natural) |
| `dim_date` | `date_id` | "inteligente" AAAAMMDD | — | `date` (implícita) |
| `fact_sales` | `sale_id` | substituta | `customer_id`, `stock_code`, `country_id`, `date_id` | — |
| `fact_sales_cancelled` | `cancel_id` | substituta | **nenhuma declarada** | — |
| `etl_load_audit` | `load_id` | substituta | — | — |

### Domínios

| Domínio lógico | Colunas | Regra |
|---|---|---|
| moeda (GBP, decimal exato) | `price`, `revenue` | `price > 0`, `revenue = quantity × price ≥ 0` em vendas; negativos em cancelamentos |
| inteiro positivo | `fact_sales.quantity` | `> 0` |
| código de nota | `invoice` | texto; prefixo `C` ⇔ cancelamento |
| data AAAAMMDD | `date_id` | `19000101..29991231`, coerente com `invoice_date` |
| booleano | `is_weekend` | `{0,1}` / `{false,true}` |

## 2. Chaves: natural × substituta (justificativas)

| Identificador | Decisão | Por quê |
|---|---|---|
| `customer_id` | **natural** | estável na origem, inteiro pequeno, já é pseudônimo. Criar substituta não traria ganho e exigiria tabela de-para |
| `stock_code` | **natural** | código de negócio único por produto; texto curto. A comparação é binária (sensível a caixa); verificado no dado real: nenhum código difere de outro só por maiúsculas/minúsculas |
| `country_id` | **substituta** sobre `country` | inteiro no fato é menor que texto repetido 793 mil vezes; `country` continua `UNIQUE`. Limitação: é recalculada a cada carga (não é estável entre cargas — consumidores não devem guardá-la) |
| `date_id` | **inteligente** AAAAMMDD | legível, ordenável, permite filtro por faixa (`BETWEEN 20111101 AND 20111130`) sem join |
| `sale_id` | **substituta obrigatória** | a origem **não tem chave natural do item**: `invoice + stock_code + price` se repete em 23.756 grupos reais; mesmo incluindo `quantity`, linhas legítimas idênticas são indistinguíveis de duplicatas |
| `invoice` | **dimensão degenerada** | atributo do pedido sem outros atributos próprios além de data/cliente/país (que já estão no fato); uma `dim_invoice` só duplicaria colunas |

## 3. Visão dimensional

### Grão

| Fato | Grão declarado | Filtros que definem o grão |
|---|---|---|
| `fact_sales` | **1 linha de nota de venda válida** | `Customer ID` presente · nota sem prefixo `C` · `quantity > 0` · `price > 0` · sem duplicata exata |
| `fact_sales_cancelled` | **1 linha de nota de cancelamento** | `Customer ID` presente · prefixo `C` · sem duplicata exata |

### Medidas

| Medida | Aditividade | Uso correto |
|---|---|---|
| `quantity` | aditiva | `SUM` em qualquer dimensão |
| `revenue` | aditiva | `SUM` em qualquer dimensão |
| `price` | **não aditiva** | nunca `SUM(price)`; usar `SUM(revenue)/SUM(quantity)` para preço médio ponderado |
| contagem de pedidos | **não aditiva entre linhas** | `COUNT(DISTINCT invoice)` — somar contagens por produto superestima pedidos com vários produtos |
| clientes ativos | **não aditiva** | `COUNT(DISTINCT customer_id)` por período; não somar meses |

### Dimensões

`dim_customer`, `dim_product`, `dim_country`, `dim_date` + dimensão degenerada
`invoice`. `dim_date` é **conformada** entre os dois fatos logicamente, mas não
fisicamente: dias que só têm cancelamento não estão em `dim_date` (por isso não há
FK de `fact_sales_cancelled.date_id`).

### Histórico de atributos (SCD)

Todas as dimensões são **tipo 1 por recarga completa** (full refresh): o valor
atual sobrescreve o anterior. Consequências documentadas:

- `primary_country` não guarda histórico de mudança de país;
- `description` de produto é a **última** observada — análises antigas exibem a
  descrição atual;
- uma evolução para SCD tipo 2 (`valid_from`, `valid_to`, `is_current` + chave
  substituta de cliente) está registrada como item de backlog
  ([sample-backlog.md](sample-backlog.md)), sem implementação.

### Semântica dos cancelamentos e risco de double counting

| Risco | Como acontece | Controle implementado |
|---|---|---|
| Receita bruta inflada por notas `C` | nota de cancelamento somada como venda | `C` vai para fato separado; CHECK no SQLite (`invoice` com prefixo `C` em `fact_sales_cancelled`) e regra `cancelamento.ausente_em_fact_sales` |
| Venda líquida errada por join interno | `JOIN dim_customer` descarta estornos de clientes sem venda válida (129 linhas reais) | regra de cálculo no [glossário](business-glossary.md#venda-líquida) + aviso `cancelamento.cliente_sem_venda_valida` |
| Pedidos contados em dobro | `SUM` de contagens por produto | medida definida como `COUNT(DISTINCT invoice)` |
| View multiplicando linhas | join fato × dimensão com chave não única | PK nas dimensões + regra `view.vw_customer_kpis_sem_double_counting` (SUM da view = SUM do fato, verificado no dado real: £ 17.685.460,64 nos dois) |
| Duplicata exata removida que era legítima | duas linhas idênticas reais | **risco aceito e documentado**: 11.996 linhas reais removidas; sem chave de linha na origem não há como distinguir |

## 4. Regras de integridade

1. Toda venda referencia cliente, produto, país e dia existentes (FK, verificada
   também por `PRAGMA foreign_key_check` após a carga).
2. Cancelamentos **não** têm FK para cliente/produto/dia: 129 clientes, 37 produtos
   reais só aparecem em cancelamentos. Decisão: preservar o estorno (receita
   líquida correta) em vez de descartá-lo para satisfazer uma FK.
3. `revenue = quantity × price` (tolerância 0,01).
4. Reconciliação: `linhas da origem = descartadas + vendas + cancelamentos`
   (fecha exatamente no dado real: 1.067.371 = 243.007 + 11.996 + 71 + 793.609 + 18.688).
