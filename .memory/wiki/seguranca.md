# Segurança

⚠️ Página com o mapa da postura de segurança e da dívida conhecida. Ver o aviso em [[index.md]].

Base: auditoria sistemática contra `manual_seguranca_sistemas_v2.md` (raiz do repo), iniciada
em 2026-05-18. O sistema é TCC **com uso real e biometria facial**, portanto sob LGPD.

## Aplicado

1. `senhas_geradas` removido do response do import-CSV — só e-mail.
2. `CAMERA_SERVICE_TOKEN` rotacionado + `.env.example` limpo.
3. Magic bytes em uploads (`core/helpers.py::validate_image_upload`).
4. Race condition em `abrir_chamada` resolvida (advisory lock + índice parcial único
   `uq_chamada_aberta_por_turma`).
5. IDOR responde **404 em vez de 403** (`require_self_or_admin` + 3 routers) — não enumera.
6. Senha com mínimo de 12 chars + check HIBP por k-anonymity (`senha_comprometida`).
7. Security headers (`core/security_headers.py`): CSP, HSTS condicional via
   `ENVIRONMENT=production`, X-Content-Type-Options, Referrer-Policy, Permissions-Policy,
   COOP, sem `Server`/`X-Powered-By`.
8. **Portal: localStorage → cookie HttpOnly + CSRF** (2026-05-19). Detalhe abaixo.
9. JWT com `type=="access"` estrito em `decode_access_token`.
10. Hardening do import CSV (CSV injection, size limit, UTF-8 obrigatório, regex de campos).
11. Temp file eliminado em `cadastrar_aluno_api` (upload direto via `BytesIO`).
12. Pipeline `security.yml` (Bandit, pip-audit, gitleaks, npm audit, SBOM CycloneDX).
13. `dependabot.yml`.
14. Boot hardening: warning de `RESEND_API_KEY`, helper `_env_int` para `DB_POOL_*`.
15. Runbook em `docs/runbooks/SECURITY_RUNBOOK.md`.

### Design do #8 (cookie + CSRF)

- Cookie **strict** (`AUTH_COOKIE_DOMAIN` vazio → só `api.scpi.me`), não compartilhado
  `.scpi.me`. `Secure` quando `ENVIRONMENT=production`.
- CSRF por **header `X-Requested-With`**, não double-submit cookie: é um header "non-simple",
  logo força o preflight CORS, que já é restrito por origin.
- `SameSite=Lax` em `scpi_access` (permite navegação top-level), `Strict` em `scpi_refresh`.
- `scpi_refresh` com `Path=/auth` — o cookie só viaja em endpoints de auth.
- `get_current_user` é **dual**: Bearer prioritário, fallback cookie. O mobile continua em
  Bearer, com `credentials: "omit"` em todos os fetch.
- Isenções de `/auth/login` e `/auth/refresh`: ver o raciocínio em [[decisions.md]] antes de
  mexer.

## Pentest white-box 2026-05-25

Audit estático completo. SQL 100% parametrizado (sem SQLi), JWT/cookies/headers sólidos.
**Os achados se concentraram em autorização lateral.** 7 fixes:

16. **BOLA em chamadas (ALTO)** — helper `_assert_professor_dono_ou_admin(turma_id, user)`
    aplicado em `ajustar`/`finalizar`/`fechar` + `status/{turma}` e `{chamada}/alunos`. Antes
    qualquer Professor reescrevia presença e roster de **turma alheia** (só
    `require_role("Professor")`, sem checar dono). O padrão já existia em `/abrir` e em
    `relatorios.py`.
17. Timing de enumeração no login: `_DUMMY_PASSWORD_HASH` + `verify_password` no caminho de
    usuário inexistente.
18. `/docs`, `/redoc`, `/openapi.json` desabilitados em prod.
19. Service token em tempo constante (`secrets.compare_digest`).
20. Delete no S3 restrito ao prefixo `alunos/` + bloqueio de `..`.
21. Endpoint de debug `/teste_reload` removido.
22. Falso positivo do gitleaks em `api.py:90` suprimido com `# gitleaks:allow`.

## Dívida M1 / M4 / B1 — toda fechada

Adiada em 2026-05-27, revertida a pedido do Gustavo em 2026-07-23.

- **M1 — Liveness**: feito 2026-07-15. Ver [[biometria-camera.md]].
- **M4 — Rate limiter multi-worker**: PR #71, 2026-07-23. Postgres, não Redis
  (ver [[decisions.md]]). `PostgresStorage` fixed-window na tabela `rate_limit_buckets`,
  **fail-open** + `swallow_errors=True`; os 10 `@limiter.limit` não mudaram. Prod roda
  `gunicorn -w 4`, então o limite furava ~4×. Purge diário no agendador.
  Validado em prod: login trava em 10/min numa linha única compartilhada (antes ~40).
- **B1 — Lockout de login por conta**: PR #71. `repositories/auth_lockout.py`, tabela
  `login_attempts`, upsert atômico, MAX_FAILS=8 / WINDOW=15min / LOCK=15min, auto-reset.
  Fiado no `login()` **antes** de autenticar; registra falha em usuário inexistente e em
  senha errada **igual**, para não permitir enumeração; limpa no sucesso. Complementa o
  limite por IP (pega brute-force distribuído entre IPs).

## Hardening A1–A6 — em prod desde 2026-08-01 (PR #89)

Validado em prod ponta a ponta. Três armadilhas que a execução revelou e que voltam a morder:

1. **pbkdf2 a 600k custa ~300 ms por hash** — ver [[patterns.md]].
2. **`get_db_cursor` devolve `None` em vez de levantar** — ver [[bugs.md]].
3. **`atualizar_senha_por_usuario_id` também zera `primeiro_acesso`** — ver [[bugs.md]].

Mudanças operacionais:

- **`CAMERA_SERVICE_TOKEN` global e `CAMERA_SALA` não existem mais.** Token **por sala** em
  `camera_tokens` (SHA-256), emitido por `BackEnd/scripts/camera_token.py`, roteiro em
  `docs/runbooks/SECURITY_RUNBOOK.md`. A sala vem do token, nunca do cliente.
- Portal sem CDN: Tailwind e Inter vendorizados, CSP por meta tag. `connect-src` fixa
  `https://api.scpi.me` e precisa ser editado junto de `portal/js/env.js` ao trocar de host —
  inclusive para dev local.
- `.gitignore` tinha `docs/*` + `!docs/SECURITY_RUNBOOK.md` seguidos de um `docs/` que
  anulava a exceção. Corrigido.

**A validação do A5 (CSP) foi incompleta e deixou bug em prod por 2 dias** — ver [[bugs.md]].
Lição: validar CSP exige exercitar a UI interativa, não só carregar a página.

## Sentry — em prod desde 2026-07-27 (PR #78)

Free tier, 5k eventos/mês. `BackEnd/core/observabilidade.py::init_sentry(componente)`, fiado
em `api.py` e em `scripts/verificar_receipts.py`; a tag `componente` separa os dois.
`SENTRY_DSN` vazio = no-op.

Postura de PII conservadora:
- **`LoggingIntegration` desligada de propósito** — ver [[decisions.md]]. **Não remover.**
- `include_local_variables=False` (senão o frame do `login()` leva senha em claro),
  `send_default_pii=False`, `max_request_body_size="never"`, `traces_sample_rate=0.0`, e
  `before_send` removendo headers de credencial + cookies + query string. O header do serviço
  de câmera é `x-service-token` e **o denylist interno do SDK não o cobre**.

Validado com um **teste negativo**: cadastro com e-mail duplicado dispara `logger.error` com
`Key (email)=(...)` e **nenhum evento** aparece no painel. Refazer esse teste se alguém mexer
na config. Detalhe que assusta e é normal: `"logging"` aparece na lista `sdk.integrations`
mesmo desligada — a integração está instalada, só com os handlers desarmados. **A lista não
prova nada; só o teste negativo prova.**

Dívidas abertas (baixo risco): `sentry_logs_level` no default `INFO` — inerte enquanto
`enable_logs=False`, mas reabre o vazamento se Sentry Logs for habilitado (caminho que usa
`before_send_log`, não `before_send`). E a `ArgvIntegration` anexa `sys.argv` em
`event["extra"]`, que `_limpar_evento` não filtra.

O Sentry deriva geo do IP de ingestão, que é o da VM — não é IP de aluno, mas é dado de
localização saindo do país; registrado no DPIA junto da transferência internacional.

## Gitleaks

`.gitleaksignore` na raiz cobre 6 findings históricos, todos de **chaves comprovadamente
descontinuadas** (confirmado pelo Gustavo em 2026-06-11): falso positivo em `api.py`,
`CAMERA_SERVICE_TOKEN` real commitado no `.env.example`, chaves do Obsidian em
`.claude/settings.local.json`, `OPENAI_API_KEY` num arquivo de perfil.

**Regra: chave morta → fingerprint no `.gitleaksignore`. Chave viva → rotacionar ANTES de
ignorar.** Falso positivo em código atual → `# gitleaks:allow` inline (mas commits antigos da
mesma linha continuam flagados no scan full-history, e esses vão para o ignore).

Ver a assimetria push/PR vs agendado em [[bugs.md]].

## Dívida de dependências

- Bandit B324: corrigido — o SHA-1 do HIBP usa `usedforsecurity=False`.
- `python-jose` PYSEC-2025-185: resolvido migrando para `PyJWT` (o pacote estava
  semi-abandonado; a vuln era em `jose.jwe.decrypt`, que o SCPI não usava).
- PyJWT PYSEC-2025-183: **ignorada com justificativa** (`--ignore-vuln` documentado no
  workflow). É disputada pelo mantenedor e exige enforcement de comprimento mínimo de chave
  pela aplicação — `core/auth_utils.py` valida `SECRET_KEY >= 32` no boot.
- npm audit no app: `overrides` pinado no `package.json` (`brace-expansion`, `js-yaml`,
  `shell-quote`, `ws`). **Não usar `npm audit fix`** — ver [[bugs.md]].
- As 13 vulns restantes do app são só **2 advisories** (o npm conta cada nó da cadeia):
  `uuid` <11.1.1 (moderate) via `expo-sharing > @expo/config-plugins > xcode > uuid@7.0.3`,
  **não explorável** porque `xcode` só chama `uuid.v4()` sem `buf`; e `@babel/core` (low),
  que exige compilar código não confiável. O `fixAvailable` do npm sugere downgrade absurdo
  (expo 46) — ignorar.

## Itens sem prazo

TLS interno entre serviços (fora do escopo de código), pentest externo anual, rotação das
chaves AWS → migrar para IAM Role, logging de origem CORS rejeitada.
