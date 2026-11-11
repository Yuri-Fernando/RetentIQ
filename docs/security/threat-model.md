# Modelo de ameaças — plataforma de dados do RetentIQ (STRIDE)

> Escopo: caminho do dado `xlsx → ETL → warehouse (SQLite/PostgreSQL) → API → web`
> e os exports. Laboratório de portfólio: não há ambiente produtivo; ameaças são
> analisadas para orientar controles **verificáveis** no repositório.

## Ativos e fronteiras de confiança

| Ativo | Classificação | Onde vive |
|---|---|---|
| Dataset bruto (`online_retail_II.xlsx`) | PESSOAL_PSEUDONIMIZADO | disco local, fora do Git |
| Warehouse (`retentiq.db` / PostgreSQL) | PESSOAL_PSEUDONIMIZADO | disco local / container |
| Exports de KPIs | PESSOAL_PSEUDONIMIZADO (token) | arquivo gerado sob demanda |
| Chave HMAC de pseudonimização | segredo | variável de ambiente |
| Segredos da API (`JWT_SECRET`, senha demo) | segredo | `.env` (no `.gitignore`) |
| Código, DDL, metadados | interno/público | GitHub |

Fronteiras: (1) arquivo de terceiro → ETL; (2) ETL → banco; (3) banco → API;
(4) API → navegador; (5) repositório → CI.

## STRIDE

| Ameaça | Cenário concreto | Controle implementado | Verificação | Lacuna |
|---|---|---|---|---|
| **S**poofing | alguém se passa por usuário da API | JWT na API (já existia) | testes da API (fora deste escopo) | sem MFA (laboratório) |
| **T**ampering — origem | `.xlsx` trocado/corrompido antes da carga | SHA-256 do arquivo em `etl_load_audit.source_sha256` | `test_load_audit_records_provenance` | hash não é comparado com valor esperado automaticamente |
| **T**ampering — warehouse | edição manual de fatos (ex.: receita) | regras `revenue_igual_qtd_x_preco`, `reconciliacao.receita_total`, FK/CHECK; API e checks abrem o banco **somente leitura** | `test_detects_revenue_tampering`, `test_detects_fk_orphans_when_constraints_bypassed` | SQLite não tem controle de acesso próprio |
| **T**ampering — schema | coluna/constraint alterada fora do processo | `schema_diff.py` (exit 1) no CI | `test_drift_is_detected_and_classified` | detecção só quando o diff roda |
| **R**epudiation | não saber quando/de onde veio a carga | `etl_load_audit` (instante UTC, origem, hash, contagens) | `test_load_audit_records_provenance` | sem identidade do executor; recriada no full refresh |
| **I**nformation disclosure — repositório | dado real ou segredo commitado | `.gitignore` de dados/segredos; fixtures sintéticas; Trivy (segredos) e pip-audit no CI | job `security` | — |
| **I**nformation disclosure — consumo | analista vê transação individual | papel `retentiq_analyst` só lê a view agregada | `test_least_privilege_roles` | — |
| **I**nformation disclosure — export | reidentificação por ID/país | HMAC-SHA256 + k-anonimato de país + redução de precisão | `test_privacy.py` | outliers de receita (ver privacy-impact-notes) |
| **D**enial of service | carga trava/falha no meio e deixa warehouse incompleto | contagem pós-insert, `foreign_key_check`, exit 1 em check crítico | testes de ETL | carga não atômica (DT-04) |
| **E**levation of privilege | papel de carga cria/alterar objetos | `retentiq_engineer` sem DDL; `REVOKE ALL FROM PUBLIC` | `test_least_privilege_roles` | — |
| Supply chain | dependência com CVE | versões fixadas + pip-audit no CI (achado real corrigido: pyarrow) | job `security` | dependências Node não auditadas neste job |
