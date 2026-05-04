# SCPI — Sistema de Controle de Presença Inteligente

Sistema acadêmico de registro de presença com reconhecimento facial via AWS Rekognition. Composto por API REST (FastAPI), portal web administrativo (React) e aplicativo mobile (Expo/React Native).

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
  - [Admin Portal (React)](#admin-portal-react)
  - [Aplicativo Mobile (Expo)](#aplicativo-mobile-expo)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Scripts Utilitários](#scripts-utilitários)
- [Endpoints da API](#endpoints-da-api)
- [Banco de Dados](#banco-de-dados)
- [Contribuição](#contribuição)

---

## Visão Geral

O SCPI automatiza o processo de chamada escolar usando reconhecimento facial em tempo real. Quando o professor abre uma chamada, a câmera da sala captura os rostos dos alunos presentes e registra a frequência automaticamente via AWS Rekognition, eliminando a chamada manual.

```
Câmera da Sala → Script Python → AWS Rekognition → FastAPI → PostgreSQL
                                                         ↓
                              Aluno recebe notificação por e-mail
```

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI 0.135, Uvicorn, Python 3.x |
| Banco de Dados | PostgreSQL 16 |
| Autenticação | JWT (python-jose) + bcrypt |
| Reconhecimento Facial | AWS Rekognition + AWS S3 |
| E-mail | Resend API |
| Admin Portal | React 18, Vite 5, Tailwind CSS 3 |
| Mobile | Expo 54, React Native 0.81, TypeScript |
| Navegação Mobile | Expo Router (file-based routing) |

---

## Arquitetura

```
SCPI/
├── BackEnd/                  # API REST FastAPI
│   ├── api.py                # Entry point da aplicação
│   ├── routers/              # Endpoints por domínio
│   │   ├── auth.py           # Autenticação e tokens
│   │   ├── admin.py          # Gestão de usuários, turmas, rostos
│   │   ├── alunos.py         # Dashboard e frequência do aluno
│   │   ├── professores.py    # Dashboard do professor
│   │   ├── turmas.py         # Turmas e alunos matriculados
│   │   ├── chamadas.py       # Abertura de chamadas + Rekognition
│   │   ├── relatorios.py     # Relatórios de frequência
│   │   └── notificacoes.py   # Notificações por e-mail
│   ├── infra/                # Database, migrations, AWS clients
│   ├── scripts/              # Utilitários (admin, câmera, importação)
│   └── requirements.txt
│
├── admin-portal/             # Dashboard web para admins
│   ├── src/
│   │   ├── components/       # Tabs: Alunos, Professores, Turmas, etc.
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
│
├── tcc-app/                  # Aplicativo para alunos e professores
│   ├── app/                  # Rotas Expo Router
│   │   ├── (auth)/           # Login, primeiro acesso, recuperação
│   │   ├── (aluno)/          # Telas do aluno
│   │   └── (professor)/      # Telas do professor
│   ├── package.json
│   └── app.json
│
├── schema_inicial.sql        # Schema inicial do banco de dados
└── .env.example              # Template de variáveis de ambiente
```

---

## Funcionalidades

### Administrador (Portal Web)
- Cadastro de professores e alunos
- Criação e gestão de turmas
- Configuração de horários de aulas
- Importação de alunos via CSV
- Gestão do banco de rostos (AWS Rekognition + S3)
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
- Cadastro de biometria facial
- Visualização de grade de horários
- Recebimento de notificações por e-mail

### Câmera da Sala
- Script Python autônomo em execução contínua
- Captura e envia frames ao AWS Rekognition
- Registra presença automaticamente ao identificar rosto cadastrado

---

## Pré-requisitos

- **Python** 3.10+
- **Node.js** 18+ e npm
- **PostgreSQL** 16+
- **Conta AWS** com Rekognition e S3 habilitados
- **Conta Resend** para envio de e-mails
- **Expo CLI** (`npm install -g expo-cli`) — para o app mobile
- **EAS CLI** (`npm install -g eas-cli`) — para builds de produção

---

## Configuração do Ambiente

Copie o arquivo de exemplo e preencha as variáveis:

```bash
cp .env.example .env
```

Veja a seção [Variáveis de Ambiente](#variáveis-de-ambiente) para detalhes de cada variável.

### AWS — Configuração Inicial

1. Crie um bucket S3 para armazenar as fotos dos rostos
2. Crie uma coleção no AWS Rekognition:
   ```bash
   aws rekognition create-collection --collection-id sua-colecao
   ```
3. Configure as credenciais AWS no `.env`

### Banco de Dados

Aplique o schema inicial ao PostgreSQL:

```bash
psql -U postgres -d scpi_db -f schema_inicial.sql
```

---

## Instalação e Execução

### Backend (FastAPI)

```bash
cd BackEnd

# Criar e ativar ambiente virtual
python -m venv ../venv
# Windows:
..\venv\Scripts\activate
# Linux/macOS:
source ../venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor de desenvolvimento
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Documentação interativa disponível em: `http://localhost:8000/docs`

---

### Admin Portal (React)

```bash
cd admin-portal

npm install
npm run dev
```

Acesso em: `http://localhost:3000`

Build de produção:
```bash
npm run build
# Artefatos gerados em admin-portal/dist/
```

---

### Aplicativo Mobile (Expo)

```bash
cd tcc-app

npm install

# Sincronizar variáveis de ambiente do .env raiz para o app
npm run sync-env

# Iniciar servidor de desenvolvimento
npm start
```

Executar em plataforma específica:
```bash
npm run android   # Emulador Android
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

Execute na máquina com câmera física conectada à sala:

```bash
cd BackEnd
python scripts/reconhecimento_tempo_real.py
```

Requer `CAMERA_SALA` e `CAMERA_SERVICE_TOKEN` configurados no `.env`.

---

## Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|---|---|---|
| `DB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco | `scpi_db` |
| `DB_USER` | Usuário do banco | `postgres` |
| `DB_PASSWORD` | Senha do banco | `senha_segura` |
| `SECRET_KEY` | Chave secreta JWT | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiração do token em minutos | `60` |
| `AWS_ACCESS_KEY_ID` | Chave de acesso AWS | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | Chave secreta AWS | `...` |
| `AWS_REGION` | Região AWS | `us-east-1` |
| `COLLECTION_ID` | ID da coleção Rekognition | `sala_de_aula` |
| `BUCKET_NAME` | Nome do bucket S3 | `faces-sala-aula-2025` |
| `RESEND_API_KEY` | Chave da API Resend | `re_...` |
| `RESEND_FROM_EMAIL` | E-mail remetente | `noreply@escola.com` |
| `ALLOWED_ORIGINS` | Origens permitidas CORS | `http://localhost:3000` |
| `VITE_API_URL` | URL da API para o portal admin | `http://localhost:8000` |
| `EXPO_PUBLIC_API_URL` | URL da API para o app mobile | `http://192.168.1.10:8000` |
| `CAMERA_SERVICE_TOKEN` | Token de autenticação da câmera | `token_estatico` |
| `CAMERA_SALA` | Identificador da sala | `Sala 101` |

---

## Scripts Utilitários

### Criar usuário administrador

```bash
cd BackEnd
ADMIN_EMAIL="admin@escola.com" ADMIN_SENHA="SenhaForte123" python scripts/criar_admin.py
```

### Importar grade de horários

```bash
cd BackEnd
python scripts/importar_grade.py
```

### Listar e excluir rostos da coleção Rekognition

```bash
cd BackEnd
python scripts/listar_e_excluir_rostos.py
```

---

## Endpoints da API

| Método | Rota | Descrição | Acesso |
|---|---|---|---|
| `POST` | `/auth/login` | Autenticação | Público |
| `POST` | `/auth/refresh` | Renovar token | Autenticado |
| `GET` | `/alunos/aluno/dashboard/{id}` | Dashboard do aluno | Aluno |
| `GET` | `/alunos/aluno/frequencias/{id}` | Frequências detalhadas | Aluno |
| `POST` | `/alunos/alunos/cadastrar-face` | Cadastrar biometria facial | Aluno |
| `DELETE` | `/alunos/aluno/biometria/{id}` | Revogar biometria | Aluno |
| `GET` | `/professores/dashboard/{id}` | Dashboard do professor | Professor |
| `POST` | `/chamadas/abrir` | Abrir chamada com Rekognition | Professor |
| `GET` | `/turmas/{usuario_id}` | Turmas do usuário | Professor |
| `GET` | `/relatorios/professor/relatorios/chamadas` | Relatórios do professor | Professor |
| `GET` | `/admin/professores` | Listar professores | Admin |
| `POST` | `/admin/usuarios/professor` | Criar professor | Admin |
| `POST` | `/admin/usuarios/aluno` | Criar aluno | Admin |
| `POST` | `/admin/turmas` | Criar turma | Admin |
| `POST` | `/admin/horarios` | Adicionar horário | Admin |
| `POST` | `/admin/turmas/{id}/importar-alunos` | Importar alunos via CSV | Admin |
| `GET` | `/admin/rostos/rekognition` | Listar banco de rostos | Admin |
| `DELETE` | `/admin/rostos/rekognition/{face_id}` | Excluir rosto | Admin |
| `GET` | `/admin/relatorios/chamadas` | Todos os relatórios | Admin |

Documentação completa (Swagger UI): `http://localhost:8000/docs`

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
| `colecao_rostos` | Mapeamento aluno ↔ FaceId Rekognition |

Schema completo: [`schema_inicial.sql`](./schema_inicial.sql)

---

## Contribuição

1. Fork o repositório
2. Crie uma branch: `git checkout -b feat/minha-funcionalidade`
3. Commit suas alterações: `git commit -m "feat: adicionar funcionalidade X"`
4. Push para a branch: `git push origin feat/minha-funcionalidade`
5. Abra um Pull Request

Convenção de commits: [Conventional Commits](https://www.conventionalcommits.org/pt-br/)
