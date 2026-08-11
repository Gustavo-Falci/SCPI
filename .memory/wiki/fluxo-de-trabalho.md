# Fluxo de Trabalho

Preferências do Gustavo, dev principal do SCPI. Trabalha em equipe (há sócios), comunica em
**português brasileiro**.

## Git — regras duras

### O Gustavo faz todos os commits

O assistente **não executa** `git commit`, `git add` de staging final, nem `git push`. Vale
para código, config, workflows, specs — tudo. Pode **sugerir** a mensagem de commit em texto,
e pode rodar `git status` / `git diff` para inspeção. Não rodar `gh pr create` sem pedido
explícito.

**Motivo:** ele prefere controle direto sobre o histórico — escolhe mensagem, granularidade e
momento.

*Exceção que não muda a regra:* em 2026-07-27, executando o hardening operacional via
subagentes, ele autorizou os agentes a commitarem **na branch de trabalho**, com o
squash-merge final ainda sendo dele. **Autorização por branch, não permanente.** Lição de
coordenação: ao delegar sob uma autorização dessas, repassar a exceção no prompt de cada
dispatch — um agente leu a regra, parou antes do commit e devolveu o trabalho staged
(comportamento correto dele, custo de uma rodada extra por omissão no prompt).

### Branch sempre com `--no-track`

```bash
git checkout -b <nome> --no-track origin/main
```

**Nunca omitir o `--no-track`.** Sem ele, o upstream da branch vira `origin/main` e um
`git push` simples empurra **direto para main**, burlando PR, revisão e a política de squash.
Aconteceu em 2026-07-31 (branch `chore/limpeza-pos-chamada-explicita`, commit `d5149ae` foi
direto para `main`). Não foi revertido — reescrever histórico publicado seria pior.

Conferir a linha que o git imprime: se disser `set up to track 'origin/main'`, corrigir antes
de commitar. Antes do `checkout -b`, rodar `git branch` — o Gustavo costuma ter adiantado a
criação.

### PRs usam squash merge

A branch de origem **perde parentesco** com `main`: o conteúdo entra como um commit novo e
único. **Depois de um merge, apagar a branch e criar outra a partir de `origin/main`.**

Se já houver commits novos numa branch mergeada:
`git checkout -b nova origin/main` + `git cherry-pick <commits novos>` resolve sem force-push.

Em 2026-07-20 a PR #57 tentou reaplicar commits já presentes em `main` e acusou conflito em
todos os arquivos — sem conflito real de conteúdo, só história divergente.

**Para saber SE um commit ficou de fora, comparar SHA não serve** — o squash reescreve tudo e
nenhum SHA da branch aparece em `main`. Conferir pelo conteúdo:
`git show origin/main:<arquivo>` e procurar a mudança.

### Docs de processo não são commitados

Specs e planos em `docs/superpowers/specs/` e `docs/superpowers/plans/` são artefatos de
trabalho **locais** — não sugerir commit e não referenciá-los por caminho na descrição de PR
(referenciar pelo conteúdo). `docs/` é git-ignored, exceto `SECURITY_RUNBOOK.md` e
`PORTAL_NGINX.md`. Outros docs (README, CHANGELOG, comentários) têm tratamento normal.

## Memória: manter os DOIS sistemas

Desde 2026-08-05 há duas memórias, e o Gustavo pediu explicitamente para manter **as duas**
atualizadas (foi perguntado se preferia consolidar numa só e respondeu "nos dois"):

1. **Memória do assistente** — `~/.claude/projects/C--Users-itconsol-Documents-SCPI/memory/`,
   arquivos individuais + um `MEMORY.md` de índice. É a que carrega automaticamente em toda
   sessão.
2. **Esta wiki** — `.memory/wiki/`, lida via `CLAUDE.md` → `AGENTS.md`. É a que outros
   agentes (Cursor, Copilot) e futuros devs encontram no repo.

**Regra:** fato novo entra nos dois, na mesma resposta. Se um for corrigido, corrigir o outro
junto — divergência silenciosa entre as duas é pior que não ter a segunda.

Fim de sessão: atualizar [[hot.md]] (estado + próximos passos) e acrescentar entrada datada em
[[log.md]] (append-only).

⚠️ **`npx memwiki update` sobrescreve `CLAUDE.md`, `AGENTS.md`, `.cursorrules` e
`.github/copilot-instructions.md` sem checar se existem.** Só rodar com o repo limpo. Os
arquivos desta wiki não são tocados por ele — só são escritos se não existirem.

## Ambiente de testes

- **Não subir Docker.** O Docker Desktop está instalado mas com o daemon parado, e subir
  banco descartável não é o fluxo dele.
- Validação contra banco real = **entregar o SQL pronto para o Gustavo rodar no DBeaver**.
  Ele já tem a conexão aberta e prefere rodar a query com os próprios olhos.
- Se o caso não der para testar no DBeaver, **pular e seguir** — não inventar outro caminho de
  infra.
- **`.env` local aponta para o `DB_HOST` de produção.** Ver o alerta sobre
  `SCPI_RUN_DB_TESTS` em [[patterns.md]].
- Deploy e SSH são executados por ele — não há chave SSH na máquina Windows.

## Fluxo de trabalho maior

Decisão dos sócios → brainstorming → writing-plans → execução (às vezes via
subagent-driven-development) → review → PR → squash-merge → deploy manual na VM →
validação em prod.

Trabalho grande costuma ser validado em três frentes: suíte de testes, review de spec +
review de qualidade, e **teste manual no device** feito por ele.
