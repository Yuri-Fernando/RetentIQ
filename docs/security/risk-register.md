# Registro de riscos — dados e segurança (RetentIQ)

> Método: probabilidade (1–3) × impacto (1–3) = nível (1–9). Tratamento conforme
> ISO/IEC 27005 (mitigar, aceitar, transferir, evitar). Responsáveis são **papéis
> simulados**. Revisado em 2026-11-10.

| ID | Risco | P | I | Nível | Tratamento | Controle | Residual |
|---|---|---|---|---|---|---|---|
| R-01 | Dependência com vulnerabilidade conhecida | 3 | 2 | 6 | mitigar | pip-audit no CI; **pyarrow 22.0.0 → 23.0.1** (PYSEC-2026-113) | 2 |
| R-02 | Segredo/dado real commitado | 2 | 3 | 6 | mitigar | `.gitignore`, fixtures sintéticas, Trivy secret scan no CI | 2 |
| R-03 | Drift de schema não detectado | 2 | 2 | 4 | mitigar | `schema_diff.py` no CI, snapshot versionado | 1 |
| R-04 | Receita incorreta publicada (double counting, adulteração) | 2 | 3 | 6 | mitigar | 30 regras de qualidade, reconciliação origem→warehouse, exit 1 | 2 |
| R-05 | Reidentificação de clientes em export | 1 | 3 | 3 | mitigar | HMAC + k-anonimato + precisão reduzida | 2 |
| R-06 | Analista com acesso a transações individuais | 2 | 2 | 4 | mitigar | papéis PostgreSQL de menor privilégio (testados) | 1 |
| R-07 | Warehouse incompleto após falha no meio da carga | 2 | 2 | 4 | aceitar (temporário) | detecção por contagem/checks; correção planejada DT-04 | 4 |
| R-08 | Perda do histórico de auditoria no full refresh | 3 | 1 | 3 | aceitar | documentado; trilha persistente no backlog | 3 |
| R-09 | Chave HMAC vazada | 1 | 3 | 3 | mitigar | só via variável de ambiente; mínimo 16 bytes; rotação anual | 2 |
| R-10 | KPI da API divergente da view (lógica duplicada) | 2 | 2 | 4 | mitigar (planejado) | DT-05: migrar API para a view | 4 |
