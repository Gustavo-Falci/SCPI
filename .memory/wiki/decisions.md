# Decisões Arquiteturais e de Produto

Cada entrada guarda o **porquê**, que é o que não dá para derivar do código.

## Produto

### Escopo acadêmico, não empresarial
O sistema é controle de presença de **alunos** por **professores** em **turmas**. Houve um
pivot empresarial e ele foi **revertido** por decisão explícita: focar em testar o que já
está construído. Manter os termos Aluno/Professor/Turma/Chamada; não sugerir migração para
Funcionário/RH.

### MFA/TOTP para Admin: descartado
A equipe avaliou em 2026-05-18, após a auditoria, e decidiu que o custo (UX + manutenção) não
compensa no contexto do TCC — mesmo com o manual de segurança recomendando. **Não propor MFA,
TOTP, WebAuthn ou Passkeys.** Pode ser citado como gap conhecido em auditoria, nunca como
ação recomendada.

### Liveness passivo, não interativo
O produto é câmera passiva (porta + sala) e **o aluno nunca interage**. Por isso AWS Face
Liveness e desafio de movimento no app foram descartados em favor de burst X-de-Y +
pose-variance. Ver [[biometria-camera.md]].

### Custo AWS: aceitar e monitorar (decisão I1, 2026-07-16)
Projeto em free tier (Rekognition 5.000 chamadas/mês por 12 meses). O back-off tem spec
pronta mas está adiado; **gatilho de implementação = o contador mensal da AWS aproximar do
teto de 5k**. A câmera-sala re-bursta ~10× a da porta e pode estourar rápido com muitas salas.

## Dados

### `ExternalImageId` = `aluno_id` (UUID), nunca o nome
Mudou em 2026-07-31. Antes era o nome normalizado (`Joao_da_Silva`) e **homônimos colidiam,
derrubando a presença no aluno errado**. O UUID é estável (nome muda por casamento, RA por
transferência), imune a homônimo, e mantém dado pessoal fora da AWS — ganho de minimização
que sustenta o DPIA. Dedup sempre por `ExternalImageId`, nunca por `FaceId` (que duplica o
mesmo aluno). `ExternalImageId` é **imutável na AWS**: trocar a origem exige revogar e
recadastrar.

### Excluir professor **orfana**, não cascateia
`UPDATE Turmas SET professor_id=NULL` + `UPDATE Chamadas SET professor_id=NULL`, depois
deleta. As presenças penduram na chamada, que sobrevive → **histórico preservado**.
`chamadas.professor_id` e `turmas.professor_id` são NULLABLE de propósito. Não recolocar
NOT NULL nem trocar por `ON DELETE CASCADE` — isso apagaria presenças.

### Chamada: mão única Tempo Real → Revisão
Encerrar é commit; não há reabertura de captura, nem endpoint, nem mudança de schema.
Reentrada na chamada Aberta se dá por banner na home + card "Em andamento → Retomar". Na
Revisão, **toda** saída passa por `confirmLeave` ("Descartar ajustes?").

### Frequência: denominador por aluno
Matrícula no meio do semestre conta só as chamadas com
`data_chamada >= data_associacao::date` (o cast `::date` é de propósito: sem ele dá
off-by-one no mesmo dia). Aluno matriculado após a última chamada tem `aulas_dadas == 0` e
recebe `situacao="Insuficiente"`, não "Risco". Limitação aceita: sem backdate de matrícula.

### Versão da política de privacidade em `core/config.py`, não em env
`POLITICA_PRIVACIDADE_VERSAO` / `_VIGENCIA`. Escolha deliberada: **o git guarda quem mudou e
quando**, que é exatamente o que se prova num questionamento. Hash do arquivo foi rejeitado —
invalidaria aceites por correção de vírgula. Bump = editar `portal/privacy.html` + as duas
constantes.

### Backfill de consentimento como aceite `'legado'`
Quem já tinha biometria ativa virou 1 linha com o timestamp do cadastro original, em vez de
re-aceite forçado. Não inventa prova de aceite versionado. **Nunca mapear `'legado'` para
`'1.0'`.**

### PDF leva RA, não CPF
O relatório circula por e-mail e WhatsApp, **fora do controle do SCPI**. O CPF é mascarado
(`core/mascaras.py`, com validação de dígito verificador); o RA institucional vai impresso,
porque sem ele a ata de uma turma com nomes repetidos fica ambígua. Minimização de dado sem
perder a função do documento.

### Registro de presença em dois estados, não um
O aluno só entra em "resolvido" **depois** que o servidor responde. Antes ele era marcado
**antes** do POST, e um POST que falhasse nunca era retentado naquela aula — virava **falta
indevida silenciosa**. Enquanto o backend resolvia a chamada globalmente a recusa era rara;
com a validação por `chamada_id` ela virou caminho normal, e a correção deixou de ser
opcional. Implementado em `scripts/registro_tracker.py`.

### Detector de textura fail-closed, com modelo não-quantizado
`DetectorTextura` levanta se não conseguir carregar o ONNX, em vez de degradar em silêncio —
um gate de vida que falha aberto é pior que gate nenhum, porque dá falsa confiança. O modelo
**tem que ser o `best_model.onnx` não-quantizado (1,9 MB)**: o quantizado (626 KB) usa
`DynamicQuantizeLinear`, não suportado pelo `cv2.dnn`. Ver [[biometria-camera.md]].

## Infraestrutura

### Tudo em Postgres — sem serviço novo
O rate limiter multi-worker foi para Postgres (`core/limiter_storage.py`,
`PostgresStorage(Storage)`, scheme `scpi-postgres://`), **não Redis**. Postura explícita de
não adicionar serviço.

### Postgres local na mesma VM do backend
Desde 2026-06-15 (`DB_HOST=127.0.0.1`). Motivo: a VM separada do banco foi terminada por
engano e causou outage de 504.

### Backup de segredos: `age` com chave **pública** na VM
A VM cifra e não decifra, nem os backups que ela mesma gerou; a chave privada mora no
password manager do Gustavo + cópia offline. Protege contra vazamento do bucket — sem isso,
`.env` + dump no mesmo bucket permitiria forjar JWT e ler dado de aluno. Divergência
deliberada do backup do Postgres, que **não** usa cripto client-side: o dump é dado, este
pacote é a chave que abre o resto. **Perder a chave privada = perder todos os backups de
segredo.**

### Portal: Tailwind CLI com CSS versionado, não build no deploy
Decisão de não meter Node na VM. O deploy segue `git pull` + nginx.

### `CAMERA_INDEX` por env, sem auto-detect
Auto-detecção ("pega a primeira câmera que abre") foi proposta e **rejeitada** em 2026-07-15:
o PC de sala pode ter webcam integrada no índice 0 apontada para lugar inútil, e a USB da
sala no índice 1 — auto-detect pegaria a errada e registraria presença de uma view errada,
em silêncio. Erro explícito é melhor. Se a reordenação de índice DSHOW virar dor real, a
saída mapeada é seleção por **nome** (`CAMERA_DEVICE_NAME` via `pygrabber`), mantendo
`CAMERA_INDEX` como override — não auto-detect.

### `LoggingIntegration` do Sentry DESLIGADA de propósito
`LoggingIntegration(level=None, event_level=None)`. A integração é default do SDK e converte
todo `logger.error` em evento e todo `logger.info` em breadcrumb, com a mensagem **já
interpolada**. No SCPI isso vazaria audit log de presença (`aluno=<RA> ip=<IP>`), e-mail do
titular, e o texto de `UniqueViolation` do psycopg2 com `Key (email)=(...)`. E **`before_send`
não alcança `logentry`/`breadcrumbs`/`extra`** — só `event["request"]`. `propagate = False`
também não protege: o SDK faz monkey-patch em `logging.Logger.callHandlers`. **Não remover.**

### Isenções de CSRF em `/auth/login` e `/auth/refresh`
`core/csrf.py::_CSRF_EXEMPT_PATHS`. O RN persiste cookies no jar nativo; após o 1º login o
`scpi_access` ficava guardado e o fetch seguinte mandava cookie sem `Authorization` e sem
`X-Requested-With` → o middleware rejeitava. **Travou logins em produção em 2026-05-19.**
Risco analisado: em `/auth/login` o CSRF clássico é inútil (o atacante precisa da senha), e
em `/auth/refresh` o cookie é `SameSite=Strict` + `Path=/auth`, então o browser não envia
cross-origin. **Não remover sem ler esse raciocínio.**

### Envelope de paginação opt-in
`?paginado=1` devolve `{items, total, has_more}`; sem o param, array puro como sempre.
Escolhido porque build antiga faz `Array.isArray(data)` e renderizaria lista vazia — **falha
silenciosa é pior que erro visível**. Backend e app sobem em qualquer ordem.

## Adiado com gatilho — auth dedicado para o Swagger (2026-08-20)

`/docs` exige sessão de **Admin** (PR #119). Decidido **não** criar autenticação própria para a
documentação agora — quem lê o Swagger hoje já é Admin, e um segundo mecanismo de auth seria
segredo novo sem leitor novo.

**Gatilho para retomar:** aparecer alguém que precise ler a documentação e **não** deva ser
Admin — dev novo no handover, auditor, sócio. Hoje ler a doc custa um crachá que vê e apaga
dado pessoal de aluno (biometria, RA, presença), o que é privilégio excessivo para leitura.

**Quando retomar, a opção a defender é um papel de leitor** no próprio sistema de usuários:
usuário real, revogável um a um, com trilha de auditoria e sem segredo novo. Custa mexer no
`tipo_usuario` (hoje `Professor|Aluno|Admin`, com pattern na validação e valor no banco).

**Basic auth no nginx foi considerada e rejeitada** como caminho preferencial: credencial
compartilhada, sem trilha de quem acessou, e revogar para uma pessoa obriga a trocar para
todos. Trocar sessão individual revogável por segredo coletivo piora a auditoria.

**Buraco conhecido, independente dessa decisão:** o gate em `core/docs_protegidos.py` **não
registra nada** — nem Admin que abriu, nem tentativa negada. O `require_role` loga negativa em
`audit_logger`; este caminho não. Cookie de Admin vazado abre o Swagger sem deixar rastro.

## Em aberto — decisão dos sócios

Levadas ao grupo em 2026-07-07 e depois; **não retomar o design até a resposta**.

1. **Multi-tenancy**: instância por cliente (A) vs `tenant_id` compartilhado (B). Critério
   combinado: nº de clientes esperado em 12 meses + ticket. Decidir **antes** do primeiro
   cliente com dados reais.
2. **Staging / rollback** (última pendência da dívida operacional, virou decisão em
   2026-07-28). Três opções na mesa: (A) VM de staging separada com banco próprio
   (custo/manutenção dobrados, testa o deploy real); (B) só rollback em prod — release
   atômico versionado + rollback de 1 comando + dump antes de migration (menor esforço, ataca
   o risco maior); (C) staging na mesma VM — unit `scpi-api-staging` em outra porta + banco
   `scpi_staging`.
3. **P2 — custo AWS** ~US$125/aula/sala.
4. **LGPD comercial** (adiada): retenção de biometria pós-desligamento (definir X dias),
   consentimento de responsável para menores, minuta de DPA.
5. **Alternativa não-biométrica de presença** (levantada 2026-07-30). Quem revoga o
   consentimento fica sem como registrar presença sozinho — sobra o professor ajustar via
   `POST /chamadas/{id}/ajustar`. Sob a LGPD o consentimento precisa ser **livre** (Art. 5º
   XII), e há discussão real sobre liberdade quando a alternativa é depender do professor
   toda aula. Não é bug, é decisão de produto. Saída usual: caminho não-biométrico
   documentado (código de presença, lista assinada) citado na política.

Quando houver resposta: transformar a decisão em spec (brainstorming → writing-plans).
