# Perguntas e respostas de entrevista — modelagem e administração de dados

> Respostas curtas, ancoradas em exemplos deste repositório (RetentIQ) e do
> FleetCam. Servem de roteiro de estudo, não de texto decorado.

**1. Diferença entre modelo conceitual, lógico e físico?**
Conceitual: entidades e relações de negócio (Cliente faz Pedido). Lógico: tabelas,
atributos, chaves, domínios, independente de SGBD (`fact_sales` com grão "linha de
nota"). Físico: implementação num SGBD — tipos, índices, constraints (`NUMERIC(14,4)`
no PostgreSQL, `REAL` no SQLite). Ver os três documentos em `docs/data-governance/`.

**2. O que é 3FN? Dê um exemplo.**
Toda coluna não-chave depende da chave, da chave inteira e de nada além da chave.
Na planilha de origem, `description` depende de `stock_code`, não do item da nota:
dependência transitiva. Prova de que causa problema: 1.232 produtos têm mais de uma
descrição no arquivo bruto (anomalia de atualização).

**3. Por que o warehouse não está em 3FN?**
É leitura analítica recriada a cada carga: as anomalias de atualização não ocorrem
e a estrela economiza joins. Registrado no ADR-004, com as redundâncias
monitoradas por regras de coerência.

**4. Estrela × floco de neve?**
Floco normaliza as dimensões (produto → categoria). O dataset não tem hierarquias;
criar `dim_category` seria inventar entidade.

**5. O que é grão? Qual o de `fact_sales`?**
O que uma linha representa. Aqui: 1 linha de nota de venda válida. Medidas
aditivas: `quantity`, `revenue`; não aditiva: `price` (usar receita/quantidade).

**6. Fato × dimensão × dimensão degenerada?**
Fato: eventos mensuráveis (vendas). Dimensão: contexto (cliente, produto, data).
Degenerada: atributo de dimensão sem tabela própria — `invoice` no fato.

**7. DDL × DML?**
DDL define estrutura (`CREATE TABLE`, `ALTER`); DML manipula dados (`INSERT`,
`UPDATE`, `DELETE`, `SELECT`). Exemplos executáveis: `schema_*.sql`,
`dml_examples.sql` (roda em transação com `ROLLBACK`).

**8. PK natural ou substituta?**
Natural quando estável e única (`stock_code`). Substituta quando não há chave
natural confiável: o mesmo `invoice+stock_code+price` repete 23.756 vezes, então
`sale_id`.

**9. Quando NÃO criar uma FK?**
Quando a referência pode legitimamente não existir e descartar o dado seria pior:
129 clientes só aparecem em cancelamentos. Sem FK, com regra de aviso.

**10. O que é cardinalidade?**
Quantas ocorrências se relacionam: cliente 1:N pedidos; no FleetCam, dispositivo
tem no máximo 1 incidente **aberto** por tipo (garantido por UNIQUE parcial).

**11. Índice sempre melhora consulta?**
Não. No benchmark, índices cobrindo deram 2,2× numa consulta por cliente e 0× nas
agregações que leem a tabela inteira (Seq Scan continua sendo o plano mais barato),
custando +60 MB. Índice tem custo de espaço e de escrita.

**12. Como analisa performance de uma consulta?**
`EXPLAIN (ANALYZE, BUFFERS)`: tipo de scan, linhas estimadas × reais, buffers lidos.
Medir antes/depois, várias execuções, mediana, registrar ambiente.

**13. Índice parcial: quando?**
Quando a consulta só olha um subconjunto pequeno. Outbox do FleetCam:
`WHERE delivered_at IS NULL` — 16 KiB contra 152 KiB de um índice completo no laboratório.

**14. Como fazer migração sem downtime?**
Aditiva primeiro (expand), migrar consumidores, remover depois (contract).
Constraint com `NOT VALID` + `VALIDATE` para lock curto; `lock_timeout`;
`CREATE INDEX CONCURRENTLY`. Nunca editar migração já aplicada (checksum do Flyway).

**15. Dicionário de dados × glossário?**
Dicionário: técnico, por coluna (tipo, nulidade, FK, origem, regra). Glossário:
negócio, por termo (o que é "venda líquida" e como calcular). Aqui o dicionário é
gerado do catálogo e o teste valida que os termos citados existem no glossário.

**16. Como evitar que o dicionário fique desatualizado?**
Gerar do banco (não digitar) e falhar o CI se houver coluna física sem metadado
(`export_dictionary.py --check`).

**17. O que é engenharia reversa de banco?**
Reconstruir o modelo a partir do banco existente. Feito via catálogo
(`PRAGMA`/`pg_catalog`), nunca via regex no DDL; e com ferramenta CASE (`db2dbml`).

**18. Encontrou schema drift. O que faz?**
Não corrige à mão. Compara (diff classificado), descobre a origem, decide: mudança
desejada → CR + atualizar modelo versionado; indesejada → restaurar pelo DDL
versionado e abrir incidente.

**19. Como garante qualidade de dados?**
Regras por dimensão (completude, unicidade, integridade, validade, consistência,
acurácia), com severidade, rodando no CI sobre fixture e na carga real;
reconciliação de contagens e somas origem → destino.

**20. `customer_id` numérico é dado anônimo?**
Não. É pseudônimo: quem tem o cadastro reidentifica (LGPD art. 13 §4º). Por isso:
classificação pessoal, papel de analista sem acesso a transações, export com
HMAC e k-anonimato.

**21. Como seria a homologação de um modelo?**
CR com impacto (dados, API, ETL, lock, PII), scripts up/down testados em banco
descartável, checklist de revisão, CI verde, aprovação do dono do dado e do DBA.
Aqui a aprovação é simulada; os testes são reais.

**22. Multitenant: por que `tenant_id` na PK?**
Com FK composta `(tenant_id, device_id)`, o banco rejeita evento de um tenant
apontando para dispositivo de outro, mesmo com bug no código (verificado no
laboratório do FleetCam: `ForeignKeyViolation`).
