# Histórico & Versionamento — Projeto Mentoria (Terminar)

> Arquivo central de registro do projeto. Toda decisão, entrega e pendência relevante é
> registrada aqui, em ordem cronológica (mais recente no topo). Não é changelog de código —
> é o "diário" de construção do projeto, para retomar o trabalho a qualquer momento sem
> perder contexto.

## Como usar este arquivo

- Cada entrada tem data, autor (Claude ou Yuri) e status.
- Pendências que dependem do usuário (API keys, login, escolhas) ficam na seção
  **Pendências (aguardando você)** até serem resolvidas.
- Versionamento de artefatos gerados (notebooks, documentos) segue sufixo `_v2`, `_v3` etc,
  nunca sobrescrevendo — ver `docs/MENTORIA.md` e regra pessoal de versionamento de arquivos.

## Versionamento do produto (RetentIQ)

O produto em si segue versionamento semântico simples, marcado nas entradas do log abaixo:

| Versão | Data | Escopo |
|---|---|---|
| **v1.0.0** | 2026-08-19 | Escopo inicial: ETL → Data Warehouse → churn/forecast → API REST → dashboard → Docker/CI/E2E básico. |
| **v2.0.0** | 2026-08-19 | Módulo "Ações de Retenção" (Kanban + chat tempo real + notas estilo Notion), motor de recomendação, GraphQL, fila assíncrona (BullMQ), PWA offline, endpoint `/metrics` (Prometheus), busca/filtro no Kanban. |
| **v2.0.1** | 2026-08-20 | Retomada pós-falha de sessão: `npm install` das duas apps validado de ponta a ponta (fora do caminho sincronizado), 2 bugs reais de TypeScript corrigidos (`auth.ts`, `dashboard/page.tsx`), configuração de ESLint criada para `apps/api` e `apps/web` (não existia), teste unitário real adicionado (`csv.test.ts`), `.env`/ícones PWA gerados, causa raiz do bloqueio de `npm install` identificada e documentada. |
| **v2.0.2** | 2026-08-21 | `node_modules` das duas apps materializado **dentro** de `apps/api/` e `apps/web/` (pendência 1 da v2.0.1 resolvida) — `npm run build`/`lint`/`test`/`dev` validados rodando direto na pasta real do projeto. Mais 1 bug real corrigido (`DELETE` de card do Kanban quebrava com clientes que tinham comentário), cache do webpack do Next.js desabilitado (causava crash do build nesta pasta sincronizada), error handler JSON global adicionado na API. |

Nenhuma versão anterior é sobrescrita — o histórico completo de cada uma fica registrado
no log cronológico abaixo, incluindo o que foi decidido, o que ficou de fora e por quê.

---

## Pendências (aguardando você)

1. ~~`npm install` diretamente dentro de `apps/api/` e `apps/web/`~~ — **resolvido na
   v2.0.2**. `node_modules` das duas apps está materializado dentro do projeto,
   `npm run dev`/`build`/`lint`/`test` rodam direto daqui. Ver "Como este projeto lida
   com Google Drive" mais abaixo se precisar reinstalar do zero no futuro (ex.: depois
   de um `git clone` novo).
2. **`infra/docker/.env`** — copiar de `infra/docker/.env.example` se for rodar a
   stack completa via Docker Compose (Postgres/Redis/Prometheus/Grafana).
3. **Dataset Olist (opcional)** — se quiser trocar o UCI Online Retail II pelo
   dataset brasileiro Olist (mais rico, mais comum em portfólios de dados BR),
   é necessário criar uma conta Kaggle e gerar um token `kaggle.json` — não
   incluído por exigir credenciais pessoais suas.
4. ~~Métricas Prometheus reais~~ — **resolvido na v2.0.0** (`apps/api/src/lib/metrics.ts`,
   endpoint `GET /metrics`).
5. **Deploy em produção** — nenhum provedor foi escolhido/configurado
   (Vercel/Render/Fly.io etc.); fica a seu critério.
6. ~~`apps/api/.env` / ícones PWA~~ — **resolvido na v2.0.1**: `.env` gerado com segredos
   aleatórios para uso local/demo, `icon-192.png`/`icon-512.png` gerados.
7. **Provedor de e-mail real** para a fila de win-back (`apps/api/src/queue/winbackWorker.ts`
   hoje só simula, escrevendo num log local) — ex.: Resend, SendGrid.

---

## Como este projeto lida com Google Drive (leia antes de rodar `npm install` de novo)

Este projeto vive dentro de uma pasta sincronizada pelo Google Drive Desktop. O
`require`/`import` do Node.js precisa que `node_modules` exista fisicamente dentro de
`apps/api/` e `apps/web/` (não tem equivalente ao `site-packages` do Python) — e o
cliente do Drive não aguenta bem a criação rápida de milhares de arquivos pequenos que
um `npm install` gera (`TAR_ENTRY_ERROR`/`EINVAL`/"Acesso negado", às vezes num cache
de pasta que fica "fantasma" — existe mas não aparece, e bloqueia recriação por um
tempo). Isso já está resolvido para o estado atual do projeto (v2.0.2), mas se um dia
for preciso reinstalar do zero (`node_modules` corrompido, `git clone` novo, etc.), o
método que funciona de forma confiável é:

1. Instalar numa pasta local curta fora de qualquer sync, ex. `C:\tmp\<algo>` — copiar
   só o `package.json` pra lá e rodar `npm install` ali (sempre funciona sem fricção).
2. Copiar o `node_modules` resultante de volta pra dentro de `apps/api/`/`apps/web/`
   via `robocopy /E /R:3 /W:2 ... /MT:2` (retry moderado, não o default do robocopy).
3. Se alguma pasta específica der "Acesso negado" repetidamente: é cache local travado
   do cliente do Drive (confirmado — um nome de pasta nunca usado antes nesse local cria
   sem problema). Criar a pasta vazia via **PowerShell `New-Item -ItemType Directory`**
   (não `mkdir` do Git Bash), esperar ~20s antes de checar se sobreviveu, e então rodar
   o robocopy só daquele subdiretório.
4. Junction/symlink de diretório **não funciona** dentro da pasta do Drive (driver
   virtual não implementa reparse points — erro "Função incorreta"). A única rota que
   funciona é copiar os arquivos de verdade.

Regra permanente equivalente registrada em `~/.claude/rules/node-env.md` (config global
do Claude Code do usuário, fora deste repositório).

**Efeito colateral também resolvido:** o cache persistente do webpack em disco
(`.next/cache`) trava o `next build`/`next dev` pelo mesmo motivo — corrigido
desabilitando esse cache em `apps/web/next.config.js` (`config.cache = false`). Builds
ficam um pouco mais lentos (recompila do zero sempre), mas funcionam de forma confiável.

---

## Log cronológico

### 2026-08-21 — v2.0.2: `node_modules` materializado na pasta real, mais 2 bugs corrigidos

**Status:** Concluído — `npm run dev`/`build`/`lint`/`test` das duas apps rodam e foram
testados **direto na pasta real do projeto**, sem nenhuma cópia/mirror pendente.
**Autor:** Claude (Sonnet 5)

**Contexto:** na v2.0.1 eu tinha instalado as dependências num mirror fora do Drive
(`C:\Jarvis\build\...`) só pra validar que o código compilava, e documentei a pendência
de materializar `node_modules` dentro da pasta real como algo que dependia do usuário
pausar o sync do Drive. Yuri corrigiu minha abordagem em dois pontos importantes:

1. Eu tinha (por engano) colocado esse mirror dentro de `C:\Jarvis\repos\`, que é a
   pasta reservada para clones de repositórios de ferramentas do próprio ecossistema
   Jarvis — não um espaço genérico para projetos de terceiros. Corrigido: nada deste
   projeto vive em `C:\Jarvis` a partir de agora.
2. O projeto **precisa continuar** na pasta atual (`Projeto Mentoria (Terminar)`,
   sincronizada por Drive) — não é opção mover pra fora. A pergunta certa não era "onde
   deixar o projeto" e sim "como fazer o `npm install` funcionar apontando pra cá".

**Solução aplicada (ver seção "Como este projeto lida com Google Drive" acima para o
passo a passo reaproveitável):** instalar numa pasta local curta (`C:\tmp\...`, fora de
qualquer sync), depois copiar o `node_modules` resultante de volta pra dentro de
`apps/api/node_modules` e `apps/web/node_modules` via `robocopy`. A cópia da API travou
especificamente em 2 pastas (`eslint-scope`, `path-key`) com "Acesso negado" repetido —
isolado como cache local do cliente do Google Drive travado (confirmado: uma pasta com
nome nunca usado antes, no mesmo lugar, criava sem problema; essas duas, criadas e
apagadas várias vezes ao longo da sessão em tentativas anteriores, ficaram num estado
"fantasma" — o `Test-Path` do PowerShell dizia que não existiam, mas `mkdir` do Bash
dizia "File exists"). Resolvido criando as pastas vazias via PowerShell `New-Item` e
aguardando ~20s antes de popular o conteúdo via robocopy — sobreviveram na segunda
tentativa.

**Validação real, direto na pasta do projeto (não em mirror) depois da cópia:**
- `apps/api`: `npm run build` (tsc), `npm run lint` (eslint) e `npm test` (vitest, 3
  testes) — todos limpos. Servidor rodando de verdade (`node dist/server.js`), login
  retornou JWT válido via `Invoke-RestMethod`.
- `apps/web`: `npm run build` (next build) — **quebrou na primeira tentativa** com
  `uncaughtException [Error: EINVAL: invalid argument, write]`, crashando o processo
  inteiro. Causa: o cache persistente do webpack em disco (`.next/cache`) sofre do
  mesmo problema de escrita em massa que `node_modules` sofria. Corrigido desabilitando
  esse cache em `next.config.js` (`config.cache = false`) — depois disso, build limpo
  e `npm run lint` limpo. `npm run dev` testado rodando de verdade, página respondendo
  `200` em `http://localhost:3000`.

**2 bugs reais adicionais encontrados e corrigidos, testando o Kanban de retenção de
ponta a ponta (criar card → comentar → funil → win-back → deletar):**
1. `DELETE /api/retention/actions/:id` quebrava com `SqliteError: FOREIGN KEY
   constraint failed` sempre que o card tinha algum comentário — e ainda vazava uma
   página HTML com stack trace completo (inclusive caminho absoluto em disco) em vez
   de um erro JSON. A intenção do código já estava certa e documentada em comentário
   ("não apaga em cascata, mantém comentários por histórico"), mas o schema declarava
   `action_id INTEGER NOT NULL REFERENCES retention_actions(id)` — uma constraint de
   verdade, que bloqueia exatamente esse caso. Corrigido removendo a `REFERENCES` do
   schema (`apps/api/src/lib/appDb.ts`) — `action_id` continua sendo o vínculo lógico
   com o card, só não é mais uma constraint que impede o comportamento documentado.
2. Nenhum error handler global no Express — qualquer exceção não tratada (como o bug
   acima) vazava a página HTML default do Express, com stack trace e caminho absoluto
   do disco. Adicionado um error handler JSON global em `server.ts` (`{"error": "Erro
   interno do servidor."}` + log no console), depois de todas as rotas.

**Outras correções pequenas:**
- `next-env.d.ts` (gerado automaticamente pelo Next.js) adicionado ao `.gitignore` raiz
  — não existia essa entrada.
- `apps/api/src/lib/csv.test.ts`: o `afterAll` só apagava o arquivo de fixture, não a
  pasta `__fixtures__` criada pelo `beforeAll` — sobrava uma pasta vazia a cada
  `npm test`. Corrigido para remover a pasta inteira.

**Regra permanente adicionada** (fora deste repositório, config global do Claude Code
do usuário): `~/.claude/rules/node-env.md` — documenta o método "instalar fora, copiar
pra dentro" para qualquer projeto futuro que viva numa pasta sincronizada por Google
Drive/OneDrive, e deixa explícito que `C:\Jarvis\repos\` não é o lugar pra isso.

---

### 2026-08-20 — v2.0.1: retomada pós-crash, `npm install` validado, bugs reais corrigidos

**Status:** Concluído — código validado de ponta a ponta localmente; único item que
depende do seu ambiente é materializar `node_modules` dentro da pasta do projeto (ver
pendência 1 acima).
**Autor:** Claude (Sonnet 5)

**Contexto:** a sessão anterior travou no meio de uma tentativa de `npm install` em
`apps/api` (log `_npm_install_log.txt` termina abruptamente em centenas de
`TAR_ENTRY_ERROR`, sem linha de conclusão) e `apps/web/node_modules` ficou com 0
pacotes. Retomei do zero: analisei todo o histórico (`docs/HISTORICO.md`,
`docs/MENTORIA.md`, `README.md`), conferi o estado real de cada pasta (warehouse
já rodado com sucesso, `apps/api` parcialmente instalado e quebrado, `apps/web` nunca
instalado) e terminei o que faltava.

**Causa raiz do `npm install` travando — identificada nesta sessão:** não é
antivírus (como suspeitado antes), é o **próprio cliente do Google Drive Desktop**
negando `EINVAL`/"Acesso negado" na criação de subpastas específicas dentro de
`node_modules`, de forma determinística e repetível (mesmas pastas falhando em
tentativas sucessivas, robocopy incluído). Confirmado isolando o teste: `npm install`
rodado num diretório **fora** do Drive (`C:\Jarvis\build\...`) completa normalmente e
sem erros (342 pacotes na API, 157 no web). Tentativas de copiar o resultado de volta
para dentro da pasta sincronizada (via `cp`, `robocopy`, junction NTFS) todas
esbarraram na mesma trava do Drive — junction nem chega a ser criável no volume `G:`
("Função incorreta": o driver virtual do Drive não implementa reparse points).
**Não é um bug do projeto** — é uma limitação de ambiente do próprio Google Drive
Desktop com este caminho específico (espaços, parênteses, acentuação + muitos arquivos
pequenos). Registrado como pendência 1 com a solução recomendada (pausar sync do Drive
antes de instalar, ou desenvolver fora de pasta sincronizada).

**Validação real feita (não apenas "deveria funcionar"):**
- `npm install` completo e limpo para `apps/api` (342 pacotes) e `apps/web`
  (157 pacotes) — rodado fora do Drive para isolar a causa.
- `npm run build` (tsc) da API: **encontrou e corrigiu um bug real** — `jwt.sign()` em
  `src/routes/auth.ts` não compilava com os tipos do `jsonwebtoken` v9
  (`expiresIn` como `string` genérica não bate com o tipo `StringValue`). Corrigido com
  cast explícito para `jwt.SignOptions["expiresIn"]`.
- `npm run build` (`next build`) do web: **encontrou e corrigiu um segundo bug real** —
  `useSWR(path, fetcher)` sem generic explícito inferia `overview`/`timeseries`/etc.
  como `{}`, quebrando o build de produção (`Property 'total_customers' does not exist
  on type '{}'`). Corrigido adicionando interfaces (`OverviewMetrics`, `RevenuePoint`,
  `ChurnSummary`, `ForecastPoint`, `TopProduct`) e generics explícitos em cada
  `useSWR<T>(...)` em `app/dashboard/page.tsx`, com os nomes de campo conferidos contra
  o código real da API (`metricsService.ts`, `churn.ts`) — nenhum campo inventado.
- Também corrigido o warning de build `Unsupported metadata themeColor` (Next 14.2+
  moveu `themeColor` de `metadata` para `viewport`) em `app/layout.tsx`.
- **`npm run lint` não tinha configuração em nenhuma das duas apps** (script existia no
  `package.json`, mas sem `.eslintrc`, o que quebraria silenciosamente o CI — o workflow
  usa `--if-present`, e o script está presente). Criado `.eslintrc.json` em `apps/api`
  (com `@typescript-eslint/parser` + `@typescript-eslint/eslint-plugin`, adicionados como
  devDependency) e em `apps/web` (`next/core-web-vitals`, com `eslint` +
  `eslint-config-next` adicionados como devDependency, que também faltavam). Lint limpo
  nas duas apps depois da correção.
- **`npm test` na API não tinha nenhum teste** (`vitest run` saía com exit 1 por "No test
  files found" — quebraria o CI). Adicionado `src/lib/csv.test.ts`, teste real (não
  placeholder) do parser de CSV usado pelas rotas de churn/forecast/recomendação,
  incluindo um teste de regressão que fixa o contrato do bug de tipo já documentado na
  v2.0.0 (campo `score` chega como string, precisa de `Number()` no consumidor).
- **Servidor da API testado rodando de verdade**: build compilado, subiu em
  `localhost:4000`, login retornou um JWT válido, endpoint `/metrics` (Prometheus)
  respondeu. Rotas que dependem do Data Warehouse (`/api/metrics/overview`,
  `/api/churn/summary`) foram exercitadas com o `retentiq.db`/CSVs reais linkados
  (via junction local, fora do Drive) e retornaram dados corretos — confirma que o
  contrato entre API e o pipeline Python (`data-platform/`) está íntegro.
- **Ícones PWA gerados**: `apps/web/public/icon-192.png` e `icon-512.png` (Pillow,
  fundo `#0a0a0a` igual ao `theme_color` do manifest, "R" em destaque), fechando a
  última pendência de configuração do PWA.
- **`.env` gerados** para uso local/demo: `apps/api/.env` (com `JWT_SECRET` via
  `openssl rand -hex 32` e `DEMO_ADMIN_PASSWORD` aleatória forte) e
  `apps/web/.env.local`. Documentado claramente que são valores de demo/portfólio, a
  trocar antes de qualquer deploy público — mesmo aviso que já estava no `.env.example`.

**O que ficou como pendência real (não resolvível por mim sozinho):**
- Materializar `node_modules` **dentro** de `apps/api/` e `apps/web/` nesta pasta
  específica — depende de uma ação sua no ambiente (pausar sync do Drive) que eu não
  posso fazer. O código em si está validado como correto e buildável.

---

### 2026-08-19 — v2.0.0: módulo de Ações de Retenção + recomendação + GraphQL + fila + PWA

**Status:** Concluído (código completo; falta só `npm install` local — ver pendência)
**Autor:** Claude (Sonnet 5), com 2 subagentes em paralelo (backend e frontend)

**Contexto:** depois de entregar a v1.0.0, Yuri pediu para incorporar mais capacidades
específicas dos PDFs de origem que tinham ficado de fora conscientemente: chat em tempo
real, Kanban, editor estilo Notion, PWA offline, GraphQL, fila (RabbitMQ/BullMQ), sistema
de recomendação, análise de vagas e funil de recrutamento — com o aval explícito de fazer
isso de forma costurada (não em colcha de retalhos), decisão já registrada na conversa.

**Decisão de reformulação (não force-fit):**
- **Funil de recrutamento** (idea dados #7) → reformulado como **funil de retenção**
  (Alto risco identificado → Sem ação → Em andamento → Resolvido). Mesmo conceito de
  funil por estágio, no domínio certo do produto.
- **Análise de vagas de emprego** (idea dados #3) → deliberadamente **fora do escopo**.
  Não existe ponte honesta com e-commerce/retenção de clientes; forçar essa peça seria
  exatamente o anti-padrão que os PDFs de origem alertam ("não adicione ferramenta sem
  finalidade que você consiga explicar"). Se for necessária no futuro, é um mini-projeto
  à parte, não uma peça do RetentIQ.

**Módulos entregues:**
1. **Kanban de Ações de Retenção** (`apps/web/app/dashboard/retention`, `apps/api/src/routes/retention.ts`)
   — cards por cliente em risco, 3 colunas, drag-and-drop HTML5 nativo (sem lib nova).
2. **Editor estilo Notion** (`apps/web/components/NotionEditor.tsx`) — notas em blocos
   (texto/título/checklist), componente próprio, sem lib externa (tiptap/slate).
3. **Chat em tempo real por card** (`apps/web/components/RetentionCardChat.tsx`,
   Socket.io com salas `retention-action-${id}`, extraído para `apps/api/src/lib/socket.ts`).
4. **Motor de recomendação** (`data-platform/ml/recommendation.py`) — coocorrência de
   produtos por nota fiscal (association rules simplificado), gera oferta de win-back por
   cliente. Rodado com sucesso: 18.742 pares produto→produto, 17.603 recomendações para
   5.878 clientes.
5. **GraphQL** (`apps/api/src/graphql/schema.ts`, `graphql-yoga`) — alternativa de leitura
   à API REST (`overview`, `revenueByCountry`, `churnSummary`), montado em `/graphql`,
   protegido por JWT.
6. **Fila assíncrona** (`apps/api/src/queue/{winbackQueue,winbackWorker}.ts`, BullMQ+Redis)
   — envio de e-mail de win-back enfileirado; worker simula o envio em log local
   (`apps/api/data/winback_emails.log` — **PENDENTE**: plugar provedor real, ex. Resend/SendGrid).
7. **PWA offline** (`apps/web/public/manifest.json` + `sw.js`) — cache-first manual das
   rotas principais, registrado via `next/script`; **PENDENTE**: gerar os ícones físicos
   `icon-192.png`/`icon-512.png` referenciados no manifest (só configuração por enquanto).
8. **Endpoint `/metrics`** (`apps/api/src/lib/metrics.ts`, `prom-client`) — fecha a
   pendência da v1.0.0 (o `prometheus.yml` já apontava pra lá desde o início).
9. **Busca/filtro no Kanban** — client-side, sem Algolia/ElasticSearch (não haveria
   volume de dados real que justificasse isso aqui).

**Como foi construído:** backend e frontend foram implementados por dois subagentes em
paralelo (cada um com instruções explícitas de não tocar nos arquivos do outro e assumir
o contrato de API combinado antecipadamente). Isso é mais rápido, mas cria risco real de
inconsistência entre as duas pontas — e esse risco se confirmou:

**Bugs de integração encontrados e corrigidos após a junção dos dois agentes:**
1. Backend armazenava/devolvia `notes_json` como **string** JSON crua; frontend assumia
   que já vinha parseado como `Block[]`. Corrigido centralizando o parse no backend
   (`serializeAction()` em `retention.ts`) — fonte única da verdade, em vez de depender de
   cada tela do frontend lembrar de fazer `JSON.parse`.
2. Formulário "+ Nova ação" enviava `customer_id` como **string** (input HTML), mas o
   schema zod do backend exige `z.number().int()` — o `POST` retornaria 400. Corrigido
   convertendo com `Number(newCustomerId)` antes do fetch.
3. Tipos TypeScript do frontend (`RetentionAction.id`, `customer_id`, `Comment.id`,
   `action_id`) estavam como `string`; o SQLite/better-sqlite3 devolve `number`. Corrigido
   nos três arquivos (`RetentionCardDetail.tsx`, `RetentionCardChat.tsx`, `retention/page.tsx`).
4. Formulário de novo card tinha `<label>` sem `htmlFor`/`id` associando ao `<input>`
   (falha de acessibilidade real, não só de teste) — corrigido, e é o que permite o novo
   teste E2E usar `getByLabel`.
5. O worker de win-back (`winbackWorker.ts`) lia `p.description`/`p.stock_code` das
   recomendações, mas as colunas reais do CSV (`data-platform/ml/recommendation.py`) são
   `recommended_description`/`recommended_stock_code` — o log de e-mail simulado sairia
   sempre com "undefined". Corrigido, e o tipo `WinbackJobData.recommendedProducts` (antes
   `Record<string,string>[]` genérico) virou uma interface nomeada (`WinbackRecommendation`)
   pra esse tipo de erro de nome de campo aparecer em tempo de compilação da próxima vez.
6. `score` das recomendações vinha do CSV como **string** (todo `readCsv` genérico devolve
   string), mas o frontend chama `r.score.toFixed(2)` esperando `number` — quebraria em
   runtime. Corrigido convertendo no backend (`Number(r.score)`), mesmo princípio do item 1:
   uma conversão de tipo centralizada, não espalhada pelos consumidores.

**Isso é exatamente o motivo de o pipeline de qualidade de dados e os testes E2E
existirem no projeto** — mesma lição já registrada na v1.0.0 com o bug do `dim_product`:
paralelismo (seja de scripts, seja de agentes) ganha velocidade e perde consistência
automática; validação explícita é o que fecha essa lacuna.

**Outras ações:**
- `infra/docker/docker-compose.yml`: novo serviço `worker` (processa a fila BullMQ) e
  volume nomeado `retentiq_api_data` para persistir `apps/api/data/` (Kanban + comentários)
  entre restarts do container.
- Novo teste E2E `tests/e2e/retention-kanban.spec.ts` (criação de card + busca).

**Pendências (aguardando você) — atualizadas:**
- `npm install` em `apps/api` e `apps/web` continua bloqueado neste ambiente por
  `TAR_ENTRY_ERROR`/`EBADF` (ver pendência já registrada na v1.0.0) — agora com mais
  dependências novas (`bullmq`, `ioredis`, `graphql`, `graphql-yoga`, `prom-client`) que
  também precisam ser baixadas. Nenhuma delas foi testada de fato rodando neste ambiente.
- Ícones PWA físicos (`apps/web/public/icon-192.png`, `icon-512.png`) — só configuração,
  faltam os arquivos de imagem em si.
- Provedor real de e-mail para a fila de win-back (Resend/SendGrid ou similar).

---

### 2026-08-19 — Projeto RetentIQ: scaffold completo (v1.0.0)

**Status:** Concluído (scaffold funcional; pendências acima documentadas)
**Autor:** Claude (Sonnet 5)

**Síntese das duas listas de ideias:** ver raciocínio completo em `docs/MENTORIA.md`.
Resumo: o repertório dev (30 ideias — frontend/backend/full stack/DevOps/QA) e o
repertório de dados (20 ideias — BI/SQL/ETL/ML, por nível de senioridade) convergem
naturalmente em um domínio comum de e-commerce/receita/clientes. Em vez de escolher
uma ideia de cada lista, o projeto funde as duas em um único produto de dados
ponta a ponta.

**Título e escopo definidos:** **RetentIQ** — plataforma full-stack de inteligência
de receita e retenção de clientes para e-commerce.

**Dataset escolhido:** UCI "Online Retail II" (real, público, sem necessidade de
login/API key) — https://archive.ics.uci.edu/dataset/502/online+retail+ii.
Baixado e extraído em `data-platform/datasets/raw/online_retail_II.xlsx`
(~1.07M linhas brutas, 2009-2011, varejista online do Reino Unido).

**Ações realizadas:**
1. Extração dos 2 PDFs de origem via PyMuPDF (ver nota abaixo sobre o Docling)
   e leitura analítica completa de ambos.
2. Download e extração do dataset UCI Online Retail II.
3. Pipeline ETL (`data-platform/ingestion/extract_transform_load.py`): limpeza,
   remoção de duplicidade/nulos/cancelamentos inválidos, modelagem em esquema
   estrela (dim_customer, dim_product, dim_country, dim_date, fact_sales,
   fact_sales_cancelled), carga em Data Warehouse SQLite
   (`data-platform/warehouse/retentiq.db`) + parquet de apoio.
4. Schema Postgres equivalente (`data-platform/warehouse/schema_postgres.sql`)
   para quando a stack rodar via Docker Compose com Postgres real.
5. Módulo de qualidade de dados (`data-platform/quality/checks.py`): 7 checagens
   (schema, nulos, integridade referencial, duplicidade de PK, volume mínimo),
   com relatório JSON e exit code não-zero em caso de falha — plugável no CI.
6. Modelo de churn (`data-platform/ml/churn_model.py`): RFM + Random Forest,
   rotulagem sem vazamento de dados (snapshot_date + janela futura de holdout),
   métricas completas (precision/recall/F1/ROC-AUC/matriz de confusão).
7. Previsão de demanda (`data-platform/ml/demand_forecast.py`): Holt-Winters
   com sazonalidade semanal, holdout de teste, métricas MAE/RMSE/MAPE.
8. API (`apps/api`, Node.js + TypeScript + Express): auth JWT, rate limiting,
   CORS, Helmet, rotas de métricas/churn/forecast lendo do warehouse, WebSocket
   (Socket.io) emitindo alertas de churn em tempo real.
9. Web (`apps/web`, Next.js 14 + Tailwind + Recharts): tela de login e dashboard
   com KPIs, gráfico de receita, painel de risco de churn, gráfico de previsão
   de demanda e ranking de produtos; escuta o WebSocket para alertas ao vivo.
10. Infraestrutura (`infra/docker/docker-compose.yml`): Postgres, Redis, API,
    Web, Prometheus, Grafana — sobe a stack completa com um comando.
11. CI (`.github/workflows/ci.yml`): valida data-platform (checks de qualidade),
    api e web (lint/build/test) a cada push/PR.
12. Testes E2E (`tests/e2e/login-e-dashboard.spec.ts`, Playwright): fluxo crítico
    de login e carregamento do dashboard.
13. `docs/MENTORIA.md`: racional completo de cada decisão técnica, como
    defender o projeto em entrevista, e próximos passos priorizados.

**Resultados reais do pipeline (rodado de ponta a ponta neste ambiente):**
- Data Warehouse: 793.609 linhas em `fact_sales`, 5.878 clientes, 4.631 produtos,
  41 países, 18.688 linhas de cancelamento em `fact_sales_cancelled`.
- Qualidade de dados: **7/7 checagens passaram** (`quality_report.json`).
- Modelo de churn: precision=0,782 / recall=0,791 / F1=0,787 / ROC-AUC=0,813
  (snapshot em 2011-09-10, janela de avaliação de 90 dias, 5.281 clientes
  analisados, taxa de churn observada de 56,6%).
- Previsão de demanda: MAE=13.758 / RMSE=28.347 / MAPE=24,1% (série de 739 dias,
  holdout de 30 dias, Holt-Winters com sazonalidade semanal).

**Problema de ambiente identificado (não é bug do código):** `npm install` em
`apps/api` e `apps/web` falha de forma intermitente com `TAR_ENTRY_ERROR` /
`EBADF` durante a extração de pacotes — sintoma clássico de antivírus ou
sincronização de nuvem (OneDrive/Drive) travando arquivos em um caminho longo
com acentos/parênteses. Tentado via Git Bash e via PowerShell nativo, ambos
com o mesmo sintoma. Instruções para o usuário rodar localmente (com dica de
pausar antivírus/sincronização durante a instalação) foram passadas no chat;
o código em si (`package.json`, `tsconfig.json`, rotas, componentes) está
completo e não depende dessa instalação para estar correto — só falta baixar
os pacotes de fato antes de `npm run dev` funcionar.

**Bug real encontrado e corrigido durante a construção** (registrado aqui como
parte do histórico, não escondido): a primeira carga do warehouse reportou
"4.631 linhas" para `dim_product` no log, mas a tabela ficou com 0 linhas no
banco — falha silenciosa do `pandas.to_sql` sem exceção. Corrigido adicionando
verificação pós-insert (`SELECT COUNT(*)` comparado ao tamanho do DataFrame,
com erro explícito em caso de divergência) em
`data-platform/ingestion/extract_transform_load.py`. Isso é também o exemplo
usado em `docs/MENTORIA.md` para justificar por que o pipeline de qualidade
existe.

**Nota técnica sobre o Docling:** a intenção original era usar o Docling (como
pedido) para extrair o texto dos PDFs. O pipeline padrão do Docling carrega
modelos de deep learning (layout/OCR) via torch+transformers, e o pagefile do
Windows deste ambiente é pequeno demais para isso (`OSError 1455 /
ERROR_COMMITMENT_LIMIT`), mesmo desligando OCR e table-structure — o modelo de
layout é obrigatório no `StandardPdfPipeline`. Como os PDFs são puramente
textuais (não escaneados), a extração com PyMuPDF (`fitz`) é equivalente em
conteúdo e não depende de nenhum modelo de ML. O notebook
`notebooks/01_extracao_docling.ipynb` continua no repositório (ele documenta a
tentativa original); o script efetivamente usado está em
`notebooks/_debug_extracao.py`.

### 2026-08-19 — Kickoff do projeto

**Status:** Em andamento
**Autor:** Claude (Sonnet 5)

**Contexto:** Yuri pediu para unificar o conteúdo de dois PDFs de repertório —
`materiais/30 IDEIAS DE PROJETOS PARA PORTFÓLIO DEV.pdf` e
`materiais/DADOS - 20 IDEIAS DE PROJETOS PARA ÁREA DE DADOS.pdf` — em um único projeto
"top tier" de portfólio que combine as capacidades de ambos (dev full-stack + dados/analytics),
com dataset real se necessário, documento de mentoria explicando o raciocínio e as decisões,
e este arquivo central de histórico.

**Ações realizadas:**
1. Localizados os 2 PDFs em `materiais/`.
2. Confirmado ambiente: Docling 2.107.0 e Jupyter instalados no Python 3.10 canônico
   (`C:\Users\Yuri_\AppData\Local\Programs\Python\Python310\python.exe`).
3. Criado `notebooks/01_extracao_docling.ipynb` — extrai o texto completo dos 2 PDFs via
   Docling, exporta para Markdown em `extracted/`, e gera `extracted/resumo_extracao.json`
   com estatísticas (páginas, palavras, tempo de conversão).
4. Notebook executado em background via `jupyter nbconvert --execute --inplace`
   (log em `extracted/execucao_log.txt`).

**Próximos passos (após extração concluída):**
- Ler o Markdown extraído dos 2 PDFs.
- Analisar profundamente as 30 ideias de projetos dev + 20 ideias de projetos de dados.
- Sintetizar um projeto único que combine capacidades de ambos os repertórios.
- Sugerir título e escopo do projeto.
- Escolher e baixar dataset real, se aplicável.
- Fazer o scaffold do projeto (estrutura de pastas, código inicial, README).
- Deixar pendências que dependem do usuário (API keys, contas, login) claramente marcadas
  e prontas para plugar — nunca inventar credenciais ou fingir que algo está configurado.
- Escrever `docs/MENTORIA.md` — documento de mentoria explicando decisões técnicas,
  trade-offs e como apresentar o projeto em entrevistas/portfólio.

---
