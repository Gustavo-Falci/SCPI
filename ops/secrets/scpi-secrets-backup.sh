#!/usr/bin/env bash
# Backup diário dos segredos e da config da VM SCPI → OCI Object Storage, cifrado com age.
# Config: /etc/scpi-secrets.env (ver ops/secrets/scpi-secrets.env.example).
# Falha em qualquer passo => exit != 0 => sem ping => healthchecks.io alerta.
set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/etc/scpi-secrets.env}"
if [[ ! -r "$CONFIG_FILE" ]]; then
    echo "ERRO: config $CONFIG_FILE ausente ou ilegível." >&2
    exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG_FILE"

# Obrigatórias — aborta com mensagem clara se faltar
: "${AGE_RECIPIENT:?AGE_RECIPIENT não definida em $CONFIG_FILE}"
: "${OCI_NAMESPACE:?OCI_NAMESPACE não definida em $CONFIG_FILE}"
: "${OCI_BUCKET:?OCI_BUCKET não definida em $CONFIG_FILE}"
: "${HEALTHCHECK_URL:?HEALTHCHECK_URL não definida em $CONFIG_FILE}"

# Opcionais com default
BACKUP_DIR="${BACKUP_DIR:-/var/backups/scpi-secrets}"
OCI_BIN="${OCI_BIN:-/opt/oci-cli/bin/oci}"
AGE_BIN="${AGE_BIN:-age}"
CURL_BIN="${CURL_BIN:-curl}"
MAX_BYTES="${MAX_BYTES:-20971520}"
OCI_PREFIX="${OCI_PREFIX:-secrets/}"

# Manifesto de produção. A config sobrescreve (o harness aponta para fixtures).
SECRET_PATHS="${SECRET_PATHS:-
/opt/scpi/.env
/etc/scpi-backup.env
/root/.pgpass
/etc/nginx/sites-available
/etc/nginx/sites-enabled
/etc/letsencrypt
}"
SYSTEMD_GLOB="${SYSTEMD_GLOB:-/etc/systemd/system/scpi-*}"

# Word splitting é intencional: as duas variáveis são listas de paths sem espaços.
# shellcheck disable=SC2206,SC2086
PATHS=( $SECRET_PATHS $SYSTEMD_GLOB )

echo "[1/6] validando manifesto (${#PATHS[@]} paths)"
for p in "${PATHS[@]}"; do
    if [[ ! -e "$p" ]]; then
        # Glob que não casa fica literal e cai aqui — units sumirem é exatamente
        # o tipo de estrago que este backup existe para detectar.
        echo "ERRO: path obrigatório ausente: $p" >&2
        exit 1
    fi
    if [[ ! -r "$p" ]]; then
        echo "ERRO: path obrigatório ilegível: $p" >&2
        exit 1
    fi
done

echo "[2/6] conferindo tamanho (teto $MAX_BYTES bytes)"
TOTAL_BYTES="$(du -sbc "${PATHS[@]}" | tail -1 | cut -f1)"
if (( TOTAL_BYTES > MAX_BYTES )); then
    echo "ERRO: manifesto tem $TOTAL_BYTES bytes, acima do teto $MAX_BYTES." >&2
    echo "Alguém adicionou path demais ao manifesto, ou um dump vazou para dentro dele." >&2
    exit 1
fi

TMPDIR_PKG="$(mktemp -d)"
chmod 700 "$TMPDIR_PKG"
trap 'rm -rf "$TMPDIR_PKG"' EXIT

echo "[3/6] gerando MANIFEST.txt"
{
    echo "SCPI — backup de segredos e config"
    echo "data:     $(date -Is)"
    echo "host:     $(hostname)"
    echo "git:      $(git -C /opt/scpi rev-parse HEAD 2>/dev/null || echo indisponivel)"
    echo "systemd:  $(systemctl --version 2>/dev/null | head -1 || echo indisponivel)"
    echo "postgres: $(psql --version 2>/dev/null || echo indisponivel)"
    echo "python:   $(python3 --version 2>&1 || echo indisponivel)"
    echo "bytes:    $TOTAL_BYTES"
    echo
    echo "arquivos:"
    ls -ld "${PATHS[@]}"
} > "$TMPDIR_PKG/MANIFEST.txt"

echo "[4/6] empacotando e cifrando"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
PKG_NAME="scpi-secrets_$(date +%F).tar.gz.age"
PKG_FILE="$BACKUP_DIR/$PKG_NAME"

# Pipe único: o tarball em claro nunca toca o disco. Os paths entram sem a barra
# inicial (com -C /) para a extração ser previsível e sem warning do tar.
tar --numeric-owner -p -czf - \
    -C "$TMPDIR_PKG" MANIFEST.txt \
    -C / "${PATHS[@]#/}" \
    | "$AGE_BIN" -r "$AGE_RECIPIENT" -o "$PKG_FILE"

chmod 600 "$PKG_FILE"

if [[ ! -s "$PKG_FILE" ]]; then
    echo "ERRO: pacote cifrado vazio: $PKG_FILE" >&2
    exit 1
fi

echo "[5/6] upload -> oci://$OCI_BUCKET/${OCI_PREFIX}${PKG_NAME}"
"$OCI_BIN" os object put \
    --auth instance_principal \
    --namespace "$OCI_NAMESPACE" \
    --bucket-name "$OCI_BUCKET" \
    --file "$PKG_FILE" \
    --name "${OCI_PREFIX}${PKG_NAME}" \
    --force

"$OCI_BIN" os object head \
    --auth instance_principal \
    --namespace "$OCI_NAMESPACE" \
    --bucket-name "$OCI_BUCKET" \
    --name "${OCI_PREFIX}${PKG_NAME}" >/dev/null

# Cópias locais só existem cifradas; a própria VM não consegue abri-las.
find "$BACKUP_DIR" -name 'scpi-secrets_*.tar.gz.age' -mtime +2 -delete

echo "[6/6] ping healthchecks"
"$CURL_BIN" -fsS --retry 3 --max-time 10 "$HEALTHCHECK_URL" >/dev/null

echo "Backup de segredos ok: $PKG_NAME ($(du -h "$PKG_FILE" | cut -f1))"
