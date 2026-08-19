# Work Log

*Changelog append-only. Datas absolutas.*

## 2026-08-05 — Migração da memória para a MemWiki

MemWiki instalada (`npx memwiki init`). Toda a memória persistente do assistente (47 arquivos)
foi sintetizada nas páginas desta wiki. `.memory/` adicionado ao `.gitignore` — o repositório
é público e o conteúdo inclui caminhos de produção, IPs, nomes de segredo e a dívida de
segurança conhecida.

Decidido no mesmo dia: **manter os dois sistemas de memória** (a do assistente e esta wiki),
sincronizados a cada fato novo. Regra em [[fluxo-de-trabalho.md]].

**Passe de ingestão (`/memwiki-ingest`) no mesmo dia**, varrendo o repositório. Acrescentou
mapa de módulos, 17 tabelas, superfície de rotas, envs e versões reais a [[stack.md]]; os
scripts de boot do portal a [[portal.md]]; agendador e inventário biométrico a [[dominio.md]];
e quatro decisões que só estavam no código a [[decisions.md]]. **Três correções ao que a
memória afirmava:** o detector de textura anti-spoofing existe e é o gate default (a memória
dizia "PAD local = futuro"); `CAMERA_SERVICE_TOKEN` ainda é o nome da env na máquina da sala
(o que acabou foi o token global); e várias versões estavam defasadas (`gunicorn` 26.0.0,
`PyJWT` 2.13.0, `reportlab` 5.0.0).

## Linha do tempo do projeto

### 2026-04 / 05 — Fundação e primeira auditoria
- 2026-05-18: início da auditoria contra `manual_seguranca_sistemas_v2.md`. Equipe descarta
  MFA para Admin.
- 2026-05-19: portal migra de localStorage para cookie HttpOnly + CSRF. Bug do cookie jar do
  RN trava logins em produção → isenções de CSRF em `/auth/login` e `/auth/refresh`.
- 2026-05-20: migração `python-jose` → `PyJWT`; upgrade Expo SDK 54 → 55 (PR #11); deploy do
  #8 em prod.
- 2026-05-21: fluxo de professor em prod (PR #16); export LGPD combo (PDF+JSON+HMAC) —
  incidente do ZIP truncado por `StreamingResponse`.
- 2026-05-25: pentest white-box, 7 fixes (BOLA em chamadas era o mais grave). Dependabot passa
  a ignorar a stack Expo.
- 2026-05-26: `fastapi 0.136.3` identificada como release malicioso; pin em 0.136.1.
- 2026-05-27: fluxo de chamada como máquina de estados (PR #33); filtros da tela Relatórios.

### 2026-06 — Consolidação
- 2026-06-11: `tcc-app/` → `app/`; `.gitleaksignore` com os 6 findings históricos; gap do
  ignore do Dependabot corrigido.
- 2026-06-15: Postgres passa a rodar local na VM do backend (a VM antiga foi terminada por
  engano).
- 2026-06-16: Dependabot passa a ignorar minor/patch do `fastapi` — o pin manual tinha sido
  derrotado e o malicioso rodou em prod por 12 dias.

### 2026-07 — Operação de verdade
- 2026-07-06/07: backup diário do Postgres em OCI Object Storage, com teste de restore.
  `GET /health` + UptimeRobot. CI de pytest.
- 2026-07-15/16: liveness passivo (burst + pose-variance + YuNet) implementado e validado em
  campo. Decisão I1: aceitar e monitorar o custo AWS.
- 2026-07-16: causa raiz do push Android — faltava credencial FCM no EAS.
- 2026-07-20: import CSV tolerante ao Excel pt-BR (BOM e `;` quebravam em silêncio).
- 2026-07-22/24: relatórios em PDF em prod; denominador de frequência por aluno; bugfix da
  frequência estourando 100%.
- 2026-07-23: M4 (rate limiter em Postgres) + B1 (lockout de login) — PR #71. Restrição da
  chave Firebase por SHA-1. `gunicorn` finalmente pinado; migração para `uvicorn-worker`.
- 2026-07-24: receipts de push níveis 1 e 2 em prod (PR #73), com timer de 15 min.
- 2026-07-27: Sentry em prod (PR #78), com `LoggingIntegration` desligada de propósito.
- 2026-07-28: backup cifrado de segredos com `age` (PRs #79/#80). Descoberto que a lifecycle
  policy do bucket **nunca existiu**, apesar de documentada.
- 2026-07-30: trilha de consentimento LGPD em prod.
- 2026-07-31: análise completa (segurança 8,5 / performance 6 / UX 7,5 / entrega 6). Achado
  central corrigido: chamada escolhida globalmente quebrava com 2+ turmas simultâneas.
  `ExternalImageId` passa a ser o UUID do aluno. Paginação dos relatórios.
  Incidente do push direto para `main` por falta de `--no-track`.

### 2026-08 — Fechamento do backlog (~20 PRs)
- 2026-08-01: hardening A1–A6 em prod (PR #89). Token de câmera por sala substitui o
  `CAMERA_SERVICE_TOKEN` global.
- 2026-08-02: índices de performance (P3) e `run_in_threadpool` (P1) — PR #90.
  `Cache-Control` no nginx. 503 da câmera vira acionável (PR #91).
- 2026-08-03: UX inteira fechada — contraste WCAG (PR #99), erros do app (PR #100),
  19 warnings de hooks zerados, `lifespan` (PR #101), `TIMESTAMPTZ` nos tokens (PR #102),
  Tailwind CLI (PR #103), P4 e P5. Units de receipts versionados.
  Bug de CSP com sintoma mudo descoberto e corrigido.
- 2026-08-04: `'unsafe-inline'` removido do `style-src` (PR #106). `TIMESTAMPTZ` nas 10
  colunas restantes (PR #108) — **o schema não tem mais nenhuma coluna sem fuso**.
- 2026-08-05: smoke test do app em device OK; `.env` local corrigido; pin de `cryptography`
  removido e em prod.
- 2026-08-05: instrumentação para medir replay de VÍDEO (branch `feat/validacao-replay-video`,
  6 commits, aguardando PR). O gate de textura nunca foi medido contra vídeo em tela — só
  contra foto. `_validar_liveness.py` passa a coletar em bursts de 5 frames em 2 s e a
  reportar max-por-burst, porque o gate decide por MAX: calibrar em frame solto subestima o
  atacante. Dois defeitos de spec pegos na review final, ambos de direção perigosa — a
  ferramenta recomendaria AFROUXAR o gate parecendo endurecê-lo. Descoberto de passagem que
  `-W error` **não** está configurado no CI.
- 2026-08-06: **medição feita — o gate de liveness está furado em produção.** Celular com
  foto de aluno na frente da câmera da sala REGISTRA presença pelo caminho normal da chamada
  (`texture_max=0.854` vs limiar `0.08`). Pior: `magnitude=2.98` vs `pose_std_min=2.0`, ou
  seja, o fallback de pose aprova o mesmo ataque — o tremor da mão segurando o celular imita
  variação de pose, e a premissa "foto é plana, então a pose não varia" só valia para foto
  imóvel (era esse o teste de campo de 2026-07-16). Os dois gates caem juntos.
  Matriz: `R=0.0017 < V=0.638` → SOBREPOSTO. Nenhum `TEXTURE_LIVENESS_MIN` separa (bloquear
  vídeo custaria 60% de falso-negativo em aluno real) e piso de bbox também não fecha.
  Camada B passa de opcional a obrigatória. Colateral: um burst de rosto REAL a 136–161px
  pontuou 0.0017 sob contraluz — falso-negativo de disponibilidade, independente do spoof.
  Colateral 2: o modelo colapsa em "live" abaixo de ~30px de rosto (mediana 0.9887 contra
  0.0159 acima de 40px). A coleta rodou em casa e sem `LIVENESS_COND`, então a matriz de 12
  células continua aberta — ela é que dirá QUAL distância/aparelho quebra.
- 2026-08-06 (2ª parte): **conserto do bypass empurrado** — branch `fix/piso-tamanho-rosto-textura`,
  2 commits, PR aberto, não mergeada. Diagnóstico da causa raiz: o MiniFASNet é documentado para
  rosto de ~80px e estava recebendo crops de 11px; abaixo de ~40px ele devolve "vivo" para
  qualquer coisa (foto em tela mediana 0.9887 contra 0.0159 dos ≥40px). Não era limiar mal
  calibrado — era o modelo operando fora da spec dele, e o 1.0000 era ruído lido como resposta.
  Correção: abaixo de `TEXTURE_FACE_MIN_PX=80` o score vira `None` ("não sei") e o fail-closed
  que já existia em `ConfirmadorBurst` manda para PENDENTE — nenhum estado novo, e
  `confirmacao_burst.py` intocado. Sobre a coleta: `video` 3/6→0/6 e `tela` 6/6→0/6 registram,
  `real` fica em 4/5, idêntico a antes. Removida `DetectorTextura.vivo()` (zero chamadores) e
  corrigida a docstring do módulo, que afirmava "foto 0.000" — foi ela que sustentou a crença
  de que o gate estava fechado. Suíte 715 passed, zero warnings.
  Descoberta estrutural do design: serão DUAS câmeras com geometrias opostas. Na PORTA o aluno
  está perto (rosto grande) e o atacante segura um aparelho cujo rosto exibido é pequeno — essa
  assimetria é o que faz o piso funcionar. Na LOUSA (3–8 m, rosto de 20–55px) tudo cai na zona
  de colapso: o modelo de textura **não a atende por construção**, e ela precisa de gate
  geométrico em spec própria, desenhado ANTES de a câmera subir.
  Sonda de bezel sobre as amostras: sinal forte (vetaria 6/6 de `video` e 5/6 de `tela`) mas
  **veta 2 de 5 bursts reais**, tropeçando em batente de porta. O difícil da camada B não é
  achar o bezel, é não confundir com parede.
  Fica aberto: calibrar o piso na porta (gate de deploy), flag `--piso` (bloqueada até o merge),
  e o tablet colado na câmera — que o piso não cobre e nunca foi coletado.
- 2026-08-06 (3ª parte): **debug da causa raiz + duas previsões minhas falsificadas.**
  Sintoma novo do Gustavo: rosto real vivo pontua MUITO baixo com frequência na porta, enquanto
  o vídeo passa. Investigação sistemática sobre as amostras + log de produção.
  REJEITADAS (não perseguir de novo): (a) classe invertida — controlando por tamanho, na faixa
  60–100px `p[0]` dá real 0.0886 contra tela 0.0159, direção certa; o "tela=0.97" era artefato
  de rosto de 11–28px, nitidez 7,5, um borrão; (b) crop pequeno sendo ampliado — 24 de 25 frames
  reais já têm crop nativo ≥128px.
  CAUSA RAIZ: **o modelo responde a NITIDEZ, não a vida.** Spearman nitidez×score: real +0.651,
  tela −0.785, video −0.564. Frames reais lidos como vivo têm nitidez 702; os lidos como fake,
  91 — 7,7×, com brilho idêntico. Borrão de movimento de quem passa pela porta derruba o score,
  e a calibração de julho foi em close-up parado e nítido. Não tem conserto por parâmetro:
  limiar não cria nitidez, ataca-se em exposição/obturador/luz.
  DUAS PREVISÕES MINHAS ERRADAS, ambas por extrapolar amostra pequena de ambiente diferente:
  (1) "na porta o rosto dá 150–300px" — dá **60–75px**, e o piso teve que cair de 80 para 50
  senão a pessoa real não passa; a porta está na faixa MARGINAL do modelo, não na confortável.
  (2) "vídeo só passa abaixo de ~91px" — passou com 79–91px e `texture_max=0.2802`. A parte da
  spec que sobreviveu foi a que veio da spec do MODELO (~80px), não da amostra.
  Contradiz julho: o ataque na mão tem magnitude de pose **7–8× MAIOR** que a pessoa real
  (19–23 contra 2.79). A premissa "foto é plana, pose não varia" está invertida na prática — se
  pose for usada, o discriminante é TETO, não piso.
  Teto de tamanho de rosto proposto e RECUSADO: falha no teste de assimetria — vencer o piso
  exige rosto maior (mais resolução, textura mais forte, bom para nós), vencer o teto exige
  rosto menor, e abaixo de ~40px o modelo devolve ~0.99 para qualquer coisa. O teto empurra o
  ataque para dentro do ponto cego.
  Entregue: log passa a imprimir `rostos_px`/`rosto_menor`/`abaixo_do_piso`, e PENDENTE
  distingue "nenhum rosto grande o bastante" de "textura baixa". Commitado e empurrado (3º
  commit da branch, que fecha com 3 no total).
  Retomada: 20 bursts do log da porta (10 real variados + 10 vídeo) para decidir com dado.
- 2026-08-06 (4ª parte): **camada B — direção medida, e ela não é geometria.** Ideia do Gustavo:
  achar o retângulo do aparelho e descartar todo rosto dentro dele. Estrutura certa; o método de
  ACHAR o aparelho é que foi medido, em 3 implementações sobre as 17 amostras. Vencedora foi a
  que NÃO ajusta retângulo: "o rosto está dentro de uma região que emite luz?" — 0/5 falso
  positivo em `real`, 4/6 de `tela` e 5/6 de `video` vetados. Ajuste de retângulo bem feito
  (Otsu + minAreaRect + retangularidade + aspecto) ficou PIOR que a heurística crua: 1/5 de falso
  positivo e só 2/6 e 1/6 de detecção. Motivos documentados em [[biometria-camera.md]] para
  ninguém repetir: Canny dá curva aberta (área ~0), celular ocluído pela mão dá 7–22 vértices
  (nunca 4), e com o aparelho perto a moldura sai do quadro — aí não existe retângulo na imagem,
  que é justamente a posição usada para vencer o piso.
  Parei na 3ª tentativa por disciplina: 3 falhas do mesmo tipo é sinal de enquadramento errado,
  não de parâmetro errado.
  **Correção de fato: o repositório é PRIVADO**, não público. Passei o dia repetindo "repo é
  público" (na spec e na wiki) como justificativa para não commitar amostras — premissa errada,
  vinda de memória desatualizada. `gh repo view` confirma `visibility: PRIVATE`.
  **Incidente de wiki:** `.memory/wiki/` sumiu do disco durante a sessão. Causa: a `main` passou
  a VERSIONAR o wiki (commit b265ffe2) e a tirar `.memory/` do `.gitignore`, enquanto esta branch
  saiu de um ponto anterior (734d87ce) onde ele era ignorado. Trocar de branch apaga os arquivos
  do disco. Recuperado com `git archive main .memory/wiki | tar -x`. **O merge da branch é
  seguro** — a base comum não tinha o wiki, então a adição da main prevalece. Mas editar o wiki
  a partir desta branch é arriscado: aqui ele é git-ignored, a edição não é commitável e o
  próximo checkout a destrói.
- 2026-08-16: **instrumentada a medição da camada B.** Commit `3c5fd9cd` em
  `feat/validacao-replay-video` (7 commits, sem PR): `_regiao_emissiva()` + `_emissivo_do_burst()` em
  `_validar_liveness.py`, 6 testes puros com imagens sintéticas, mais flags `--piso PX` e
  `--percentil P`, e uma seção nova no relatório do `--test`. Suíte 733 passed, 81 skipped.
  Assim UMA coleta na porta responde de uma vez: limiar de textura, valor do piso e se a
  camada B sobrevive com fundo e luz reais.
  O teste sintético pegou um bug real da sonda original: `>` estrito sobre o percentil zera a
  máscara quando a área acesa é maior que (100−percentil)% do quadro. Corrigido para `>=` mais
  guarda de área (>50% do quadro = cena, não aparelho — o que também impede brilho uniforme
  vetar rosto real). Efeito: `tela` subiu de 4/6 para **5/6** vetados mantendo 0/5 em `real`.
  O número 4/6 registrado antes está corrigido para 5/6 em [[biometria-camera.md]].
  Dívida deixada explícita: `_rosto_avaliavel` na ferramenta é duplicata temporária de
  `anti_spoofing.rosto_avaliavel` (branch do fix, não mergeada) — virar import no merge.
  Worktree criado em `C:/Users/itconsol/Documents/SCPI-wt-tool` porque trocar de branch no
  diretório principal APAGA `.memory/wiki/` do disco (branches antigas o ignoram). Removido
  depois do commit; o commit sobrevive porque vive no objeto do repo, não no worktree. **Padrão
  a repetir** enquanto as branches divergirem no `.gitignore`: worktree em vez de checkout.
- 2026-08-16: **veto anti-replay em produção, tudo mergeado, branches limpas.**
  Implementado `scripts/deteccao_tela.py`: o rosto está dentro de uma região que emite luz?
  Veta com precedência sobre a textura, exige ≥2 frames do burst, e é **fail-open** de propósito
  (erro no detector não veta — falta silenciosa de aluno é pior que ataque que passa).
  Medido na porta antes de subir: vídeo **7/7** bursts vetados (5/5 frames em todos), rosto real
  **0/6**. Confirmado rodando em produção: 3/3 bursts de ataque barrados, e um tinha
  `texture_max=0.2314` contra `tex_limiar=0.22` — **teria registrado presença** sem o veto.
  A textura sozinha, no mesmo dado da porta, deixava passar 7/7 (0.221–0.880 contra rosto real
  0.997–0.9996: folga de só 1.13×, que iluminação ruim derruba — no apartamento o real caiu a
  0.002). Por isso o conserto NÃO foi mexer no limiar.
  PRs #112 (veto + log de tamanho + wiki) e #113 (ferramenta) mergeadas com squash. Apagadas
  também quatro branches antigas com PR já mergeada (#106, #107, #108, #109). Sobrou só `main`,
  761 testes verdes; única remota viva é a do Dependabot (#111).
  **Armadilha do squash confrontada:** `fix/piso-tamanho-rosto-textura` já estava mergeada (#109)
  e tinha recebido commits novos. Simulação de merge (`git merge-tree`) acusou conflito em
  `reconhecimento_tempo_real.py`. Solução: branch nova a partir da `main` levando só os 5
  arquivos do trabalho novo, em vez de forçar a antiga.
  **Bug pego por rodar o binário, não a suíte:** ao trocar as duplicatas da ferramenta pelos
  módulos de produto, `_validar_liveness.py` quebrou com `ModuleNotFoundError` — e **761 testes
  passaram assim mesmo**, porque o pytest resolve o `sys.path` e o script solto não. Só apareceu
  no `--help`. Shim adicionado com o comentário explicando. Lição: para script executável,
  suíte verde não prova que ele sobe.
  Correção de fato: `.memory/wiki/` passou a ser versionado na `main` (repo é PRIVADO; a crença
  de que era público estava errada e foi repetida o dia todo).
  **Fica aberto e não é detalhe:** o `0/6` de falso positivo do veto foi medido com rosto de
  161–358px, parado e perto. Em produção o aluno passa a 60–75px — condição NÃO testada. Falso
  positivo ali vira falta silenciosa. Também não testados: porta com sol, e tablet.
- 2026-08-17: **Security Scan agendado voltou a verde — 4 advisories high no `npm audit (app)`.**
  Falhava desde o push de 2026-08-16 (e na run agendada de segunda), sempre no mesmo job; PR não
  pegava porque o `paths-filter` só roda o job de mobile quando o PR toca `app/`. Diagnóstico:
  `js-yaml` (GHSA-5p4m-2wfm-xmqj) — os overrides `js-yaml@3: 3.15.0` / `js-yaml@4: 4.3.0`
  ficaram **um patch curtos**: a advisory nova corta exatamente em 3.15.1 / 4.3.1, ou seja, o
  pin que resolvia a advisory anterior virou o alvo da seguinte. `nanoid` (GHSA-2v37-7h3g-55p8)
  — 3.3.16 na árvore via `@react-navigation/native`, `expo-router` e `postcss`; a PR do
  Dependabot para `/app` **falhou** (`bin/run update_files` exit 1, sem detalhe no log) enquanto
  a de `/portal` mergeou, e o Dependabot ignora a stack Expo/react-navigation, então sozinho não
  ia resolver. `image-size` (GHSA-w3rx-r6r6-pgpr e GHSA-5p2g-fcmc-qvqq) — **sem correção
  possível**: o range é `<= 2.0.2` e 2.0.2 é a última versão publicada; entra como 1.2.1 pinado
  por `metro@0.83.7` (expo 55). O `fixAvailable` do npm sugeria `expo 53.0.27`, que é
  **downgrade de major** — não confiar nesse campo.
  Correção: overrides para 3.15.1 / 4.3.1 e `nanoid@3: 3.3.18`; os dois GHSA de `image-size`
  entraram na ALLOWLIST do gate com motivo e condição de saída (metro é bundler de build, não
  vai no binário e só processa asset do próprio repo). Removida a entrada de `brace-expansion`
  — o gate já vinha avisando por `::notice::` que ela não aparecia mais no audit, prova de que
  vale a pena o script reclamar de allowlist obsoleta.
  Verificado com o comando do CI (`npm audit --json | node .github/scripts/npm-audit-gate.mjs`):
  exit 0, 10 high restantes todos nas cadeias de `image-size`. `tsc --noEmit` e `expo lint` verdes;
  diff do lockfile é só version/resolved/integrity dos 3 pacotes.
  **Armadilha local:** no PowerShell o pipe entre dois executáveis insere BOM e o gate morre com
  "Não foi possível parsear a saída" — artefato de shell no Windows, não bug do script (o CI roda
  em bash). Rodar esse pipe pelo Bash.
- 2026-08-17: **revisão das 2 PRs abertas (#114, #115) — as duas verdes e mergeáveis.**
  #114: `nanoid` 3.3.17→3.3.18 no `portal/package-lock.json`, devDep (postcss/tailwind), fecha o
  **único alerta aberto** do Dependabot. #115: grupo `python-minor`, 13 pins do BackEnd; `fastapi`
  fica em 0.136.1 (o pin contra o release malicioso não foi tocado), pip-audit --strict e os 761
  testes verdes com o `requirements.txt` novo instalado de fato pelo CI. Starlette 1.3.1→1.6.0 é o
  maior salto e é inócuo aqui: as mudanças são GZipMiddleware, header Range e um `max_body_size`
  opt-in, e não usamos nenhum dos três (`api.py` só registra CSRF/CORS/ProxyHeaders/SecurityHeaders).
  **sentry-sdk 2.68.0 torna `enable_logs`/`enable_metrics` no-op** e move a coleta automática para
  um `capture_sentry_logs` por integração, **default False**. Nossa postura de PII sobrevive
  intacta porque ela nunca dependeu de `enable_logs`: é `LoggingIntegration(level=None,
  event_level=None)` em `core/observabilidade.py`, e não chamamos a API `sentry_sdk.logger.X`.
  **Risco real que o CI não cobre:** `opencv-python` 4.13→4.14 e `numpy` 2.5.1→2.5.2 rodam na
  máquina da câmera, que não tem teste automatizado — e a margem do liveness é fina (limiar 0.22
  contra medições de 0.22–0.28 em ataque). Depois de atualizar a máquina da porta, **remedir com
  `_validar_liveness.py`** antes de confiar nos limiares.
  **Descoberta que muda em que sinal confiar:** os alertas do Dependabot para `/app` estão
  **errados**. `js-yaml` (2 alertas) e `nanoid` aparecem como **`fixed`** enquanto o
  `app/package-lock.json` da `main` ainda tem 3.15.0/4.3.0/3.3.16 — versões dentro do range das
  advisories. E os dois GHSA de `image-size` **nunca geraram alerta nenhum**. Ou seja: a tela de
  alertas mostra `/app` limpo, o `npm audit` mostra 4 high. **O gate do `security.yml` é o sinal;
  a tela de alertas não é.**

## 2026-08-18 — Suíte de manuais de handover, fase 1 (PR #117)

Objetivo do trabalho: se o Gustavo parar, quem assumir opera, entende e altera o sistema só
com os documentos. Onze manuais planejados; esta fase entregou a ferramenta e quatro deles.

`docs/gerar_manuais.py` converte fonte Markdown em `.docx` no padrão dos dois manuais legados
(capa, campo de sumário do Word, `Heading 1/2/3` numerados, tabelas, código, callouts). 44
testes. **Falha barulhento** em front-matter incompleto, tabela com colunas inconsistentes,
bloco de código não fechado, título que pula nível e referência cruzada para manual
inexistente — e valida ANTES de escrever, para não deixar `.docx` corrompido em disco.

Manuais entregues: `01-ambiente-dev.md` (do clone ao primeiro PR), `06-portal-web.md`,
`07-banco-de-dados.md`, `11-fluxo-ci.md`. Fontes em `docs/`, `.docx` em `docs/dist/`, ambos
versionados. `docs/` saiu do `.gitignore` (só `docs/superpowers/` continua fora) — a DPIA da
LGPD e o runbook de deploy estavam sem backup nenhum fora da máquina local.

**Cinco defeitos do gerador, todos da mesma família: degradar em silêncio.** Separador de
tabela espaçado (`| --- | --- |`) não era reconhecido e a tabela virava um parágrafo com os
pipes colados; título que pulava nível gerava numeração `1.0.1`; pipe escapado cortava a
célula; callout quebrado em várias linhas virava um callout por linha; `**negrito com `código`
dentro**` imprimia as crases. Os três últimos **já estavam nos `.docx` entregues** e só
apareceram porque alguém abriu o arquivo gerado, não a fonte.

O `.docx` passou a ser determinístico (timestamps do zip fixos): antes, regerar sem mudar nada
produzia bytes diferentes, o que com onze manuais viraria ruído permanente no `git status`.
`docs/**` entrou nos gatilhos do `tests.yml` com um passo `pytest docs/`, e `python-docx` foi
declarado em `requirements-dev.txt` — ele não estava em requirements nenhum.

**Verificar cada comando na máquina real expôs onze pontos em que o README afirmava o que o
código não faz.** Os três piores: a URL da API do portal mora em `portal/js/env.js` e não num
`<script>` inline no `index.html` (que a própria CSP sem `unsafe-inline` proibiria);
`VITE_API_URL` não era lida por código nenhum; e `criar_admin.py` usa
`load_dotenv(override=True)`, então o comando com variáveis inline do README nunca funcionou.

Dois defeitos de produção foram achados ao documentar o banco e estão em [[bugs.md]], seção
"Bugs de produção ABERTOS": o `CASCADE` de professor que apaga histórico de presença, e a
exclusão de aluno travada pelo consentimento (o caminho do direito ao esquecimento).

Fica para as fases 2 e 3: VM Oracle, DNS/TLS, AWS, App Mobile, Contas e Segredos, Câmera e
LGPD. E um buraco de inventário que o review final encontrou: **a API/backend não tem manual
em nenhum dos onze planejados**, sendo o componente que mais se altera no repositório.

## 2026-08-19 — Swagger da API documentado, etapa A (PR #118)

Decisão: em vez de um manual Word da API, melhorar o `/docs`. Documentação de rota que mora
junto do código é a única que não envelhece sozinha.

Estado antes: 68 rotas sem `summary`, 52 sem descrição, as 2 rotas de `public.py` sem tag
(caíam no grupo "default"), e o app só com `title="SCPI API"`. O Swagger mostrava caminho e
parâmetros de entrada, e quase nada sobre o que volta.

Agora: 69 operações com `summary` e descrição, 9 tags descritas, e uma `description` de app
que explica o que o Swagger não tinha como mostrar — autenticação por cookie `HttpOnly` (não
há header `Authorization`), `X-Requested-With` exigido em mutação, isenção de CSRF em
login/refresh, `error_code` nas respostas de erro, rate limit e lockout.

`BackEnd/tests/test_openapi_documentado.py` é o guarda: reprova rota sem summary, sem
descrição ou sem tag, tag sem descrição em `openapi_tags`, schema que não gera, e marcador de
pendência esquecido. **Armadilha do guarda**, aprendida na prática: buscar "todo" em minúsculas
dá falso positivo em português ("todo" = "inteiro") e obriga a reescrever frase correta — só
marcador MAIÚSCULO (`TODO`, `FIXME`, `TBD`) e frases inequívocas de rascunho.

`response_model` NÃO entrou: ele filtra o payload e pode sumir com campo que portal ou app
consomem, em silêncio. É a etapa B, rota a rota, com verificação contra os consumidores.

Achados de código que a documentação revelou, todos registrados nas próprias docstrings:
- `DELETE /admin/turmas/{id}` apaga chamadas e presenças da turma via CASCADE, **pela API**, e
  não valida existência (id inexistente devolve sucesso). Mesmo padrão em
  `DELETE /admin/horarios/{id}`. É o terceiro caso da família CASCADE — ver [[bugs.md]].
- `relatorios.py`: `frequencia_baixa` filtra em Python DEPOIS do `LIMIT` do SQL, então com
  `limit` pequeno o resultado é "as de baixa frequência dentro das N mais recentes". Inofensivo
  só porque o portal manda o teto de 2000.
- `POST /auth/register` e `/auth/register-aluno-com-face` continuam registradas e desabilitadas.
- `GET /admin/alunos` não valida teto de `limit`: acima de 100 é reduzido em silêncio.
- Warning `Duplicate Operation ID health_health_get`: `/health` serve GET e HEAD no mesmo
  `api_route`, e ID duplicado quebra gerador de cliente OpenAPI. Não corrigido.

