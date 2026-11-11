# Mapeamento de controles — ISO/IEC 27001:2022, NIST CSF 2.0, LGPD, GDPR

> **Análise de aderência técnica, não certificação nem parecer jurídico.** Liga
> cada controle implementado neste repositório à referência normativa que ele
> ajuda a atender. "Parcial" = o controle técnico existe, mas o requisito
> normativo exige processo/organização que um projeto de portfólio não tem.

| Controle no repositório | Evidência | ISO 27001:2022 (Anexo A) | NIST CSF 2.0 | LGPD | GDPR | Cobertura |
|---|---|---|---|---|---|---|
| Classificação de cada coluna, validada por teste | `metadata/columns.yaml`, `test_data_dictionary.py` | 5.12 Classificação · 5.13 Rotulagem | ID.AM-07 | art. 5º I (dado pessoal) | art. 4(1), 4(5) | implementado |
| Catálogo, dicionário, linhagem | `docs/data-governance/` | 5.9 Inventário de ativos | ID.AM-07, ID.AM-08 | art. 37 (registro das operações) | art. 30 | parcial |
| Menor privilégio por papel (PostgreSQL) | `roles_postgres.sql`, `test_least_privilege_roles` | 5.15 Controle de acesso · 8.3 Restrição de acesso · 5.3 Segregação de funções | PR.AA-05 | art. 46 | art. 32(1)(b) | implementado (laboratório) |
| Pseudonimização HMAC + k-anonimato em exports | `privacy.py`, `test_privacy.py` | 8.11 Mascaramento de dados | PR.DS-01 | art. 6º III (necessidade), art. 13 §4º | art. 25, 32(1)(a) | implementado |
| Minimização: só colunas necessárias; analista vê agregado | ETL, papéis | 5.34 Privacidade e proteção de PII | PR.DS-01 | art. 6º III | art. 5(1)(c) | implementado |
| Integridade: PK/FK/CHECK, 30 regras, reconciliação | `schema_sqlite.sql`, `checks.py` | 8.27 Arquitetura segura (princípios) | PR.DS-01, PR.DS-02 | art. 6º V (qualidade) | art. 5(1)(d) | implementado |
| Trilha de auditoria da carga | `etl_load_audit` | 8.15 Registro de eventos (logging) | DE.CM-09 | art. 37 | art. 30 | parcial (sem identidade, sem retenção longa) |
| Gestão de mudanças: CR, up/down testados, schema diff no CI | `change-control.md`, `migrations/`, CI | 8.32 Gestão de mudanças | PR.PS-01 | — | — | implementado |
| Gestão de vulnerabilidades técnicas | pip-audit + Trivy no CI; correção do pyarrow | 8.8 Vulnerabilidades técnicas | ID.RA-01, PR.PS-02 | art. 46 | art. 32 | implementado |
| Segredos fora do código | `.gitignore`, variáveis de ambiente, Trivy secret | 8.24 Uso de criptografia · 5.17 Informação de autenticação | PR.DS-01 | art. 46 | art. 32 | implementado |
| Desenvolvimento seguro e testes | 106 testes, lint SQL, CI | 8.25 Ciclo de desenvolvimento seguro · 8.29 Testes de segurança | PR.PS-06 | art. 46 §2º (privacy by design) | art. 25 | implementado |
| Dados de teste sintéticos | `governance/fixtures.py` | 8.33 Informação de teste | PR.DS-01 | art. 6º III | art. 25 | implementado |
| Resposta a incidentes | `incident-response.md`, ticket de exemplo | 5.24–5.28 Gestão de incidentes | RS.MA, RS.AN, RC.RP | art. 48 | art. 33, 34 | parcial (runbook; sem equipe) |
| Avaliação de impacto | `privacy-impact-notes.md` | 5.34 | GV.RM | art. 38 (RIPD) | art. 35 (DPIA) | parcial |
| Retenção | `retention-policy-example.md` | 5.33 Proteção de registros · 8.10 Exclusão de informação | PR.DS-01 | art. 15, 16 | art. 5(1)(e) | documental (sem expurgo automático) |
| Modelagem de ameaças e riscos | `threat-model.md`, `risk-register.md` | 5.7 Inteligência de ameaças (parcial) · 6.1 (cláusula) | ID.RA-03, ID.RA-05 | — | art. 32(2) | documentado |
