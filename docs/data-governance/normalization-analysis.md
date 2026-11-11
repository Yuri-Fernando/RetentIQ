# Normalização e desnormalização — RetentIQ

> Os exemplos usam o **próprio domínio** (linhas reais do Online Retail II) e o OLTP
> inferido descrito em [conceptual-model.md](conceptual-model.md). A origem que
> recebemos é uma planilha plana — ela é o ponto de partida da análise.

## 1. A relação de origem (não normalizada)

`VENDA_PLANA(invoice, stock_code, description, quantity, invoice_date, price, customer_id, country)`

Uma linha por item de nota. Exemplo real (primeiras linhas carregadas):

| invoice | stock_code | description | quantity | invoice_date | price | customer_id | country |
|---|---|---|---|---|---|---|---|
| 489434 | 85048 | 15CM CHRISTMAS GLASS BALL 20 LIGHTS | 12 | 2009-12-01 07:45 | 6,95 | 13085 | United Kingdom |
| 489434 | 79323P | PINK CHERRY LIGHTS | 12 | 2009-12-01 07:45 | 6,75 | 13085 | United Kingdom |

## 2. Dependências funcionais (DFs) observadas

| DF | Vale no dado real? | Comentário |
|---|---|---|
| `invoice → invoice_date, customer_id` | esperado sim (cabeçalho do pedido) | |
| `invoice → country` | **quase** | o país é por linha na origem |
| `stock_code → description` | **não** | medido no arquivo bruto: 1.232 de 4.950 códigos têm mais de uma descrição (por isso `dim_product` guarda a última) |
| `customer_id → country` | **não** | 13 clientes reais aparecem com mais de um país |
| `(invoice, stock_code) → quantity, price` | **não** | o mesmo produto aparece em linhas distintas da mesma nota (23.756 grupos `invoice+stock_code+price` repetidos) |

Consequência direta: **não existe chave candidata composta por atributos de
negócio** para o item. Por isso o modelo usa chave substituta (`sale_id`).

## 3. Formas normais (aplicadas ao OLTP inferido)

### 1FN — valores atômicos, sem grupos repetitivos

A planilha já está em 1FN: cada célula tem um valor atômico e não há colunas
`produto1, produto2, ...`. ✔

### 2FN — sem dependência parcial de uma chave composta

Se a chave do item fosse `(invoice, linha)`, os atributos `invoice_date` e
`customer_id` dependeriam só de `invoice` (parte da chave): **violação de 2FN**.
Decomposição:

- `pedido(invoice PK, invoice_date, customer_id)`
- `item_pedido(invoice FK, linha, stock_code, quantity, price, PK(invoice, linha))`

### 3FN — sem dependência transitiva

Em `item_pedido`, `description` depende de `stock_code`, que não é chave:
**dependência transitiva** `(invoice, linha) → stock_code → description`.
Decomposição: `produto(stock_code PK, description)`.

O mesmo vale para o país se ele for atributo do cliente:
`cliente(customer_id PK, country)` — mas o dado real mostra que o país **não** é
função do cliente (13 exceções), então em 3FN ele ficaria no pedido.

### Anomalia de atualização — exemplo concreto

Na planilha plana, a descrição de um produto se repete em cada linha vendida.
Corrigir a descrição de um produto exigiria atualizar **todas** as linhas desse
produto; esquecer uma deixa duas descrições para o mesmo código. A própria origem
exibe exatamente esse sintoma (descrições diferentes para a mesma referência). Em
3FN a descrição mora em uma única linha de `produto` e a anomalia não existe.

Outras anomalias da forma plana:

- **inserção:** não dá para cadastrar um produto que nunca foi vendido;
- **exclusão:** apagar a única venda de um produto apaga o próprio produto.

## 4. Por que o warehouse é DESNORMALIZADO (esquema estrela)

| Escolha | Normalizado (3FN) | Estrela adotada | Trade-off |
|---|---|---|---|
| Cabeçalho do pedido | tabela `pedido` | colunas `invoice`, `invoice_date`, `customer_id`, `country_id`, `date_id` repetidas em cada linha de `fact_sales` | +bytes por linha · −1 join em toda consulta |
| País | atributo do pedido | `country_id` no fato **e** `primary_country` (texto) em `dim_customer` | redundância intencional, com semânticas diferentes (§5) |
| Calendário | derivado de `invoice_date` na consulta | `dim_date` + `date_id` no fato | duplica a informação de data · consultas por mês/fim de semana sem funções de data |
| KPIs por cliente | calculados sob demanda | `vw_customer_kpis` (view, **não** materializada) | lógica de agregação em um só lugar; custo de cálculo a cada leitura |

Justificativa: o warehouse é **somente leitura** entre cargas (full refresh). As
anomalias de atualização que a normalização evita não ocorrem porque ninguém
atualiza linha a linha — o ETL recria tudo a partir da origem. Em troca, as
consultas analíticas ficam com no máximo um join por dimensão. A decisão está
registrada em [ADR-004](../adr/ADR-004-dimensional-model.md).

Custo medido: as agregações completas no PostgreSQL local levam de 344 a 755 ms
sobre 793.609 linhas ([benchmark](performance-benchmark.md)) — sem a desnormalização
do cabeçalho seria necessário um join adicional com a tabela de pedidos em cada uma.

## 5. Redundâncias analisadas (sem mudar nada antes de entender a semântica)

### `dim_customer.primary_country` × `dim_country`

- **Não é uma FK.** `primary_country` é texto e significa "país da última linha do
  cliente na ordem do arquivo"; `fact_sales.country_id` é o país **da venda**.
- Para 13 clientes reais as duas informações divergem em algumas vendas.
- **Decisão:** manter. Trocar por `primary_country_id REFERENCES dim_country` seria
  normalização correta, mas muda uma coluna lida pela API (regra C: não renomear
  colunas). Registrado como dívida técnica em [naming-standards.md](naming-standards.md#dívidas-técnicas-registradas).

### `fact_sales.invoice_date` × `dim_date`

- `invoice_date` tem **hora**; `dim_date` tem **dia**. Não é duplicação pura:
  análises de hora do dia precisam do timestamp.
- Risco: `date_id` divergir de `invoice_date`. **Controle:** regra
  `datas.date_id_coerente_com_invoice_date` (0 divergências no dado real).

### `fact_sales.revenue` × `quantity * price`

- Medida derivada materializada para que `SUM(revenue)` seja simples e aditiva.
- **Controle:** CHECK `revenue >= 0` + regra `fact_sales.revenue_igual_qtd_x_preco`.
