# Glossário de negócio — RetentIQ

> Escopo: termos usados no warehouse analítico construído a partir do dataset público
> **Online Retail II (UCI)**. Cada termo tem definição, regra de cálculo e limitações
> conhecidas. Os nomes de termo abaixo (`###`) são referenciados pela coluna
> `glossary_term` do [dicionário de dados](data-dictionary.csv). Um teste automatizado
> falha se o dicionário citar um termo que não existe aqui.
>
> Moeda: a origem não declara moeda por linha. O varejista é do Reino Unido e a
> documentação da UCI descreve preços em libra esterlina — **assume-se GBP** para
> todas as linhas, sem conversão cambial (limitação registrada).

### Cliente

- **Definição:** pessoa ou empresa compradora identificada pelo varejista por um
  `Customer ID` numérico.
- **No modelo:** `dim_customer.customer_id`, `fact_sales.customer_id`.
- **Regra:** só entra no warehouse quem tem `Customer ID` preenchido. No dado real,
  243.007 linhas (≈ 22,8% da origem) não têm cliente e são descartadas — portanto
  receita "de clientes" ≠ receita total do varejista.
- **Privacidade:** `customer_id` é **pseudônimo**, não dado anonimizado (ver
  [data-classification.md](data-classification.md)).

### País

- **Definição:** país informado na linha da nota (`Country`).
- **No modelo:** `dim_country`, `fact_sales.country_id`, `dim_customer.primary_country`.
- **Regra:** nulo vira `Unspecified`. O país da **venda** (fato) pode diferir do país
  **associado ao cliente** (`primary_country` = país da última linha do cliente na
  ordem do arquivo). 13 clientes reais têm mais de um país.
- **Limitação:** o dataset não diz se é país de entrega ou de cadastro.

### Produto

- **Definição:** item de catálogo identificado por `StockCode` (SKU alfanumérico).
- **No modelo:** `dim_product`.
- **Regra:** descrição = última descrição observada para o código. Códigos de
  serviço/ajuste da origem (ex.: `POST`, `M`, `DOT`) **não são filtrados** — são
  tratados como produtos (limitação conhecida, candidata a regra de negócio futura).

### Pedido

- **Definição:** uma nota fiscal/pedido (`Invoice`), que agrupa um ou mais itens.
- **No modelo:** dimensão degenerada `fact_sales.invoice` (sem tabela própria).
- **Regra:** contagem de pedidos = `COUNT(DISTINCT invoice)`, nunca `COUNT(*)`
  (que conta itens).

### Item de Venda

- **Definição:** uma linha de nota (produto × quantidade × preço) de uma venda válida.
- **No modelo:** 1 linha de `fact_sales` (é o **grão** do fato).
- **Regra:** a origem não tem chave natural para o item — o mesmo
  `invoice + stock_code + price` aparece em linhas distintas (23.756 grupos no dado
  real) — por isso a chave é substituta (`sale_id`).

### Data de Venda

- **Definição:** data/hora de emissão da nota (`InvoiceDate`).
- **No modelo:** `fact_sales.invoice_date` (timestamp) e `dim_date` (dia).
- **Limitação:** o dataset não distingue data de venda, faturamento ou
  processamento, nem informa fuso. Assume-se **data de venda em hora local do
  varejista**. `dim_date` só contém dias com venda (não é calendário contínuo):
  dias sem venda não aparecem em séries temporais feitas só com `dim_date`.

### Cancelamento

- **Definição:** nota cujo número começa com `C` (regra documentada pela própria
  origem): cancelamento ou devolução de itens.
- **No modelo:** `fact_sales_cancelled` (quantidade e receita negativas).
- **Regra:** cancelamentos **nunca** entram em `fact_sales` (check
  `cancelamento.ausente_em_fact_sales`). Não há vínculo item-a-item entre a nota
  `C` e a venda original (a origem não traz essa referência).

### Receita Bruta

- **Definição:** soma de `quantity × price` das vendas válidas.
- **No modelo:** `SUM(fact_sales.revenue)`; `vw_customer_kpis.total_revenue`.
- **Regra:** exclui linhas sem cliente, duplicadas exatas, preço ≤ 0, quantidade
  ≤ 0 e notas `C`. Medida **aditiva** em todas as dimensões.
- **Valor real medido** (carga completa do Online Retail II): **£ 17.685.460,64**.

### Venda Líquida

- **Definição:** receita bruta menos o valor estornado em cancelamentos.
- **Cálculo:** `SUM(fact_sales.revenue) + SUM(fact_sales_cancelled.revenue)`
  (o segundo termo já é negativo).
- **Valor real medido:** £ 17.685.460,64 − £ 1.092.067,63 = **£ 16.593.393,01**.
- **Regra:** **não** existe coluna materializada nem view para venda líquida — a
  `vw_customer_kpis` é **bruta**. Como cancelamentos podem referenciar clientes sem
  venda válida, a venda líquida por cliente deve usar `LEFT JOIN` a partir da
  união das duas tabelas de fato, para não perder estornos órfãos.

### Carga

- **Definição:** uma execução completa do ETL (full refresh).
- **No modelo:** 1 linha em `etl_load_audit`.
- **Regra:** registra hash SHA-256 da origem e as contagens que fecham a
  reconciliação `origem = descartadas + vendas + cancelamentos`.
