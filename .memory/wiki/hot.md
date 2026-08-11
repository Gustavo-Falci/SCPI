# Hot Cache

*Contexto imediato. Atualizar ao fim de toda sessão.*

**Última atualização: 2026-08-06.**

## 🔴 Aberto e grave: liveness furado em produção (2026-08-06)

Celular exibindo **foto de aluno** na frente da câmera da sala **registra presença**, pelo
caminho normal da chamada. `texture_max=0.854` contra limiar `0.08` (passou por 10,7×) e
`magnitude=2.98` contra `pose_std_min=2.0` — **os dois gates falham no mesmo ataque**, então
`ENABLE_TEXTURE=0` não é mitigação.

A medição de replay que a branch `feat/validacao-replay-video` existia para produzir deu
`R=0.0017 < V=0.638` → **SOBREPOSTO**: não existe valor de `TEXTURE_LIVENESS_MIN` que separe.
Não mexer no limiar.

**Correção parcial já empurrada:** branch `fix/piso-tamanho-rosto-textura` (2 commits, PR
aberto, **não mergeada**), **3 commits, todos empurrados**. Abaixo de `TEXTURE_FACE_MIN_PX` a
textura devolve `None` ("não sei") e o fail-closed que já existia manda para PENDENTE. O 3º
commit faz o log imprimir `rostos_px` / `rosto_menor` / `abaixo_do_piso` — é o instrumento sem o
qual não dá para calibrar o piso, e é ele que já está gerando o dado da retomada.

**⚠️ Duas conclusões minhas foram falsificadas pelo log de produção no mesmo dia.** Os números
reais da porta estão em [[biometria-camera.md]] — leia a seção "Números REAIS" antes de
qualquer decisão:

- rosto real na porta é de **60–75px**, não 150–300px como a spec assumiu. O piso teve que cair
  de 80 para **50**, senão a pessoa real não passa. A porta está na faixa **marginal** do modelo.
- vídeo passou com rosto de **79–91px** (`texture_max=0.2802`), dentro da faixa que eu tinha
  afirmado ser segura.

**Causa raiz do rosto real pontuar baixo: o modelo mede NITIDEZ, não vida** (ρ=+0.651 com
variância do laplaciano; nítido 702 contra borrado 91). Borrão de movimento de quem passa pela
porta derruba o score. **Isso não tem conserto por parâmetro** — é exposição/obturador/luz.

Estado dos envs na máquina do Gustavo neste momento: `TEXTURE_FACE_MIN_PX=50`,
`TEXTURE_LIVENESS_MIN=0.22`, `LIVENESS_POSE_STD_MIN=4.0` (esta última não faz nada com
`ENABLE_TEXTURE=1` — pose é advisory).

**Não considerar fechado.** O ataque de vídeo ainda registra presença.

Decisão pendente com o Gustavo: o que fazer no interino (supervisão do professor / camera-sala
deixar de auto-registrar / aceitar e divulgar).

## Estado atual

Backlog de código da análise de 2026-07-31 está **zerado**. Segurança (A1–A6), performance
(P1/P3/P4/P5) e UX inteira fecharam entre 2026-08-01 e 2026-08-04, ~20 PRs em produção.
Suíte com 722 testes verdes e zero warnings — mas `-W error` **não** está configurado no CI
(`tests.yml` roda `python -m pytest tests -v` puro). O zero-warnings é disciplina, não gate.

Fechado em 2026-08-05: smoke test do app em device Android (as 12 telas da PR #100, sem
loop de render), correção do `.env` local que apontava para `scpi_db`/`postgres`, e remoção
do pin de `cryptography` (mergeado e em prod).

Em aberto desde 2026-08-05: branch `feat/validacao-replay-video` empurrada, **sem PR ainda**.
Instrumenta `_validar_liveness.py` para medir replay de vídeo. Detalhe em [[biometria-camera.md]].

## Próximos passos

- [ ] **RETOMAR AQUI: coletar 20 bursts do log da porta.** Não precisa da ferramenta — o log
      novo já traz `texture_max` + tamanhos por burst, no caminho real. ~10 passagens de pessoa
      real **variadas** (rápido, devagar, de perfil, contra a luz — a variação é o ponto, porque
      a causa raiz é nitidez) e ~10 do vídeo (variando distância e brilho). Com isso dá para
      responder: existe limiar que separa? com que folga? quanto custa em falso-negativo?
      Indício animador de n=1: real **0.7537** contra vídeo **0.2802**, fator 2,7× — um limiar
      em ~0.45 separaria esse par. **Mas duas linhas de log não sustentam decisão** — foi
      confiar em amostra pequena que produziu os dois erros do dia.
      Se as distribuições se cruzarem, está respondido que parâmetro nenhum fecha, e vai para
      camada B com dado da porta.
- [ ] **Flag `--piso` em `_validar_liveness.py`** — Task 4 do mesmo plano, BLOQUEADA até o fix
      mergear (importa `rosto_avaliavel`, que só passa a existir com ele). Vai para a
      `feat/validacao-replay-video`.
- [ ] **Camada B anti-replay** (bezel por Canny+Hough, moiré por FFT) — fecha o tablet colado
      na câmera, que o piso não cobre. Sonda de 2026-08-06 mostrou sinal forte (mediana de
      linhas longas: `real` 0, `tela` 2, `video` 1) **mas vetou 2 de 5 bursts reais**,
      tropeçando em batente de porta e prateleira. O difícil não é achar o bezel, é não
      confundir com parede — os discriminadores são quadrilátero FECHADO envolvendo o rosto,
      razão de aspecto de aparelho, e **co-movimento com o rosto ao longo do burst** (moldura
      acompanha, parede fica parada). Precisa da matriz refeita antes: calibrar contra 17
      bursts de um corredor de apartamento é overfitar num batente. Falta a spec.
- [ ] **Refazer a matriz na máquina da sala** — pré-requisito da camada B. A coleta de
      2026-08-06 rodou em casa e sem `LIVENESS_COND` (17 bursts em `sem_cond`), então não diz
      QUAL distância/aparelho quebra. 12 células, ≥6 bursts cada, **incluindo tablet, que nunca
      foi coletado**. Runbook em `docs/superpowers/plans/2026-08-05-validacao-replay-video.md`.
- [ ] **Gate da câmera da lousa** — ela ainda não existe em produção, mas quando existir o
      modelo de textura **não a atende** (rosto de 20–55px, zona de colapso). Precisa de gate
      geométrico, spec própria. Desenhar antes de subir a câmera, não depois.
- [ ] **Investigar rosto real rejeitado**: um burst real com rosto de 136–161px pontuou
      0.0017 (contraluz estourado) — em produção vira PENDENTE e o aluno não registra
      presença. Problema de disponibilidade, separado do spoof.
- [ ] **Medir `pg_stat_user_indexes.idx_scan` depois de uma aula real** — única verificação
      ainda aberta; confirma que os 6 índices do P3 estão sendo usados. SQL pronto em
      `ops/sql/verificar_indices_p3.sql`, para rodar no DBeaver.
- [ ] GitHub Settings → General → Pull Requests → **Automatically delete head branches**.
- [ ] Placeholders do `portal/privacy.html`, seções 1 e 2 (instituição, CNPJ, endereço,
      e-mail, 3 campos do DPO) — precisa dos dados, não de código. Ver [[lgpd.md]].
- [ ] **SHA-1 do Play App Signing** na chave Firebase ANTES de publicar na Play Store,
      senão push quebra em prod. Ver [[app-mobile.md]].
- [ ] Validar em campo o warning `Sala X com 2 chamadas abertas hoje (candidatas=[...])`.
- [ ] Na VM: criar `/etc/scpi-receipts.env` e instalar os units versionados de
      `ops/receipts/` — hoje a VM roda a versão feita à mão. Ver [[ops.md]].

## Pulados por decisão — não repropor

- **Sweep do `DB_INDISPONIVEL`**: precisa de decisão de escopo antes de virar branch.
  Critério útil: "o chamador toma decisão diferente se for banco fora?". Ver [[bugs.md]].
- **jest no app**: infra nova, complicada pelo Expo SDK gerenciar os pacotes; entraria via
  `jest-expo`.
- **Teste de integração do `camera_token.py`**: dispensado em 2026-08-05.
- **MFA/TOTP para Admin**: descartado pela equipe. Ver [[decisions.md]].
- **Rotacionar o check do healthchecks de receipts**: decidido não rotacionar em 2026-08-03.

## Bloqueado em decisão dos sócios

P2 (custo AWS ~US$125/aula/sala), multi-tenancy, staging/rollback, LGPD comercial e
alternativa não-biométrica de presença. Detalhe em [[decisions.md]].
