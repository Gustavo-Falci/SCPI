# SCPI — Sistema de Controle de Presença Inteligente

Sistema acadêmico de registro de presença com reconhecimento facial via AWS Rekognition. Composto por API REST (FastAPI), portal web administrativo (HTML/JS estático) e aplicativo mobile (Expo/React Native).

---

## Sumário

- [Visão Geral](#visão-geral)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Liveness e Anti-Spoofing](#liveness-e-anti-spoofing)
- [Pré-requisitos](#pré-requisitos)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Instalação e Execução](#instalação-e-execução)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Admin Portal (Estático)](#admin-portal-estático)
  - [Aplicativo Mobile (Expo)](#aplicativo-mobile-expo)
  - [Script de Câmera (Sala de Aula)](#script-de-câmera-sala-de-aula)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Scripts Utilitários](#scripts-utilitários)
- [Endpoints da API](#endpoints-da-api)
- [Banco de Dados](#banco-de-dados)
- [Segurança e LGPD](#segurança-e-lgpd)
- [Testes](#testes)
- [CI e Análise Estática](#ci-e-análise-estática)
- [Operação](#operação)
- [Contribuição](#contribuição)

---

## Visão Geral

O SCPI automatiza o processo de chamada escolar usando reconhecimento facial em tempo real. Quando o professor abre uma chamada, a câmera fixa captura os rostos dos alunos presentes e registra a frequência automaticamente via AWS Rekognition, eliminando a chamada manual.

```
Câmera → Detecção facial (YuNet) → Burst de frames
                                        ↓
                   Liveness local: veto de tela + textura (ONNX, offline)
                                        ↓
                        AWS Rekognition (identificação) → FastAPI → PostgreSQL
                                                              ↓
                            Aluno recebe push (Expo/FCM) + e-mail (Resend)
```

O liveness roda **antes** do Rekognition e é local: frame reprovado não sai da máquina da câmera.

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI 0.136.1, Uvicorn (dev), Gunicorn + `uvicorn-worker` (produção), Python 3.12 |
| Banco de Dados | PostgreSQL 16 (pg8000 + psycopg2-binary) |
| Autenticação | JWT HS256 (PyJWT, sem `cryptography`) + bcrypt/passlib + cookies httpOnly + CSRF double-submit |
| Rate limiting | SlowAPI + `limits` com storage compartilhado em PostgreSQL |
| Reconhecimento Facial | AWS Rekognition + AWS S3 |
| Liveness (local) | OpenCV DNN — YuNet (detecção) + modelo de textura em ONNX |
| E-mail | Resend API |
| Push | Expo Push (FCM V1) |
| PDF (relatórios e export LGPD) | ReportLab |
| Observabilidade | Sentry SDK (`SENTRY_DSN`), endpoint `/health` |
| Admin Portal | HTML estático + Tailwind CSS 3.4 compilado via CLI (CSS versionado) + JS vanilla (módulos ES) |
| Mobile | Expo 55, React Native 0.83, React 19.2, TypeScript 5.9 |
| Navegação Mobile | Expo Router (file-based routing) |

---

## Arquitetura

```
SCPI/
├── BackEnd/                  # API REST FastAPI
│   ├── api.py                # Entry point (lifespan, middlewares, routers)
│   ├── routers/              # Endpoints por domínio
│   │   ├── public.py         # /health, /politica-privacidade
│   │   ├── auth.py           # Login, refresh, primeiro acesso, recuperação
│   │   ├── admin.py          # Gestão de usuários, turmas, rostos, relatórios
│   │   ├── alunos.py         # Dashboard, frequência, biometria, consentimento, export LGPD
│   │   ├── professores.py    # Dashboard do professor (prefixo /professor)
│   │   ├── turmas.py         # Turmas e alunos matriculados
│   │   ├── chamadas.py       # Abertura/fechamento de chamada + Rekognition
│   │   ├── relatorios.py     # Relatórios de frequência (JSON e PDF)
│   │   └── notificacoes.py   # Registro de push token
│   ├── core/                 # CSRF, security headers, limiter, errors, regras, máscaras, CSV
│   ├── services/             # Lógica de domínio + agendador (fechamento, purge, receipts)
│   ├── repositories/         # Acesso ao banco
│   ├── schemas/              # Pydantic
│   ├── infra/                # DB pool, AWS clients, PDF, ZIP, notificações
│   │   └── migrations.py     # Migrations em Python, aplicadas no startup
│   ├── migrations/           # SQL avulso (001_presenca_por_aula.sql)
│   ├── scripts/
│   │   ├── reconhecimento_tempo_real.py  # Loop da câmera
│   │   ├── anti_spoofing.py              # Textura (ONNX) + pose
│   │   ├── deteccao_tela.py              # Veto por região emissiva
│   │   ├── confirmacao_burst.py          # Consenso do burst e decisão
│   │   ├── registro_tracker.py           # Dedup de registro por aluno
│   │   ├── camera_token.py               # Emitir/revogar token de serviço por sala
│   │   ├── criar_admin.py
│   │   ├── verificar_receipts.py         # Receipts de push
│   │   ├── _validar_liveness.py          # Ferramenta de medição (coleta de amostras)
│   │   └── models/                       # ONNX (git-ignored)
│   ├── tests/                # Pytest (842 testes)
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── portal/                   # Admin portal (estático)
│   ├── index.html            # CSP sem 'unsafe-inline'
│   ├── privacy.html          # Política de privacidade (LGPD)
│   ├── src/input.css         # Fonte do Tailwind
│   ├── css/tailwind.css      # CSS compilado, VERSIONADO
│   ├── package.json          # Build do CSS (Node só em dev)
│   └── js/
│       ├── tabs/             # alunos, professores, turmas, rostos, relatórios, etc.
│       └── ...               # api.js, auth.js, config.js, state.js, toast.js
│
├── app/                      # App mobile (alunos e professores)
│   ├── app/                  # Rotas Expo Router
│   │   ├── (auth)/           # Login, primeiro acesso, recuperação
│   │   ├── (aluno)/          # Telas do aluno
│   │   └── (professor)/      # Telas do professor
│   ├── scripts/sync-env.js   # Propaga .env raiz → app
│   └── app.json
│
├── ops/                      # Operação da VM (units systemd, scripts)
│   ├── backup/               # Backup do Postgres (timer + bucket OCI)
│   ├── secrets/              # Backup de segredos (age)
│   ├── receipts/             # Timer de receipts de push
│   └── sql/                  # Consultas de verificação
│
├── docs/                     # Runbooks e manuais (versionado, exceto docs/superpowers/)
├── .memory/wiki/             # Base de conhecimento para agentes (MemWiki)
├── schema_inicial.sql        # Schema inicial
└── .env.example              # Template de variáveis
```

---

## Funcionalidades

### Administrador (Portal Web)
- Cadastro, edição (PATCH) e importação CSV de professores e alunos
- Criação e gestão de turmas e matrículas (com "Selecionar Todos") e desmatrícula em lote
- Configuração de horários de aulas
- Gestão do banco de rostos (AWS Rekognition + S3) com paginação, agrupamento, colunas configuráveis e exclusão em lote
- Inventário biométrico (divergências entre banco, Rekognition e S3)
- Relatórios de frequência por chamada, turma e período — com filtros, paginação e exportação em PDF

### Professor (App Mobile)
- Dashboard com turmas e horários
- Abertura de chamada (aciona a câmera da sala)
- Lista de presença em tempo real e ajuste manual antes de fechar
- Navegação por máquina de estados (Aberta → Fechada → home), com banner "Retomar chamada"
- Relatórios de frequência com filtros, paginação e PDF
- Encerramento manual de chamadas (o agendador fecha as expiradas)

### Aluno (App Mobile)
- Dashboard com percentual de frequência por turma (limite de 75%)
- Histórico detalhado de presenças e faltas
- Cadastro de biometria facial multi-ângulo (~4 FaceIds por aluno)
- Revogação da própria biometria
- Consentimento LGPD com trilha append-only e versionamento da política
- Visualização da grade de horários (ordem visual da semana)
- Export LGPD (Art. 18): ZIP com PDF + JSON + foto + manifesto HMAC
- Notificações por push (Expo/FCM) e e-mail ao registrar presença

### Câmera da Sala
- Script Python autônomo em execução contínua, autenticado por token de serviço **emitido por sala**
- Detecta rostos com YuNet, captura um burst e exige consenso do mesmo aluno
- Aplica o liveness local antes de chamar o Rekognition (ver seção abaixo)
- Informa a chamada da sala (`chamada_id`) ao registrar — a presença nunca cai na aula de outra turma
- Dedup por aluno dentro da janela da chamada

---

## Liveness e Anti-Spoofing

Ataque coberto: **celular ou monitor exibindo foto/vídeo de um aluno** diante da câmera.

Duas camadas, ambas locais e anteriores ao Rekognition:

1. **Veto por região emissiva** (`scripts/deteccao_tela.py`) — o rosto está dentro de uma área que emite luz? Rosto real não emite; rosto exibido está sempre dentro de uma tela acesa. Tem precedência sobre a textura, exige `TELA_MIN_FRAMES` frames do burst e é **fail-open de propósito**: erro no detector não veta, porque falta silenciosa de aluno legítimo é pior desfecho que um ataque que passa.
2. **Textura** (`scripts/anti_spoofing.py`, modelo ONNX) — score de vida por frame. Abaixo de `TEXTURE_FACE_MIN_PX` o modelo está fora da faixa em que foi treinado: o score vira `None` e o burst cai em **PENDENTE** (fail-closed).

Decisão do burst em `scripts/confirmacao_burst.py`: só `CONFIRMADO` registra presença; `PENDENTE` não registra.

A pose (`LIVENESS_POSE_STD_MIN`) é **advisory** enquanto `ENABLE_TEXTURE=1` — só é logada. Volta a ser gate no fallback `ENABLE_TEXTURE=0`.

**Limitações conhecidas:**

- O modelo de textura mede **nitidez** mais do que vida (correlação alta com a variância do laplaciano). Borrão de movimento derruba o score de rosto real; é característica de exposição/obturador/luz, não ajustável por parâmetro.
- Os limiares são calibrados **por câmera**. `TEXTURE_LIVENESS_MIN` e `TEXTURE_FACE_MIN_PX` precisam ser remedidos ao instalar uma câmera nova, com `scripts/_validar_liveness.py`.
- Câmera com rosto muito pequeno em quadro (20–55 px, caso de uma câmera voltada para a lousa) fica **fora da faixa útil** do modelo de textura e exige um gate geométrico próprio, ainda não implementado.
- `TELA_PERCENTIL` é percentil **da cena**: iluminação muito diferente da calibrada (sol direto, janela no quadro) pede nova medição.

---

## Pré-requisitos

- **Python** 3.12 (versão do CI e da produção)
- **Node.js** 20+ e npm (app mobile e build do CSS do portal — nenhum dos dois exige Node em produção)
- **PostgreSQL** 16+
- **Conta AWS** com Rekognition e S3 habilitados
- **Conta Resend** para envio de e-mails
- **Expo CLI** / **EAS CLI** — app mobile e builds de produção
- **Modelos ONNX** em `BackEnd/scripts/models/` — apenas na máquina com câmera (git-ignored; URLs no `.env.example`)

> Python 3.12, Node 20 e PostgreSQL 16 são os alvos do CI e da produção (fixados em `.github/workflows/tests.yml` e na VM). Versões mais novas funcionam normalmente numa máquina de desenvolvimento — a suíte não depende da versão exata.

---

## Configuração do Ambiente

```bash
cp .env.example .env
# preencha todos os campos obrigatórios
```

### AWS — Configuração Inicial

1. Crie um bucket S3 para armazenar as fotos dos rostos
2. Crie a coleção Rekognition:
   ```bash
   aws rekognition create-collection --collection-id sala_de_aula
   ```
3. Configure as credenciais AWS no `.env`

### Banco de Dados

Aplique o schema inicial:

```bash
psql -U postgres -d scpi_db -f schema_inicial.sql
```

As migrations são declaradas em `BackEnd/infra/migrations.py` (Python) e aplicadas automaticamente no startup da API — inclusive a criação das tabelas base (`ensure_base_schema`), o que torna o `schema_inicial.sql` dispensável em banco vazio. Falha de migration derruba o startup por design (fail-loud).

---

## Instalação e Execução

### Backend (FastAPI)

```bash
cd BackEnd

# Ambiente virtual
python -m venv ../venv
# Windows:
..\venv\Scripts\activate
# Linux/macOS:
source ../venv/bin/activate

# Dependências
pip install -r requirements.txt
# Para rodar os testes:
pip install -r requirements-dev.txt

# Servidor de dev
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/docs`

Produção (systemd, na VM):
```bash
gunicorn -w 4 -k uvicorn_worker.UvicornWorker api:app
```

---

### Admin Portal (Estático)

O portal não tem build de JS — mas **tem** build de CSS. O Tailwind é compilado pelo CLI e o resultado (`portal/css/tailwind.css`) vai versionado; a VM não roda Node.

```bash
cd portal
npm install
npm run build     # ou: npm run watch, durante o desenvolvimento
```

> Mexeu em classe Tailwind no HTML/JS? Rode `npm run build` **antes de commitar**, senão a mudança não chega a lugar nenhum.

Dev local:
```bash
cd portal
python -m http.server 3000
```

Acesso: `http://localhost:3000`

A URL da API é lida em `portal/js/config.js` a partir de `window.__SCPI_API_URL__`, definido em `portal/js/env.js` (carregado por `portal/index.html:18`):
```javascript
window.__SCPI_API_URL__ = 'https://api.scpi.me';
```
Por padrão aponta para produção — não há `<script>` inline, e não poderia haver: a CSP do portal (sem `'unsafe-inline'` em `script-src`) bloquearia. Para apontar o portal local para a API local são **duas** edições manuais, nenhuma delas commitável: trocar o valor em `portal/js/env.js` para `http://localhost:8000` **e** acrescentar `http://localhost:8000` ao `connect-src` da meta CSP em `portal/index.html` (sem essa segunda edição a CSP bloqueia a chamada, e a tela fica sem dados sem erro visível fora do console).

A CSP do portal **não** permite `'unsafe-inline'` em `script-src` nem em `style-src`: nada de handler inline (`onclick=`) nem de `<style>` avulso. Valor de estilo contínuo (largura de barra, etc.) vai por `el.style`, que a CSP não bloqueia. Há teste automatizado cobrando isso.

Produção: publicar `portal/` em qualquer web server (Nginx — ver `docs/runbooks/PORTAL_NGINX.md`).

---

### Aplicativo Mobile (Expo)

```bash
cd app
npm install

# Sincroniza variáveis do .env raiz para o app
npm run sync-env

# Inicia o Metro
npm start
```

Plataforma específica:
```bash
npm run android   # Emulador/dispositivo Android
npm run ios       # Simulador iOS (macOS)
npm run web       # Navegador
```

Build de produção via EAS:
```bash
eas build --platform android
eas build --platform ios
```

> Pacote gerenciado pelo SDK do Expo só se atualiza com `expo install --fix`. O Dependabot está configurado para **ignorar** a stack Expo justamente por isso.

---

### Script de Câmera (Sala de Aula)

Executar na máquina com câmera física conectada:

```bash
cd BackEnd
python scripts/reconhecimento_tempo_real.py
```

Requer no `.env`: `SCPI_API_URL`, `CAMERA_SERVICE_TOKEN`, `CAMERA_INDEX`, `FACE_MATCH_THRESHOLD_SALA` e os modelos ONNX em `scripts/models/` (`FACE_MODEL_PATH`, `TEXTURE_MODEL_PATH`).

O token é emitido **por sala** e vale só para ela:
```bash
python scripts/camera_token.py emitir --sala "Sala 101"
python scripts/camera_token.py revogar --id <id>
```

---

## Variáveis de Ambiente

### Banco de dados

| Variável | Descrição | Exemplo |
|---|---|---|
| `DB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco | `scpi_db` |
| `DB_USER` | Usuário do banco | `postgres` |
| `DB_PASSWORD` | Senha do banco | `senha_segura` |
| `DB_POOL_MIN` / `DB_POOL_MAX` | Pool de conexões | `2` / `10` |
| `DB_CONNECT_TIMEOUT` | Timeout (s) para abrir conexão; banco fora dá erro rápido (default `3`) | `3` |

### API e autenticação

| Variável | Descrição | Exemplo |
|---|---|---|
| `SECRET_KEY` | Chave JWT HS256 (`secrets.token_urlsafe(48)`) | `...` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiração do token | `60` |
| `ENVIRONMENT` | `production` habilita HSTS e hardenings HTTPS | `production` |
| `ALLOWED_ORIGINS` | Origens CORS (CSV) | `https://scpi.me,https://api.scpi.me` |

### AWS, e-mail e bootstrap

| Variável | Descrição | Exemplo |
|---|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Credenciais AWS | `AKIA...` |
| `AWS_REGION` | Região AWS | `us-east-1` |
| `COLLECTION_ID` | Coleção Rekognition | `sala_de_aula` |
| `BUCKET_NAME` | Bucket S3 das fotos | `faces-sala-aula-2025` |
| `RESEND_API_KEY` | Chave Resend | `re_...` |
| `RESEND_FROM_EMAIL` | Remetente | `SCPI <noreply@dominio>` |
| `ADMIN_NOME` / `ADMIN_EMAIL` / `ADMIN_SENHA` | Bootstrap do usuário admin | — |

### Clientes

| Variável | Descrição | Exemplo |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | URL da API consumida pelo app | `http://192.168.1.10:8000` |
| `SCPI_API_URL` | URL da API consumida pelo script da câmera | `http://localhost:8000` |

> A URL da API consumida pelo portal **não** vem de variável de ambiente: é definida em `portal/js/env.js` (`window.__SCPI_API_URL__`). Ver [Admin Portal (Estático)](#admin-portal-estático).

### Câmera e reconhecimento

| Variável | Descrição | Default |
|---|---|---|
| `CAMERA_SERVICE_TOKEN` | Token de serviço da câmera, emitido por sala via `scripts/camera_token.py` | — |
| `CAMERA_INDEX` | Índice do dispositivo de câmera (`1+` para webcam USB externa) | `0` |
| `FACE_MATCH_THRESHOLD_SALA` | Similaridade mínima do Rekognition na câmera fixa (0–100) | `90` |
| `FACE_MODEL_PATH` | Modelo YuNet de detecção facial (ONNX) | `BackEnd/scripts/models/face_detection_yunet_2023mar.onnx` |

### Liveness — burst e pose

| Variável | Descrição | Default |
|---|---|---|
| `BURST_FRAMES` | Frames capturados por burst quando um rosto é detectado | `5` |
| `BURST_MIN_MATCHES` | Matches do mesmo aluno exigidos no burst (consenso X-de-Y) | `3` |
| `BURST_DURACAO_S` | Duração da janela de captura do burst, em segundos | `2` |
| `LIVENESS_POSE_STD_MIN` | Magnitude mínima `hypot(std_yaw, std_pitch)`. **Advisory** com a textura ligada; vira gate no fallback `ENABLE_TEXTURE=0` | `3.0` |

### Liveness — textura (gate primário)

| Variável | Descrição | Default |
|---|---|---|
| `ENABLE_TEXTURE` | Liga (`1`) / desliga (`0`) o gate de textura | `1` |
| `TEXTURE_MODEL_PATH` | Modelo `best_model.onnx` **não-quantizado** (o quantizado usa `DynamicQuantizeLinear`, incompatível com `cv2.dnn`) | `BackEnd/scripts/models/best_model.onnx` |
| `TEXTURE_LIVENESS_MIN` | Limiar do score de vida (0..1). **Calibrar por câmera** | `0.08` |
| `TEXTURE_FACE_MIN_PX` | Piso do lado menor do bbox para a textura opinar; abaixo disso o burst vira PENDENTE (fail-closed) | `80` |

### Liveness — veto por tela

| Variável | Descrição | Default |
|---|---|---|
| `ENABLE_TELA` | Liga (`1`) / desliga (`0`) o veto por região emissiva | `1` |
| `TELA_PERCENTIL` | Percentil de luminância **da cena** que define "área emissiva" | `96` |
| `TELA_MIN_FRAMES` | Frames do burst que precisam acusar tela para vetar | `2` |

### LGPD e observabilidade

| Variável | Descrição | Exemplo |
|---|---|---|
| `SCPI_EXPORT_HMAC_KEY` | Chave HMAC do manifesto de export LGPD (`secrets.token_hex(32)`) | `...` |
| `SCPI_PRIVACY_URL` | URL pública da política; o `?app=1` esconde o link para o portal. A **versão** da política fica em `BackEnd/core/config.py`, não aqui | `https://admin.scpi.me/privacy.html?app=1` |
| `SENTRY_DSN` | DSN do Sentry; vazio desativa (dev normalmente fica sem) | `https://...` |

> A ferramenta de medição `scripts/_validar_liveness.py` usa ainda `LIVENESS_SAMPLES_DIR` e `LIVENESS_COND` (rótulo da condição medida). Nenhuma das duas é lida pelo fluxo de produção.

---

## Scripts Utilitários

### Criar usuário administrador

Preencha `ADMIN_NOME`, `ADMIN_EMAIL` e `ADMIN_SENHA` no bloco 6 do `.env` da raiz antes de rodar — o script chama `load_dotenv(..., override=True)`, então o `.env` sobrescreve qualquer valor passado inline na linha de comando:

```bash
cd BackEnd
python scripts/criar_admin.py
```

### Token de serviço da câmera

```bash
cd BackEnd
python scripts/camera_token.py emitir --sala "Sala 101"
python scripts/camera_token.py revogar --id <id>
```

### Câmera da sala (reconhecimento contínuo)

```bash
cd BackEnd
python scripts/reconhecimento_tempo_real.py
```

### Calibração do liveness (coleta de amostras)

```bash
cd BackEnd
LIVENESS_COND="porta_movimento" python scripts/_validar_liveness.py
```

### Verificação de receipts de push

```bash
cd BackEnd
python scripts/verificar_receipts.py
```

---

## Endpoints da API

Principais rotas (lista completa via Swagger UI em `/docs`):

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| `GET` | `/health` | Healthcheck com verificação do banco | Público |
| `GET` | `/politica-privacidade` | URL e versão vigente da política | Público |
| `POST` | `/auth/login` | Autenticação (cookies httpOnly, isento de CSRF) | Público |
| `POST` | `/auth/refresh` | Renovar token (isento de CSRF) | Autenticado |
| `POST` | `/auth/logout` | Encerrar sessão | Autenticado |
| `GET` | `/auth/session` | Perfil da sessão atual | Autenticado |
| `POST` | `/auth/alterar-senha-primeiro-acesso` | Definir senha inicial | Público (token) |
| `POST` | `/auth/esqueci-senha` · `/auth/verificar-codigo` · `/auth/redefinir-senha` | Fluxo de recuperação de senha | Público |
| `GET` | `/aluno/dashboard/{usuario_id}` | Dashboard do aluno | Aluno |
| `GET` | `/aluno/frequencias/{usuario_id}` | Frequências detalhadas | Aluno |
| `POST` | `/alunos/cadastrar-face` | Cadastrar biometria | Aluno |
| `GET` | `/alunos/status-angulos-face/{usuario_id}` | Ângulos já cadastrados | Aluno |
| `DELETE` | `/aluno/biometria/{usuario_id}` | Revogar biometria | Aluno |
| `GET` | `/aluno/consentimento/{usuario_id}` | Estado do consentimento LGPD | Aluno |
| `GET` | `/aluno/meus-dados/{usuario_id}?formato=zip` | Export LGPD (PDF+JSON+foto+HMAC) | Aluno |
| `POST` | `/notificacoes/registrar-token` | Registrar push token do dispositivo | Autenticado |
| `GET` | `/professor/dashboard/{usuario_id}` | Dashboard do professor | Professor |
| `GET` | `/turmas/{usuario_id}` | Turmas do usuário | Professor |
| `POST` | `/chamadas/abrir` | Abrir chamada | Professor |
| `GET` | `/chamadas/aberta/sala` | Chamada aberta da sala (consultada pela câmera) | Serviço |
| `POST` | `/chamadas/registrar_presenca_camera` | Registrar presença identificada | Serviço (token de sala) |
| `POST` | `/chamadas/{chamada_id}/ajustar` | Ajuste manual da lista | Professor |
| `POST` | `/chamadas/{chamada_id}/finalizar` | Fechar chamada | Professor |
| `GET` | `/professor/relatorios/chamadas` | Relatórios do professor (filtros; envelope paginado com `paginado=1`) | Professor |
| `GET` | `/professor/relatorios/chamadas/{chamada_id}?formato=pdf` | Relatório de uma chamada em PDF | Professor |
| `GET` | `/professor/relatorios/turmas/{turma_id}/frequencia` | Frequência consolidada da turma | Professor |
| `GET` `POST` `PATCH` | `/admin/professores` · `/admin/usuarios/professor` · `/admin/usuarios/professor/{id}` | Gestão de professores | Admin |
| `POST` | `/admin/importar-professores` | Importar professores via CSV | Admin |
| `GET` `POST` `PATCH` | `/admin/alunos` · `/admin/usuarios/aluno` · `/admin/alunos/{id}` | Gestão de alunos | Admin |
| `POST` | `/admin/turmas` · `/admin/horarios` | Criar turma e horários | Admin |
| `POST` | `/admin/turmas/{turma_id}/matricular-alunos` · `/desmatricular-alunos` · `/importar-alunos` | Matrículas | Admin |
| `GET` | `/admin/rostos/inventario` | Divergências banco ↔ Rekognition ↔ S3 | Admin |
| `DELETE` | `/admin/rostos/rekognition/{face_id}` · `/admin/rostos/rekognition/bulk` | Excluir rostos | Admin |
| `GET` | `/admin/relatorios/chamadas` | Todos os relatórios (filtros e PDF) | Admin |

---

## Banco de Dados

Tabelas do schema base:

| Tabela | Descrição |
|---|---|
| `usuarios` | Usuários do sistema (admin, professor, aluno) |
| `professores` | Dados específicos de professores |
| `alunos` | Dados específicos de alunos |
| `turmas` | Turmas/disciplinas |
| `turma_alunos` | Matrículas |
| `horarios_aulas` | Grade de horários das turmas |
| `chamadas` | Chamadas abertas/fechadas |
| `presencas` | Presença por aula (migração `001_presenca_por_aula.sql`) |
| `colecao_rostos` | Mapeamento aluno ↔ FaceId Rekognition (multi-ângulo) |
| `pushtokens` | Tokens de push por dispositivo |
| `refreshtokens` | Refresh tokens ativos |
| `passwordresetcodes` | Códigos de recuperação de senha |

As migrations em `infra/migrations.py` acrescentam ainda as tabelas de consentimento LGPD, de tokens de câmera por sala e o storage do rate limit.

Schema base: [`schema_inicial.sql`](./schema_inicial.sql).

---

## Segurança e LGPD

- Autenticação via cookies httpOnly + CSRF double-submit (rotas `/auth/login` e `/auth/refresh` isentas por design — o cookie jar do React Native motivou a isenção)
- JWT assinado em **HS256**; `cryptography` foi removida das dependências por ser superfície de advisory sem uso (há teste cobrando o algoritmo simétrico)
- HSTS, CSP e demais headers em `core/security_headers.py` (ativam com `ENVIRONMENT=production`)
- CSP do portal **sem `'unsafe-inline'`** em `script-src` e `style-src`
- Rate limiting via SlowAPI com **storage compartilhado em PostgreSQL** (vale entre os workers do Gunicorn) e **lockout progressivo de login**
- Token de serviço da câmera **por sala**, emitido e revogável por CLI
- 27 ErrorCodes padronizados (toast stack no portal, `useErrorToast` no mobile)
- Autorização por objeto revisada contra BOLA — o dono do recurso é conferido no backend, não inferido do path
- Telemetria de erros no Sentry com `LoggingIntegration` **desligada de propósito**: ela vazava RA/e-mail/IP por `logentry` e breadcrumbs, fora do alcance do `before_send`
- Export LGPD (Art. 18 §1): `/aluno/meus-dados?formato=zip` entrega PDF + JSON + foto + manifesto assinado com `SCPI_EXPORT_HMAC_KEY`
- Consentimento LGPD com trilha **append-only** e versão da política em `BackEnd/core/config.py`; o backend precisa ser atualizado **antes** do app
- Máscara de dado pessoal nos relatórios (PDF leva RA, não CPF) em `core/mascaras.py`
- Backups versionados e testados: Postgres (timer + bucket OCI, retenção 30 dias) e segredos (`age`, chave privada fora da VM)
- Decisão deliberada de **não** implementar MFA/TOTP

---

## Testes

```bash
cd BackEnd
pip install -r requirements-dev.txt
pytest
```

**842 testes** cobrindo backend, migrations, liveness/burst, CSV, export LGPD, consentimento, rate limit, lockout e guardas textuais (portal e SQL).

Testes de integração com banco são **opt-in**: sem `SCPI_RUN_DB_TESTS=1` eles são pulados sem tentar conectar.

```bash
SCPI_RUN_DB_TESTS=1 DB_HOST=localhost DB_NAME=scpi_test DB_USER=scpi_test DB_PASSWORD=scpi_test pytest
```

---

## CI e Análise Estática

| Workflow | Job | O que roda |
|---|---|---|
| `tests.yml` | pytest (BackEnd) | Python 3.12 + Postgres 16 de serviço, com `SCPI_RUN_DB_TESTS=1` |
| `tests.yml` | frontend | `tsc --noEmit` e `expo lint` no app |
| `tests.yml` | portal-css | Recompila o Tailwind e **falha se `portal/css/tailwind.css` commitado estiver defasado** |
| `security.yml` | Bandit | SAST Python |
| `security.yml` | pip-audit | SCA das dependências Python + SBOM CycloneDX |
| `security.yml` | Gitleaks | Segredos (o scan agendado varre o histórico completo; em PR, só o diff) |
| `security.yml` | npm audit | Dependências do app mobile, com allowlist explícita |

---

## Operação

- Produção em `/opt/scpi` (venv Python 3.12), serviço `scpi-api` sob systemd
- Deploy: `git pull` → `cd BackEnd && pip install -r requirements.txt --upgrade` → restart do `scpi-api`
- `GET /health` monitorado externamente a cada 5 minutos
- Timers systemd versionados em `ops/` (backup do Postgres, backup de segredos, receipts de push)
- Runbooks: `docs/runbooks/SECURITY_RUNBOOK.md`, `docs/runbooks/PORTAL_NGINX.md`

---

## Contribuição

1. Crie uma branch **sem tracking**, para que um `git push` sem argumentos não vá parar na `main`:
   ```bash
   git checkout -b feat/minha-funcionalidade --no-track
   ```
2. Faça commits seguindo [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
3. Abra um Pull Request

Convenção de commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.

PRs são integradas por **squash merge** — depois que a PR é mergeada, não acrescente commits àquela branch: a PR seguinte conflita.

Mexeu em classe Tailwind? `cd portal && npm run build` antes de commitar.
