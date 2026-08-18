# Deploy SCPI — Notas Operacionais

## Servidor de Produção

- Local: `/opt/scpi`
- venv: Python 3.12
- Service systemd: `scpi-api`
- Banco: PostgreSQL 16 local na própria VM (`127.0.0.1`, desde 2026-06-15)
- AWS: Rekognition + S3 (credenciais em `.env`)
- `.env` fica em `/opt/scpi/.env` (raiz do repo, não `BackEnd/.env`)
- Backup diário do banco: ver `ops/backup/README.md` (timer `scpi-backup`, bucket OCI `scpi-backups`, alerta healthchecks.io)

## Procedimento padrão de deploy

```bash
cd /opt/scpi
git pull
cd BackEnd
pip install -r requirements.txt --upgrade
sudo systemctl restart scpi-api
sudo journalctl -u scpi-api -n 50 --no-pager
```

Verificar nos logs que o serviço subiu sem `RuntimeError`.

### Serviço não sobe após o deploy

As migrations são fail-loud desde 2026-07-27: migration que falha, ou banco
fora do ar, abortam o boot e o systemd entra em restart loop. É intencional —
schema incompleto com a API no ar produz 500s aleatórios longe da causa.

```bash
sudo journalctl -u scpi-api -n 100 --no-pager | grep -i "migration\|RuntimeError"
```

A mensagem tem o formato `Migration <nome_da_etapa> falhou: <erro do psycopg2>`
e diz exatamente qual `ensure_*` de `BackEnd/infra/migrations.py` quebrou.

## Variáveis de ambiente obrigatórias

Conferir `/opt/scpi/.env` contra `.env.example`. Em particular:

- `DB_*` — conexão PostgreSQL
- `SECRET_KEY` — assinatura JWT
- `AWS_*`, `COLLECTION_ID`, `BUCKET_NAME` — Rekognition + S3
- `RESEND_API_KEY` — envio de e-mails
- `CAMERA_SERVICE_TOKEN` — autenticação do script de câmera
- `ALLOWED_ORIGINS` — CORS em produção
- `SCPI_EXPORT_HMAC_KEY` — assinatura HMAC do export LGPD (ver abaixo)
- `SENTRY_DSN` — *opcional*, telemetria de erros. Vazio desativa. O mesmo DSN
  serve à API e ao job `scpi-receipts`; a tag `componente` separa os dois no
  painel.

---

## Export LGPD — Chave HMAC

O endpoint `GET /aluno/meus-dados/{usuario_id}?formato=zip` retorna um pacote
ZIP contendo PDF, JSON, foto e um manifesto de integridade assinado com
HMAC-SHA256. A chave de assinatura vem da env `SCPI_EXPORT_HMAC_KEY`.

### Geração da chave (uma vez)

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Configuração

Adicionar em `/opt/scpi/.env`:

```
SCPI_EXPORT_HMAC_KEY=<saída do comando acima>
```

Reiniciar o serviço:

```bash
sudo systemctl restart scpi-api
```

Se a env estiver ausente, o backend recusa subir com
`RuntimeError: SCPI_EXPORT_HMAC_KEY não definida`.

### Rotação

Trocar a chave **invalida** verificações HMAC de exports antigos. O SHA-256
do payload continua verificável por qualquer pessoa, independentemente.

Antes de rotacionar:

1. Avisar o DPO.
2. Registrar data da rotação para que solicitações antigas possam ser
   reemitidas se necessário.
3. Trocar a env e reiniciar o serviço.

### Verificação manual de um ZIP

Para conferir o SHA-256 de um `dados.json` recebido:

```bash
python -c "import json,hashlib; \
print(hashlib.sha256(json.dumps(json.load(open('dados.json')), \
sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest())"
```

O valor deve bater com o campo `SHA-256` em `INTEGRIDADE.txt`. O HMAC só pode
ser verificado pelo servidor SCPI (chave secreta).
