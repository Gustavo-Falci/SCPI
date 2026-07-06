#!/usr/bin/env bash
# Backup diário do Postgres SCPI → OCI Object Storage.
# Config: /etc/scpi-backup.env (ver ops/backup/scpi-backup.env.example).
# Falha em qualquer passo => exit != 0 => sem ping => healthchecks.io alerta.
set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/scpi-backup.env}"
if [[ ! -r "$CONFIG_FILE" ]]; then
    echo "ERRO: config $CONFIG_FILE ausente ou ilegível." >&2
    exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG_FILE"

# Obrigatórias — aborta com mensagem clara se faltar
: "${OCI_NAMESPACE:?OCI_NAMESPACE não definida em $CONFIG_FILE}"
: "${OCI_BUCKET:?OCI_BUCKET não definida em $CONFIG_FILE}"
: "${HEALTHCHECK_URL:?HEALTHCHECK_URL não definida em $CONFIG_FILE}"
: "${PGUSER:?PGUSER não definida em $CONFIG_FILE}"
: "${PGDATABASE:?PGDATABASE não definida em $CONFIG_FILE}"

# Opcionais com default
BACKUP_DIR="${BACKUP_DIR:-/var/backups/scpi}"
OCI_BIN="${OCI_BIN:-/opt/oci-cli/bin/oci}"
PGHOST="${PGHOST:-127.0.0.1}"
export PGPASSFILE="${PGPASSFILE:-/root/.pgpass}"

DUMP_NAME="scpi_$(date +%F).dump"
DUMP_FILE="$BACKUP_DIR/$DUMP_NAME"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

echo "[1/5] pg_dump ${PGDATABASE}@${PGHOST} -> $DUMP_FILE"
pg_dump -Fc -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -f "$DUMP_FILE"

if [[ ! -s "$DUMP_FILE" ]]; then
    echo "ERRO: dump vazio: $DUMP_FILE" >&2
    exit 1
fi

echo "[2/5] upload -> oci://$OCI_BUCKET/$DUMP_NAME"
"$OCI_BIN" os object put \
    --auth instance_principal \
    --namespace "$OCI_NAMESPACE" \
    --bucket-name "$OCI_BUCKET" \
    --file "$DUMP_FILE" \
    --name "$DUMP_NAME" \
    --force

echo "[3/5] validando objeto no bucket"
"$OCI_BIN" os object head \
    --auth instance_principal \
    --namespace "$OCI_NAMESPACE" \
    --bucket-name "$OCI_BUCKET" \
    --name "$DUMP_NAME" >/dev/null

echo "[4/5] limpando dumps locais com mais de 2 dias"
find "$BACKUP_DIR" -name 'scpi_*.dump' -mtime +2 -delete

echo "[5/5] ping healthchecks"
curl -fsS --retry 3 --max-time 10 "$HEALTHCHECK_URL" >/dev/null

echo "Backup ok: $DUMP_NAME ($(du -h "$DUMP_FILE" | cut -f1))"
