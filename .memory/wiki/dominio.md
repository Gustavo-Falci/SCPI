# Domínio — Chamada, Professor, Aluno, Relatórios

## Fluxo de chamada (professor)

Dirigido pelo **estado da chamada** (Aberta → Fechada → home), não por pilha de navegação
linear. Mergeado em 2026-05-27 (PR #33).

Motivo: havia dois becos sem saída no app. (1) Ao voltar do "Tempo Real", a chamada ficava
Aberta no banco sem caminho de reentrada — o índice único `uq_chamada_aberta_por_turma` mais
a exigência de horário impediam reabrir via `/abrir`. (2) Ao voltar da Revisão caía no Tempo
Real já Fechado, sem botão de avançar de volta.

Decisões de design (ver também [[decisions.md]]):

- **Mão única** Tempo Real → Revisão. Encerrar é commit; sem endpoint de reabertura, sem
  mudança de schema.
- **Reentrada na chamada Aberta** por banner na home + card "Em andamento → Retomar" no
  picker. A saída do Tempo Real é livre; a captura segue rodando.
- **Revisão com edição segura "só enquanto na tela"**: toda saída (Voltar do header,
  hardware-back e os 4 itens do FloatingMenu) passa por `confirmLeave`. Reedição de chamada
  **fechada** continua fora de escopo — `relatorio-detalhe.tsx` é read-only. Se for
  implementar, o backend `/chamadas/{id}/ajustar` **já aceita** chamada Fechada; falta só UI.

Backend (aditivo, só GET): `/professor/dashboard` devolve
`chamada_ativa: {chamada_id, turma_id, turma_nome} | null`; `/turmas/{id}` devolve por turma
`chamada_aberta: bool` + `chamada_id`. A query de turmas usa `LEFT JOIN LATERAL ... LIMIT 1`.

Autorização: `_assert_professor_dono_ou_admin` em `ajustar`/`finalizar`/`fechar` +
`status/{turma}` e `{chamada}/alunos` — ver o BOLA em [[seguranca.md]].

`registrar_presenca_por_face` resolve a chamada **pela sala do token**, não globalmente. Ver
o bug em [[bugs.md]] e o warning ainda a validar em campo (`Sala X com 2 chamadas abertas
hoje`).

## Professor

Fluxo de criação/edição/import igualado ao do aluno em 2026-05-21 (PR #16) — antes o backend
tinha `primeiro_acesso=TRUE` mas portal e mobile não tinham UX equivalente.

- `PATCH /admin/professores/{id}`
- `POST /admin/importar-professores` (CSV `nome,email,departamento`)
- Mobile: `/auth/primeiro-acesso` adapta badge e botão por role (Professor **pula** a etapa
  de face).
- O CSV de professor separa `importados` de `duplicados` na response; o de aluno foi mantido
  inalterado, porque lá `importados` significa matrículas efetivas — **semântica diferente**.

**Excluir professor orfana turmas e chamadas** — ver [[decisions.md]].

## Aluno / matrícula

- Desmatricular: `POST /admin/turmas/{id}/desmatricular-alunos`, repo
  `desmatricular_alunos_da_turma`. **Histórico de presença é preservado**: `presencas` tem FK
  para chamadas e alunos, não para `turma_alunos`, e não há cascade.
- Re-import de CSV é seguro: `ON CONFLICT DO NOTHING` preserva `data_associacao` (que é o que
  o cálculo de frequência usa como início da janela).

## Import CSV

Core único: `services/import_alunos.py::processar_csv_alunos(conteudo, turma_id_fixo=None,
on_novo_usuario=None)`. As duas rotas são cascas sobre ele:

- `POST /admin/importar-alunos` — coluna `turma` opcional (= `codigo_turma`);
- `POST /admin/turmas/{turma_id}/importar-alunos` — turma fixa, ignora a coluna.

Tolerância ao Excel pt-BR e o `criar_leitor_csv` estão em [[patterns.md]]. O modelo que o
portal gera sai com `;` + BOM **de propósito** — é o que abre em colunas no Excel pt-BR; o
upload aceita os dois delimitadores. Gerador compartilhado:
`portal/js/utils.js::baixarModeloCsv`.

## Relatórios

### Filtros (professor)

`GET /professor/relatorios/chamadas` aceita `data_inicio`, `data_fim`, `turma_id`, `turno`,
`semestre`. `GET /professor/relatorios/filtros` devolve `{turmas, turnos, semestres}` **só
com opções que têm chamadas Fechadas do professor** — evita filtro que não retorna nada.
Repos: `listar_relatorios_chamadas` e `listar_opcoes_filtros_relatorios`.

### Paginação (2026-07-31)

Envelope opt-in `?paginado=1` — ver o porquê em [[decisions.md]]. `FlatList` +
`onEndReached`, 20 por página, `RelatorioCard` extraído e memoizado (`renderItem` inline
recria a função a cada render e anula parte da virtualização).

- **Token de requisição** (`useRef` incremental) descarta resposta em voo quando o filtro
  muda. Sem isso, a página antiga é acrescentada sobre a lista de outro recorte — bug raro e
  difícil de reproduzir.
- **`contar_relatorios` não aceita `frequencia_baixa`**, de propósito, com teste travando a
  assinatura via `inspect.signature`: aquele filtro roda em Python **depois** do SQL, então um
  `COUNT` daria total maior que a lista exibida.

### PDF — em prod desde 2026-07-22

Três documentos gerados no backend com reportlab: **Ata de Presença** (1 chamada),
**Consolidado** (período filtrado) e **Frequência por aluno** (1 turma). Os endpoints
existentes ganharam `?formato=pdf`, mesmo precedente do export LGPD.

- Denominador **por aluno** e o bugfix de numerador/denominador na mesma janela: ver
  [[decisions.md]] e [[bugs.md]].
- `gerar_pdf_frequencia` conta "Regulares" por `situacao == "Regular"` explícito — senão
  "Insuficiente" era contado como Regular.
- A divergência lista×PDF no admin foi resolvida fazendo a **tela puxar do servidor**:
  `portal/js/tabs/relatorios.js` fetcha `/admin/relatorios/chamadas` com `turno` + `semestre`
  + `limit=2000` (mesmo teto do `TETO_CONSOLIDADO` do PDF), com cache por assinatura de
  filtro. Escopo: parity de filtro server-side, **não** paginação offset-real.
- **Cuidado ao validar números contra a turma de teste BD-123**: ela tem
  `data_associacao=hoje` com chamadas retroativas (dado bagunçado), então "dadas" aparece
  baixo e "assistidas" = 0. Não é bug, é o dado. Validar contra turma real.
- Dívida aberta: ~15 linhas duplicadas entre `compartilharPdf` (`relatorios.tsx`) e
  `exportarPdf` (`relatorio-detalhe.tsx`). Review recomendou **deferir** a extração do hook
  até surgir uma terceira tela.

## Agendador

`services/agendador.py` roda em loop assíncrono: `fechar_chamadas_expiradas` (offloaded com
`run_in_executor`, porque é psycopg2 síncrono) e, para cada chamada fechada,
`notificar_alunos_presentes`. O UPDATE virou **claim atômico** com guarda
`cur.rowcount != 1` — sem isso, dois workers notificavam a mesma turma (bug do double-notify,
fechado na PR #78). O purge diário do `rate_limit_buckets` também roda aqui.

## Auditoria de biometria (aba Biometria)

`services/inventario_biometrico.py` reconcilia **AWS × banco**: agrupa os registros ativos por
aluno e calcula os **ângulos faltantes por diferença** contra `core/regras.ANGULOS_VALIDOS`.
Registro com `revogado_em` preenchido conta como `revogado`, não como `ok`. É função pura —
recebe as três listas prontas, sem boto3 nem psycopg2. Exposta em `GET /rostos/inventario`.

## Frequência — limiar único

`core/regras.LIMITE_FREQUENCIA = 75`. O mesmo número decide o rótulo textual
(Regular / Risco) **e** a cor da linha no PDF; `Insuficiente` é caso à parte (aluno com
`aulas_dadas == 0`). Ver [[decisions.md]].

## Sistema de erros

Três camadas, mensagens em PT-BR:

- **Backend** — `BackEnd/core/errors.py`: enum `ErrorCode` com 27 códigos, helpers
  `http_error` / `not_found` / `forbidden`, handler 429 consistente.
- **Portal** — `toast.js` (stack, barra de progresso, 4 tipos) e `extractErrorMessage()` no
  `api.js`, que trata arrays do Pydantic e mapeia status HTTP → mensagem PT-BR.
- **Mobile** — `ErrorToast.tsx`, `useErrorToast.ts`, `errorMessages.ts`, provider no
  `_layout.tsx`. 10 telas migradas de `Alert.alert` para `showError`, com **três exceções
  deliberadas**: `aluno/frequencia` já renderiza o erro em estado próprio; `_layout` renderiza
  o provider, então `useErrorToast` lançaria ali; e `lista-presencas` roda a cada 3s e só
  reporta a primeira falha de cada sequência.
