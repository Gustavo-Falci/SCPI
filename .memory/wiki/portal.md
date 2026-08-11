# Portal Administrativo (`admin.scpi.me`)

## Stack

HTML/CSS/JS **vanilla**, sem build step de app — migrado de React + Vite. ES Modules nativos
do browser, servido por nginx com root em `/opt/scpi/portal`. API em `https://api.scpi.me`.

Desde 2026-08-03 (PR #103) o CSS é **Tailwind compilado pelo CLI e versionado no repo**
(`portal/css/tailwind.css`). Saíram o build de browser do Tailwind (~120 KB de JS que gerava
regras em runtime) e o `portal/js/tailwind-config.js`; a config agora é
`portal/tailwind.config.js` (CommonJS). Node é dependência **só de desenvolvimento** — ver o
porquê em [[decisions.md]].

**Regra: mexeu em classe → `npm run build` em `portal/` e commita o CSS junto.** O job
`portal css (build atualizado)` recompila e falha se o versionado divergir. O build é
determinístico entre Windows e o Linux do runner.

O `content` cobre `./index.html` e `./js/**/*.js`. **`privacy.html` fica fora de propósito**:
não usa Tailwind, e incluí-la faria o scanner extrair utilitários da prosa jurídica.

## Estrutura

```
portal/
├── index.html          # SPA shell (login + dashboard)
├── privacy.html        # política de privacidade (fora do Tailwind)
├── css/
│   ├── app.css         # animações, scrollbar, inputs, checkboxes, classes do CSP
│   └── tailwind.css    # compilado, versionado
├── tailwind.config.js
└── js/
    ├── config.js  env.js  icons.js  utils.js
    ├── api.js          # fetch wrapper (auth + refresh 401 automático)
    ├── auth.js         # sessão (só o perfil público em localStorage)
    ├── state.js        # estado global (filtros, cache, aba ativa)
    ├── toast.js  confirm.js  pagination.js  persist.js  modal.js  skeleton.js
    ├── boot-gate.js  boot-sidebar.js   # rodam no <head>, antes do main.js
    ├── registry.js     # registry compartilhado do FAB mobile
    ├── privacy-app-view.js
    ├── main.js         # entrypoint, router, sidebar, header
    └── tabs/           # turmas, horarios, professores, alunos, relatorios, rostos
```

### Scripts de boot (rodam antes do `main.js`)

Existem para evitar salto visual e travamento, e são **deliberadamente independentes** do
`main.js` — inclusive de uma versão dele em cache.

- **`boot-sidebar.js`** — aplica `sidebar-collapsed` no `<html>` **antes do primeiro paint**.
  Sem ele a sidebar pinta com 256px e salta para o rail meio segundo depois, quando o
  `main.js` roda. O `try/catch` é obrigatório: `localStorage` lança com cookies bloqueados, e
  uma exceção ali mataria o resto do `<head>`.
- **`boot-gate.js`** — rede de segurança do splash. Sem perfil salvo vai direto ao login, sem
  splash; e há **teto absoluto de 6s**, para que nenhum caminho deixe o splash preso.
- **`registry.js`** — registry de uma função só, para o FAB mobile, **evitando import
  circular** entre `main.js` e as tabs (lembrando que nada pode importar `main.js`).
- **`skeleton.js`** — larguras de placeholder como **classe literal**
  (`w-[55%]`, `w-[70%]`…), não `style="width:${x}%"`: o CSP bloqueia atributo de estilo e o
  scanner do Tailwind não resolve interpolação. O escalonamento da animação vem do `.stagger`
  no container.
- **`privacy-app-view.js`** — remove o link "Voltar ao Portal" quando a URL tem `?app=1`.

**Nada importa `main.js`** — ver [[patterns.md]]. Foi por isso que `modal.js` existe.

## Abas

| Aba | Funcionalidades |
|---|---|
| Turmas | Criar, atribuir professor, matricular/desmatricular (modal de abas), importar CSV, excluir |
| Horários | Grade de 7 dias, filtro turno+semestre, adicionar aula (modal de slots), excluir |
| Professores | CRUD, exibe senha temporária pós-criação, editar, importar CSV |
| Alunos | CRUD, editar (modal), senha temporária, importar CSV em massa (turma opcional) |
| Relatórios | Lista paginada com Presentes/Ausentes/Parciais/Freq%, modal de detalhe, export PDF |
| Biometria | Rekognition + S3 agrupados por aluno, expansível, seleção, bulk delete |

### MatriculaModal (`showMatriculaModal` em `turmas.js`)

Duas abas: "Matricular" (elegíveis = não matriculados + turno compatível) e "Matriculados"
(desmatrícula em massa). Estado **independente por aba**
(`estado = { matricular: {...}, matriculados: {...} }`), com reset ao trocar. Checkbox
"Selecionar Todos" com estado indeterminado, busca por nome/RA, paginação 8/página, contador
no botão. Desmatricular passa por `confirm.show` (é destrutivo).

## Segurança do portal

- Auth por **cookie HttpOnly + CSRF** — ver [[seguranca.md]]. O `auth.js` guarda só
  `admin_user` (perfil público) e limpa as chaves legadas `admin_token`/`admin_refresh_token`.
  O `api.js` usa `credentials: 'include'` + `X-Requested-With` por default.
- **CSP sem `'unsafe-inline'` em `script-src` E `style-src`** desde 2026-08-04 (PR #106).
  A remoção do `style-src` **não veio de graça com o CLI**, como a dívida original supunha:
  exigiu converter 21 pontos (20 atributos `style=` + o bloco `<style>` do `privacy.html`).
  Só **dois** precisavam de JS; o resto era estilo estático disfarçado de dinâmico:
  - `animation-delay:${i*45}ms` (7×) → `.stagger > *:nth-child(n)` no container (funciona
    porque os itens são sempre os únicos filhos);
  - avatar (cor + tamanho) → 8 classes de cor × 2 de tamanho, paleta fixa;
  - larguras de skeleton → classes Tailwind **literais** (`w-[55%]`…), porque o scanner não
    resolve interpolação;
  - `grid-template-columns`, scrollbar, barra inferior e gradiente → classes em `app.css`;
  - **largura da barra de frequência** e **duração do toast** → `el.style` em JS.
- O guarda `test_portal_csp_sem_inline_handlers.py` varre `style="`, `<style>` e handlers
  inline, e checa `script-src` e `style-src` nas duas páginas. Ele **ignora linhas de
  comentário** em vez de isentar arquivos.
- `connect-src` fixa `https://api.scpi.me` e precisa ser editado junto de `portal/js/env.js`
  ao trocar de host, inclusive para dev local.
- Toda interpolação de dado de usuário passa por `escapeHtml` (aplicado em 14 pontos como
  hardening preventivo de XSS).

## Contraste WCAG — em prod desde 2026-08-03 (PR #99)

Dois tokens em vez de um só, para não achatar a hierarquia: `muted` `#9ca3af` (6,73 no pior
fundo) e `faint` `#8b9099` (5,33), substituindo `text-gray-400/500/600/700`. **O pior caso
real era gray-700 sobre card-hover a 1,66:1**, não 2,5. A folga do `faint` é de propósito —
o mais escuro que passaria é `#80848c` a 4,55:1. Branco sobre `accent` já dava 6,71, então
botões nunca foram problema.

`test_portal_contraste_wcag.py` **recalcula** o contraste em vez de proibir nomes de classe,
então um fundo novo mais claro quebra o teste sozinho.

## Persistência de UI no F5

`persist.js`: wrapper de `sessionStorage` na chave `scpi.portal.ui`, JSON, falha silenciosa.
Escopo do `sessionStorage`: sobrevive ao F5, some ao fechar a aba, independente entre abas.

- Global (aba + turno + semestre) hidratado/salvo em `state.js` (`GLOBAL_KEYS`); `main.js`
  restaura a aba via `tabValida()` com fallback para turmas; `clearUI()` no logout.
- Por aba (`{search, page}`): alunos, professores, turmas e relatórios hidratam no `mount`.
- Fora de escopo: rostos (seleções transitórias), modal de matrícula, `state.cache.*`.

## Cache

`state.cache.*` — `null` = não carregado, array = carregado. `invalidate(...keys)` limpa
depois de mutação. Lazy load por aba.

## nginx

Ver [[ops.md]] para os headers e as duas armadilhas de `add_header` / `try_files`.
