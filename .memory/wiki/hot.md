# Hot Cache

*Contexto imediato. Atualizar ao fim de toda sessão.*

**Última atualização: 2026-08-20.**

## ✅ Liveness: o bypass foi FECHADO — mas com um teste faltando

**Tudo mergeado na `main`.** PR #112 (veto anti-replay por região emissiva + log de tamanho de
rosto) e PR #113 (ferramenta de medição). Nenhuma branch de liveness em aberto; a única branch
remota viva é a do Dependabot (#111).

**O ataque:** celular exibindo foto/vídeo de aluno registrava presença pelo caminho normal da
chamada. `texture_max=0.854` contra limiar `0.08` **e** `magnitude=2.98` contra
`pose_std_min=2.0` — os dois gates falhavam no mesmo ataque, então `ENABLE_TEXTURE=0` nunca foi
mitigação. Textura sozinha deixava passar **7/7** bursts de vídeo na porta.

**A correção, em duas camadas:**

1. **Piso de tamanho** (`TEXTURE_FACE_MIN_PX`): abaixo dele a textura devolve `None` ("não sei")
   e o fail-closed que já existia manda para PENDENTE. Fecha o uso do modelo fora da faixa dele.
2. **Veto por região emissiva** (`scripts/deteccao_tela.py`): o rosto está dentro de uma área que
   emite luz? Rosto real não emite; rosto exibido está sempre dentro de uma tela acesa. Veta com
   precedência sobre a textura, exige ≥2 frames do burst, e é **fail-open** de propósito (erro no
   detector não veta — falta silenciosa de aluno é pior desfecho que ataque que passa).

Medido na porta: **vídeo 7/7 vetados (5/5 frames em todos), rosto real 0/6.** Confirmado em
produção: 3/3 bursts de ataque barrados, e um deles tinha `texture_max=0.2314` contra
`tex_limiar=0.22` — **teria registrado presença** sem o veto.

### ⚠️ O que ainda NÃO foi testado — não tratar como encerrado

- **O caso difícil do rosto real.** O `0/6` de falso positivo foi medido com rosto de
  **161–358px** (parado, perto da câmera). Em produção o aluno passa andando e aparece a
  **60–75px**. Se o veto acusar nessa condição, vira **falta silenciosa** de aluno legítimo.
  É o único risco sério que sobrou.
- **Porta com sol direto ou janela no quadro.** O limiar é percentil **da cena**, medido em uma
  iluminação só.
- **Tablet.** Está no threat model e nunca foi coletado.

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

A decisão de interino (supervisão do professor / camera-sala deixar de auto-registrar) **deixou
de ser necessária** — o ataque está barrado em produção desde 2026-08-16.

## Estado atual

Backlog de código da análise de 2026-07-31 está **zerado**. Segurança (A1–A6), performance
(P1/P3/P4/P5) e UX inteira fecharam entre 2026-08-01 e 2026-08-04, ~20 PRs em produção.
Suíte com 722 testes verdes e zero warnings — mas `-W error` **não** está configurado no CI
(`tests.yml` roda `python -m pytest tests -v` puro). O zero-warnings é disciplina, não gate.

Fechado em 2026-08-05: smoke test do app em device Android (as 12 telas da PR #100, sem
loop de render), correção do `.env` local que apontava para `scpi_db`/`postgres`, e remoção
do pin de `cryptography` (mergeado e em prod).

Em 2026-08-16 as branches de liveness foram todas mergeadas e apagadas (#112, #113), junto com
quatro antigas que já tinham PR mergeada (#106, #107, #108, #109). **Só `main` existe agora**,
com 761 testes verdes; a única remota viva é a do Dependabot (#111, aberta).

Em 2026-08-17 o **Security Scan** estava vermelho na `main` (desde o push de 2026-08-16 e na run
agendada) por 4 advisories high no `npm audit (app)`. Corrigido e **mergeado na `main`
pela PR #116** (`f7070c8e`): overrides de `js-yaml` para
3.15.1/4.3.1 (os pins antigos ficaram um patch curtos da advisory nova), `nanoid@3: 3.3.18` (a PR
do Dependabot para `/app` falhou), e os dois GHSA de `image-size` na ALLOWLIST do gate — não têm
versão corrigida publicada e vêm pinados pelo metro do Expo 55. Gate roda exit 0 local, `tsc` e
`expo lint` verdes. Detalhe em [[log.md]].

`.memory/wiki/` passou a ser **versionado na `main`** (o repo é PRIVADO — a crença de que era
público estava errada). Branch criada antes disso ignora `.memory/` e **apaga o wiki do disco no
checkout**; recuperar com `git archive main .memory/wiki | tar -x`.

Em 2026-08-18 entrou a **fase 1 da suíte de manuais de handover** (PR #117): o gerador
`docs/gerar_manuais.py` (44 testes, `.docx` determinístico, `pytest docs/` no CI) e quatro
manuais — ambiente de desenvolvimento, portal, banco e fluxo/CI. `docs/` deixou de ser
git-ignored; só `docs/superpowers/` continua fora. Detalhe em [[log.md]].

**Dois defeitos de produção apareceram ao documentar o banco** e estão em [[bugs.md]], seção
"Bugs de produção ABERTOS": o `ON DELETE CASCADE` de professor que apaga histórico de presença
num `DELETE` manual, e a exclusão de aluno bloqueada por `ConsentimentosLGPD` — que é o caminho
do direito ao esquecimento da LGPD. Nenhum dos dois foi corrigido: são migration e decisão de
política.

Em 2026-08-19 entrou o **Swagger da API, etapa A** (PR #118): 69 operações com summary e
descrição, 9 tags, metadados de autenticação e erro, mais o guarda
`tests/test_openapi_documentado.py`. `response_model` ficou para a etapa B. Detalhe em
[[log.md]].

Em 2026-08-20 entrou o **/docs protegido em produção** (PR #119, **em prod e validado**):
`/docs`, `/redoc` e `/openapi.json` deixaram de ser desligados em produção e passaram a exigir
sessão de **Admin**, respondendo **404** (não 401/403) para o resto — 404 não confirma que a
documentação existe no host. Gate em `core/docs_protegidos.py`, com dependency própria porque
`get_current_user` levanta 401 antes de a rota rodar. Junto entrou o fix do `Duplicate
Operation ID` do `/health` (GET e HEAD em decoradores separados; o HEAD que o UptimeRobot usa
saiu do schema). 785 testes verdes.

Validado em produção no mesmo dia: Admin logado no portal abre `api.scpi.me/docs` e vê o
Swagger; anônimo recebe 404 nas três rotas. **Nenhuma config de servidor mudou** — nginx é só
proxy (o 404 vinha do FastAPI, com `{"detail":"Not Found"}`), a CSP relaxada de docs já saía em
produção pelo middleware, e o gate reusa o `ENVIRONMENT=production` que já estava na VM.
Detalhe em [[log.md]].

**Atenção ao subir a API local:** o lifespan roda `_migrations.run_all()` (`api.py:116`) e o
`.env` da raiz aponta `DB_HOST=168.138.134.208` — **produção**. `uvicorn api:app` na máquina do
Gustavo executa migrations contra o banco de produção. Para só ler o Swagger, gerar o
`openapi.json` via `app.openapi()` sem subir servidor.

O `/docs` ganhou **tema escuro** (PRs #120, #121 e `75b3bb46`, em prod). O escuro vem do
**dark mode nativo do Swagger UI 5** — 180 regras `html.dark-mode` no CSS base, ligadas pela
classe que `core/docs_protegidos.py` injeta no `<html>`. `static/swagger-tema-escuro.css` é só
a camada de marca (paleta do portal + accent no Execute/Authorize + foco visível), com
`@import` do CSS base como primeira regra — `swagger_css_url` **substitui** a folha base, e
comentário antes do `@import` faz o navegador descartá-lo.

**Regra de manutenção do tema:** algo ilegível no /docs → primeiro checar se o nativo já cobre.
A primeira versão reimplementou à mão o que já existia e deixou a seção Schemas clara. Override
a mais é o que quebra. Os selos `1.0.0` e `OAS 3.1` ficam com o estilo original de propósito
(teste `test_tema_nao_repinta_os_badges_de_versao_do_cabecalho` trava isso).

⚠️ Depois de deploy que mexe no /docs, **Ctrl+F5**: o navegador guarda o HTML anterior, sem a
classe `dark-mode`, e a página parece não ter mudado.

## Próximos passos

- [ ] **RETOMAR AQUI: passar pela porta do jeito DIFÍCIL, com o veto ligado.** É o único risco
      sério que sobrou. Andando, na distância real de uso (rosto de ~60–75px, não colado na
      câmera), de perfil, contra a luz. No log, `tela_frames` tem que dar **0**. Se der ≥2 numa
      passagem legítima, o veto está tirando presença de aluno — nesse caso subir
      `TELA_PERCENTIL` ou `TELA_MIN_FRAMES` e remedir, não deixar rodando.
      Todas as medições do `0/6` de falso positivo foram com rosto de 161–358px, parado.
- [ ] **Testar o veto com sol na porta / janela no quadro.** O limiar é percentil DA CENA e foi
      medido em uma iluminação só. É o segundo caminho para falso positivo.
- [ ] **Tablet** — está no threat model e **nunca foi coletado**. É o aparelho capaz de exibir
      rosto grande, e com a moldura fora do quadro o veto emissivo fica cego (aí só a textura
      segura). Coletar `v` com tablet, perto e longe.
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
- [ ] **Swagger etapa B** — desenho já decidido em 2026-08-20, falta escrever: modelos de saída
      declarados por `responses={200: {"model": X}}`, **não** `response_model=` (este filtra o
      payload e sumiria com campo que portal ou app leem). Modelos em
      `BackEnd/schemas/respostas/`, um arquivo por router. Fidelidade garantida por helper de
      teste com `model_validate` e `extra="forbid"`, que pega campo documentado que não existe
      E campo devolvido que não está documentado. Escopo do lote 1: só as **~12 rotas** que já
      têm teste exercitando o handler (TestClient ou chamada direta) — o resto entra numa lista
      `SEM_MODELO_DE_SAIDA` no guarda, que só encolhe. Nada declarado sem prova.
- [ ] Apagar as branches mergeadas (`docs/manuais-handover`, `docs/swagger-api`,
      `feat/docs-protegido-prod`, `feat/swagger-tema-escuro`, `fix/swagger-badges-versao`,
      `feat/swagger-dark-mode-nativo`) e ligar "Automatically delete head branches" no
      GitHub. **PR aberta = branch congelada**: commitar em branch já mergeada fez o compare
      conflitar duas vezes em 2026-08-20 (#120, #121), porque o squash reescreve o commit.
- [ ] **Log de auditoria do `/docs`** (adiado, não decidido): o gate em
      `core/docs_protegidos.py` não registra nada — nem Admin que abriu, nem tentativa
      negada. `require_role` loga negativa em `audit_logger`; este caminho não. Cookie de
      Admin vazado abre o Swagger sem deixar rastro.
- [ ] **Manuais fase 2** — VM de Produção (Oracle) e Domínio/DNS/TLS (Namecheap). Dependem de
      comandos rodados na VM e de dados do painel. **Destravado**: há acesso SSH
      (`ubuntu@144.22.240.31:22`, chave em `%USERPROFILE%\.ssh\scpi_vm`) — ver [[ops.md]].
- [ ] **Manuais fase 3** — AWS, App Mobile/EAS/Firebase, Contas e Segredos, Câmera (instalação
      e calibração), LGPD. Dependem de entrevista de console.
- [ ] **Decidir sobre o manual da API/backend** — não está em nenhum dos onze planejados, e é o
      componente que mais se altera no repositório.
- [ ] Publicar a convenção de escrita da suíte em lugar versionado (hoje só existe na spec, que
      é git-ignored) — decide se os sete manuais restantes saem no mesmo formato.
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
