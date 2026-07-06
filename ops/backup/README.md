# Backup do Postgres SCPI

Backup diário (03:30 BRT) do banco `scpi` para OCI Object Storage, com
retenção de 30 dias e alerta por dead-man switch (healthchecks.io).

Spec: `docs/superpowers/specs/2026-07-06-backup-postgres-design.md`.

## Arquivos

| Arquivo | Papel |
|---|---|
| `scpi-backup.sh` | pg_dump → upload OCI → validação → ping |
| `scpi-backup.service` / `.timer` | agendamento systemd (Persistent=true) |
| `scpi-backup.env.example` | template de `/etc/scpi-backup.env` |

## Setup — uma vez

### 1. Console OCI

1. Bucket **privado** `scpi-backups` no compartment da VM.
2. Policy para o service principal do Object Storage — sem ela a criação da
   lifecycle rule falha com `InsufficientServicePermissions`. O identificador é
   `objectstorage-<region>` (São Paulo: `objectstorage-sa-saopaulo-1`):
   `Allow service objectstorage-sa-saopaulo-1 to manage object-family in compartment <compartment> where target.bucket.name='scpi-backups'`
   (se a criação da rule ainda falhar, usar a forma sem o `where`; recursos na
   raiz do tenancy → trocar `in compartment <compartment>` por `in tenancy` —
   é o caso desta tenancy, policy criada assim em 2026-07-06)
3. Lifecycle rule no bucket: regra `DELETE`, alvo *objects*, 30 dias.
4. Dynamic group `scpi-backup-dg`, matching rule (OCID da VM em Compute → Instances):
   `Any {instance.id = 'ocid1.instance.oc1...'}`
5. Policy no compartment (substituir `<compartment>`; raiz → `in tenancy`):
   `Allow dynamic-group scpi-backup-dg to manage objects in compartment <compartment> where target.bucket.name='scpi-backups'`

### 2. healthchecks.io

1. Conta grátis → novo check `scpi-backup`.
2. Period = 1 day, Grace = 2 hours.
3. Canal de alerta: e-mails da equipe.
4. Copiar a URL de ping para `HEALTHCHECK_URL` no `/etc/scpi-backup.env`.

### 3. VM (como root)

```bash
# OCI CLI em venv dedicado (isolado do venv do app)
python3 -m venv /opt/oci-cli
/opt/oci-cli/bin/pip install oci-cli
/opt/oci-cli/bin/oci --version

# .pgpass (host:port:db:user:senha) — senha do usuário scpi do .env do app
install -m 600 -o root -g root /dev/null /root/.pgpass
echo '127.0.0.1:5432:scpi:scpi:SENHA_AQUI' > /root/.pgpass

# Config
cd /opt/scpi/ops/backup
cp scpi-backup.env.example /etc/scpi-backup.env
chmod 600 /etc/scpi-backup.env
vim /etc/scpi-backup.env   # preencher OCI_NAMESPACE (`/opt/oci-cli/bin/oci os ns get --auth instance_principal`) e HEALTHCHECK_URL

# ATENÇÃO: OnCalendar com timezone exige systemd >= 252 (`systemctl --version`).
# Ubuntu 22.04 tem systemd 249: nesse caso, editar scpi-backup.timer e trocar
#   OnCalendar=*-*-* 03:30:00 America/Sao_Paulo
# por UTC equivalente (Brasil sem horário de verão, offset fixo -03):
#   OnCalendar=*-*-* 06:30:00 UTC

# Instalar units
chmod +x scpi-backup.sh
cp scpi-backup.service scpi-backup.timer /etc/systemd/system/
systemd-analyze verify /etc/systemd/system/scpi-backup.{service,timer}
systemctl daemon-reload
systemctl enable --now scpi-backup.timer
systemctl list-timers scpi-backup.timer
```

## Validação pós-implantação (obrigatória)

```bash
# Carregar config (define OCI_NAMESPACE)
set -a; . /etc/scpi-backup.env; set +a

# 1. Rodada manual
systemctl start scpi-backup.service
journalctl -u scpi-backup -n 30 --no-pager    # esperar "Backup ok: scpi_....dump"

# 2. Objeto no bucket
/opt/oci-cli/bin/oci os object list --auth instance_principal \
  -ns $OCI_NAMESPACE -bn scpi-backups --fields name,size

# 3. Teste de falha: colocar OCI_BUCKET=nao-existe em /etc/scpi-backup.env,
#    systemctl start scpi-backup.service => deve falhar (status=1) e healthchecks
#    NÃO recebe ping (check fica "late"/"down" após o prazo). Reverter config.

# 4. Teste de restore (OBRIGATÓRIO — backup não testado não é backup)
sudo -u postgres createdb scpi_restore_test
/opt/oci-cli/bin/oci os object get --auth instance_principal \
  -ns $OCI_NAMESPACE -bn scpi-backups --name scpi_$(date +%F).dump --file /tmp/scpi.dump
sudo -u postgres pg_restore -d scpi_restore_test --no-owner /tmp/scpi.dump
# Conferir contagens contra o banco real:
sudo -u postgres psql -d scpi_restore_test -c \
  "SELECT (SELECT count(*) FROM usuarios) usuarios,
          (SELECT count(*) FROM presencas) presencas,
          (SELECT count(*) FROM colecao_rostos) rostos;"
sudo -u postgres dropdb scpi_restore_test
rm /tmp/scpi.dump
```

## Restore em desastre

```bash
# Carregar config (define OCI_NAMESPACE)
set -a; . /etc/scpi-backup.env; set +a

# 1. Baixar o dump mais recente
/opt/oci-cli/bin/oci os object list --auth instance_principal \
  -ns $OCI_NAMESPACE -bn scpi-backups --fields name | sort
/opt/oci-cli/bin/oci os object get --auth instance_principal \
  -ns $OCI_NAMESPACE -bn scpi-backups --name scpi_YYYY-MM-DD.dump --file /tmp/scpi.dump

# 2. Restaurar (banco existente: --clean derruba e recria objetos)
systemctl stop scpi-api    # --clean falha se houver conexões ativas
sudo -u postgres pg_restore -d scpi --clean --if-exists --no-owner /tmp/scpi.dump

# 3. Subir o serviço e validar login no portal
systemctl restart scpi-api
```

Com dump disponível, `schema_inicial.sql` + `criar_admin.py` ficam
desnecessários no restore (dump contém schema + dados).

## Limitações conhecidas

- RPO de 24h (sem WAL/PITR) — aceito nesta fase; reavaliar com clientes pagantes.
- Fotos ficam no S3/AWS (durável); não entram neste backup.
- `/opt/scpi/BackEnd/.env` NÃO é coberto (segredos exigem cifragem client-side — escopo separado).
- Dumps locais em `/var/backups/scpi` são retidos por 2 dias (amortecedor se a OCI estiver fora no horário do backup).
