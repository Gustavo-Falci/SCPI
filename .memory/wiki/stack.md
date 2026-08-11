# Tech Stack

*Estrutura e versões conferidas contra o código em 2026-08-05 (`/memwiki-ingest`).*

## Visão geral

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, psycopg2 (SQL cru, sem ORM) |
| Banco | PostgreSQL 16, local na própria VM (`127.0.0.1`) |
| App mobile | React Native via **Expo SDK 55**, expo-router |
| Portal admin | HTML/CSS/JS vanilla, ES Modules nativos, Tailwind via CLI |
| Biometria | AWS Rekognition (collection) + S3 |
| Servidor web | nginx → gunicorn (4 workers) + UvicornWorker |
| Infra | VM Oracle Cloud (OCI); backups em OCI Object Storage |
| Observabilidade | Sentry (backend), UptimeRobot, healthchecks.io |
| Push | Expo Push + FCM V1 (Firebase `scpi-6f501`) |
| E-mail | Resend (`SCPI <noreply@scpi.me>`) |

Domínios: API em `https://api.scpi.me`, portal em `https://admin.scpi.me`.

## Backend — mapa de módulos

```
BackEnd/
├── api.py            # entrypoint; init_sentry ANTES dos imports de core/infra; lifespan
├── core/
│   ├── config.py            auth_utils.py     security.py        csrf.py
│   ├── errors.py            helpers.py        security_headers.py
│   ├── limiter.py           limiter_storage.py  (PostgresStorage)
│   ├── csv_utils.py         tempo.py          observabilidade.py
│   ├── mascaras.py     # máscara de CPF em documento que sai do sistema
│   └── regras.py       # regra acadêmica pura, compartilhada entre camadas
├── infra/
│   ├── database.py          migrations.py     notificacoes.py
│   ├── aws_clientes.py      rekognition_aws.py  s3_aws.py
│   ├── export_pdf.py        export_zip.py     export_integridade.py
│   └── relatorio_pdf.py
├── repositories/     # alunos, professores, turmas, chamadas, presencas, horarios,
│                     # usuarios, tokens, auth_lockout, camera_tokens, consentimentos,
│                     # rostos, notificacoes
├── services/         # import_alunos, relatorios, notificacoes, agendador,
│                     # inventario_biometrico
├── routers/          # public, auth, admin, alunos, professores, turmas, chamadas,
│                     # relatorios, notificacoes
├── schemas/          # admin, auth, chamada
├── scripts/          # reconhecimento_tempo_real, confirmacao_burst, anti_spoofing,
│                     # registro_tracker, camera_token, criar_admin, verificar_receipts,
│                     # _validar_liveness
└── tests/            # 72 arquivos, 518 funções de teste
```

### Módulos com razão de existir não óbvia

- **`core/regras.py`** — regra acadêmica pura que não pertence a service nem a infra:
  `LIMITE_FREQUENCIA = 75` (rótulo Regular/Risco **e** a cor da linha no PDF) e
  `ANGULOS_VALIDOS = {frontal, esquerda, direita, baixo}` (o cadastro valida contra a lista
  e a auditoria da aba Biometria calcula os faltantes por diferença). **Centralizado porque
  duas cópias divergiriam sem ninguém perceber** — o service rotulando com um limiar e o PDF
  pintando com outro.
- **`core/mascaras.py`** — o PDF de relatório circula por e-mail e WhatsApp, fora do controle
  do SCPI. **CPF não vai impresso; o RA institucional vai**, porque sem ele a ata de uma turma
  com nomes repetidos fica ambígua. Valida os dígitos verificadores (módulo 11).
- **`services/inventario_biometrico.py`** — reconciliação AWS × banco para a aba Biometria.
  **Função pura de propósito**: recebe as três listas prontas e não conhece boto3 nem
  psycopg2, então a regra de "isto aqui é lixo" fica testável de mesa.
- **`scripts/registro_tracker.py`** — contabilidade de quem já foi tratado na chamada atual,
  com **dois estados em vez de um**. Antes o aluno entrava em `presentes_chamada` **antes** do
  POST: um POST que falhasse nunca era retentado e virava **falta indevida silenciosa**.
  Enquanto o backend resolvia a chamada globalmente a recusa era rara; com a validação por
  `chamada_id` ela virou caminho normal. Classe pura, no molde do `confirmacao_burst.py`.
  Não é thread-safe por si: o `SistemaReconhecimento` já serializa sob `self.lock`, e embutir
  um lock aqui daria a impressão falsa de que reivindicar-e-submeter é atômico.

## Banco — tabelas

Criadas por `infra/migrations.py::ensure_base_schema()` (`CREATE TABLE IF NOT EXISTS`,
serializado por **advisory lock**, porque os 4 workers do gunicorn sobem juntos):

`Usuarios`, `Alunos`, `Professores`, `Turmas`, `Turma_Alunos`, `Chamadas`, `Presencas`,
`Horarios_Aulas`, `Colecao_Rostos`, `ConsentimentosLGPD`, `RefreshTokens`,
`PasswordResetCodes`, `PushTokens`, `PushReceiptsPendentes`, `camera_tokens`,
`login_attempts`, `rate_limit_buckets`.

As migrations são **21 funções `ensure_*` idempotentes**, encadeadas em `_ETAPAS` e
**fail-loud** (exceção propaga com o nome da etapa). As mais recentes:
`ensure_timestamptz_tokens`, `ensure_timestamptz_restante`, `ensure_indices_performance`,
`ensure_camera_tokens_table`, `ensure_login_attempts_table`, `ensure_rate_limit_table`.

Pontos do schema que carregam decisão:
- `uq_chamada_aberta_por_turma` — índice parcial único (`ensure_chamada_aberta_unica`).
- `unique(aluno_id, angulo)` em `Colecao_Rostos` (`ensure_multi_angle_faces`).
- `chamadas.professor_id` e `turmas.professor_id` **NULLABLE de propósito**
  (`ensure_chamada_professor_nullable`) — ver [[decisions.md]].
- **Nenhuma coluna `timestamp` sem fuso** desde 2026-08-04. Coluna nova nasce `TIMESTAMPTZ`.
- `aluno_id` / `turma_id` são `uuid` — ver o gotcha de cast em [[patterns.md]].

## API — superfície

9 routers montados em `api.py`: `public`, `auth`, `admin`, `notificacoes`, `alunos`,
`professores`, `turmas`, `chamadas`, `relatorios`.

| Grupo | Rotas |
|---|---|
| Público | `GET /`, `GET /health` (GET+HEAD), `GET /politica-privacidade` |
| Auth | `POST /login`, `/logout`, `/refresh`, `/register`, `/alterar-senha`, `/alterar-senha-primeiro-acesso`, `/esqueci-senha`, `/verificar-codigo`, `/redefinir-senha`, `GET /session` |
| Admin | CRUD de `usuarios/aluno`, `usuarios/professor`, `turmas`, `horarios`; `importar-alunos`, `importar-professores`, `turmas/{id}/{matricular,desmatricular,importar}-alunos`; `rostos/inventario`, deletes de Rekognition/S3 |
| Chamadas | `POST /abrir`, `/{id}/ajustar`, `/{id}/finalizar`, `/fechar/{turma_id}`, `/registrar_presenca_camera`; `GET /status/{turma_id}`, `/{id}/alunos`, `/aberta/sala` |
| Relatórios | `/{professor,admin}/relatorios/{chamadas,filtros}`, `.../chamadas/{id}`, `.../turmas/{id}/frequencia` (todos com `?formato=pdf`) |
| Aluno/LGPD | `GET /aluno/{dashboard,frequencias,historico-chamadas,consentimento,meus-dados,biometria-foto}/{usuario_id}`, `DELETE /aluno/biometria/{usuario_id}` |
| Push | `POST /registrar-token` |

## Variáveis de ambiente

- **Obrigatórias no boot** (ausência derruba o import): `SECRET_KEY` (≥32 chars),
  `SCPI_EXPORT_HMAC_KEY` (32 bytes hex), `DB_*`.
- Banco: `DB_HOST/PORT/NAME/USER/PASSWORD`, `DB_POOL_MIN/MAX`, `DB_CONNECT_TIMEOUT`.
- Auth: `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALLOWED_ORIGINS`, `AUTH_COOKIE_DOMAIN`,
  `ENVIRONMENT` (`production` liga HSTS, `Secure` e desliga `/docs`).
- AWS: `AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY/REGION`, `BUCKET_NAME`, `COLLECTION_ID`.
- Câmera: `CAMERA_INDEX`, `CAMERA_SERVICE_TOKEN`, `FACE_MATCH_THRESHOLD_SALA` (default 90),
  `FACE_MODEL_PATH`, `BURST_FRAMES`/`BURST_MIN_MATCHES`/`BURST_DURACAO_S`,
  `LIVENESS_POSE_STD_MIN`, `ENABLE_TEXTURE`, `TEXTURE_MODEL_PATH`, `TEXTURE_LIVENESS_MIN`.
- Outros: `RESEND_API_KEY`/`RESEND_FROM_EMAIL`, `SENTRY_DSN` (vazio = no-op),
  `SCPI_PRIVACY_URL`, `ADMIN_*` (só para `criar_admin.py`), `EXPO_PUBLIC_API_URL`.

> `CAMERA_SERVICE_TOKEN` **continua existindo como nome de env na máquina da sala** — o que
> acabou foi o *token global compartilhado*. Hoje o valor é um token **por sala**, emitido por
> `scripts/camera_token.py` e guardado com hash na tabela `camera_tokens`.

## Versões (conferidas no `requirements.txt`)

```
fastapi==0.136.1     starlette==1.3.1      uvicorn==0.51.0
gunicorn==26.0.0     uvicorn-worker==0.4.0 python-multipart==0.0.32
psycopg2-binary==2.9.12   pg8000==1.31.5
pydantic==2.13.4     pydantic_core==2.46.4
PyJWT==2.13.0        passlib==1.7.4
boto3==1.43.56       opencv-python==4.13.0.92   numpy==2.5.1
slowapi==0.1.10      limits==5.8.0
resend==2.34.0       reportlab==5.0.0      sentry-sdk==2.66.1
```

Pins que carregam decisão — ver [[bugs.md]]:
- **`fastapi==0.136.1`**: a 0.136.3 é maliciosa. O comentário do motivo mora no próprio
  `requirements.txt`.
- **`gunicorn`**: pinado só em 2026-07-23; antes era instalado à mão na VM e ficava invisível
  para pip-audit e Dependabot.
- **`uvicorn-worker`**: o módulo `uvicorn.workers` seria removido e o restart derrubaria a API.
- **`PyJWT` sem o extra `[crypto]`**: `cryptography` só serve aos algoritmos assimétricos, e o
  SCPI assina em **HS256**, que o PyJWT resolve com `hmac`/`hashlib` da stdlib. Removida em
  2026-08-05 junto de `cffi` e `pycparser`. Se `core.auth_utils.ALGORITHM` deixar de ser
  `HS*`, ela precisa voltar — `test_jwt_algoritmo_simetrico.py` cobra isso.
- **`opencv-python` na linha 4.x**: a 5.0 removeu `CascadeClassifier` do core.
- Comentário do próprio arquivo: `opencv`/`numpy` só são necessários na máquina com câmera e
  podem sair num servidor headless.

Dev: `requirements-dev.txt` (`pytest==9.1.1`, `httpx==0.28.1`), fora do de prod de propósito.
`tzdata` só no dev Windows, em nenhum requirements.

App: `expo ~55.0.0`, `react-native 0.83.6`, `react 19.2.0`.

## Testes

72 arquivos, **518 funções de teste** (a suíte reporta ~700 casos com parametrização).
Cobertura por eixo: migrations (11 arquivos), câmera/liveness (6), relatórios/PDF (7),
export/LGPD (7), auth/lockout/rate-limit (7), portal (3 guardas textuais).

Suíte 100% mockada por padrão (não conecta em DB nem AWS); integração é opt-in via
`SCPI_RUN_DB_TESTS=1`. Ver os alertas em [[patterns.md]].

## CI

`.github/workflows/`:

- **`tests.yml`** — pytest (`BackEnd/**`), job `tsc + eslint (app)`, job
  `portal css (build atualizado)`. Paths: `BackEnd/** + portal/** + app/**`. Service
  `postgres:16` para os testes gated. Env dummies `SECRET_KEY` e `SCPI_EXPORT_HMAC_KEY`.
- **`security.yml`** — Bandit, pip-audit, gitleaks, npm audit, SBOM CycloneDX, com
  `dorny/paths-filter@v3` escopando por pasta.
- **`dependabot.yml`** — `ignore` deliberados: stack Expo, `fastapi` (minor+patch),
  `opencv-python` (major), `pydantic-core`.

Branch `main` **não é protegida**; falha de CI não bloqueia merge.

## Ver também

[[ops.md]], [[portal.md]], [[app-mobile.md]], [[dominio.md]].
