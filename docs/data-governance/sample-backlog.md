# Backlog e quadro Kanban — modelagem e governança (exemplo)

> **Artefato de laboratório.** Quadro em Markdown para organizar o trabalho deste
> repositório. Não representa uma equipe Scrum real nem ferramenta de gestão.

## História de usuário — catálogo

> **Como** analista de BI, **quero** consultar o significado, a origem e a regra
> de qualidade de cada coluna do warehouse **para** montar relatórios sem
> perguntar ao time de dados.

Critérios de aceite:
- [x] dicionário cobre 100% das colunas físicas (teste falha se não cobrir)
- [x] cada coluna tem classificação, origem, transformação e regra de qualidade
- [x] glossário define receita bruta, venda líquida, pedido, cancelamento
- [x] dicionário é regenerado do banco, não digitado à mão (`--check` no CI)
- [ ] dicionário publicado em página navegável (fora do escopo atual)

## Quadro

| A fazer | Em andamento | Feito (v2.2.0) |
|---|---|---|
| DT-01 `primary_country_id` (expand/contract) | — | schema físico SQLite com PK/FK/CHECK/view |
| DT-04 carga atômica (`os.replace`) | — | auditoria de carga + reconciliação |
| DT-05 API consumir `vw_customer_kpis` | — | 30 regras de qualidade + catálogo YAML |
| SCD tipo 2 em `dim_customer` | — | dicionário gerado + glossário + catálogo + linhagem |
| `pgaudit` no PostgreSQL | — | engenharia reversa + schema diff + `@dbml/cli` |
| trilha de auditoria fora do full refresh | — | CR-001 up/down testada em PostgreSQL |
| expurgo automático de exports > 90 dias | — | papéis de menor privilégio testados |
| incorporar CR-001 ao DDL base | — | benchmark com EXPLAIN ANALYZE |

## Definição de pronto (DoD)
Código + teste + documentação + CI verde + CHANGELOG + dicionário/snapshot regenerados.
