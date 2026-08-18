---
titulo: Manual do Portal Web
subtitulo: Portal administrativo: build, deploy e as regras que o mantêm seguro
versao: "1.0"
data: 2026-08-18
---

## Introdução

### Para quem é este manual

Este manual é para quem assume o desenvolvimento do portal administrativo do SCPI — a tela onde o administrador da instituição cadastra alunos, professores, turmas, horários e o banco de rostos, e de onde saem os relatórios em PDF.

Ele parte do princípio de que o ambiente já está montado (isso está no Manual de Ambiente de Desenvolvimento) e foca no que é específico do portal: como ele é construído, por que o CSS precisa de um passo de build que o JavaScript não tem, como a política de segurança do navegador restringe o código permitido, e como uma edição de configuração local pode acidentalmente ir para produção — ou nunca chegar lá.

### Como ler

Os capítulos de Build do CSS e de CSP não são opcionais: são as duas regras que, se quebradas, produzem sintomas silenciosos — tela sem estilo ou botão que não faz nada, sem exceção no console. Leia os dois antes de tocar em qualquer classe ou em qualquer HTML novo.

O capítulo de Configuração da URL da API é o que resolve a dúvida mais comum de quem começa a mexer no portal: "por que estou vendo dados que não cadastrei?".

### O que não está aqui

- **A API que o portal consome** — rotas, autenticação por cookie, regras de negócio — ainda não tem manual próprio nesta suíte. Para as rotas disponíveis, use o Swagger em `/docs` (a API expõe o schema automaticamente); o `README.md` na raiz do repositório é a fonte atual para uma visão geral.
- **A VM de produção, o systemd e o processo de deploy em si** (`git pull`, `nginx reload`) estão no Manual da VM de Produção (ainda não escrito); este manual aponta para o runbook do nginx em vez de repetir os comandos.
- **Contas de terceiros** — o portal não usa nenhuma diretamente; toda integração externa (AWS, Resend) passa pela API.

> **Atenção:** nenhum valor de segredo aparece neste manual. O portal, aliás, não guarda segredo nenhum do lado do cliente — a sessão vive em cookies `HttpOnly` que o JavaScript do portal nem consegue ler.

## Arquitetura do portal

### Estático, sem framework, sem build de JavaScript

O portal é HTML, CSS e JavaScript servidos como arquivos estáticos — sem React, sem Vite, sem bundler. `portal/index.html` é uma única página (um SPA shell) que alterna entre a tela de login e o dashboard trocando classes `hidden` em blocos já presentes no HTML. O JavaScript é organizado em **módulos ES nativos do navegador** (`<script type="module">`), importados uns pelos outros com `import`/`export` puro — sem `webpack`, sem `esbuild`.

A ausência de bundler é deliberada: o deploy em produção é `git pull` seguido de reload do nginx, sem passo de instalação. Não existe processo Node rodando na VM.

Existe, porém, build — só que de **CSS**, não de JavaScript. Ver o capítulo seguinte.

### Mapa dos arquivos em `portal/js/`

| Arquivo | Responsabilidade |
|---|---|
| `main.js` | Entrypoint. Router de abas, montagem da sidebar e da navegação inferior, login/logout, filtros de turno e semestre, atalhos de teclado |
| `config.js` | `API_URL` (lida de `window.__SCPI_API_URL__`) e as constantes de domínio: slots de horário, dias da semana, semestres, períodos, turnos |
| `env.js` | Define `window.__SCPI_API_URL__`. Único ponto de configuração da URL da API |
| `api.js` | Wrapper de `fetch`: injeta `credentials: 'include'` e o header anti-CSRF, mapeia código HTTP para mensagem em português, renova a sessão automaticamente num 401 |
| `auth.js` | Sessão local: guarda só o perfil público do usuário (`admin_user`) em `localStorage`; nunca um token |
| `state.js` | Estado global em memória — aba ativa, turno, semestre, cache por recurso — com um pequeno pub/sub (`on`/`setState`) |
| `persist.js` | Persiste UI (aba, filtros, página) em `sessionStorage`, sobrevive ao F5, some ao fechar a aba |
| `toast.js` | Fila de notificações no canto da tela |
| `confirm.js` | Modal de confirmação para ações destrutivas, baseado em Promise |
| `modal.js` | `openModal`/`closeModal`/`animateRemove`, compartilhados entre `main.js` e as abas — existe para que nada precise importar `main.js` (ver o capítulo de Cache) |
| `pagination.js` | Paginação client-side genérica: fatia array e desenha os controles |
| `skeleton.js` | Telas de carregamento (placeholders animados) para cada layout de aba |
| `icons.js` | Biblioteca própria de ícones SVG inline (sem dependência externa) |
| `utils.js` | `escapeHtml`, `debounce`, `avatar` (iniciais com cor determinística), download de CSV/blob |
| `registry.js` | Um registro de uma função só, para o botão flutuante (FAB) mobile chamar o formulário de criação da aba ativa sem import circular |
| `boot-sidebar.js` | Roda no `<head>`, antes de qualquer módulo: aplica a classe de sidebar recolhida antes do primeiro paint |
| `boot-gate.js` | Roda no `<head>`: some com o overlay de boot se não houver perfil salvo, e tem teto de 6 segundos independente do `main.js` |
| `privacy-app-view.js` | Usado só por `privacy.html`: remove o link "Voltar ao Portal" quando a página é aberta pelo app (`?app=1`) |

`boot-sidebar.js` e `boot-gate.js` são carregados por `<script>` comum (não `type="module"`) direto no `<head>`, propositalmente independentes do `main.js` — inclusive de uma cópia dele presa em cache do navegador. Sem eles, a sidebar nasceria larga e encolheria visivelmente, e uma falha no `main.js` deixaria o usuário preso no spinner de boot para sempre.

### Mapa das abas em `portal/js/tabs/`

| Arquivo | Aba | O que faz |
|---|---|---|
| `turmas.js` | Turmas | CRUD de turmas, atribuição de professor, matrícula/desmatrícula em massa (modal com duas sub-abas e "Selecionar Todos"), importação por CSV |
| `horarios.js` | Horários | Grade semanal de 7 dias, filtrada por turno e semestre; adicionar aula por um modal de slots pré-definidos |
| `professores.js` | Professores | CRUD, exibição da senha temporária após criação, edição, importação por CSV |
| `alunos.js` | Alunos | CRUD, edição em modal, senha temporária, importação por CSV em massa com turma opcional |
| `relatorios.js` | Relatórios | Lista paginada de presença (Presentes/Ausentes/Parciais/Frequência%), modal de detalhe por chamada, exportação de PDF |
| `rostos.js` | Biometria | Inventário do banco de rostos (AWS Rekognition + S3), agrupado por aluno, expansível, seleção múltipla e exclusão em massa |

Cada módulo de aba expõe uma função `mount(container)` assíncrona, chamada pelo router de `main.js` ao trocar de aba; o conteúdo anterior é substituído e o `state.cache` evita recarregar da API o que já foi buscado nesta sessão.

### Acrescentar uma aba nova

Um arquivo novo em `tabs/` com `mount()` exportado, por si só, **não aparece em lugar nenhum** do portal. `main.js` não descobre abas automaticamente: ele importa cada módulo de aba por nome e mantém um array literal, `TABS`, com uma entrada por aba. As duas coisas — import e entrada no array — moram juntas no topo do arquivo:

```javascript
import { mount as mountTurmas } from './tabs/turmas.js';
import { mount as mountHorarios } from './tabs/horarios.js';
import { mount as mountProfessores } from './tabs/professores.js';
import { mount as mountAlunos } from './tabs/alunos.js';
import { mount as mountRelatorios } from './tabs/relatorios.js';
import { mount as mountRostos } from './tabs/rostos.js';

const TABS = [
  { id: 'turmas',      label: 'Turmas',    bLabel: 'Turmas',    iconName: 'graduation-cap', title: 'Turmas',          subtitle: 'Gestão de disciplinas e matrículas',   mount: mountTurmas,      skeleton: () => skeletons.twoCol(6) },
  // ... uma entrada por aba
];
```

Cada entrada de `TABS` traz `id` (usado em `data-tab`, no cache e na persistência de UI), `label`/`bLabel` (nome completo na sidebar e abreviado na navegação inferior), `iconName` (chave de `icons.js`), `title`/`subtitle` (cabeçalho da área principal), `mount` (a função importada) e `skeleton` (a tela de carregamento de `skeleton.js` mostrada antes do `mount` resolver).

O roteiro mínimo para uma aba nova:

1. Criar o arquivo em `portal/js/tabs/`, seguindo o padrão das abas existentes (import de `api.js`, `toast.js`, `state.js` conforme a necessidade).
2. Exportar uma função `mount(container)` assíncrona a partir dele — é o único contrato que o router exige.
3. Em `main.js`, acrescentar o `import { mount as mountX } from './tabs/x.js'` junto dos outros seis, e uma entrada nova em `TABS` com `id`, `label`, `iconName`, `title`, `subtitle`, `mount` e `skeleton`. Sem essa entrada, a função existe mas nenhum botão de navegação chega a chamá-la.
4. **Incrementar o `?v=N`** da tag `<script type="module" src="js/main.js?v=13">` em `index.html`. `main.js` mudou — ganhou um import e uma entrada em `TABS` — e é justamente esse número que força o navegador a buscar a versão nova em vez de servir a antiga do cache (ver o capítulo de Cache e versionamento de módulo).
5. Se a marcação da aba usar alguma classe Tailwind que ainda não aparece em nenhum outro arquivo do portal, rodar `npm run build` em `portal/` antes de commitar — o scanner do Tailwind só inclui no CSS compilado as classes que encontra em `index.html` e em `js/**/*.js` (ver o capítulo de Build do CSS).
6. Nenhum handler de evento inline (`onclick=`) na marcação da aba nova. A CSP do portal bloqueia, em silêncio, e `test_portal_csp_sem_inline_handlers.py` cobre qualquer arquivo novo em `portal/js/` ou `portal/` sem precisar de configuração — o teste varre por `rglob`.

> **Pegadinha:** os passos 3 e 4 são fáceis de separar sem notar. Alguém que só acrescenta a entrada em `TABS` e esquece o `?v=N` vê a aba nova funcionar na própria máquina — o navegador local ainda não tem `main.js` em cache com a versão antiga — e só descobre o problema quando um usuário com a aba já aberta em produção não vê a mudança depois do deploy.

### Como o portal fala com a API

`api.js` centraliza toda chamada HTTP. Dois pontos importam para quem for depurar:

- Toda requisição vai com `credentials: 'include'` (os cookies `HttpOnly` de sessão) e o header `X-Requested-With: XMLHttpRequest`, exigido pelo backend como contramedida de CSRF.
- Um 401 dispara uma tentativa automática de `/auth/refresh` antes de desistir; só se o refresh também falhar é que a sessão local é limpa e a tela de login volta.

## Build do CSS

### Por que existe build, sem existir bundler

O portal usa Tailwind CSS, mas não carrega o Tailwind no navegador. `portal/src/input.css` é a entrada:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

O Tailwind CLI compila esse arquivo em `portal/css/tailwind.css` — só as classes efetivamente usadas em `index.html` e em `js/**/*.js`, minificado — e **esse resultado vai versionado no repositório**. `index.html` carrega o arquivo compilado com uma tag `<link>` comum:

```html
<link rel="stylesheet" href="css/tailwind.css">
```

O motivo de versionar o CSS compilado, em vez de gerá-lo no deploy, é que **a VM de produção não roda Node**. O deploy é `git pull` mais reload do nginx; não há passo de `npm install` nem de build no servidor. Node é dependência só da máquina de quem desenvolve.

### O comando

A partir de `portal/`:

```bash
npm run build
```

Este manual executou o comando na máquina de referência: terminou em menos de um segundo e não alterou `portal/css/tailwind.css`, porque nenhuma classe havia mudado desde o último commit — a saída do build é determinística entre a máquina de desenvolvimento (Windows) e o runner do CI (Linux).

Para desenvolvimento contínuo, sem repetir o comando a cada classe nova:

```bash
npm run watch
```

Os dois scripts vêm de `portal/package.json`:

```json
"scripts": {
  "build": "tailwindcss -i src/input.css -o css/tailwind.css --minify",
  "watch": "tailwindcss -i src/input.css -o css/tailwind.css --watch"
}
```

> **Importante:** mexeu em classe Tailwind no HTML ou em qualquer arquivo de `js/`? Rode `npm run build` **antes de commitar**, e commite `css/tailwind.css` junto. Esquecer não quebra a build — quebra a tela, calado: o elemento sobe sem estilo, e nada no console aponta para a causa.

### O job de CI que fecha essa lacuna

O job `portal-css` (`portal css (build atualizado)`) de `.github/workflows/tests.yml` existe porque a regra acima depende de disciplina humana. Ele recompila o CSS do zero e compara com o que está commitado:

```yaml
portal-css:
  name: portal css (build atualizado)
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v7
    - uses: actions/setup-node@v7
      with:
        node-version: "20"
        cache: "npm"
        cache-dependency-path: portal/package-lock.json
    - name: Install dependencies (no scripts)
      working-directory: portal
      run: npm ci --ignore-scripts
    - name: Rebuild CSS
      working-directory: portal
      run: npm run build
    - name: CSS versionado tem de bater com a fonte
      run: |
        if ! git diff --quiet -- portal/css/tailwind.css; then
          echo "::error::portal/css/tailwind.css está defasado. Rode 'npm run build' em portal/ e commite o resultado."
          git diff --stat -- portal/css/tailwind.css
          exit 1
        fi
        echo "CSS versionado confere com a fonte."
```

Se o `git diff` depois do rebuild não for vazio, o job falha. Reproduzir localmente é exatamente `npm run build` seguido de `git diff` em `portal/`.

O workflow dispara em push e Pull Request para `main` quando o diff toca `BackEnd/`, `portal/`, `app/` ou o próprio workflow — não só quando o `portal/` é tocado diretamente, porque `test_portal_csp_sem_inline_handlers.py` mora em `BackEnd/tests` mas lê arquivos do portal.

> **Pegadinha:** o job usa `npm ci --ignore-scripts`, então instala exatamente o que está em `portal/package-lock.json` — `tailwindcss` na versão `3.4.17`, a única dependência de desenvolvimento do portal. Uma diferença de versão do Tailwind entre a máquina local e o CI pode produzir uma minificação byte a byte diferente mesmo com as mesmas classes; se o job falhar sem nenhuma mudança de classe aparente, confira a versão instalada.

### `app.css` continua à mão

Nem tudo é Tailwind. `portal/css/app.css` — carregado **depois** de `tailwind.css`, de propósito, para as regras próprias vencerem as utilitárias em empate — traz o que o Tailwind não cobre bem: animações (`@keyframes`), a barra de rolagem customizada, os estados de foco dos inputs e as classes que substituem estilo inline banido pela CSP (`av-0` a `av-7` para cor de avatar, `.stagger` para atraso de animação escalonado por `nth-child`). Ele não passa pelo build do Tailwind e é editado diretamente.

## CSP sem `unsafe-inline`

### O que a política proíbe

A meta tag de `Content-Security-Policy` em `portal/index.html` e em `portal/privacy.html` é:

```text
default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self' https://api.scpi.me; base-uri 'none'; form-action 'none'; object-src 'none'
```

Nem `script-src` nem `style-src` incluem `'unsafe-inline'`. Isso proíbe, na marcação HTML:

- Atributos de evento inline — `onclick=`, `onchange=`, e qualquer outro `on*=`.
- Atributo `style="..."` em qualquer elemento.
- Bloco `<style>` solto no HTML.

Hash e nonce não resolvem o caso de atributo — eles só liberam blocos `<script>` ou `<style>` específicos, nunca um atributo inline. Sem `'unsafe-inline'`, esses atributos são bloqueados incondicionalmente pelo navegador.

> **Pegadinha:** o sintoma de um `onclick=` bloqueado é mudo do lado do JavaScript. Nenhuma exceção sobe, nenhum erro aparece fora do console do navegador — o handler simplesmente nunca dispara. Foi assim que os botões de fechar (X e Cancelar) dos modais pararam de funcionar antes da correção.

### O padrão em uso: delegação de evento

Nenhum elemento do portal usa `onclick=`. `main.js` registra um único listener no elemento estático `#modal-overlay` (que nunca é recriado, ao contrário do conteúdo de `#modal-box`, que é trocado por `innerHTML` a cada modal) e delega para `[data-close-modal]`:

```javascript
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) return closeModal();
  if (e.target.closest('[data-close-modal]')) closeModal();
});
```

O mesmo padrão se repete em `toast.js`, que anexa o listener de fechar depois de montar o nó do toast, nunca por atributo.

### O padrão em uso: valor de estilo contínuo por `el.style`

A política filtra a **marcação** (`style="..."`), não a manipulação programática do objeto de estilo pelo JavaScript. Um valor contínuo — que não cabe numa classe fixa, como a largura de uma barra de progresso de 0 a 100% ou a duração de uma animação que varia por tipo de toast — é escrito via CSSOM:

```javascript
// portal/js/tabs/relatorios.js — largura da barra de frequência
list.querySelectorAll('.prog-bar-fill[data-largura]').forEach(barra => {
  barra.style.width = `${barra.dataset.largura}%`;
});
```

```javascript
// portal/js/toast.js — duração varia por tipo (3s a 6s)
barra.style.animation = `toast-shrink ${duration}ms linear forwards`;
```

Isso é permitido e é o caminho correto. O que **não** é permitido é o mesmo valor entrando como string de HTML (`` `<div style="width:${x}%">` ``) — mesmo que o efeito visual final seja idêntico, a CSP bloqueia o atributo na marcação e libera a propriedade via `el.style`.

> **Quando usar:** se o valor tem um número finito de estados conhecidos (cor de avatar, largura de skeleton, atraso de animação em lista), prefira classe fixa em `app.css` ou Tailwind — é mais barato de auditar e não engorda a lógica de renderização. Reserve `el.style` para o caso em que o valor é genuinamente contínuo e não cabe num conjunto pequeno de classes.

### O teste automatizado

`BackEnd/tests/test_portal_csp_sem_inline_handlers.py` varre todo `.js` e `.html` de `portal/` (menos `node_modules/`, `vendor/` e `tailwind.config.js`) atrás de handler inline e de estilo inline, e confere que nenhuma das duas diretivas da meta CSP ganhou `'unsafe-inline'` ou `'unsafe-hashes'` de volta — em `index.html` e em `privacy.html`.

O teste ignora linhas que começam com comentário (`//`, `/*`, `*`, `<!--`), para não acusar a própria documentação do padrão — como este trecho:

```python
def _e_comentario(linha: str) -> bool:
    s = linha.strip()
    return s.startswith(("//", "/*", "*", "<!--"))
```

Roda junto da suíte inteira do BackEnd:

```bash
cd BackEnd
python -m pytest tests/test_portal_csp_sem_inline_handlers.py -v
```

## Configuração da URL da API

### Onde a URL mora

A URL da API que o portal consome é definida em um único lugar, `portal/js/env.js`:

```javascript
window.__SCPI_API_URL__ = 'https://api.scpi.me';
```

Esse arquivo é carregado por `portal/index.html`, por um `<script>` comum no `<head>`, antes do entrypoint em módulo. `portal/js/config.js` lê essa global e só cai no fallback local se ela não existir:

```javascript
export const API_URL = window.__SCPI_API_URL__ || 'http://localhost:8000';
```

Por padrão, `env.js` aponta para a **API de produção**. Isso significa que subir o portal localmente com `python -m http.server` e abrir `http://localhost:3000` produz uma tela de login funcional que autentica contra produção — sem nenhum aviso.

> **Não é variável de ambiente.** O `.env.example` da raiz do repositório teve, até recentemente, uma entrada `VITE_API_URL` sugerindo o contrário; nenhum código do portal nunca leu essa variável, e ela foi removida do `.env.example` como configuração morta. A única fonte da URL da API é `portal/js/env.js`.

### Reapontar o portal para a API local

São **duas** edições manuais de arquivo, e nenhuma das duas pode ser commitada.

**Edição 1 — a URL em si.** Em `portal/js/env.js`, trocar:

```javascript
window.__SCPI_API_URL__ = 'https://api.scpi.me';
```

por:

```javascript
window.__SCPI_API_URL__ = 'http://localhost:8000';
```

**Edição 2 — liberar a origem local na CSP.** Em `portal/index.html` (e em `portal/privacy.html`, se for testar a página de privacidade localmente), a diretiva `connect-src` da meta CSP hoje é:

```text
connect-src 'self' https://api.scpi.me
```

Acrescentar `http://localhost:8000`.

A segunda edição é obrigatória porque, do ponto de vista do navegador, `http://localhost:8000` é uma origem diferente de `http://localhost:3000` (onde o portal está sendo servido). Fazer só a primeira edição produz um portal que aponta para o lugar certo, mas cujas chamadas o próprio navegador bloqueia por CSP — a tela fica vazia, sem nenhum erro fora do console.

> **Atenção:** nenhuma das duas edições pode ir para um commit. As duas reconfiguram o portal de produção para apontar para a máquina do desenvolvedor. Antes de commitar qualquer coisa, confira que a árvore está limpa nesses dois arquivos:
>
> ```bash
> git diff -- portal/js/env.js portal/index.html
> ```
>
> A saída tem de estar vazia.

## Cache e versionamento de módulo

### O que o nginx de produção envia

O runbook do nginx documenta que o server block de produção define, no nível do `server` (não em `location` nenhum, ver o motivo no próprio runbook), quatro headers que cobrem `index.html`, `privacy.html` e tudo em `js/`, `css/`, `fonts/` e `vendor/`:

```nginx
add_header Content-Security-Policy "frame-ancestors 'none'" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Cache-Control "no-cache, must-revalidate" always;
```

`no-cache` não significa "não guardar em cache" — significa "revalidar com o servidor antes de reusar o que está guardado". Na prática o navegador manda uma requisição condicional a cada carregamento, e o servidor responde `304` (poucos bytes) se nada mudou, ou o conteúdo novo se mudou. Isso evita que um `index.html` velho — com a meta CSP antiga junto — sobreviva a um deploy no cache do navegador de um usuário. Ver o Manual da VM de Produção (ainda não escrito) para o `location` que faz o `try_files` correspondente devolver `404` de verdade para um asset inexistente, em vez de `200` com o próprio `index.html` de fallback — hoje esse `location` já está documentado no runbook `docs/runbooks/PORTAL_NGINX.md`.

Isso é o que a produção envia. O servidor estático de desenvolvimento, `python -m http.server`, não envia nenhum header de cache — na máquina local, um `main.js` antigo pode ficar preso no cache do navegador sem que nada o force a revalidar.

### O `?v=N` do entrypoint

Por isso `index.html` carrega o único módulo importado diretamente por `<script>`, `main.js`, com um parâmetro de versão:

```html
<script type="module" src="js/main.js?v=13"></script>
```

O comentário no próprio arquivo documenta a regra: incrementar esse número a cada deploy força o navegador a buscar o bundle novo, em vez de rodar uma cópia em cache contra um `index.html` já atualizado.

### Por que nada mais pode importar `main.js`

Esse `?v=N` cria um segundo risco, independente de cache: para o mecanismo de módulos ES do navegador, a **identidade** de um módulo é a URL exata, incluindo a query string. `js/main.js` e `js/main.js?v=13` são, para o navegador, dois módulos diferentes — mesmo apontando para o mesmo arquivo.

Isso já aconteceu no portal: as abas em `js/tabs/` precisavam de funções que moravam em `main.js` (abrir/fechar modal) e as importavam de volta com `import { openModal } from '../main.js'` — sem a query. O navegador já tinha `js/main.js?v=13` carregado a partir do `<script>` do `index.html`; o import sem query criava uma **segunda instância** do mesmo módulo, com seu próprio `DOMContentLoaded`, sua própria chamada de `init()`, e todo `addEventListener` registrado em dobro.

A correção não foi "usar a query no import" — seria frágil, porque o número muda a cada deploy e um import esquecido volta a divergir. A correção foi extrair as funções compartilhadas para um módulo à parte, `modal.js`, que não tem relação nenhuma com o `<script>` do HTML. Hoje **nada no portal importa `main.js`**; ele é exclusivamente o entrypoint carregado pela tag `<script type="module">`, e todo compartilhamento entre módulos passa por arquivos irmãos como `modal.js`, `api.js`, `state.js`.

> **Importante:** ao criar uma função nova que `main.js` e alguma aba precisem dividir, o lugar dela é um módulo novo ou existente fora de `main.js` — nunca de volta para dentro dele. Importar `main.js` de qualquer lugar reintroduz a duplicação.

## Deploy

O portal é publicado por nginx a partir de `/opt/scpi/portal`, sem processo de aplicação — é `root` de arquivos estáticos. O runbook `docs/runbooks/PORTAL_NGINX.md` documenta a configuração do server block em si — os quatro headers de segurança no nível do `server`, a armadilha do `add_header` dentro de `location` que descarta em vez de somar, o `try_files` dos assets e a verificação com `curl` — mas não traz `git pull` nem um procedimento de deploy passo a passo; isso fica para o Manual da VM de Produção (ainda não escrito).

Este manual cobre apenas o que precede o deploy: garantir que `css/tailwind.css` está atualizado (capítulo de Build do CSS) e que `portal/js/env.js` e a CSP de `portal/index.html` não carregam nenhuma edição local de desenvolvimento (capítulo de Configuração da URL da API).

## Verificação

| Prova | Como conferir | Resultado esperado |
|---|---|---|
| Dependência de build instalada | `npm ci` (ou `npm install`) em `portal/` | Termina sem erro; instala só `tailwindcss` |
| CSS compilado bate com a fonte | `npm run build` em `portal/`, depois `git diff -- portal/css/tailwind.css` | `git diff` vazio |
| Portal servido e estilizado | `python -m http.server 3000` em `portal/`, abrir `http://localhost:3000` | Tela de login com estilo aplicado |
| Nenhuma edição local de configuração pendente | `git diff -- portal/js/env.js portal/index.html` | Saída vazia |
| Guarda de CSP e de estilo/handler inline | `python -m pytest tests/test_portal_csp_sem_inline_handlers.py -v` em `BackEnd/` | Todos os casos passando |
| Headers de produção presentes | `curl -sI https://admin.scpi.me/` | `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` e `Cache-Control` (os quatro headers da seção de Cache e versionamento de módulo) na resposta |

> **Quando usar:** repita a checagem de `git diff` nos dois arquivos de configuração sempre, antes de qualquer commit que tenha passado por uma sessão de desenvolvimento local — é o único jeito de garantir que uma URL de API local não vaza para produção.

## Problemas conhecidos

| Sintoma | Causa | Solução |
|---|---|---|
| Portal abre sem nenhum estilo | `npm run build` não rodou; `css/tailwind.css` está defasado da fonte | `cd portal && npm run build` |
| CI falha no job `portal css (build atualizado)` | Alguém commitou uma classe nova sem rodar o build, ou uma versão de `tailwindcss` diferente da travada em `package-lock.json` | `npm ci` seguido de `npm run build` em `portal/`, conferir `git diff`, commitar o CSS |
| Portal carrega, mas nenhuma tela traz dados, sem erro visível | A CSP bloqueia a chamada para a origem local da API | Acrescentar a origem local ao `connect-src` da meta CSP em `portal/index.html`, localmente, sem commitar |
| Portal mostra dados que ninguém cadastrou nesta máquina | `portal/js/env.js` ainda aponta para a API de produção | Trocar `window.__SCPI_API_URL__` para a API local, localmente, sem commitar |
| Botão não faz nada, sem erro no console | Handler `onclick=` inline na marcação, bloqueado pela CSP em silêncio | Registrar o listener em JavaScript, por delegação se o nó for recriado dinamicamente |
| Elemento com o estilo errado, ou aviso do teste de estilo inline | `style="..."` na marcação, ou bloco `<style>` solto | Mover para classe em `css/app.css` ou Tailwind; se o valor for contínuo, escrever via `el.style` em JavaScript |
| Listener registrado em dobro / evento dispara duas vezes | Algum módulo importou `main.js` (com ou sem `?v=N`), criando uma segunda instância do módulo | Extrair a função compartilhada para um módulo próprio (como `modal.js`); nada deve importar `main.js` |
| Um deploy novo não aparece para usuários com a aba já aberta | `js/main.js?v=N` não foi incrementado | Incrementar o `?v=` na tag `<script type="module">` de `index.html` a cada deploy que altera JavaScript |
| Asset em `js/`/`css/`/`fonts/` devolve `index.html` (200) em vez de 404 quando o caminho está errado | `location` de assets sem `try_files $uri =404` próprio | Ver o runbook do nginx — não é um problema deste manual, mas o sintoma aparece primeiro no portal |

## Referência rápida

### Comandos do dia a dia

| Ação | Comando | Pasta |
|---|---|---|
| Instalar a dependência de build | `npm install` | `portal/` |
| Compilar o CSS | `npm run build` | `portal/` |
| Recompilar continuamente | `npm run watch` | `portal/` |
| Servir localmente | `python -m http.server 3000` | `portal/` |
| Conferir que nenhuma configuração local vazou | `git diff -- portal/js/env.js portal/index.html` | Raiz |
| Rodar o guarda de CSP | `python -m pytest tests/test_portal_csp_sem_inline_handlers.py -v` | `BackEnd/` |

### Mapa de segredos

O portal, do lado do cliente, **não guarda segredo nenhum**. A sessão vive em cookies `HttpOnly` emitidos pela API — inacessíveis ao JavaScript do portal por desenho. Não há chave de API, token ou credencial em nenhum arquivo de `portal/`.

| Item | Onde mora | Observação |
|---|---|---|
| URL da API | `portal/js/env.js` | Não é segredo, mas é a única configuração de ambiente do portal, e não pode ser commitada quando alterada para desenvolvimento local |
| Cookies de sessão (`scpi_access`, `scpi_refresh`) | Emitidos pela API, `HttpOnly` | O portal nunca lê o valor; só confia na presença deles via `credentials: 'include'` |
| Perfil público do usuário | `localStorage`, chave `admin_user` | Nome, papel, e-mail — nada sensível o bastante para exigir cookie |

### Arquivos-fonte deste manual

| Arquivo | O que fixa |
|---|---|
| `portal/index.html` | Estrutura da página, a meta CSP, a ordem de carregamento dos scripts, o `?v=N` do entrypoint |
| `portal/privacy.html` | Página de privacidade, fora do escopo do Tailwind |
| `portal/package.json` | Os scripts `build` e `watch`, e a única dependência de desenvolvimento (`tailwindcss`) |
| `portal/src/input.css` | Entrada do build do Tailwind |
| `portal/css/app.css` | CSS escrito à mão: animações, classes que substituem estilo inline |
| `portal/js/env.js` | Onde mora `window.__SCPI_API_URL__` |
| `portal/js/config.js` | Leitura da URL da API e as constantes de domínio do portal |
| `portal/js/api.js` | Wrapper de `fetch`, renovação de sessão, mapeamento de erro HTTP |
| `portal/js/auth.js` | O que o portal guarda em `localStorage` sobre a sessão |
| `portal/js/state.js` | Estado global e cache por recurso |
| `portal/js/toast.js` | Exemplo de `el.style` para valor contínuo e de listener sem `onclick` |
| `portal/js/modal.js` | Por que nada importa `main.js` |
| `portal/js/main.js` | Router de abas, o `?v=N` e o comentário sobre cache |
| `portal/js/tabs/*.js` | Uma aba por arquivo — ver o mapa das abas |
| `docs/runbooks/PORTAL_NGINX.md` | Configuração de produção do nginx: os quatro headers, `try_files`, e a verificação com `curl` |
| `.github/workflows/tests.yml` | O job `portal-css` e os `paths` que disparam o workflow |
| `BackEnd/tests/test_portal_csp_sem_inline_handlers.py` | O guarda automatizado de CSP, handler inline e estilo inline |
