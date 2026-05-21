# SCPI — Sistema de Controle de Presença Inteligente

Sistema acadêmico de registro de presença com reconhecimento facial via AWS Rekognition. Composto por API REST (FastAPI), portal web administrativo (HTML/JS estático) e aplicativo mobile (Expo/React Native).

---

## Sumário

- [Visão Geral](#visão-geral)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
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
- [Contribuição](#contribuição)

---

## Visão Geral

O SCPI automatiza o processo de chamada escolar usando reconhecimento facial em tempo real. Quando o professor abre uma chamada, a câmera fixa da sala captura os rostos dos alunos presentes e registra a frequência automaticamente via AWS Rekognition, eliminando a chamada manual.

```
Câmera da Sala → Script Python → AWS Rekognition → FastAPI → PostgreSQL
                                                       ↓
                          Aluno recebe notificação por e-mail (Resend)
```

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI 0.136, Uvicorn, Python 3.10+ |
| Banco de Dados | PostgreSQL 16 (pg8000 + psycopg2-binary) |
| Autenticação | JWT (PyJWT) + bcrypt + cookies httpOnly + CSRF double-submit |
| Rate limiting | SlowAPI |
| Reconhecimento Facial | AWS Rekognition + AWS S3 |
| E-mail | Resend API |
| PDF (export LGPD) | ReportLab |
| Admin Portal | HTML estático + Tailwind CDN + JS vanilla (módulos ES) |
| Mobile | Expo 55, React Native 0.83, React 19.2, TypeScript |
| Navegação Mobile | Expo Router (file-based routing) |

---

## Arquitetura

```
SCPI/
├── BackEnd/                  # API REST FastAPI
│   ├── api.py                # Entry point
│   ├── routers/              # Endpoints por domínio
│   │   ├── auth.py           # Login, refresh, primeiro acesso, recuperação
│   │   ├── admin.py          # Gestão de usuários, turmas, rostos, relatórios
│   │   ├── alunos.py         # Dashboard, frequência, biometria, export LGPD
│   │   ├── professores.py    # Dashboard do professor
│   │   ├── turmas.py         # Turmas e alunos matriculados
│   │   ├── chamadas.py       # Abertura de chamada + Rekognition
│   │   ├── relatorios.py     # Relatórios de frequência
│   │   ├── notificacoes.py   # Notificações por e-mail
│   │   └── public.py         # Endpoints públicos (políticas, etc.)
│   ├── core/                 # CSRF, segurança, limiter, errors, utils, CSV
│   ├── services/             # Lógica de domínio + agendador
│   ├── repositories/         # Acesso ao banco
│   ├── schemas/              # Pydantic
│   ├── infra/                # DB pool, AWS clients, migrations runner
│   ├── migrations/           # SQL migrations versionadas
│   ├── scripts/              # criar_admin.py, reconhecimento_tempo_real.py
│   ├── tests/                # Pytest
│   └── requirements.txt
│
├── portal/                   # Admin portal (estático)
│   ├── index.html
│   ├── privacy.html
│   ├── css/
│   └── js/
│       ├── tabs/             # alunos, professores, turmas, rostos, etc.
│       └── ...               # api.js, auth.js, state.js, toast.js, ...
│
├── tcc-app/                  # App mobile (alunos e professores)
│   ├── app/                  # Rotas Expo Router
│   │   ├── (auth)/           # Login, primeiro acesso, recuperação
│   │   ├── (aluno)/          # Telas do aluno
│   │   └── (professor)/      # Telas do professor
│   ├── scripts/sync-env.js   # Propaga .env raiz → app
│   └── app.json
│
├── schema_inicial.sql        # Schema inicial
└── .env.example              # Template de variáveis
```

---

## Funcionalidades

### Administrador (Portal Web)
- Cadastro, edição (PATCH) e importação CSV de professores e alunos
- Criação e gestão de turmas e matrículas (com "Selecionar Todos")
- Configuração de horários de aulas
- Gestão do banco de rostos (AWS Rekognition + S3) com paginação, agrupamento e colunas configuráveis
- Relatórios de frequência por chamada

### Professor (App Mobile)
- Dashboard com turmas e horários
- Abertura de chamada (aciona câmera da sala)
- Visualização de lista de presença em tempo real
- Relatórios de frequência com filtros
- Encerramento manual de chamadas

### Aluno (App Mobile)
- Dashboard com percentual de frequência por turma
- Histórico detalhado de presenças e faltas
- Cadastro de biometria facial multi-ângulo (~4 FaceIds por aluno)
- Revogação da própria biometria
- Visualização da grade de horários (ordem visual da semana)
- Export LGPD (Art. 18): ZIP com PDF + JSON + foto + manifesto HMAC
- Recebimento de notificações por e-mail

### Câmera da Sala
- Script Python autônomo em execução contínua
- Captura e envia frames ao AWS Rekognition
- Registra presença automaticamente ao identificar rosto cadastrado
- Threshold de similaridade separado de selfie (variáveis dedicadas)

---

## Pré-requisitos

- **Python** 3.10+
- **Node.js** 18+ e npm (apenas para o app mobile)
- **PostgreSQL** 16+
- **Conta AWS** com Rekognition e S3 habilitados
- **Conta Resend** para envio de e-mails
- **Expo CLI** (`npm install -g expo-cli`) — app mobile
- **EAS CLI** (`npm install -g eas-cli`) — builds de produção

> O admin portal é estático: não exige build nem Node em produção.

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

Migrations subsequentes ficam em `BackEnd/migrations/` e são aplicadas automaticamente no startup pelo runner em `infra/migrations`.

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

# Servidor de dev
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Swagger: `http://localhost:8000/docs`

---

### Admin Portal (Estático)

O portal não tem build step. Servir os arquivos de `portal/` via qualquer servidor estático ou abrir `index.html` apontando para um backend válido.

Dev local:
```bash
cd portal
python -m http.server 3000
```

Acesso: `http://localhost:3000`

A URL da API consumida pelo portal é definida em `portal/index.html`:
```html
<script>window.__SCPI_API_URL__ = 'https://api.scpi.me'</script>
```
Substitua por `http://localhost:8000` em dev.

Produção: publicar `portal/` em qualquer CDN ou web server (Nginx, S3+CloudFront, etc.).

---

### Aplicativo Mobile (Expo)

```bash
cd tcc-app
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

---

### Script de Câmera (Sala de Aula)

Executar na máquina com câmera física conectada à sala:

```bash
cd BackEnd
python scripts/reconhecimento_tempo_real.py
```

Requer no `.env`: `SCPI_API_URL`, `CAMERA_SERVICE_TOKEN`, `CAMERA_SALA`, `FACE_MATCH_THRESHOLD_SALA`.

---

## Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|---|---|---|
| `DB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco | `scpi_db` |
| `DB_USER` | Usuário do banco | `postgres` |
| `DB_PASSWORD` | Senha do banco | `senha_segura` |
| `DB_POOL_MIN` / `DB_POOL_MAX` | Pool de conexões | `2` / `10` |
| `SECRET_KEY` | Chave JWT (`secrets.token_urlsafe(48)`) | `...` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiração do token | `60` |
| `ENVIRONMENT` | `production` habilita HSTS e hardenings HTTPS | `production` |
| `ALLOWED_ORIGINS` | Origens CORS (CSV) | `https://scpi.me,https://api.scpi.me` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Credenciais AWS | `AKIA...` |
| `AWS_REGION` | Região AWS | `us-east-1` |
| `COLLECTION_ID` | Coleção Rekognition | `sala_de_aula` |
| `BUCKET_NAME` | Bucket S3 das fotos | `faces-sala-aula-2025` |
| `RESEND_API_KEY` | Chave Resend | `re_...` |
| `RESEND_FROM_EMAIL` | Remetente | `SCPI <noreply@dominio>` |
| `ADMIN_NOME` / `ADMIN_EMAIL` / `ADMIN_SENHA` | Bootstrap do usuário admin | — |
| `VITE_API_URL` | URL da API consumida pelo portal | `http://localhost:8000` |
| `EXPO_PUBLIC_API_URL` | URL da API consumida pelo app | `http://192.168.1.10:8000` |
| `SCPI_API_URL` | URL da API consumida pelo script da câmera | `http://localhost:8000` |
| `CAMERA_SERVICE_TOKEN` | Token estático autenticando o script da câmera | `...` |
| `CAMERA_SALA` | Identificador da sala física | `Sala 101` |
| `FACE_MATCH_THRESHOLD_SELFIE` | Similaridade mínima (selfie) | `90` |
| `FACE_MATCH_THRESHOLD_SALA` | Similaridade mínima (câmera fixa) | `80` |
| `SCPI_EXPORT_HMAC_KEY` | Chave HMAC do manifesto de export LGPD (`secrets.token_hex(32)`) | `...` |

---

## Scripts Utilitários

### Criar usuário administrador

```bash
cd BackEnd
ADMIN_EMAIL="admin@escola.com" ADMIN_SENHA="SenhaForte123" python scripts/criar_admin.py
```

### Câmera da sala (reconhecimento contínuo)

```bash
cd BackEnd
python scripts/reconhecimento_tempo_real.py
```

---

## Endpoints da API

Principais rotas (lista completa via Swagger UI em `/docs`):

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| `POST` | `/auth/login` | Autenticação (cookies httpOnly, isento de CSRF) | Público |
| `POST` | `/auth/refresh` | Renovar token (isento de CSRF) | Autenticado |
| `POST` | `/auth/primeiro-acesso` | Definir senha inicial | Público (token) |
| `POST` | `/auth/recuperar-senha` | Reset de senha | Público |
| `GET` | `/alunos/aluno/dashboard/{id}` | Dashboard do aluno | Aluno |
| `GET` | `/alunos/aluno/frequencias/{id}` | Frequências detalhadas | Aluno |
| `POST` | `/alunos/alunos/cadastrar-face` | Cadastrar biometria | Aluno |
| `DELETE` | `/alunos/aluno/biometria/{id}` | Revogar biometria | Aluno |
| `GET` | `/alunos/aluno/meus-dados?formato=zip` | Export LGPD (PDF+JSON+foto+HMAC) | Aluno |
| `GET` | `/professores/dashboard/{id}` | Dashboard do professor | Professor |
| `POST` | `/chamadas/abrir` | Abrir chamada com Rekognition | Professor |
| `GET` | `/turmas/{usuario_id}` | Turmas do usuário | Professor |
| `GET` | `/relatorios/professor/relatorios/chamadas` | Relatórios do professor | Professor |
| `GET` | `/admin/professores` | Listar professores | Admin |
| `POST` | `/admin/usuarios/professor` | Criar professor | Admin |
| `PATCH` | `/admin/usuarios/professor/{id}` | Editar professor | Admin |
| `POST` | `/admin/professores/importar` | Importar professores via CSV | Admin |
| `POST` | `/admin/usuarios/aluno` | Criar aluno | Admin |
| `POST` | `/admin/turmas` | Criar turma | Admin |
| `POST` | `/admin/horarios` | Adicionar horário | Admin |
| `POST` | `/admin/turmas/{id}/importar-alunos` | Importar alunos via CSV | Admin |
| `GET` | `/admin/rostos/rekognition` | Listar banco de rostos (paginado) | Admin |
| `DELETE` | `/admin/rostos/rekognition/{face_id}` | Excluir rosto | Admin |
| `GET` | `/admin/relatorios/chamadas` | Todos os relatórios | Admin |

---

## Banco de Dados

Principais tabelas:

| Tabela | Descrição |
|---|---|
| `Usuarios` | Usuários do sistema (admin, professor, aluno) |
| `Professores` | Dados específicos de professores |
| `alunos` | Dados específicos de alunos + biometria |
| `Turmas` | Turmas/disciplinas |
| `horarios_aulas` | Grade de horários das turmas |
| `chamadas` | Registros de chamadas abertas |
| `presencas` | Presença por aula (migração `001_presenca_por_aula.sql`) |
| `colecao_rostos` | Mapeamento aluno ↔ FaceId Rekognition (multi-ângulo) |

Schema base: [`schema_inicial.sql`](./schema_inicial.sql). Migrations versionadas: `BackEnd/migrations/`.

---

## Segurança e LGPD

- Autenticação via cookies httpOnly + CSRF double-submit (rotas `/auth/login` e `/auth/refresh` isentas por design)
- HSTS, CSP e demais headers em `core/security_headers.py` (ativam quando `ENVIRONMENT=production`)
- Rate limiting via SlowAPI nos endpoints sensíveis
- 27 ErrorCodes padronizados (toast stack no portal, `useErrorToast` no mobile)
- Export LGPD (Art. 18 §1): `/aluno/meus-dados?formato=zip` entrega PDF + JSON + foto + manifesto assinado com `SCPI_EXPORT_HMAC_KEY`
- Auditoria de segurança completa aplicada em 2026-05-20 (15 itens); decisão deliberada de não implementar MFA/TOTP

---

## Testes

```bash
cd BackEnd
pytest
```

Cobertura atual concentra-se no fluxo de export LGPD (`tests/test_export_*`).

---

## Contribuição

1. Crie uma branch: `git checkout -b feat/minha-funcionalidade`
2. Faça commits seguindo [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
3. Abra um Pull Request

Convenção de commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
