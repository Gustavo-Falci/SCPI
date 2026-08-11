# Padrões de Código

Convenções estabelecidas e armadilhas que já morderam este projeto. Cada item tem custo
real de incidente atrás.

## SQL / psycopg2

- **`%` literal quebra o `execute`, inclusive dentro de comentário.** psycopg2 varre a query
  inteira procurando placeholders `%s`; um `100%` num comentário `--` estoura
  `IndexError: tuple index out of range` em runtime. Escapar como `%%` ou reescrever.
  Incidente 2026-07-24: derrubou o PDF de frequência em prod com 500.
  **Mock cursor não pega isso** — `MagicMock.execute` não parseia `%`. Mesma cegueira vale
  para mismatch entre nº de `%s` e params. Guarda: `test_repo_sql_nao_tem_percent_literal_nao_escapado`.
- **Cast de UUID em `ANY`**: `ANY(%s)` com lista de `str` vira `text[]` e dá
  `operator does not exist: uuid = text`. Sempre `ANY(%s::uuid[])`. (`= %s` com string única
  funciona, porque o literal vira `unknown` e coage.)
- **SQL 100% parametrizado** — auditado, sem SQLi. Manter.
- **Coluna de data nova nasce `TIMESTAMPTZ`.** Numa coluna `timestamp` sem fuso, `NOW()`
  grava hora de parede local (UTC−3) e datetime do Python grava UTC; misturar as duas fontes
  deixa os valores 3h deslocados entre si. Foi bug real: `purgar_tokens_expirados` apagava
  refresh token 3h adiantado.
- `core/tempo.py::agora_utc()` é a fonte única de "agora". Hoje devolve **aware**; guarda
  textual em `test_tempo_utc.py` proíbe `datetime.utcnow()`.

## FastAPI

- **Bytes já em memória → `Response(content=...)`, nunca `StreamingResponse(io.BytesIO(...))`.**
  Incidente 2026-05-21: o ZIP do export LGPD chegava truncado em ~337 bytes atrás de
  gunicorn+nginx, com 200 no log. `io.BytesIO` como iterador itera line-by-line (até `\n`) e
  não serve para binário denso. Passar `Content-Length` explícito. `StreamingResponse` só
  quando o gerador for realmente lazy.
- **Trabalho bloqueante dentro de `async def` → `run_in_threadpool`.** pbkdf2 a 600k custa
  ~300 ms por hash; um laço que hasheia por linha trava o event loop e, com
  `gunicorn --timeout 30`, o worker morre com o import CSV parcialmente commitado (commit por
  linha, e-mails já enviados, sem rollback). Dependency `def` síncrona já roda em threadpool
  por conta do FastAPI — não precisa embrulhar.
- Erros usam o enum `ErrorCode` de `BackEnd/core/errors.py` (27 códigos, mensagens PT-BR) +
  helpers `http_error` / `not_found` / `forbidden`.
- IDOR responde **404, não 403**, para não permitir enumeração (`require_self_or_admin`).

## Onde uma regra deve morar

- **Constante usada por duas camadas vira módulo próprio em `core/`.** `LIMITE_FREQUENCIA` e
  `ANGULOS_VALIDOS` estão em `core/regras.py` porque o service rotula Regular/Risco e o PDF
  pinta a linha com o mesmo número — duas cópias divergiriam sem ninguém perceber. Mesma
  lógica valeu para `core/csv_utils.py` (aluno + professor) e `core/tempo.py`.
- **Regra testável de mesa vira função pura, sem cliente de IO.** `inventario_biometrico`
  recebe as três listas prontas e não conhece boto3 nem psycopg2; `ConfirmadorBurst` e
  `RegistroTracker` não conhecem câmera, rede nem env; `verificar_receipts` separa `processar`
  (pura) de `main` (I/O). É o molde padrão do projeto para lógica não trivial.
- **Documento que sai do sistema passa por `core/mascaras.py`.** O PDF circula por e-mail e
  WhatsApp, fora do controle do SCPI: CPF não vai impresso, RA institucional vai.

## Testes

- **Todo teste-guarda textual precisa isentar o arquivo que documenta o padrão proibido.**
  A busca é textual e não distingue código de comentário. Aconteceu três vezes em
  2026-08-03. Manter uma constante `_ISENTOS` no topo do teste com o motivo escrito, e
  incluir nela o módulo canônico, os arquivos de config e o próprio teste. Varredura sobre
  `portal/` também ignora `node_modules/` e artefatos de build.
  Guardas textuais existentes: CSP inline handlers, `utcnow()`, contraste WCAG, build do
  Tailwind, `%` literal em SQL.
- Suíte de repositório usa mock cursor — bug de SQL real passa verde. Verificação contra
  banco tem três caminhos, nesta ordem: (1) teste gated `SCPI_RUN_DB_TESTS=1` que roda no CI;
  (2) SQL avulso entregue ao Gustavo para colar no DBeaver; (3) pular.
- **NUNCA setar `SCPI_RUN_DB_TESTS=1` na máquina local**: o `.env` de dev aponta `DB_HOST`
  de **produção** e as fixtures `pg`/`pg_academico` dão `TRUNCATE`.
- Fixture autouse `_limiter_em_memoria` troca o storage do limiter global por `MemoryStorage`;
  sem ela, endpoint com `@limiter.limit` pendura um connect-timeout por request.
- Um teste que "demonstra o erro" vale mais que um que só confirma o acerto — ex.:
  `test_migration_timestamptz_restante.py` aplica a cláusula errada e **exige** o
  deslocamento, para pegar quem tentar uniformizar as duas migrações.

## Frontend — Portal

- **Nada importa `main.js`.** O `index.html` carrega `js/main.js?v=N`; um import de
  `../main.js` sem a query é URL diferente para o browser e instancia o módulo **duas vezes**
  (dois `DOMContentLoaded`, todo listener em dobro). Helper compartilhado vira módulo próprio
  (foi assim que nasceu `portal/js/modal.js`).
- **Mexeu em classe do portal → `npm run build` em `portal/` e commita o CSS junto.** O CSS
  do Tailwind é versionado; o job `portal css (build atualizado)` recompila e falha se
  divergir.
- Classe montada por variável só funciona se o valor aparecer como **string literal** na
  fonte. `'text-' + cor` some do CSS sem aviso — proibido por teste.
- **CSP sem `'unsafe-inline'` em `script-src` E `style-src`.** Sem `onclick=` (usar delegação
  em `#modal-overlay` + `[data-close-modal]`) e sem `style=`. Valor **contínuo** vai por
  `el.style` em JS: o CSSOM não é bloqueado pelo CSP, a política filtra a marcação, não a API.
- Toda interpolação de dado de usuário em HTML passa por `escapeHtml`
  (`portal/js/utils.js`).

## Frontend — App

- **`Modal` do RN renderiza fora da hierarquia do `SafeAreaView`** e não herda inset nem com
  `edges` declarado. Rodapé com padding fixo fica atrás da barra de navegação do Android. Fix:
  `useSafeAreaInsets()` + `paddingBottom: Math.max(insets.bottom, 28)` **inline** (o
  `StyleSheet.create` é estático e não enxerga o hook).
- **`DateTimePicker` dentro de outro `<Modal>`**: renderizar dentro do filho visível, não
  como sibling do overlay — o Modal clipa os filhos após o primeiro root visível e o picker
  fica invisível, sem erro.
- ScrollView horizontal de chips: `flexShrink: 0` no row e nos chips, nunca `maxHeight`
  rígido (densidade alta e font scaling estouram o cap).
- `react-hooks/exhaustive-deps` está em **zero** e `--max-warnings 0` mora no script `lint`.
  Duas armadilhas ao mexer: a lista de deps é avaliada **durante o render**, então `const`
  referenciada antes da própria atribuição estoura TDZ (exige reordenar as funções); e função
  auxiliar declarada dentro do componente é recriada a cada render, impede o `useCallback` de
  estabilizar e leva o `useFocusEffect` a loop — subir para o módulo.
- Erro de tela vai por `showError` / `useErrorToast`, não `Alert.alert`.
- Polling em tela que roda a cada poucos segundos reporta só a **primeira falha de cada
  sequência** (flag em ref, zerada em ciclo limpo) — senão vira um toast por ciclo com a
  rede fora.

## Import CSV

- Reusar `core/csv_utils.py::criar_leitor_csv(decoded, colunas_obrigatorias)`, nunca
  `csv.DictReader` direto. Ele detecta o delimitador, normaliza o header e **levanta
  `ValueError` se faltar coluna obrigatória**.
- Decodificar sempre com `utf-8-sig`. O Excel pt-BR salva com `;` e BOM — os dois quebravam
  o import **em silêncio** (zero importados, zero erros).
- O core do import de alunos é `services/import_alunos.py::processar_csv_alunos`; as duas
  rotas são cascas sobre ele.

## Ver também

[[fluxo-de-trabalho.md]] (git e commits), [[bugs.md]], [[seguranca.md]].
