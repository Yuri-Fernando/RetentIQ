# Classificação da informação — RetentIQ

> Classificação **técnica** para orientar controles. Não é parecer jurídico nem
> declaração de conformidade com a LGPD/GDPR. Esquema inspirado no controle 5.12
> (classificação da informação) da ISO/IEC 27001:2022.

## Níveis

| Nível | Definição | Exemplos no warehouse | Controles mínimos |
|---|---|---|---|
| `PUBLICO` | divulgação não causa dano | calendário (`dim_date`) | nenhum específico |
| `INTERNO` | uso interno; dano baixo se divulgado | catálogo de produtos, países, auditoria de carga | acesso autenticado |
| `CONFIDENCIAL` | dado comercial sensível | receita, quantidade, preço, número da nota, datas de compra | acesso por papel; sem export linha a linha para fora do time de dados |
| `PESSOAL_PSEUDONIMIZADO` | dado pessoal indireto (LGPD art. 5º, I; GDPR art. 4(1) e 4(5)) | `customer_id`, `primary_country` e qualquer fato que os contenha | minimização, pseudonimização HMAC em exports, k-anonimato em quase-identificadores, retenção definida, acesso restrito |

Não existe nível "sensível" (LGPD art. 5º, II): o dataset não tem saúde, origem
racial, biometria etc.

## Por que `customer_id` é dado pessoal (e não anônimo)

- É um identificador **atribuído pelo varejista**. Quem tem o cadastro do varejista
  consegue reidentificar a pessoa → é **pseudônimo**, não anonimização
  (LGPD art. 13 §4º; GDPR considerando 26).
- Ser numérico **não** o torna anônimo.
- Combinado com país, datas e valores, pode singularizar um cliente: no dado real,
  23 dos países associados a clientes têm menos de 10 clientes cada — país sozinho
  já é quase-identificador nesses casos.

## Campos classificados

A classificação de cada coluna está no [dicionário](data-dictionary.csv) (coluna
`classification`), vem de [`metadata/columns.yaml`](metadata/columns.yaml) e é
validada por teste: toda coluna `customer_id`/`primary_country` precisa estar
como `PESSOAL_PSEUDONIMIZADO`.

| Tabela | Nível máximo | Motivo |
|---|---|---|
| `dim_customer`, `fact_sales`, `fact_sales_cancelled`, `vw_customer_kpis` | PESSOAL_PSEUDONIMIZADO | contêm `customer_id` |
| `dim_product`, `dim_country`, `etl_load_audit` | INTERNO/CONFIDENCIAL | sem dado pessoal |
| `dim_date` | PUBLICO | calendário |
