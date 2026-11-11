# Notas de impacto à privacidade — RetentIQ

> Análise de aderência **técnica**, no formato de um RIPD/DPIA simplificado
> (LGPD art. 38; GDPR art. 35). **Não** substitui avaliação jurídica e **não**
> declara conformidade. Projeto de portfólio sobre dataset público de terceiro.

## 1. Tratamento

| Item | Registro |
|---|---|
| Dado | Online Retail II (UCI): `Customer ID` pseudônimo + país + transações |
| Finalidade declarada | análise de retenção, receita e churn para fins de estudo/portfólio |
| Base de dados no Git | **não** — dataset, warehouse e parquet estão no `.gitignore` |
| Testes/CI | fixture sintética (`customer_id` 90001+), nenhum dado real |
| Titulares | clientes de um varejista do Reino Unido (2009–2011), desconhecidos do autor |

## 2. Princípios (LGPD art. 6º) × controles técnicos

| Princípio | Controle implementado | Onde | Status |
|---|---|---|---|
| Finalidade | finalidade registrada neste documento e no catálogo | docs | documentado |
| Necessidade / minimização | ETL carrega só as 8 colunas da origem; warehouse não tem nome/e-mail/endereço; papel analista só lê KPI agregado | ETL, `roles_postgres.sql` | **implementado e testado** (`test_least_privilege_roles`) |
| Qualidade dos dados | 30 regras de qualidade, reconciliação origem→warehouse | `quality/checks.py` | **implementado e testado** |
| Transparência | catálogo, dicionário, linhagem versionados | docs | documentado |
| Segurança | menor privilégio por papel, pseudonimização HMAC em export, chave fora do repositório, consultas read-only nos checks, segredos fora do Git | `privacy.py`, `roles_postgres.sql`, `.gitignore` | **implementado e testado** (`test_privacy.py`) |
| Prevenção | regras de CI barram coluna nova sem classificação | `test_data_dictionary.py` | **implementado** |
| Responsabilização | trilha `etl_load_audit` (hash SHA-256 da origem, contagens) | ETL | **implementado** |

## 3. Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação | Residual |
|---|---|---|---|---|
| Reidentificação via `customer_id` + cadastro do varejista | baixa (portfólio não tem o cadastro) | médio | export usa token HMAC com chave secreta | baixo |
| Singularização por país raro | média | médio | export generaliza países com < k clientes (padrão k=10) para `OUTROS` | baixo |
| Singularização por receita extrema única | média | baixo | export arredonda e reduz datas a mês; **não** resolve outliers de receita | **médio — limitação aceita** |
| Vazamento do warehouse local | baixa | médio | arquivo fora do Git; API abre o banco em modo read-only | baixo |
| Chave de pseudonimização vazada | baixa | alto (tokens reversíveis por força bruta no domínio pequeno de IDs) | chave ≥ 16 bytes, só via variável de ambiente; rotação invalida tokens antigos | baixo |

## 4. Limites deste trabalho

- k-anonimato só sobre país; não houve análise de l-diversidade nem privacidade
  diferencial.
- Pseudonimização ≠ anonimização: o export continua sendo dado pessoal.
- Controles de banco (papéis) foram testados em PostgreSQL de laboratório; não há
  ambiente produtivo.
- Direitos do titular (acesso, eliminação) não se aplicam operacionalmente: não há
  canal com titulares de um dataset histórico público.
