#!/usr/bin/env bash
# Harness de teste do scpi-secrets-backup.sh. Roda em Linux, sem root, sem OCI,
# sem rede: fixtures em tmpdir + stubs para oci/curl + chave age efêmera.
#
# Uso: bash ops/secrets/test-scpi-secrets-backup.sh
# Requer: age, age-keygen (sudo apt install -y age)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALVO="$SCRIPT_DIR/scpi-secrets-backup.sh"
FALHAS=0

ok()    { echo "  ok: $1"; }
falha() { echo "  FALHA: $1" >&2; FALHAS=$((FALHAS + 1)); }

if ! command -v age-keygen >/dev/null 2>&1; then
    echo "ERRO: age não instalado. sudo apt install -y age" >&2
    exit 1
fi

# Monta um ambiente isolado: fixtures, stubs e config.
# Ecoa o diretório raiz do sandbox; o chamador usa $SANDBOX/config.env.
fixture_config() {
    local sandbox
    sandbox="$(mktemp -d)"
    mkdir -p "$sandbox/fake/etc" "$sandbox/fake/systemd" "$sandbox/bin" "$sandbox/out"

    printf 'SECRET=abc123\n' > "$sandbox/fake/etc/.env"
    chmod 600 "$sandbox/fake/etc/.env"
    printf 'HEALTHCHECK_URL=https://exemplo\n' > "$sandbox/fake/etc/scpi-backup.env"
    chmod 600 "$sandbox/fake/etc/scpi-backup.env"
    printf '127.0.0.1:5432:scpi:scpi:senha\n' > "$sandbox/fake/etc/.pgpass"
    chmod 600 "$sandbox/fake/etc/.pgpass"
    printf '[Service]\nExecStart=/bin/true\n' > "$sandbox/fake/systemd/scpi-fake.service"

    # Stubs: registram argumentos em $STUB_OUT/<nome>.log e saem 0.
    cat > "$sandbox/bin/oci" <<'STUB'
#!/usr/bin/env bash
echo "$@" >> "$STUB_OUT/oci.log"
exit 0
STUB
    cat > "$sandbox/bin/curl" <<'STUB'
#!/usr/bin/env bash
echo "$@" >> "$STUB_OUT/curl.log"
exit 0
STUB
    chmod +x "$sandbox/bin/oci" "$sandbox/bin/curl"

    age-keygen -o "$sandbox/chave.txt" 2>/dev/null
    local pub
    pub="$(age-keygen -y "$sandbox/chave.txt")"

    cat > "$sandbox/config.env" <<EOF
AGE_RECIPIENT=$pub
OCI_NAMESPACE=ns-teste
OCI_BUCKET=bucket-teste
HEALTHCHECK_URL=https://hc.exemplo/teste
BACKUP_DIR=$sandbox/backups
OCI_BIN=$sandbox/bin/oci
CURL_BIN=$sandbox/bin/curl
SECRET_PATHS="$sandbox/fake/etc/.env $sandbox/fake/etc/scpi-backup.env $sandbox/fake/etc/.pgpass"
SYSTEMD_GLOB="$sandbox/fake/systemd/scpi-*"
EOF

    echo "$sandbox"
}

teste_config_ausente() {
    echo "teste: config ausente aborta"
    local saida rc
    saida="$(CONFIG_FILE=/caminho/que/nao/existe bash "$ALVO" 2>&1)"; rc=$?
    if [[ $rc -ne 0 ]]; then ok "exit != 0"; else falha "exit foi 0"; fi
    if grep -q "ausente ou ilegível" <<<"$saida"; then ok "mensagem clara"; else falha "mensagem: $saida"; fi
}

teste_variavel_obrigatoria_faltando() {
    echo "teste: variável obrigatória faltando aborta"
    local sandbox rc
    sandbox="$(fixture_config)"
    grep -v '^AGE_RECIPIENT=' "$sandbox/config.env" > "$sandbox/sem-age.env"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/sem-age.env" bash "$ALVO" >/dev/null 2>&1; rc=$?
    if [[ $rc -ne 0 ]]; then ok "exit != 0"; else falha "exit foi 0"; fi
    rm -rf "$sandbox"
}

teste_path_obrigatorio_ausente() {
    echo "teste: path obrigatório ausente aborta sem pingar"
    local sandbox rc
    sandbox="$(fixture_config)"
    rm "$sandbox/fake/etc/.pgpass"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/config.env" bash "$ALVO" >/dev/null 2>&1; rc=$?
    if [[ $rc -ne 0 ]]; then ok "exit != 0"; else falha "exit foi 0"; fi
    if [[ ! -f "$sandbox/out/curl.log" ]]; then ok "healthchecks não foi pingado"; else falha "pingou mesmo falhando"; fi
    rm -rf "$sandbox"
}

teste_teto_de_tamanho() {
    echo "teste: manifesto acima do teto aborta sem pingar"
    local sandbox rc
    sandbox="$(fixture_config)"
    head -c 2000000 /dev/urandom > "$sandbox/fake/etc/gordo.bin"
    echo "SECRET_PATHS=\"$sandbox/fake/etc/.env $sandbox/fake/etc/gordo.bin\"" >> "$sandbox/config.env"
    echo "MAX_BYTES=1000000" >> "$sandbox/config.env"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/config.env" bash "$ALVO" >/dev/null 2>&1; rc=$?
    if [[ $rc -ne 0 ]]; then ok "exit != 0"; else falha "exit foi 0"; fi
    if [[ ! -f "$sandbox/out/curl.log" ]]; then ok "healthchecks não foi pingado"; else falha "pingou acima do teto"; fi
    rm -rf "$sandbox"
}

teste_round_trip_cifrado() {
    echo "teste: pacote cifrado decripta e preserva conteúdo e permissão"
    local sandbox pkg extraido
    sandbox="$(fixture_config)"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/config.env" bash "$ALVO" >/dev/null 2>&1

    pkg="$(find "$sandbox/backups" -name 'scpi-secrets_*.tar.gz.age' 2>/dev/null | head -1)"
    if [[ -n "$pkg" ]]; then ok "pacote gerado"; else falha "nenhum pacote em $sandbox/backups"; rm -rf "$sandbox"; return; fi

    # Nenhum tarball em claro pode ter sobrado
    if [[ -z "$(find "$sandbox/backups" -name '*.tar.gz' 2>/dev/null)" ]]; then
        ok "nenhum tarball em claro no disco"
    else
        falha "sobrou tarball em claro"
    fi

    extraido="$sandbox/restore"
    mkdir -p "$extraido"
    age -d -i "$sandbox/chave.txt" "$pkg" | tar -xpf - --numeric-owner -C "$extraido"

    if [[ -f "$extraido/MANIFEST.txt" ]]; then ok "MANIFEST.txt presente"; else falha "MANIFEST.txt ausente"; fi

    local origem="$sandbox/fake/etc/.env"
    local destino="$extraido${origem}"
    if [[ -f "$destino" ]]; then
        if [[ "$(sha256sum < "$origem")" == "$(sha256sum < "$destino")" ]]; then
            ok "sha256 do .env bate"
        else
            falha "sha256 do .env divergiu"
        fi
        if [[ "$(stat -c %a "$destino")" == "600" ]]; then
            ok "permissão 600 preservada"
        else
            falha "permissão virou $(stat -c %a "$destino")"
        fi
    else
        falha "arquivo restaurado ausente: $destino"
    fi
    rm -rf "$sandbox"
}

teste_upload_e_ping() {
    echo "teste: happy path sobe o objeto e pinga o healthchecks"
    local sandbox rc
    sandbox="$(fixture_config)"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/config.env" bash "$ALVO" >/dev/null 2>&1; rc=$?
    if [[ $rc -eq 0 ]]; then ok "exit 0"; else falha "exit foi $rc"; fi

    if grep -q "object put" "$sandbox/out/oci.log" 2>/dev/null; then ok "object put chamado"; else falha "sem object put"; fi
    if grep -q "object head" "$sandbox/out/oci.log" 2>/dev/null; then ok "object head chamado"; else falha "sem object head"; fi
    if grep -q "secrets/scpi-secrets_" "$sandbox/out/oci.log" 2>/dev/null; then ok "prefixo secrets/ no nome"; else falha "nome sem prefixo secrets/"; fi
    if grep -q "hc.exemplo/teste" "$sandbox/out/curl.log" 2>/dev/null; then ok "healthchecks pingado"; else falha "sem ping"; fi
    rm -rf "$sandbox"
}

teste_falha_de_upload_nao_pinga() {
    echo "teste: falha no upload aborta sem pingar"
    local sandbox rc
    sandbox="$(fixture_config)"
    cat > "$sandbox/bin/oci" <<'STUB'
#!/usr/bin/env bash
echo "$@" >> "$STUB_OUT/oci.log"
exit 1
STUB
    chmod +x "$sandbox/bin/oci"
    STUB_OUT="$sandbox/out" CONFIG_FILE="$sandbox/config.env" bash "$ALVO" >/dev/null 2>&1; rc=$?
    if [[ $rc -ne 0 ]]; then ok "exit != 0"; else falha "exit foi 0"; fi
    if [[ ! -f "$sandbox/out/curl.log" ]]; then ok "healthchecks não foi pingado"; else falha "pingou com upload quebrado"; fi
    rm -rf "$sandbox"
}

teste_config_ausente
teste_variavel_obrigatoria_faltando
teste_path_obrigatorio_ausente
teste_teto_de_tamanho
teste_round_trip_cifrado
teste_upload_e_ping
teste_falha_de_upload_nao_pinga

echo
if [[ $FALHAS -eq 0 ]]; then echo "TODOS OS TESTES PASSARAM"; exit 0; fi
echo "$FALHAS verificação(ões) falharam" >&2; exit 1
