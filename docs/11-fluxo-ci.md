---
titulo: Manual de Fluxo de Trabalho e CI
subtitulo: Como uma mudança vai do editor até a produção
versao: "1.0"
data: 2026-08-18
---

## Introdução

### Para quem é este manual

Este manual descreve o caminho que uma mudança de código percorre no SCPI: como abrir uma
branch sem se machucar, o que os dois workflows do GitHub Actions verificam a cada push e a
cada Pull Request, o que o Dependabot atualiza sozinho e o que ele ignora de propósito, e o
que fazer quando o **Security Scan** fica vermelho.

Ele parte de quem já tem o ambiente montado — clonar, instalar e subir os quatro componentes
está no Manual de Ambiente de Desenvolvimento — e termina em como uma mudança chega à `main`
pronta para o deploy manual, descrito no Manual da VM de Produção (ainda não escrito).

### Como ler

Os capítulos seguem a ordem cronológica de uma mudança: branch, commits, Pull Request, o que
os workflows verificam, o que o Dependabot propõe sozinho, e o que fazer quando alguma coisa
fica vermelha. Depois da primeira leitura, os capítulos de Problemas conhecidos e Referência
rápida são o que você vai reabrir.

Os comandos deste manual rodam em shell POSIX (bash), porque é o que os workflows do GitHub
Actions usam internamente e o que reproduz o comportamento deles com mais fidelidade. Quando
um comando só faz sentido no PowerShell, o texto avisa.

### O que não está aqui

- **Montagem do ambiente local** — clonar, `.env`, banco, subir API/portal/app — está no
  Manual de Ambiente de Desenvolvimento. Este manual assume esse trabalho pronto.
- **A VM de produção, o deploy e o systemd** — estão no Manual da VM de Produção (ainda não
  escrito). Os workflows deste manual **não fazem deploy**: eles só travam ou liberam merge.
  Quem publica em produção é o Gustavo, à mão, com acesso à VM — o caminho desse acesso será
  documentado no Manual da VM de Produção.
- **Contas de terceiros e a origem das credenciais** de CI (não há nenhuma neste projeto além
  do `GITHUB_TOKEN` automático) estão fora do escopo — os dois workflows deste manual não
  usam segredo nenhum de conta externa.

> **Atenção:** nenhum valor de segredo aparece neste manual. Onde um segredo é citado — o
> `SECRET_KEY` dummy do CI, por exemplo — o texto usa o valor exatamente como ele está no
> repositório, marcado como fake pelo próprio comentário do arquivo.

## Ciclo de uma mudança

### Criar a branch

Antes de criar, veja o que já existe:

```bash
git branch
```

Crie a sua branch **sempre** com `--no-track`, a partir de `origin/main`:

```bash
git checkout -b feat/minha-funcionalidade --no-track origin/main
```

> **Atenção:** nunca omita o `--no-track`. Sem ele, o upstream da branch vira `origin/main`, e
> um `git push` sem argumentos empurra o commit **direto para a `main`**, contornando Pull
> Request, revisão e a política de squash. Foi exatamente o que aconteceu em 2026-07-31: a
> branch `chore/limpeza-pos-chamada-explicita` foi criada sem `--no-track`, e o commit
> `d5149ae1` foi parar direto na `main`. Não foi revertido — reescrever histórico já publicado
> seria pior que o incidente em si.

Confira a linha que o Git imprime ao criar a branch. Se ela disser
`set up to track 'origin/main'`, o `--no-track` não pegou — corrija antes de commitar
qualquer coisa.

### Commits

O projeto usa Conventional Commits, em português:

| Prefixo | Quando usar |
|---|---|
| `feat:` | Funcionalidade nova |
| `fix:` | Correção de defeito |
| `refactor:` | Mudança de estrutura sem mudança de comportamento |
| `docs:` | Documentação, incluindo os manuais desta suíte |
| `chore:` | Manutenção, dependências, configuração |
| `test:` | Testes, sem mudança de código de produção |

> **Importante:** no fluxo atual do projeto, quem executa `git commit`, `git push` e abre o
> Pull Request é o Gustavo, dono do repositório. Um assistente automatizado que trabalha no
> código prepara a mudança e a mensagem de commit sugerida, mas não executa nenhum dos três
> comandos.

### Antes de abrir o Pull Request

Esta lista antecipa o que os workflows vão conferir — rodá-la localmente é mais rápido do que
esperar o CI:

- Suíte do BackEnd verde: `python -m pytest tests -v` dentro de `BackEnd/`.
- Se mexeu em classe Tailwind: `npm run build` dentro de `portal/`, com o CSS resultante
  commitado junto.
- Se mexeu no app: `npx tsc --noEmit` e `npm run lint` dentro de `app/`, ambos sem erro.
- Nenhum segredo no diff. O `.env` está no `.gitignore`, mas uma chave colada em código ou em
  teste passa por ele sem esbarrar em nada — é o Gitleaks, no CI, que pega isso.

### Abrir o Pull Request

Abra o Pull Request contra `main`, descrevendo o que muda e por quê. Não referencie por
caminho os artefatos de planejamento em `docs/superpowers/`: são artefatos locais de trabalho,
não versionados, e não existem para quem lê o Pull Request depois. Referencie pelo conteúdo da
mudança, não pelo processo que a gerou.

### Squash merge

Os Pull Requests são integrados por **squash merge**: a branch inteira entra na `main` como um
único commit novo, e a branch de origem perde parentesco com a `main` — nenhum SHA dela
sobrevive.

> **Atenção:** depois que um Pull Request é mergeado, não acrescente commits àquela branch. O
> Pull Request seguinte, aberto a partir dela, conflita em **todos** os arquivos por história
> divergente — sem conflito real de conteúdo. Foi o que aconteceu na PR #57, em 2026-07-20.

Se já houver commits novos numa branch mergeada, a saída sem reescrever histórico é criar uma
branch nova a partir de `origin/main` e trazer só o que falta:

```bash
git checkout -b nova origin/main
git cherry-pick <sha-do-commit-novo>
```

> **Pegadinha:** para saber se um commit ficou de fora da `main`, comparar SHA **não serve** —
> o squash reescreve tudo e nenhum SHA da branch aparece na `main`. Confira pelo conteúdo:
> `git show origin/main:<arquivo>` e procure a mudança.

### Depois do merge

O procedimento correto é apagar a branch mergeada e, para o próximo assunto, criar outra a
partir de `origin/main` — nunca continuar cometendo na antiga.

> **Importante:** a `main` **não é protegida** e falha de CI não bloqueia merge. Nada no
> GitHub impede um Pull Request vermelho de ser mergeado. A disciplina de rodar os testes
> antes de abrir o Pull Request, descrita acima, é o que substitui essa proteção — não a
> configuração do repositório.

## Os workflows um a um

O SCPI tem dois workflows do GitHub Actions, ambos em `.github/workflows/`: `tests.yml` e
`security.yml`. Os dois rodam contra `push` em `main` e contra Pull Request; `security.yml`
também roda numa agenda semanal.

### Quando cada um dispara

| Workflow | `push` em `main` | Pull Request | Agenda |
|---|---|---|---|
| `tests.yml` | Sim, se o diff tocar `BackEnd/**`, `portal/**`, `app/**` ou o próprio arquivo do workflow | Mesma condição de `paths` | Não tem |
| `security.yml` | Sempre | Sempre | Toda segunda 06:00 UTC (03:00 América/São Paulo) |

> **Importante:** `portal/**` está nos `paths` do `tests.yml` por um motivo específico:
> `test_portal_csp_sem_inline_handlers.py` mora em `BackEnd/tests`, mas lê arquivos do portal.
> Sem essa entrada, uma PR que só mexesse no portal — justamente o tipo de PR capaz de
> reintroduzir um `onclick=` inline — não dispararia esse guarda. `app/**` entra no `tests.yml`
> pelo job `frontend`, que não tem suíte própria e depende do `tsc`/`eslint` como única rede.

### `tests.yml` — pytest (BackEnd)

Roda a suíte inteira do backend em Python 3.12, contra um `postgres:16` de serviço descartável
(usuário, senha e banco `scpi_test`), com `SCPI_RUN_DB_TESTS=1` — os testes de integração que
ficam pulados em máquina local rodam aqui de verdade. `SECRET_KEY` e `SCPI_EXPORT_HMAC_KEY` são
valores dummy fixos no workflow, marcados como fake pelo próprio comentário ao lado.

Reproduzir localmente, dentro de `BackEnd/`:

```bash
python -m pytest tests -v
```

Sem `SCPI_RUN_DB_TESTS=1`, os testes de integração ficam pulados — é o comportamento normal
numa máquina de dev, cujo `.env` aponta para o banco de produção.

> **Atenção:** nunca defina `SCPI_RUN_DB_TESTS=1` numa máquina de desenvolvimento cujo
> `DB_HOST` aponte para produção. As fixtures de integração executam `TRUNCATE`. O lugar certo
> desse gate ligado é o CI, contra o `postgres:16` descartável.

### `tests.yml` — tsc + eslint (app)

Não existe suíte de testes automatizados para o app (sem Jest — os pacotes são gerenciados
pelo Expo SDK, e adicionar Jest exigiria a infraestrutura de `jest-expo`). O `tsc` e o
`eslint`, com `--max-warnings 0`, são a única rede deste job.

Reproduzir localmente, dentro de `app/`:

```bash
npx tsc --noEmit
npm run lint
```

O `--max-warnings 0` mora no script `lint` do `package.json`, para o CI e a máquina do dev
cobrarem exatamente a mesma coisa.

> **Importante:** este job roda em **qualquer** PR que toque `BackEnd/`, `portal/` ou `app/` —
> os `paths` do workflow são a união dos três alvos, e o filtro é por workflow inteiro, não por
> job individual. Uma PR que só mexe no backend também dispara `tsc`/`eslint`, custando cerca
> de um minuto de runner a mais. É uma troca deliberada: separar isso exigiria um job de
> detecção de mudanças como o que `security.yml` já tem, complexidade que não se paga num
> workflow deste tamanho.

### `tests.yml` — portal css (build atualizado)

O Tailwind do portal é compilado pelo CLI e o resultado, `portal/css/tailwind.css`, é
**versionado** no repositório — a VM de produção não roda Node, então não há build no deploy.
O preço é o arquivo poder ficar defasado da fonte: quem adiciona uma classe e esquece o
`npm run build` sobe elemento sem estilo, calado. Este job recompila do zero e falha se o
resultado divergir do que está commitado.

Reproduzir localmente, dentro de `portal/`:

```bash
npm run build
```

E, a partir da raiz, confirmar que nada mudou:

```bash
git diff --stat -- portal/css/tailwind.css
```

Saída vazia é sucesso. Qualquer linha nela é o mesmo sinal que faria o job falhar no CI —
commite o CSS recompilado junto da mudança de classe.

### `security.yml` — o job `changes`

Antes dos scanners, um job usa `dorny/paths-filter` para descobrir se o diff tocou `BackEnd/**`
(saída `backend`) ou `app/**` (saída `mobile`). Bandit e pip-audit checam `backend`; o npm
audit do app checa `mobile`. Essa condição só filtra em Pull Request — `push` em `main` e a
run agendada sempre rodam todos os jobs, independente do que mudou.

> **Pegadinha:** o `npm-audit-mobile` só roda em PR que toca `app/**`. Uma advisory nova numa
> dependência do app fica invisível em toda PR que não mexe em `app/` e só aparece quando
> alguém finalmente faz `push` em `main` — foi o que deixou a `main` vermelha de 2026-07-21 a
> 2026-07-23 sem nenhuma PR reprovada no caminho. Não existe correção estrutural para isso sem
> abrir mão do filtro; é a troca que o projeto fez conscientemente.

### `security.yml` — Bandit (SAST Python)

Varre a AST de `BackEnd/` em busca de padrões inseguros conhecidos, excluindo
`BackEnd/tests`, `BackEnd/__pycache__` e `BackEnd/logs`. O gate é `--severity-level high`
com `--confidence-level medium`: só falha o pipeline em achado de severidade alta com
confiança média ou maior.

Reproduzir localmente, dentro de `BackEnd/`, com `bandit==1.7.10` instalado:

```bash
python -m bandit -r . --exclude ./tests,./__pycache__,./logs --severity-level high --confidence-level medium
```

Na máquina de referência, saída atual:

```text
Test results:
	No issues identified.

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 8
		Medium: 9
		High: 0
```

### `security.yml` — pip-audit (SCA Python)

Audita `BackEnd/requirements.txt` contra o banco de CVEs conhecidos (PyPI Advisory Database).

Reproduzir localmente, dentro de `BackEnd/`, com `pip-audit==2.7.3` instalado:

```bash
pip-audit --requirement requirements.txt --strict --ignore-vuln PYSEC-2025-183
```

Na máquina de referência: `No known vulnerabilities found`.

Em `push` para `main`, o job também gera um SBOM em formato CycloneDX
(`pip-audit --format cyclonedx-json`) e sobe como artefato do run, com `continue-on-error: true`
— o gate de segurança é o `--strict` acima, o SBOM é inventário de conveniência, e o upload já
falhou uma vez por um problema efêmero do armazenamento de artefatos do GitHub sem nenhum CVE
novo envolvido, marcando o Security Scan inteiro como vermelho à toa.

### `security.yml` — Gitleaks (Secrets Scan)

Varre o código e o histórico do Git em busca de segredos. Roda **sempre**, sem gate do job
`changes` — segredo importa em qualquer área do repositório.

> **Atenção:** o Gitleaks é **assimétrico** entre execuções. O `push`/Pull Request faz
> checkout com `fetch-depth: 0`, mas o `gitleaks-action` sem `--all` só escaneia os commits
> novos daquele push. A run **agendada** de segunda-feira escaneia o histórico **completo**.
> Isso significa que uma run agendada pode falhar com a `main` limpa — um segredo antigo, já
> removido do arquivo atual mas ainda presente em algum commit velho, só aparece ali. Run de
> push verde **não prova** que a run agendada vai passar.

> **Pegadinha:** este workflow **não tem `workflow_dispatch`** — não dá para disparar a run
> manualmente pela CLI ou pela interface; `gh workflow run security.yml` falha com HTTP 422.
> Para forçar uma varredura completa fora da agenda, é preciso esperar a segunda-feira ou fazer
> um `push`/PR (que não escaneia o histórico completo, só os commits novos).

### `security.yml` — npm audit (app)

Audita as dependências de `app/` (Expo/React Native) via `npm audit --json`, filtrado por
`.github/scripts/npm-audit-gate.mjs` — ver o capítulo seguinte para o motivo do script e como
usar a allowlist dele.

Reproduzir localmente, dentro de `app/`, no Bash:

```bash
npm audit --json | node ../.github/scripts/npm-audit-gate.mjs
```

Na máquina de referência:

```text
Ignorada (risco aceito): GHSA-w3rx-r6r6-pgpr — image-size
Ignorada (risco aceito): GHSA-5p2g-fcmc-qvqq — image-size
Nenhuma vulnerabilidade high+ fora da allowlist (10 high / 0 critical no relatório, todas em cadeias já cobertas).
```

> **Atenção:** rode esse pipe pelo Bash, não pelo PowerShell. No PowerShell, o pipe entre dois
> executáveis insere um BOM na saída, e o gate morre com "Não foi possível parsear a saída do
> `npm audit --json`" — artefato do shell no Windows, não um bug do script. O CI roda em bash e
> não sofre disso.

### `security.yml` — notify-failure

Roda só quando a run **agendada** falha (`failure() && github.event_name == 'schedule'`), e
depende dos quatro jobs de scan. Abre uma issue nova com as labels `ci-failure` e `security`
— ou, se já houver uma issue aberta com a label `ci-failure`, comenta nela em vez de abrir
outra. Existe porque uma falha da run agendada não bloqueia merge nem aparece em nenhum lugar
que o time olhe no dia a dia por padrão: o Gitleaks já pegou uma chave do Firebase numa run
agendada e o achado ficou três dias sem ação antes desse job existir.

## Dependabot

`.github/dependabot.yml` mantém três ecossistemas, cada um com seu próprio agendamento e sua
própria lista de exceções.

| Ecossistema | Diretório | Frequência | Limite de PRs abertas | Labels |
|---|---|---|---|---|
| `pip` | `/BackEnd` | Semanal, segunda 06:00 (América/São Paulo) | 5 | `dependencies`, `security` |
| `npm` | `/app` | Semanal, segunda 06:00 (América/São Paulo) | 5 | `dependencies`, `mobile` |
| `github-actions` | `/` (raiz) | Mensal | 3 | `ci` |

Os dois primeiros agrupam atualizações de `minor`/`patch` num único Pull Request — grupo
`python-minor` no backend, `js-minor` no app — para não inundar a lista de PRs abertas com uma
por pacote.

### O que ele ignora, e por quê

Todo `ignore` do `dependabot.yml` existe porque uma atualização automática já causou um
problema real. Nenhum é estético.

#### Stack Expo

Todo o conjunto gerenciado pelo Expo SDK é ignorado: `expo`, `expo-*`, `@expo/*`, `react`,
`react-dom`, `react-native`, `react-native-*`, `@react-native-community/*`,
`@react-navigation/*`, `eslint`, `eslint-config-expo`, `typescript`, e as transitivas `uuid`,
`@babel/core` e `brace-expansion`.

O SDK do Expo fixa versões compatíveis entre si para todo esse conjunto; atualizar um pacote
sozinho com `npm install` desalinha do SDK. A atualização certa é sempre:

```bash
npx expo install --fix
```

> **Pegadinha:** a PR #34 do Dependabot já bumpou `@react-native-community/datetimepicker`
> para 9.1.0 enquanto o SDK 55 esperava 8.6.0 — exatamente o desalinhamento que o `ignore`
> existe para prevenir. `eslint` e `typescript` entram pela mesma razão: eslint 10 quebra o
> `eslint-config-expo@55` (API do plugin React removida) e TypeScript 6 desalinha do
> `expo/tsconfig.base`; os dois só sobem juntos, no upgrade de SDK.

`uuid` e `@babel/core` são transitivas do toolchain Metro/Expo: o Dependabot não consegue
bumpá-las isoladas (uma PR de security update falhou em `update_files` em 2026-07-23, porque
`uuid` exigiria pular de 7.0.3 para 14.0.1 — major fixado pelo pacote pai). O alerta de
segurança correspondente continua visível na aba Security do GitHub; o `ignore` só suprime o
Pull Request automático, não o alerta.

`brace-expansion` (`GHSA-mh99-v99m-4gvg`, DoS por expansão sem limite) continua ignorada:
o patch só existe a partir da 5.0.8, e `minimatch@3` — parte da toolchain Metro/ESLint — exige
a API callable da série 1.x, que a 5.x não expõe. Uma tentativa do Dependabot de corrigir isso
sozinho falhou em `update_files` em 2026-07-27, porque exigiria bumpar 33 pacotes de nível
superior de uma vez.

> **Atenção:** o comentário do `dependabot.yml` para essa entrada diz que o risco está
> "documentado na ALLOWLIST de `.github/scripts/npm-audit-gate.mjs`" — mas essa referência
> está desatualizada. A entrada `GHSA-mh99-v99m-4gvg` foi **removida** dessa `ALLOWLIST` em
> 2026-08-17 (PR #116): o gate já vinha avisando, por `::notice::`, que ela não aparecia mais
> na saída do `npm audit` (o override de versão que a corrigia já estava em vigor havia
> semanas). O que saiu da `ALLOWLIST` foi a exceção do **gate de auditoria do npm**, em
> `.github/scripts/npm-audit-gate.mjs` — outro arquivo, outro mecanismo. `brace-expansion`
> em si **continua** ignorada pelo Dependabot em `.github/dependabot.yml`; os dois arquivos não
> tratam da mesma coisa e é fácil confundir um com o outro.

#### Majors do OpenCV

```yaml
- dependency-name: "opencv-python"
  update-types:
    - "version-update:semver-major"
```

O motivo original desta exceção: o OpenCV 5 removeu o `CascadeClassifier` do pacote core
(foi para `opencv-contrib`), o que quebrava `BackEnd/scripts/reconhecimento_tempo_real.py` —
descoberto por um smoke test em 2026-07-07.

> **Importante:** esse motivo original **já não se aplica** ao script atual. O
> `reconhecimento_tempo_real.py` já migrou para `cv2.FaceDetectorYN.create(...)` — não há mais
> nenhuma chamada a `CascadeClassifier` no arquivo. O pin em `opencv-python` na linha 4.x
> **continua** em vigor mesmo assim; as fontes consultadas não deixam claro qual é o motivo
> atual para mantê-lo (o comentário do próprio `dependabot.yml` ainda descreve o motivo
> antigo, sem mencionar que a migração já ocorreu). Antes de propor remover este `ignore`,
> confirme com o Gustavo se falta algo além da migração do script — por exemplo, validar o
> `FaceDetectorYN` contra uma v5 de fato instalada, o que não tem teste automatizado, já que a
> máquina da câmera não entra no CI.

#### fastapi 0.136.3

```yaml
- dependency-name: "fastapi"
  update-types:
    - "version-update:semver-minor"
    - "version-update:semver-patch"
```

A versão `0.136.3` do fastapi é um release **malicioso** (`MAL-2026-4750`): injeta a
dependência `fastar` no extra `[standard]`. A PR #35 do Dependabot já re-subiu essa versão uma
vez, como se fosse um patch normal de `0.136.1` para `0.136.3`. O projeto fica travado em
`0.136.1`, o pin auditado — e a `0.137.1`, mais recente, ainda declara `fastar>=0.9.0` no
`[standard]`, ou seja, a cadeia **não foi saneada** upstream. O SCPI instala `fastapi` puro,
sem o extra `[standard]`, então `fastar` não é puxado de qualquer forma — mas o `ignore`
continua até o pacote malicioso sumir da árvore de dependências do próprio `fastapi`.

> **Atenção:** `pip-audit` **não pega** identificadores `MAL-*` (advisories de pacote
> malicioso, não de CVE). A única defesa aqui é o `ignore` do Dependabot somado ao pin exato no
> `requirements.txt` — não existe scanner automatizado neste pipeline capaz de detectar essa
> classe de problema.

Uma última exceção do ecossistema `pip`, `pydantic-core`, não é sobre um pacote perigoso: ele é
pinado a uma versão exata pelo próprio `pydantic` (`==2.46.4` para `pydantic 2.13.4`), e um PR
avulso do Dependabot quebraria a resolução de dependências. Ele sobe junto do `pydantic`,
nunca sozinho.

## Quando o Security Scan fica vermelho

### Procedimento geral

1. Abra a run que falhou e identifique **qual job** ficou vermelho — Bandit, pip-audit,
   Gitleaks ou npm audit têm causas e correções completamente diferentes.
2. Se for a run **agendada**, o job `notify-failure` já abriu ou comentou numa issue com a
   label `ci-failure` — comece por ela.
3. Corrija a causa raiz sempre que possível. Um `ignore`/allowlist é o último recurso, não o
   primeiro — o exemplo do Bandit B324 abaixo é o padrão a seguir: trocar o código, não
   silenciar o scanner.
4. Se a correção não for possível — sem patch publicado, sem versão compatível com o resto da
   árvore — documente a exceção **no arquivo certo**, com motivo e condição de saída. As quatro
   seções abaixo mostram onde cada scanner espera essa exceção.

### Bandit vermelho

Um achado de severidade alta e confiança média ou maior aparece na saída do job com o código
(`B###`) e o arquivo. O caminho preferido é corrigir o padrão no código, não suprimir.

Exemplo real do projeto: o Bandit acusava `B324` (uso de hash fraco) no SHA-1 usado para
checar senha comprometida via HIBP k-anonymity. A correção não foi ignorar o achado — foi
adicionar `usedforsecurity=False` à chamada de `hashlib.sha1`, em
`BackEnd/core/auth_utils.py`, porque esse SHA-1 não protege segredo nenhum (é o algoritmo que
a própria API do HIBP exige) e o parâmetro deixa isso explícito para o Bandit e para quem ler
o código depois.

Quando o achado é mesmo um falso positivo no código atual — não um padrão a corrigir — o
projeto usa `# nosec` no ponto exato, com o motivo na mesma linha ou na de cima. Não há
nenhuma ocorrência disso no BackEnd hoje: até agora, todo achado teve correção de código.

### pip-audit vermelho

Uma CVE nova numa dependência do `BackEnd/requirements.txt` falha o `--strict`. Primeiro,
tente resolver subindo a dependência — muitas vezes é só esperar o Dependabot ou rodar
`pip install -U <pacote>` e testar.

Quando não há correção aplicável — a vulnerabilidade é disputada pelo mantenedor, ou a
correção exigiria uma versão incompatível com o resto da árvore — adicione
`--ignore-vuln <ID>` ao comando `pip-audit` em `.github/workflows/security.yml`, com um
comentário explicando por quê. O padrão já em uso:

```yaml
# PYSEC-2025-183 (PyJWT): disputado pelo mantenedor — exige enforcement de comprimento
# mínimo de chave pela aplicação. core/auth_utils.py valida SECRET_KEY >= 32 caracteres
# no boot, satisfazendo a mitigação. Sem fix upstream.
run: pip-audit --requirement BackEnd/requirements.txt --strict --ignore-vuln PYSEC-2025-183
```

O que torna esse `--ignore-vuln` legítimo, e não apenas conveniente: a vulnerabilidade é
disputada pelo próprio mantenedor do pacote, e a mitigação que ela pede (comprimento mínimo de
chave) já existe no código, verificável em `core/auth_utils.py`.

### Gitleaks vermelho

Primeiro, decida se o segredo encontrado está **vivo**:

> **Atenção:** chave viva → **rotacione antes de qualquer outra coisa**. Chave morta →
> registre no `.gitleaksignore`. Nunca faça o segundo sem antes confirmar qual dos dois casos é
> este.

Para uma chave já rotacionada ou nunca real (chave morta), adicione uma linha ao
`.gitleaksignore` na raiz, no formato que o próprio arquivo documenta:

```text
<commit>:<arquivo>:<regra>:<linha>
```

Cada linha do `.gitleaksignore` do projeto hoje carrega o motivo em comentário acima dela —
siga o padrão, não deixe uma entrada sem explicação. Exemplo real, para uma chave do Firebase
que segue **ativa e no repositório de propósito** (é uma client key do Android, embarcada no
APK por design, mitigada por restrição no Google Cloud Console):

```text
# Chave de API Android do Firebase em app/google-services.json — ATIVA e no tree
# de propósito: é client key, embarcada no APK por design [...]
f65fb4072628d93ec47bbdd232508875223fc2e4:app/google-services.json:gcp-api-key:18
```

Para um falso positivo em **código atual** (não em histórico) — um valor que parece segredo
mas não é, como um dummy de CI ou um título de aplicação — use `# gitleaks:allow` inline, na
mesma linha do valor:

```python
SECRET_KEY: ci-dummy-secret-key-nao-e-segredo-0123456789abcdef # gitleaks:allow — dummy de CI, não é segredo
```

> **Pegadinha:** o `# gitleaks:allow` inline só livra o **commit atual** dessa linha. A run
> agendada, que varre o histórico completo, continua acusando os commits **antigos** da mesma
> linha, de antes do comentário existir. Esses commits antigos precisam de entrada própria no
> `.gitleaksignore` — é exatamente o padrão que duas das entradas do arquivo do projeto
> documentam: a primeira entrada (o falso positivo de `api.py:90`) e a sexta (o `SECRET_KEY`
> dummy do CI) têm cada uma sua linha, presa a um commit anterior ao comentário
> `gitleaks:allow` correspondente.

### npm audit vermelho

O `npm audit` nativo não tem equivalente ao `--ignore-vuln` do pip-audit: ou o comando bloqueia
tudo de severidade `high`+, ou nada. Por isso o projeto tem
`.github/scripts/npm-audit-gate.mjs`, que lê a saída de `npm audit --json`, mantém o bloqueio
em `high`+, e abre exceção só para os IDs GHSA listados no objeto `ALLOWLIST` do próprio
script.

Cada entrada da `ALLOWLIST` exige `pacote`, `motivo` e `remover_quando` — a condição que
destrava a remoção da exceção, não só o motivo de ela existir hoje:

```javascript
"GHSA-w3rx-r6r6-pgpr": {
  pacote: "image-size",
  motivo:
    "DoS por laço infinito no parser ICNS. SEM CORREÇÃO PUBLICADA: [...]",
  remover_quando:
    "image-size publicar 2.0.3+ E o metro do SDK do Expo em uso passar a " +
    "resolver essa versão (checar `npm ls image-size` em app/).",
},
```

Uma advisory nova de severidade `high`/`critical` que não estiver na `ALLOWLIST` falha o job
com a lista de pacotes bloqueantes na saída — corrija a dependência primeiro (`npm audit fix`,
upgrade manual, ou aguardar o Dependabot) antes de considerar adicionar à `ALLOWLIST`.

O script também avisa sozinho quando uma entrada da `ALLOWLIST` já não corresponde a nada na
árvore de dependências atual (`::notice::` no log) — é assim que a exceção de
`GHSA-mh99-v99m-4gvg` (`brace-expansion`) foi identificada como obsoleta e removida da
`ALLOWLIST` em 2026-08-17. O pacote `brace-expansion` em si segue ignorado, separadamente, no
`.github/dependabot.yml` — ver o capítulo anterior.

### Quando uma allowlist é legítima

O padrão comum às quatro exceções acima — `--ignore-vuln` do pip-audit, `.gitleaksignore`,
`# gitleaks:allow` e a `ALLOWLIST` do gate do npm audit — é o mesmo em todas: uma exceção só é
legítima quando tem **motivo verificável** (não "não deu tempo de olhar") e **condição de
saída** (o que precisa acontecer para a exceção deixar de existir), documentados no próprio
arquivo onde a exceção mora — nunca só numa mensagem de commit ou numa conversa. Toda exceção
hoje no repositório segue esse formato; é o critério para julgar se uma nova também deveria.

## Verificação

Estas são as provas de que o fluxo de CI está inteiro, reproduzidas localmente com o mesmo
comando que o workflow correspondente executa.

| Prova | Como conferir | Pasta | Resultado esperado |
|---|---|---|---|
| Suíte do BackEnd | `python -m pytest tests -v` | `BackEnd/` | 761 passando, 81 pulados |
| Tipos do app | `npx tsc --noEmit` | `app/` | Termina sem erro, sem saída |
| Lint do app | `npm run lint` | `app/` | Termina sem warning (gate em zero) |
| CSS do portal em dia | `npm run build` seguido de `git diff --stat -- portal/css/tailwind.css`, a partir da raiz | `portal/` | `git diff` sem saída |
| Bandit | `python -m bandit -r . --exclude ./tests,./__pycache__,./logs --severity-level high --confidence-level medium` | `BackEnd/` | `No issues identified` |
| pip-audit | `pip-audit --requirement requirements.txt --strict --ignore-vuln PYSEC-2025-183` | `BackEnd/` | `No known vulnerabilities found` |
| npm audit (app) | `npm audit --json` redirecionado para `node ../.github/scripts/npm-audit-gate.mjs`, pelo Bash | `app/` | Sai com código 0, listando as exceções ignoradas por nome |

> **Quando usar:** rode esta lista inteira antes de abrir um Pull Request que mexeu em mais de
> um componente, ou depois de qualquer atualização de dependência feita à mão (fora do
> Dependabot). É mais barato descobrir o job que vai falhar aqui do que esperar o CI.

## Problemas conhecidos

### Tabela de sintomas

| Sintoma | Causa | Solução |
|---|---|---|
| Commit foi parar direto na `main` | Branch criada sem `--no-track` | Recriar a branch com `--no-track origin/main`. Se já foi para a `main`, não reescreva histórico publicado |
| Pull Request novo conflita em todos os arquivos | Branch criada a partir de outra já mergeada por squash | Criar branch nova a partir de `origin/main` e usar `git cherry-pick` nos commits que faltam |
| `security.yml` falhou na run agendada, mas toda run de push/PR recente estava verde | Gitleaks agendado varre o histórico completo; push/PR só varre commits novos | Abrir a run e o achado; se for segredo morto, registrar no `.gitleaksignore`; se vivo, rotacionar primeiro |
| Advisory nova do app só apareceu depois do `push` em `main`, não em nenhuma PR | `npm-audit-mobile` só roda em PR que toca `app/**`; PRs de outras áreas não disparam o job | Corrigir a dependência e, se for exceção legítima, documentar na `ALLOWLIST` de `npm-audit-gate.mjs` |
| `gh workflow run security.yml` falha com HTTP 422 | O workflow não tem `workflow_dispatch` | Não há disparo manual; esperar a próxima segunda-feira, ou um push/PR (que não cobre o histórico completo) |
| Security Scan inteiro vermelho, mas nenhum CVE novo na saída do pip-audit | Falha efêmera do upload de artefato do SBOM (`Failed to FinalizeArtifact`) | Conferir se o passo vermelho é o `pip-audit --strict` (gate real) ou o `Upload SBOM artifact` (`continue-on-error: true`, mas ainda pode marcar a run) — reexecutar a run costuma bastar |
| Pipe de `npm audit --json` para o gate morre no PowerShell com "Não foi possível parsear a saída" | O pipe entre dois executáveis no PowerShell insere BOM na saída | Rodar o mesmo comando pelo Bash — é o que o CI usa |
| `pip-audit` local acusa `PYSEC-2025-183` mesmo com o `.env` correto | O comando local não incluiu `--ignore-vuln PYSEC-2025-183` | Reproduzir com a linha exata do workflow, incluindo a flag |
| Bandit acusa hash fraco (`B324`) num SHA-1 que não protege segredo | Padrão comum em integrações que exigem SHA-1 por contrato externo (como o HIBP) | Adicionar `usedforsecurity=False` na chamada, não suprimir com `# nosec` |
| PR abre e o `tsc`/`eslint` do app rodam mesmo sem nenhuma mudança em `app/` | `paths` do `tests.yml` é a união de `BackEnd/`, `portal/` e `app/`; o filtro é por workflow, não por job | Esperado — não é bug. Custa cerca de 1 minuto de runner |
| Pacote do Expo SDK desalinhou depois de um `npm install` manual | Atualização direta em vez de `expo install --fix` | `npx expo install --fix` dentro de `app/`; para o futuro, deixar o Dependabot ignorar (já está ignorando por padrão) |

### Quando a wiki diverge do README

O `README.md` tem uma seção de contribuição própria, com um comando que diverge do que este
manual e a wiki interna do projeto documentam:

- O `README.md` mostra `git checkout -b feat/minha-funcionalidade --no-track`, **sem**
  `origin/main` no final. A wiki interna (`.memory/wiki/fluxo-de-trabalho.md`) e o Manual de
  Ambiente de Desenvolvimento — a fonte já revisada da suíte — usam
  `--no-track origin/main`, explícito. O efeito de omitir o ponto de partida depende de qual
  branch está com checkout no momento, o que torna o comando do `README.md` frágil da mesma
  forma que o incidente de 2026-07-31 mostrou ser perigoso. Este manual segue a forma explícita.

## Referência rápida

### Comandos do dia a dia

| Ação | Comando | Pasta |
|---|---|---|
| Criar branch de trabalho | `git checkout -b <nome> --no-track origin/main` | Raiz |
| Ver branches existentes antes de criar uma nova | `git branch` | Raiz |
| Rodar a suíte do BackEnd (igual ao CI) | `python -m pytest tests -v` | `BackEnd/` |
| Checar tipos do app (igual ao CI) | `npx tsc --noEmit` | `app/` |
| Lint do app (igual ao CI) | `npm run lint` | `app/` |
| Recompilar o CSS do portal antes de commitar | `npm run build` | `portal/` |
| Conferir se o CSS commitado está em dia | `git diff --stat -- portal/css/tailwind.css` | Raiz |
| Bandit local (igual ao CI) | `python -m bandit -r . --exclude ./tests,./__pycache__,./logs --severity-level high --confidence-level medium` | `BackEnd/` |
| pip-audit local (igual ao CI) | `pip-audit --requirement requirements.txt --strict --ignore-vuln PYSEC-2025-183` | `BackEnd/` |
| npm audit do app com o gate (igual ao CI, rodar no Bash) | `npm audit --json` redirecionado para `node ../.github/scripts/npm-audit-gate.mjs` | `app/` |
| Atualizar pacote gerenciado pelo Expo SDK | `npx expo install --fix` | `app/` |
| Confirmar se um commit ficou de fora da `main` após squash | `git show origin/main:<arquivo>` | Raiz |

### Mapa de segredos

Nenhum segredo real aparece neste manual, e o pipeline de CI deste projeto não usa credencial
de conta externa nenhuma além do `GITHUB_TOKEN` automático do próprio GitHub Actions.

| Valor | Onde mora | Natureza |
|---|---|---|
| `SECRET_KEY` do job `pytest (BackEnd)` | `.github/workflows/tests.yml` | Dummy fixo, marcado `# gitleaks:allow` no próprio arquivo — não é segredo |
| `SCPI_EXPORT_HMAC_KEY` do job `pytest (BackEnd)` | `.github/workflows/tests.yml` | Dummy fixo (`00...0`) — não é segredo |
| Credenciais do `postgres:16` de serviço | `.github/workflows/tests.yml` | `scpi_test`/`scpi_test`, descartadas ao fim de cada run |
| `GITHUB_TOKEN` | Injetado automaticamente pelo GitHub Actions | Usado por `gitleaks-action` e por `notify-failure` (abrir/comentar issue); nunca aparece em texto no repositório |
| Chave de API Android do Firebase | `app/google-services.json` | Ativa e no repositório **de propósito** — client key embarcada no APK por design, restrita por SHA-1 no Google Cloud Console; documentada no `.gitleaksignore` |

> **Atenção:** o `.gitleaksignore` registra segredos **mortos** ou falsos positivos — nunca é
> onde uma chave viva deveria ficar. Uma chave viva encontrada pelo Gitleaks se resolve
> rotacionando, não documentando.

### Arquivos-fonte deste manual

| Arquivo | O que fixa |
|---|---|
| `.github/workflows/tests.yml` | Os três jobs de `tests.yml`, seus `paths` de disparo e as versões de Python/Node |
| `.github/workflows/security.yml` | Os seis jobs de `security.yml` (`changes`, Bandit, pip-audit, Gitleaks, npm audit e `notify-failure`) e a agenda semanal |
| `.github/dependabot.yml` | Os três ecossistemas, o agendamento de cada um e toda exceção de `ignore` com o motivo |
| `.github/scripts/npm-audit-gate.mjs` | O gate do npm audit, a `ALLOWLIST` e o formato exigido de cada entrada |
| `.gitleaksignore` | O formato de fingerprint aceito e as exceções já registradas |
| `.memory/wiki/fluxo-de-trabalho.md` | As regras de branch, commit e squash merge, com as datas dos incidentes que as originaram |
| `.memory/wiki/seguranca.md` | O histórico da pipeline de segurança e a dívida de dependências aceita conscientemente |
| `.memory/wiki/bugs.md` | A assimetria do Gitleaks agendado e o efeito do `paths-filter` sobre o npm audit |
| `README.md` | Seção "Contribuição" e "CI e Análise Estática" — cotejadas com os arquivos acima |
