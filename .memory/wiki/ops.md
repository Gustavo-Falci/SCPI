# Operações — Produção, Deploy, Backup, Monitoramento

⚠️ Página com caminhos e detalhes de infraestrutura de produção. Ver o aviso em [[index.md]].

## Servidor

- Host `scpi` (Ubuntu, usuário `ubuntu`), VM na Oracle Cloud.
- Projeto em `/opt/scpi`; backend em `/opt/scpi/BackEnd`; venv em `/opt/scpi/venv`
  (Python 3.12).
- **`.env` fica em `/opt/scpi/.env`**, na raiz do repo — não em `BackEnd/.env`
  (`find_dotenv()` acha subindo diretórios). **Correção 2026-08-18**: linha anterior aqui
  afirmava que `docs/runbooks/deploy.md` dizia `BackEnd/.env` e estava desatualizado — falso,
  verificado; o runbook (linha 10) sempre disse `/opt/scpi/.env`. O problema real do runbook
  era outro: o bloco de deploy não ativava o venv antes do `pip install` (corrigido em
  2026-08-18).
- Banco de produção: `DB_NAME=scpi`, `DB_USER=scpi`, `DB_HOST=127.0.0.1`. **Não existe
  segundo banco na VM** — o `scpi_db`/`postgres` que aparecia no `.env` local do Gustavo era
  erro, corrigido em 2026-08-05.
- **TimeZone do Postgres = `America/Sao_Paulo`**, não UTC.
- **Não há acesso SSH a partir da máquina Windows do Gustavo** (sem `~/.ssh/config`, chave
  ou agent). Todo deploy é executado por ele.

## Deploy

```bash
cd /opt/scpi
git pull origin main
source venv/bin/activate
cd BackEnd
pip install -r requirements.txt --upgrade
sudo systemctl restart scpi-api
```

- **Restart é obrigatório** após mudança em `requirements.txt` ou em código Python — os
  workers mantêm os módulos em memória.
- **Prod não roda uvicorn direto**: a unit sobe
  `gunicorn -w 4 -b 0.0.0.0:8000 -k uvicorn_worker.UvicornWorker api:app`. Notas de release
  do uvicorn sobre supervisor/workers/SIGHUP **não se aplicam**.
- **A unit `scpi-api` não é versionada** no repo (só `ops/backup/scpi-backup.service` é).
  Mudanças de unit são feitas com `sed` direto em prod, sem review.
- `override.conf` já tem `Wants=` + `After=postgresql.service`. A unit não seta `StartLimit*`,
  mas `RestartSec=10` espaça os starts em ≥10s, então 5 starts em 10s é impossível e ela
  **nunca entra em `failed` definitivo** — retenta para sempre.
- Migrations concorrentes dos 4 workers estão cobertas por advisory lock em
  `infra/migrations.py::run_all`. Migrations são **fail-loud**: exceções propagam e `_ETAPAS`
  re-levanta com o nome da etapa.
- Rollback de schema exige rollback do deploy junto (código *aware* não funciona com colunas
  naive).

### Verificar a API pós-deploy sem SSH

- `GET https://api.scpi.me/health` — checa o DB.
- Alternativa: `POST /auth/login` com body `{}` → 422 prova nginx→uvicorn→FastAPI. `GET /`
  → 200 prova só o nginx.

### `pg_dump` de tabelas específicas na VM

```bash
PGPASSWORD=$(grep -m1 '^DB_PASSWORD=' /opt/scpi/.env | cut -d= -f2-) \
pg_dump -h 127.0.0.1 -U scpi -d scpi -t tabela1 -t tabela2 -f ~/dump-$(date +%F).sql
```
`sudo -u postgres pg_dump` não serve — o dono do banco é o usuário `scpi`.

### Recriar o banco do zero

1. `CREATE USER scpi` + `CREATE DATABASE scpi OWNER scpi` (via `sudo -u postgres psql`).
2. `DROP SCHEMA public CASCADE; CREATE SCHEMA public AUTHORIZATION scpi;`
   `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
3. O schema se auto-monta no boot (`ensure_base_schema`); `schema_inicial.sql` é redundância.
4. `cd BackEnd && venv/bin/python scripts/criar_admin.py` (usa `ADMIN_*` do `.env`).
5. `systemctl restart scpi-api`.

Ruídos inofensivos no load: `transaction_timeout` (param só PG17+, o server é PG16) e
`already exists` das auxiliares.

## Monitoramento

Três camadas, com janelas diferentes de propósito:

| Ferramenta | O que pega | Janela |
|---|---|---|
| UptimeRobot | API/VM/DB fora | ~5 min |
| healthchecks.io (`scpi-receipts`) | job de receipts parado | 15 min |
| healthchecks.io (backup) | backup quebrado | ~26 h |

- `GET /health` em `routers/public.py`: `SELECT 1`, 200 `{"status":"ok"}` / 503
  `{"status":"degraded"}`, rate limit 30/min, sem vazar erro interno.
- **Pegadinha**: o free tier do UptimeRobot manda **HEAD** e o método não é configurável.
  Por isso a rota usa `@router.api_route(methods=["GET","HEAD"])`, não `@router.get`.
- **O caminho de falha do `infra/database.py` custa 2× `DB_CONNECT_TIMEOUT`** (tentativa de
  pool + fallback cru) ≈ 20s com o valor 10. Acima de `DB_CONNECT_TIMEOUT=15`, o UptimeRobot
  (timeout 30s) acusaria timeout em vez de 503.
- Sentry: ver [[seguranca.md]]. `journalctl -u scpi-receipts` mostra
  `Sentry ativo — componente verificar_receipts.` a cada 15 min; no `scpi-api` essa linha
  **não aparece de propósito** (o `init_sentry` roda antes do `basicConfig`, para capturar
  erro de config em tempo de import).

## Backup do Postgres — concluído 2026-07-07

`ops/backup/scpi-backup.sh`: `pg_dump -Fc` → OCI Object Storage (instance principal) →
validação → ping no healthchecks.io. Timer systemd às 03:30 America/Sao_Paulo,
`Persistent=true`. Config real em `/etc/scpi-backup.env` (modo 600; a `HEALTHCHECK_URL` é
segredo), auth PG via `/root/.pgpass`, OCI CLI em venv próprio `/opt/oci-cli`.

Bucket `scpi-backups`, namespace de tenancy `grasggtqcknr`, compartment raiz (policies com
`in tenancy`). Sem cripto client-side — o at-rest da OCI basta para um dump.

**Duas lições caras:**
- **A lifecycle policy não existia até 2026-07-28**, apesar de o rollout de 2026-07-07 dar a
  retenção de 30d como concluída: o console mostrou a policy vazia, com os 22 dumps todos lá.
  *"Documentado no README" não é evidência de que o recurso existe no provedor — conferir no
  console.*
- As regras têm **prefixos disjuntos de propósito**: `expirar-dumps-30d` (prefixo `scpi_`) e
  `expirar-secrets-365d` (prefixo `secrets/`). Sem prefixo, a regra dos dumps casaria os
  pacotes de segredo e mataria a retenção de 365d.

Outros fatos do bucket: **versionamento desativado** — nada apagado ali é recuperável. A
instance principal tem só `manage objects`, então operações bucket-level retornam
**404 BucketNotFound**, que é *permissão faltando disfarçada de bucket inexistente*.

Pegadinha de rollout: `OnCalendar` com timezone exige systemd ≥ 252 (Ubuntu 22.04 tem 249).

## Backup de segredos — concluído 2026-07-28

Diário às 03:45 BRT → prefixo `secrets/` do mesmo bucket, cifrado com `age`, retenção 365d,
check próprio `scpi-secrets`. Script e units **separados de propósito**: falha aqui não pode
alarmar nem derrubar o backup do banco. Chave pública em uso na VM:
`age1jyltlqsdmmq769y6pyus8xza8vn4tngg7h3ylqnw2z76etx5tc7sly69sx`; a privada fica com o
Gustavo, fora do repo. Ver o porquê em [[decisions.md]].

Manifesto: `/opt/scpi/.env`, `/etc/scpi-backup.env`, `/root/.pgpass`,
`/etc/systemd/system/scpi-*`, `/etc/nginx/sites-{available,enabled}`, `/etc/letsencrypt`.
O ONNX do YuNet **não entra** — o script de câmera roda na máquina da sala.

Invariantes do script: fail-loud (path obrigatório ausente = exit 1 **antes** do ping); teto
`MAX_BYTES=20MB` checado antes de empacotar (glob errado não pode arrastar dado pessoal para
um objeto com 365d de retenção); `tar | age` em pipe único, tarball em claro nunca toca o
disco. Testes em `ops/secrets/test-scpi-secrets-backup.sh` (7 testes / 16 asserts, sem root,
rede ou OCI) — **só rodam em Linux**; no Git Bash o assert de modo 600 daria falso verde.

Critério de pronto de qualquer backup neste projeto: **teste de restore** (sha256 batendo) +
**teste de falha** (aborta sem pingar).

## Receipts de push — timer a cada 15 min

`scpi-receipts.service` (oneshot) + `.timer` (`OnCalendar=*:0/15`), rodando
`/opt/scpi/venv/bin/python -m scripts.verificar_receipts`. O `.service` usa `ExecStopPost`
com `$SERVICE_RESULT` → pinga `$HC_URL` no sucesso e `$HC_URL/fail` na falha.

**Divergência pendente entre repo e VM:** os units foram versionados em `ops/receipts/` só em
2026-08-03, e a versão do repo usa `EnvironmentFile=/etc/scpi-receipts.env` em vez do
`Environment=HC_URL=...` inline que ainda está na VM — a URL de ping é segredo (quem a tem
manda ping de sucesso e mascara job parado). **Falta na VM:** criar `/etc/scpi-receipts.env`,
copiar os units novos e rodar `systemctl start` uma vez para confirmar que o ping sai.
A URL apareceu numa conversa em 2026-08-03 e o Gustavo **decidiu não rotacionar o check** —
não sugerir de novo. Risco aceito e limitado: a URL só permite mascarar o sinal do job, não
lê nem altera dado.

## nginx

Server block de `admin.scpi.me` tem `Cache-Control: no-cache, must-revalidate` + CSP
`frame-ancestors`, `X-Frame-Options` e `X-Content-Type-Options` **no nível do server**.
Duas armadilhas que o `docs/runbooks/PORTAL_NGINX.md` documenta errado:

1. **`add_header` num `location` substitui os herdados do server, não soma.** Por isso os
   quatro headers ficam no server e as `location` não têm `add_header` nenhum.
2. `try_files $uri $uri/ /index.html` devolvia `index.html` com **200** para asset
   inexistente. Conserta com
   `location ~* ^/(js|vendor|fonts|css)/ { try_files $uri =404; }`.
