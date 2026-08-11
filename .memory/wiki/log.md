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
