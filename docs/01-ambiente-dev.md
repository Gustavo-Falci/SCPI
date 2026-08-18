---
titulo: Manual de Ambiente de Desenvolvimento
subtitulo: Do clone do repositório ao primeiro Pull Request
versao: "1.0"
data: 2026-08-18
---

## Introdução

### Para quem é este manual

Este manual é para a pessoa que assume o desenvolvimento do SCPI. Ele parte do zero — uma máquina sem nada instalado e sem acesso prévio ao projeto — e termina com o ambiente completo rodando localmente e a primeira contribuição pronta para virar Pull Request.

O objetivo é que a leitura deste documento, sem nenhuma conversa com o desenvolvedor anterior, seja suficiente para clonar, configurar, subir, testar e alterar o sistema.

### Como ler

Leia os capítulos em ordem na primeira vez. Cada capítulo depende do anterior: o banco só sobe depois do `.env`, a API só sobe depois do banco, o app só conecta depois da API.

Depois da primeira montagem, o capítulo de referência rápida e a tabela de problemas conhecidos são o que você vai reabrir no dia a dia.

Os comandos aparecem em blocos de código. Quando o comando difere entre Windows e Linux, os dois aparecem, identificados. A máquina de referência deste manual é Windows 11 com PowerShell; os comandos de shell POSIX foram mantidos porque o CI e a VM de produção rodam Linux.

### De onde cada comando roda

Esta é a convenção mais importante do manual, e vale para todos os capítulos:

- **Cada bloco declara a pasta de onde parte, na frase imediatamente antes dele** — quase sempre a raiz do repositório, a pasta `SCPI/` criada pelo clone; às vezes a pasta em que o bloco anterior deixou você, e nesse caso a frase diz "ainda dentro de". Leia essa frase antes de copiar o bloco.
- Um bloco que começa com `cd` usa caminho **relativo à raiz**. Rodar `cd BackEnd` duas vezes seguidas falha, porque a segunda procuraria `BackEnd/BackEnd`.
- Quando um bloco deixa você em outra pasta e o bloco seguinte precisa da raiz, o `cd ..` aparece escrito dentro do próprio bloco.

> **Pegadinha:** o erro mais comum de quem monta o ambiente pela primeira vez é rodar `cp .env.example .env` de dentro de `BackEnd/`, logo depois do `pip install`. O arquivo `BackEnd/.env.example` não existe, o comando falha, e o `.env` da raiz nunca é criado — mas o sintoma só aparece páginas adiante, quando a API não sobe.

Quatro rótulos aparecem ao longo do texto:

- **Importante** — informação que muda o resultado do passo.
- **Pegadinha** — comportamento que já custou tempo a alguém e não é óbvio pelo código.
- **Atenção** — risco de estrago real, inclusive em produção.
- **Quando usar** — critério para escolher entre dois caminhos.

### O que não está aqui

Este manual cobre a máquina do desenvolvedor. Três assuntos vizinhos moram em outros manuais da suíte:

- **Produção** — a VM, o systemd, o nginx, o deploy, os backups e os timers estão no Manual de Operações da VM. Nada neste documento deve ser executado contra o servidor de produção.
- **Câmera e liveness** — o script de reconhecimento contínuo, os modelos ONNX, a calibração dos limiares e as duas camadas de anti-spoofing estão no Manual de Liveness. Aqui a câmera aparece só como um dos quatro componentes do sistema.
- **Contas de terceiros e segredos** — AWS, Resend, Expo, Firebase, Sentry, e o backup de segredos cifrado com `age`, estão no Manual de Contas e Segredos. Aqui você aprende a **gerar** as chaves locais, não a recuperar as de produção.

> **Atenção:** nenhum valor de segredo aparece neste manual, por decisão de projeto. Onde uma chave é necessária, o texto diz onde ela mora e como gerar uma nova.

## Visão geral do sistema

### Os quatro componentes

O SCPI é um sistema de registro de presença acadêmica por reconhecimento facial. São quatro componentes independentes, em quatro pastas do mesmo repositório.

| Componente | Pasta | Tecnologia | Onde roda | Precisa em dev |
|---|---|---|---|---|
| API REST | `BackEnd/` | FastAPI + Python | VM de produção sob gunicorn; local sob uvicorn | Sim |
| Portal administrativo | `portal/` | HTML, CSS e JS estáticos | nginx em produção; servidor estático local | Sim |
| Aplicativo mobile | `app/` | Expo e React Native | Celular do aluno e do professor | Sim |
| Script da câmera | `BackEnd/scripts/` | Python e OpenCV | Máquina com câmera física na sala | Não |

### A API

`BackEnd/api.py` é o ponto de entrada. Ele carrega o `.env`, inicializa o Sentry, aplica as migrations do banco, sobe o agendador de tarefas e monta nove routers: `public`, `auth`, `admin`, `alunos`, `professores`, `turmas`, `chamadas`, `relatorios` e `notificacoes`.

Toda a lógica de domínio vive em `services/`, o acesso ao banco em `repositories/`, e as integrações externas em `infra/`. Não há ORM: o SQL é escrito à mão e sempre parametrizado.

### O portal administrativo

O portal é HTML estático com módulos ES nativos. Não existe build de JavaScript. Existe build de **CSS**: o Tailwind é compilado pelo CLI e o resultado, `portal/css/tailwind.css`, vai versionado no repositório, porque a VM de produção não roda Node.

O portal é onde o administrador cadastra alunos, professores, turmas, horários e o banco de rostos, e de onde saem os relatórios em PDF.

### O aplicativo mobile

O app atende aluno e professor, com rotas separadas por perfil sob `app/app/`. Usa Expo Router para navegação baseada em arquivos. O professor abre e fecha chamadas; o aluno cadastra biometria, acompanha frequência, dá consentimento LGPD e exporta os próprios dados.

### O script da câmera

Um processo Python autônomo que roda na máquina da sala, autenticado por um token de serviço emitido **por sala**. Ele detecta rostos, captura um burst de frames, aplica o liveness local e só então chama o AWS Rekognition. Não é necessário para desenvolver as outras três partes.

### Como os quatro conversam

```text
Camera (BackEnd/scripts)  --HTTP + token de sala-->  API (BackEnd)
Portal (portal/)          --HTTP + cookie httpOnly-->  API
App mobile (app/)         --HTTP + cookie httpOnly-->  API
                                                        |
                                     PostgreSQL  <-------+-------> AWS Rekognition e S3
                                                        |
                                              Resend (e-mail) e Expo Push (FCM)
```

A API é o único componente que fala com o banco, com a AWS, com o Resend e com o serviço de push. Portal, app e câmera só falam HTTP com a API.

## Pré-requisitos

### Ferramentas e versões

A coluna "Alvo do projeto" é a versão que o CI e a produção usam. A coluna "Medido" é o que estava instalado na máquina de referência quando este manual foi escrito.

| Ferramenta | Alvo do projeto | Como conferir | Medido |
|---|---|---|---|
| Python | 3.12 | `python --version` | Python 3.13.5 |
| Node.js | 20 | `node --version` | v22.18.0 |
| npm | acompanha o Node | `npm --version` | 11.16.0 |
| PostgreSQL | 16 | `psql --version` | psql (PostgreSQL) 17.6 |
| Git | qualquer versão recente | `git --version` | 2.49.0.windows.1 |

O alvo de Python vem de `.github/workflows/tests.yml`, que fixa `python-version: "3.12"`, e da VM de produção. O alvo de Node vem do mesmo arquivo, `node-version: "20"`, nos jobs `frontend` e `portal-css`. O alvo de PostgreSQL vem do service `postgres:16` do mesmo workflow.

> **Importante:** a máquina de desenvolvimento atual está **à frente da produção** nas três versões que importam: roda Python 3.13.5 contra os 3.12 do CI e da VM, Node 22.18.0 contra o Node 20 do CI, e PostgreSQL 17.6 contra o Postgres 16 do CI e da produção. A suíte de 842 testes passa assim. Versão mais nova funciona hoje, mas quem for reproduzir um problema de CI ou de produção precisa usar as versões-alvo, não as da própria máquina, e quem montar uma máquina nova precisa saber que está adiantado, não alinhado.

### Contas e serviços externos

Para desenvolver as telas, os relatórios, o fluxo de chamada e a maior parte da API, você precisa apenas de Python, Node, PostgreSQL e Git.

As contas de terceiros só são necessárias para exercitar as funcionalidades que dependem delas:

- **AWS** com Rekognition e S3 — cadastro e reconhecimento de biometria facial.
- **Resend** — envio de e-mail de recuperação de senha e de senha temporária.
- **Expo e EAS** — build do app e notificações push.
- **Sentry** — telemetria de erro; em desenvolvimento normalmente fica desligado.

A API **sobe sem nenhuma dessas contas configuradas**. A ausência de credencial AWS ou de chave Resend só produz aviso no log, nunca falha de startup. A obtenção das credenciais está no Manual de Contas e Segredos.

### Modelos ONNX

Os dois modelos de visão computacional usados pelo liveness ficam em `BackEnd/scripts/models/` e **não são versionados** — o `.gitignore` exclui `BackEnd/scripts/models/*.onnx`. Eles só são necessários na máquina com câmera física. Se você não vai mexer no liveness, ignore-os.

## Clonar e configurar

### Clonar o repositório

A partir da pasta onde você guarda seus projetos:

```bash
git clone https://github.com/Gustavo-Falci/SCPI.git
cd SCPI
```

O `cd SCPI` deixa você na **raiz do repositório**. É de lá que partem todos os blocos seguintes.

O repositório é **privado**. Sem acesso concedido à sua conta do GitHub o clone falha na autenticação.

### Criar o ambiente virtual

O ambiente virtual fica na **raiz do repositório**, na pasta `venv/`, que é ignorada pelo Git. Os dois blocos abaixo rodam a partir da raiz.

Windows, PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux ou macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

> **Pegadinha:** o `README.md` manda criar o venv de dentro de `BackEnd/`, com `python -m venv ../venv`. É o mesmo destino: a pasta `venv/` na raiz. Criar um segundo venv dentro de `BackEnd/` funciona, mas deixa dois ambientes na máquina e nenhum aviso sobre qual está ativo.

### Instalar as dependências Python

A partir da raiz do repositório, com o venv ativo:

```bash
cd BackEnd
pip install -r requirements.txt -r requirements-dev.txt
```

Este bloco deixa você dentro de `BackEnd/`.

Esta é exatamente a linha que o CI executa no job `pytest (BackEnd)`. O `requirements.txt` traz a API, o banco, a AWS, o PDF e a visão computacional; o `requirements-dev.txt` traz só as ferramentas de teste, propositalmente fora do arquivo de produção.

Três pacotes precisam de instalação à parte:

| Pacote | Quando instalar | Por quê |
|---|---|---|
| `tzdata` | Sempre, no Windows | O `ZoneInfo` do Python não encontra o banco de fusos do sistema operacional no Windows. Está documentado no cabeçalho de `requirements-dev.txt` e não entra em nenhum requirements. |
| `python-docx` | Para gerar os manuais desta suíte | `docs/gerar_manuais.py` importa `docx`, e o pacote não está em nenhum dos dois arquivos de requirements. |
| Modelos ONNX | Só na máquina com câmera | Não são pacotes pip; são arquivos baixados à parte, descritos no Manual de Liveness. |

Ainda dentro de `BackEnd/`:

```bash
pip install tzdata python-docx
```

> **Pegadinha:** `psycopg2-binary` costuma falhar de instalar no Windows quando o pip decide compilar a partir do fonte. Ver o capítulo de problemas conhecidos.

### Criar o arquivo .env

Existe **um único** `.env`, na raiz do repositório. Ele alimenta a API, os scripts do backend, o script da câmera e — via `npm run sync-env` — o app mobile.

> **Atenção:** este passo roda **na raiz do repositório**, e o passo anterior deixou você em `BackEnd/`. Por isso os dois blocos abaixo começam com `cd ..`. Rodados de dentro de `BackEnd/`, eles falham: `BackEnd/.env.example` não existe.

Linux ou macOS, a partir de `BackEnd/`:

```bash
cd ..
cp .env.example .env
```

Windows, PowerShell, a partir de `BackEnd/`:

```powershell
cd ..
Copy-Item .env.example .env
```

Se você já estiver na raiz, pule o `cd ..`. Para conferir onde está, use `pwd` no shell POSIX ou `Get-Location` no PowerShell: a pasta certa é a que contém `README.md`, `.env.example` e `schema_inicial.sql`.

> **Pegadinha:** várias mensagens de erro do backend dizem "configure no arquivo `BackEnd/.env`". Esse arquivo **não existe**. O código usa `load_dotenv(find_dotenv())`, que sobe a árvore de diretórios até achar o `.env` da raiz. Criar um `.env` dentro de `BackEnd/` faz o `find_dotenv()` parar nele e ignorar o da raiz, deixando dois arquivos de configuração divergentes.

### Quais blocos do .env preencher

O `.env.example` está dividido em doze blocos numerados, um por subsistema. Uma máquina de desenvolvimento **não** precisa de todos.

| Bloco | Assunto | Máquina de dev | Observação |
|---|---|---|---|
| 1 | Ambiente | Deixar vazio | `ENVIRONMENT` vazio mantém `/docs` acessível e não força HSTS no navegador. `ALLOWED_ORIGINS` vazio faz a API aceitar `http://localhost:3000`, `http://localhost:8081` e `http://localhost:19006`. |
| 2 | Banco de dados | **Obrigatório** | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD`. A ausência de qualquer uma derruba a API no import. As demais têm default. |
| 3 | Autenticação e sessão | **Obrigatório** | `SECRET_KEY` com no mínimo 32 caracteres. As outras três têm default. |
| 4 | AWS | Só para biometria | Sem elas a API sobe e registra aviso no log. `AWS_REGION`, `COLLECTION_ID` e `BUCKET_NAME` têm default no código. |
| 5 | Resend | Só para e-mail | Sem a chave, recuperação de senha e envio de senha temporária ficam indisponíveis, com aviso no log. |
| 6 | Bootstrap do admin | Preencher uma vez | Consumido por `scripts/criar_admin.py` para criar o primeiro usuário. `ADMIN_SENHA` exige 8 caracteres ou mais. |
| 7 | Clientes | Preencher `EXPO_PUBLIC_API_URL` | É a única variável do bloco que algum código lê. Ver a pegadinha logo abaixo. |
| 8 | Câmera — conexão | **Ignorar** | Só é lido na máquina com câmera física. |
| 9 | Câmera — liveness | **Ignorar** | Só é lido na máquina com câmera física. |
| 10 | LGPD | **Obrigatório** | `SCPI_EXPORT_HMAC_KEY` derruba a API no import se faltar. `SCPI_PRIVACY_URL` é opcional. |
| 11 | Observabilidade | Deixar vazio | `SENTRY_DSN` vazio desativa o envio. Em dev, normalmente fica sem. |
| 12 | Desenvolvimento e testes | Deixar **vazio** | Ver o alerta sobre `SCPI_RUN_DB_TESTS` no capítulo de testes. |

> **Pegadinha:** `VITE_API_URL`, no bloco 7, não é lida por nenhum código do repositório. Ela sobrevive no `.env.example` e no `README.md`, mas o portal lê a URL da API de `portal/js/env.js`. Preenchê-la não tem efeito nenhum.

### Gerar as chaves locais

Duas variáveis são chaves criptográficas que **você mesmo gera**, uma vez, na sua máquina. Elas não são compartilhadas, não vêm de nenhum cofre e não têm relação com as de produção.

Os dois comandos abaixo não dependem da pasta; só exigem o venv ativo.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

O resultado vai em `SECRET_KEY`. É a chave de assinatura do JWT em HS256. O backend recusa subir com menos de 32 caracteres.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

O resultado vai em `SCPI_EXPORT_HMAC_KEY`. É a chave que assina o manifesto de integridade do export LGPD.

> **Atenção:** trocar a `SECRET_KEY` invalida todas as sessões emitidas com a anterior. Em desenvolvimento isso só significa refazer o login. Em produção significa deslogar todo mundo.

## Banco de dados local

### Criar o banco

Instale o PostgreSQL e crie um banco vazio cujo nome bata com o `DB_NAME` do seu `.env`:

```sql
CREATE DATABASE scpi_db;
```

Não é preciso criar nenhuma tabela à mão.

### O schema

Existem dois caminhos para o schema, e o segundo torna o primeiro dispensável.

O arquivo `schema_inicial.sql`, na raiz, é um dump das tabelas base. Aplicá-lo é opcional. O bloco abaixo roda **a partir da raiz do repositório**: o caminho do arquivo é relativo, e de dentro de `BackEnd/` o `psql` não o encontra.

```bash
psql -U postgres -d scpi_db -f schema_inicial.sql
```

As migrations vivem em `BackEnd/infra/migrations.py`, escritas em Python, e são aplicadas **automaticamente no startup da API**. A primeira etapa, `ensure_base_schema()`, cria as tabelas base com `CREATE TABLE IF NOT EXISTS`. Em banco vazio, subir a API já monta tudo.

> **Quando usar:** aplique `schema_inicial.sql` apenas se quiser inspecionar o schema antes de subir a API, ou reproduzir um estado específico. Para o fluxo normal, crie o banco vazio e deixe a API montar o resto.

### Como as migrations se comportam

São vinte e uma funções `ensure_*` idempotentes, encadeadas e executadas por `run_all()` dentro do `lifespan` da aplicação.

| Característica | Comportamento | Motivo |
|---|---|---|
| Idempotência | Rodar de novo não quebra nem duplica | Os quatro workers do gunicorn sobem juntos em produção |
| Advisory lock | `run_all()` serializa a execução no próprio Postgres | Sem ele, workers concorrentes colidiam no `CREATE TABLE` |
| Fail-loud | Qualquer falha aborta o boot com `RuntimeError` | Schema incompleto com a API no ar gera erros 500 aleatórios longe da causa |

> **Importante:** se a API não sobe e o erro cita uma etapa `ensure_alguma_coisa`, o problema é migration, não código de aplicação. O nome da etapa vem junto na exceção, de propósito.

### Tabelas criadas

O conjunto completo, depois de todas as migrations: `Usuarios`, `Alunos`, `Professores`, `Turmas`, `Turma_Alunos`, `Chamadas`, `Presencas`, `Horarios_Aulas`, `Colecao_Rostos`, `ConsentimentosLGPD`, `RefreshTokens`, `PasswordResetCodes`, `PushTokens`, `PushReceiptsPendentes`, `camera_tokens`, `login_attempts` e `rate_limit_buckets`.

### Criar o primeiro usuário administrador

Com o `.env` preenchido e o banco no ar, a partir da raiz do repositório, com o venv ativo:

```bash
cd BackEnd
python scripts/criar_admin.py
```

O script lê `ADMIN_NOME`, `ADMIN_EMAIL` e `ADMIN_SENHA` do bloco 6 do `.env`, recusa senha com menos de 8 caracteres e cria o usuário com a senha já hasheada.

> **Pegadinha:** o `README.md` mostra este script sendo chamado com as variáveis na frente da linha de comando. Não funciona: o script chama `load_dotenv(find_dotenv(), override=True)`, e o `override=True` faz o valor do `.env` **vencer** o valor do ambiente. Preencha o bloco 6 do `.env` em vez de passar variáveis inline. Em PowerShell o prefixo inline nem sequer é sintaxe válida.

## Subir cada parte

### Três terminais

API, portal e app ficam em execução ao mesmo tempo, e cada um ocupa o seu terminal até você interrompê-lo. Abra **três terminais, todos na raiz do repositório**, e use um para cada parte. É o que evita a confusão de pasta: cada terminal faz o seu `cd` uma única vez, a partir da raiz.

### A API

Terminal 1, a partir da raiz do repositório, com o venv ativo:

```bash
cd BackEnd
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

O `--host 0.0.0.0` é o que permite o celular da mesma rede alcançar a API. Sem ele, o uvicorn escuta só em `127.0.0.1` e o app mobile não conecta.

Quando funciona, você vê:

- No log, a aplicação das migrations e o resultado da verificação de conectividade com a AWS.
- `http://localhost:8000/` respondendo `{"mensagem": "API SCPI está rodando!"}`.
- `http://localhost:8000/docs` abrindo o Swagger com todos os endpoints.
- `http://localhost:8000/health` respondendo `{"status": "ok", "database": "ok"}` com status 200.

Se o banco estiver inacessível, `/health` responde 503 com `{"status": "degraded", "database": "error"}`. O detalhe do erro vai só para o log — nunca para a resposta.

> **Pegadinha:** `api.py` chama `load_dotenv(find_dotenv(), override=True)`. O `.env` **sobrescreve** variáveis já presentes no ambiente do shell. Exportar uma variável antes de subir a API não adianta se ela também estiver no `.env`.

> **Importante:** `/docs`, `/redoc` e `/openapi.json` só existem quando `ENVIRONMENT` **não** é `production`. Em produção eles são desligados de propósito, para não expor a superfície inteira da API a anônimos.

### O portal administrativo

Terminal 2, a partir da raiz do repositório:

```bash
cd portal
npm install
npm run build
python -m http.server 3000
```

O `npm run build` compila `src/input.css` para `css/tailwind.css` com o Tailwind CLI. O `python -m http.server` serve a pasta como arquivos estáticos, o que é suficiente porque não há build de JavaScript nem servidor de aplicação.

Quando funciona, `http://localhost:3000` abre a tela de login **com estilo aplicado**. Tela sem estilo é sintoma de CSS não compilado.

> **Pegadinha:** por padrão o portal local aponta para a **API de produção**. O arquivo `portal/js/env.js` define `window.__SCPI_API_URL__` com a URL pública, e `portal/js/config.js` só cai no fallback `http://localhost:8000` se essa variável não existir. Você fará login contra produção sem perceber.

#### Reapontar o portal para a API local

São **duas** edições manuais de arquivo, ambas obrigatórias. Fazer só a primeira produz um portal que não carrega nada.

**Passo 1 — trocar a URL da API.** Em `portal/js/env.js`, de:

```javascript
window.__SCPI_API_URL__ = 'https://api.scpi.me';
```

para:

```javascript
window.__SCPI_API_URL__ = 'http://localhost:8000';
```

**Passo 2 — liberar a origem local na CSP.** Em `portal/index.html`, na meta `Content-Security-Policy`, acrescentar `http://localhost:8000` à diretiva `connect-src`, que hoje é:

```text
connect-src 'self' https://api.scpi.me
```

O passo 2 é obrigatório porque uma API em `localhost:8000` é **outra origem** que o portal em `localhost:3000`. Sem a entrada na diretiva, o navegador bloqueia toda chamada, e o sintoma é uma tela que não carrega nada, sem erro visível fora do console.

> **Atenção:** nenhuma das duas edições pode ser commitada. As duas apontam o portal de produção para a máquina do desenvolvedor. Antes de commitar qualquer coisa, rode `git diff -- portal/js/env.js portal/index.html` a partir da raiz do repositório: a saída tem de estar vazia.

> **Atenção:** a CSP do portal não permite `'unsafe-inline'` em `script-src` nem em `style-src`. Nada de `onclick=` na marcação e nada de `<style>` avulso — há teste automatizado cobrando isso. Valor de estilo contínuo, como largura de barra, vai por `el.style` em JavaScript, que a CSP não bloqueia.

> **Importante:** mexeu em classe Tailwind no HTML ou no JS? Rode `npm run build` **antes de commitar** e commite o CSS junto. O CSS compilado é versionado e o job `portal css (build atualizado)` do CI recompila e falha se o arquivo commitado estiver defasado.

### O aplicativo mobile

Terminal 3, a partir da raiz do repositório:

```bash
cd app
npm install
npm run sync-env
npm start
```

O `sync-env` copia as linhas que começam com `EXPO_PUBLIC_` do `.env` da raiz para `app/.env`, porque o Metro bundler só lê o `.env` do diretório do próprio projeto. O script `start` já executa `sync-env` antes de subir o Metro — a chamada avulsa serve para conferir a saída, que informa quantas variáveis foram propagadas.

Quando funciona, o Metro abre com o QR code, e o app carrega no Expo Go ou no dev client.

Os alvos por plataforma, todos passando pelo `sync-env` antes. Ainda dentro de `app/`, e um de cada vez:

```bash
npm run android
npm run ios
npm run web
```

> **Pegadinha:** `EXPO_PUBLIC_API_URL` com `localhost` não funciona em celular físico. Para o aparelho, `localhost` é o próprio aparelho. Use o IP da sua máquina na rede local, e suba a API com `--host 0.0.0.0`.

Se a variável não chegar ao app, o erro é explícito e vem de `app/services/api.js`: `EXPO_PUBLIC_API_URL não definida. Execute 'npm run sync-env' na pasta app antes de iniciar.`

> **Atenção:** os pacotes gerenciados pelo SDK do Expo só podem ser atualizados com `expo install --fix`. O Dependabot está configurado para ignorar a stack Expo por esse motivo. Atualizar um deles com `npm install` à mão quebra a compatibilidade do SDK.

### O script da câmera

Não é necessário para desenvolver API, portal ou app. Ele exige câmera física, os modelos ONNX e um token de serviço emitido para uma sala específica. O procedimento completo está no Manual de Liveness.

## Rodar os testes

### A suíte do BackEnd

A partir da raiz do repositório, com o venv ativo:

```bash
cd BackEnd
python -m pytest tests -v
```

É a linha que o CI executa. Na máquina de referência, a suíte completa levou 16 segundos e terminou com **761 testes passando e 81 pulados**, num total de 842.

Os 81 pulados são os testes de integração com banco, que ficam desativados por padrão. Suíte verde com pulados é o resultado esperado em máquina local.

A suíte é mockada de ponta a ponta: não conecta em banco, não chama a AWS e não envia e-mail. Ela cobre migrations, liveness e burst, importação de CSV, export LGPD, consentimento, rate limit, lockout de login e as guardas textuais do portal e do SQL.

### O gate SCPI_RUN_DB_TESTS

Os testes de integração só rodam com `SCPI_RUN_DB_TESTS=1`. Sem isso, eles são pulados sem sequer tentar conectar.

> **Atenção:** nunca defina `SCPI_RUN_DB_TESTS=1` na máquina local. O `.env` de desenvolvimento aponta o `DB_HOST` para o banco de **produção**, e as fixtures de integração executam `TRUNCATE` nas tabelas. Ligar o gate localmente apaga dados de produção.

O lugar certo desses testes é o CI, que sobe um serviço `postgres:16` descartável e usa banco, usuário e senha próprios (`scpi_test`), definidos em `.github/workflows/tests.yml`.

Se precisar validar SQL contra banco real fora do CI, o caminho combinado no projeto é entregar a consulta pronta para ser executada à mão em um cliente de banco, com os olhos de quem tem a conexão aberta. O caminho alternativo é pular a validação.

### Os testes do gerador de manuais

A suíte desta própria suíte de documentos fica em `docs/` e roda **a partir da raiz do repositório**. O bloco anterior deixou você em `BackEnd/`, então este começa com `cd ..`:

```bash
cd ..
python -m pytest docs/ -q
```

Na máquina de referência: **29 testes passando** em 0,28 segundo. Ela exige o `python-docx` instalado e valida o parser da fonte Markdown, a numeração hierárquica, as tabelas, os callouts e a geração do arquivo `.docx`.

### Gerar os manuais

A partir da raiz do repositório:

```bash
python docs/gerar_manuais.py
```

Sem argumento, o comando regera todos os manuais. Com o nome de um arquivo, regera só aquele. A saída vai para `docs/dist/`.

### O que o CI roda

O workflow `.github/workflows/tests.yml` dispara em push para `main` e em Pull Request, quando o diff toca `BackEnd/`, `portal/`, `app/` ou o próprio workflow.

| Job | O que faz | Como reproduzir localmente |
|---|---|---|
| `pytest (BackEnd)` | Python 3.12, service `postgres:16`, gate de banco ligado | `python -m pytest tests -v` dentro de `BackEnd/` |
| `tsc + eslint (app)` | Checagem de tipos e lint do app, com zero warnings tolerados | `npx tsc --noEmit` e `npm run lint` dentro de `app/` |
| `portal css (build atualizado)` | Recompila o Tailwind e falha se o CSS commitado divergir | `npm run build` dentro de `portal/` e `git diff` limpo |

> **Importante:** a branch `main` não é protegida e falha de CI não bloqueia merge. A disciplina de rodar os testes antes de abrir o Pull Request é o que substitui a proteção.

## Primeiro Pull Request

### Criar a branch

Os comandos de Git funcionam de qualquer pasta dentro do repositório. Antes de criar, veja o que já existe — pode haver uma branch adiantada para o assunto:

```bash
git branch
```

Depois crie a sua, **sempre** com `--no-track`:

```bash
git checkout -b feat/minha-funcionalidade --no-track origin/main
```

> **Atenção:** nunca omita o `--no-track`. Sem ele o upstream da branch vira `origin/main`, e um `git push` sem argumentos empurra o commit **direto para a main**, contornando Pull Request, revisão e a política de squash. Aconteceu em 2026-07-31, com a branch `chore/limpeza-pos-chamada-explicita`. Não foi revertido: reescrever histórico já publicado seria pior.

Confira a linha que o Git imprime ao criar a branch. Se ela disser `set up to track 'origin/main'`, corrija antes de commitar qualquer coisa.

### Antes de commitar

- Suíte do BackEnd verde.
- Se mexeu em classe Tailwind, `npm run build` rodado em `portal/` e o CSS commitado junto.
- Se mexeu no app, `npx tsc --noEmit` e `npm run lint` limpos.
- Nenhum segredo no diff. O `.env` está no `.gitignore`, mas chave colada em código ou em teste passa.

### Mensagem de commit

O projeto usa Conventional Commits, em português.

| Prefixo | Quando usar |
|---|---|
| `feat:` | Funcionalidade nova |
| `fix:` | Correção de defeito |
| `refactor:` | Mudança de estrutura sem mudança de comportamento |
| `docs:` | Documentação, incluindo os manuais desta suíte |
| `chore:` | Manutenção, dependências, configuração |
| `test:` | Testes, sem mudança de código de produção |

### Squash merge e o que ele implica

Os Pull Requests são integrados por **squash merge**. Toda a branch entra na `main` como um único commit novo, e a branch de origem perde parentesco com a `main`.

> **Atenção:** depois que um Pull Request é mergeado, não acrescente commits àquela branch. O Pull Request seguinte, aberto a partir dela, conflita em todos os arquivos por história divergente — sem conflito real de conteúdo. Aconteceu em 2026-07-20.

O procedimento correto após um merge é apagar a branch e criar outra a partir de `origin/main`. Se já houver commits novos numa branch mergeada, a saída sem reescrever histórico é:

```bash
git checkout -b nova origin/main
git cherry-pick <sha-do-commit-novo>
```

> **Pegadinha:** para saber se um commit ficou de fora da `main`, comparar SHA **não serve**. O squash reescreve tudo e nenhum SHA da branch aparece na `main`. Confira pelo conteúdo, com `git show origin/main:<arquivo>`.

### Abrir o Pull Request

Abra o Pull Request contra `main`, descrevendo o que muda e por quê. Não referencie por caminho os artefatos de planejamento em `docs/superpowers/`: eles são locais, estão no `.gitignore` e não existem para quem lê o Pull Request. Referencie pelo conteúdo.

> **Importante:** no fluxo atual do projeto, os commits e a abertura de Pull Request são executados pelo responsável pelo repositório. Assistentes automatizados que trabalham no código preparam a mudança e a mensagem, mas não executam `git commit`, `git push` nem criam o Pull Request.

## Verificação

Ao final da montagem, estas são as provas de que o ambiente está inteiro. Nenhuma delas depende de conta de terceiros.

| Prova | Como conferir | Resultado esperado |
|---|---|---|
| Dependências instaladas | `pip install -r requirements.txt -r requirements-dev.txt` em `BackEnd/` | Termina sem erro |
| Banco alcançável e schema aplicado | Subir a API e ler o log | Migrations aplicadas, sem exceção de etapa `ensure_*` |
| API no ar | Abrir `http://localhost:8000/health` | Status 200 com `{"status": "ok", "database": "ok"}` |
| Superfície da API visível | Abrir `http://localhost:8000/docs` | Swagger lista os endpoints dos nove routers |
| Portal servido e estilizado | Abrir `http://localhost:3000` | Tela de login com estilo aplicado |
| Portal conversando com a API | Fazer login com o usuário criado por `criar_admin.py` | Entra no painel; nenhum bloqueio de CSP no console |
| App conectando | `npm start` em `app/` e abrir no aparelho | Tela de login carrega, sem o erro de `EXPO_PUBLIC_API_URL` |
| Suíte verde | `python -m pytest tests -v` em `BackEnd/` | 761 passando e 81 pulados |
| Gerador de manuais | `python -m pytest docs/ -q` | 29 passando |

> **Quando usar:** repita esta lista inteira depois de qualquer mudança grande de ambiente — troca de versão de Python, recriação do venv, mudança do `.env`. É mais rápido que descobrir a peça quebrada no meio de uma alteração de código.

## Problemas conhecidos

### Tabela de sintomas

| Sintoma | Causa | Solução |
|---|---|---|
| API não sobe: `SECRET_KEY ausente ou fraca` | `SECRET_KEY` vazia ou com menos de 32 caracteres | Gerar com `python -c "import secrets; print(secrets.token_urlsafe(48))"` e colar no bloco 3 do `.env` |
| API não sobe: `SCPI_EXPORT_HMAC_KEY não definida` | Bloco 10 do `.env` vazio | Gerar com `python -c "import secrets; print(secrets.token_hex(32))"` |
| API não sobe: `Variáveis de ambiente obrigatórias não configuradas` | Falta alguma das cinco variáveis `DB_` | Preencher o bloco 2 do `.env` por inteiro |
| API não sobe com erro citando uma etapa `ensure_*` | Migration falhou; o startup é fail-loud de propósito | Corrigir o acesso ao banco ou a migration. A API não sobe com schema incompleto, e isso é intencional |
| API sobe, mas `/health` responde 503 | Banco inacessível ou credencial errada | Conferir o bloco 2 do `.env` e se o PostgreSQL está no ar. A resposta não traz detalhe: o erro está no log |
| Portal abre sem nenhum estilo | `npm run build` não rodou; `css/tailwind.css` desatualizado | `cd portal` e `npm run build` |
| Portal carrega, mas nenhuma tela traz dados | A CSP bloqueia a chamada para `localhost:8000` | Acrescentar `http://localhost:8000` ao `connect-src` da meta CSP em `portal/index.html`, localmente, sem commitar |
| Portal mostra dados que você não cadastrou | `portal/js/env.js` aponta para a API de produção | Trocar o valor de `window.__SCPI_API_URL__` para `http://localhost:8000`, localmente, sem commitar |
| Botão do portal não faz nada, sem erro no console | Handler inline `onclick=` na marcação, bloqueado pela CSP | Usar delegação de evento em JavaScript. Há teste textual cobrando isso |
| App não conecta na API | `EXPO_PUBLIC_API_URL` com `localhost` | Trocar pelo IP da máquina na rede local e subir a API com `--host 0.0.0.0` |
| App acusa `EXPO_PUBLIC_API_URL não definida` | `app/.env` desatualizado ou ausente | `npm run sync-env` dentro de `app/` |
| `pip install` falha em `psycopg2` no Windows | O pip tentou compilar do fonte, sem Build Tools do Visual C++ | O projeto pina `psycopg2-binary`, que traz binário pronto. Garanta que está instalando pelo `requirements.txt` e com pip atualizado; não instale `psycopg2` sem o sufixo |
| Erro de fuso horário nos testes, só no Windows | `ZoneInfo` não acha o banco de fusos do sistema | `pip install tzdata` |
| `python docs/gerar_manuais.py` falha com `ModuleNotFoundError: docx` | `python-docx` não está em nenhum requirements | `pip install python-docx` |
| Teste textual do portal falha acusando o próprio arquivo que documenta o padrão | Guarda textual varre comentário como se fosse código | Já aconteceu três vezes no projeto. Isentar o arquivo que documenta o padrão, com o motivo escrito no teste |
| Pull Request novo conflita em todos os arquivos | Branch criada a partir de outra já mergeada por squash | Criar branch nova a partir de `origin/main` e usar `git cherry-pick` nos commits que faltam |
| Commit foi parar direto na `main` | Branch criada sem `--no-track` | Recriar a branch com `--no-track origin/main`. Se já foi para a `main`, não reescreva histórico publicado |

### Quando a saída diverge do README

O `README.md` é a fonte de contexto do projeto, mas nem todo trecho dele acompanhou o código. Onde este manual e o `README.md` discordam, o critério é a máquina e o código.

Divergências conhecidas e já refletidas neste manual:

- O `README.md` afirma que `window.__SCPI_API_URL__` é definido em `portal/index.html`. Ele é definido em `portal/js/env.js`, com a URL de produção.
- O `README.md` documenta `VITE_API_URL` como a URL da API consumida pelo portal. Nenhum código lê essa variável.
- O `README.md` chama `criar_admin.py` com variáveis inline. O script usa `override=True` ao carregar o `.env`, e o valor do arquivo vence o do ambiente.
- Mensagens de erro do backend citam `BackEnd/.env`. O arquivo lido é o `.env` da raiz.
- A wiki interna do projeto tem uma lista de versões de pacotes mais antiga que a do `requirements.txt`. O `requirements.txt` é a fonte correta.

## Referência rápida

### Comandos do dia a dia

| Ação | Comando | Pasta |
|---|---|---|
| Ativar o venv, PowerShell | `.\venv\Scripts\Activate.ps1` | Raiz |
| Ativar o venv, POSIX | `source venv/bin/activate` | Raiz |
| Instalar dependências Python | `pip install -r requirements.txt -r requirements-dev.txt` | `BackEnd/` |
| Subir a API | `uvicorn api:app --reload --host 0.0.0.0 --port 8000` | `BackEnd/` |
| Rodar a suíte | `python -m pytest tests -v` | `BackEnd/` |
| Criar o admin inicial | `python scripts/criar_admin.py` | `BackEnd/` |
| Compilar o CSS do portal | `npm run build` | `portal/` |
| Recompilar o CSS continuamente | `npm run watch` | `portal/` |
| Servir o portal | `python -m http.server 3000` | `portal/` |
| Propagar variáveis para o app | `npm run sync-env` | `app/` |
| Subir o Metro | `npm start` | `app/` |
| Checar tipos do app | `npx tsc --noEmit` | `app/` |
| Lint do app | `npm run lint` | `app/` |
| Testar o gerador de manuais | `python -m pytest docs/ -q` | Raiz |
| Gerar os manuais | `python docs/gerar_manuais.py` | Raiz |
| Criar branch de trabalho | `git checkout -b <nome> --no-track origin/main` | Raiz |

### Mapa de segredos

Nenhum valor aparece neste manual, e nenhum deve aparecer em commit.

| Segredo | Onde mora em dev | Como obter |
|---|---|---|
| `SECRET_KEY` | `.env` da raiz, bloco 3 | Você gera, com `secrets.token_urlsafe(48)`. Local, não compartilhada |
| `SCPI_EXPORT_HMAC_KEY` | `.env` da raiz, bloco 10 | Você gera, com `secrets.token_hex(32)`. Local, não compartilhada |
| `DB_PASSWORD` | `.env` da raiz, bloco 2 | Você define ao instalar o PostgreSQL local |
| `ADMIN_SENHA` | `.env` da raiz, bloco 6 | Você define. Mínimo de 8 caracteres |
| Credenciais AWS | `.env` da raiz, bloco 4 | Conta AWS do projeto. Ver o Manual de Contas e Segredos |
| `RESEND_API_KEY` | `.env` da raiz, bloco 5 | Painel do Resend. Ver o Manual de Contas e Segredos |
| `CAMERA_SERVICE_TOKEN` | `.env` da máquina da câmera, bloco 8 | Emitido por sala com `scripts/camera_token.py`. Ver o Manual de Liveness |
| `SENTRY_DSN` | `.env` da raiz, bloco 11 | Projeto no Sentry. Opcional em dev |
| Chaves de produção | Nunca na máquina de dev | Backup cifrado com `age`, com a chave privada fora da VM. Ver o Manual de Contas e Segredos |

> **Atenção:** o `.env` e o `.env.bak` estão no `.gitignore`, mas o `.gitignore` não protege contra chave colada dentro de código, de teste ou de arquivo de exemplo. O CI roda uma varredura de segredos, e o scan agendado varre o histórico completo do repositório.

### Arquivos-fonte deste manual

Cada afirmação deste documento foi conferida contra um destes arquivos ou contra a saída de um comando executado na máquina de referência.

| Arquivo | O que fixa |
|---|---|
| `README.md` | Visão geral, arquitetura e comandos de referência |
| `.env.example` | Os doze blocos de configuração e o que cada variável faz |
| `BackEnd/requirements.txt` | Dependências de produção e os pins com motivo escrito |
| `BackEnd/requirements-dev.txt` | Dependências de teste e a nota sobre `tzdata` no Windows |
| `BackEnd/api.py` | Ordem do startup, migrations no lifespan, CORS e desligamento do `/docs` |
| `BackEnd/core/auth_utils.py` | Exigência de 32 caracteres na `SECRET_KEY` |
| `BackEnd/core/config.py` | Exigência da `SCPI_EXPORT_HMAC_KEY` e defaults da AWS |
| `BackEnd/infra/database.py` | As cinco variáveis `DB_` obrigatórias |
| `BackEnd/infra/migrations.py` | `run_all()`, advisory lock e comportamento fail-loud |
| `BackEnd/routers/public.py` | Respostas de `/` e `/health` |
| `BackEnd/scripts/criar_admin.py` | Bootstrap do admin e o `override=True` |
| `portal/package.json` | Scripts `build` e `watch` do Tailwind |
| `portal/js/env.js` e `portal/js/config.js` | De onde o portal tira a URL da API |
| `portal/index.html` | A política de CSP do portal |
| `app/package.json` | Scripts do app e versões do SDK do Expo |
| `app/scripts/sync-env.js` | Propagação das variáveis `EXPO_PUBLIC_` |
| `app/services/api.js` | Erro explícito quando a URL da API não chega ao app |
| `.github/workflows/tests.yml` | Versões-alvo de Python e Node, os três jobs e o gate de banco |
| `.gitignore` | O que não vai para o repositório |
| `docs/gerar_manuais.py` | Regras da fonte Markdown desta suíte |
