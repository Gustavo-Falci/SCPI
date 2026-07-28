# Backup dos segredos e config da VM SCPI

Backup diário (03:45 BRT) dos segredos e da config de infraestrutura da VM,
cifrado com `age` antes de sair da máquina, para OCI Object Storage, com
retenção de 365 dias e alerta por dead-man switch (healthchecks.io).

Spec: `docs/superpowers/specs/2026-07-28-backup-segredos-design.md`.

## O que é e o que não é

Cobre o que faz a VM funcionar: `/opt/scpi/.env`, credenciais do Postgres,
units systemd, config do nginx e certificados. **Não** cobre os dados — esses
vivem no backup do Postgres (`ops/backup/README.md`). Os dois juntos, mais um
`git clone`, reconstroem a VM.

| Arquivo | Papel |
|---|---|
| `scpi-secrets-backup.sh` | valida manifesto → `tar` \| `age` → upload OCI → validação → ping |
| `test-scpi-secrets-backup.sh` | harness de teste (sem root, sem OCI, sem rede) |
| `scpi-secrets-backup.service` / `.timer` | agendamento systemd (`Persistent=true`) |
| `scpi-secrets.env.example` | template de `/etc/scpi-secrets.env` |

## O que entra no pacote

| Path | Conteúdo |
|---|---|
| `/opt/scpi/.env` | segredos da API |
| `/etc/scpi-backup.env` | config do backup do banco |
| `/root/.pgpass` | senha do Postgres |
| `/etc/systemd/system/scpi-*` | units e o `scpi-api.service.d/override.conf` |
| `/etc/nginx/sites-available`, `sites-enabled` | proxy e TLS |
| `/etc/letsencrypt` | account key e conf de renovação |

Ausência de qualquer um deles aborta o backup com `exit 1` e **sem** ping — um
backup verde que não contém o `.env` só seria descoberto no dia do desastre.

## Setup — uma vez

### 1. Gerar a chave (na máquina do Gustavo, NUNCA na VM)

```bash
age-keygen -o scpi-secrets-key.txt
age-keygen -y scpi-secrets-key.txt    # chave PÚBLICA → vai em AGE_RECIPIENT
```

> **Perdeu a chave privada, perdeu todos os backups de segredo.** Não há
> recuperação: a VM só tem a pública e por isso não consegue decriptar nem o
> que ela mesma gerou. Guardar `scpi-secrets-key.txt` no password manager **e**
> em uma cópia offline. Nunca em git, nunca na VM, nunca no bucket.

### 2. Console OCI

Bucket `scpi-backups` e dynamic group já existem (ver `ops/backup/README.md`).
Falta só a retenção deste prefixo:

1. Lifecycle rule no bucket: regra `DELETE`, alvo *objects*, **prefixo `secrets/`**, **365 dias**.
2. A regra de 30 dias dos dumps continua valendo — ela não tem prefixo e as duas
   convivem, mas confira que a de 30 dias não passou a casar `secrets/`.
3. Se a criação falhar com `InsufficientServicePermissions`, é a policy do
   service principal `objectstorage-sa-saopaulo-1` — mesma causa e mesma
   correção documentadas em `ops/backup/README.md` (aconteceu em 2026-07-07).

Nenhuma credencial nova: o upload usa instance principal, e a policy do dynamic
group já concede `manage objects` no bucket.

### 3. healthchecks.io

1. Novo check `scpi-secrets` (separado do `scpi-backup`, para o alerta dizer
   qual dos dois quebrou).
2. Period = 1 day, Grace = 2 hours.
3. Copiar a URL de ping para `HEALTHCHECK_URL` em `/etc/scpi-secrets.env`.

### 4. VM

```bash
sudo apt install -y age
sudo git config --system --add safe.directory /opt/scpi   # senão o MANIFEST.txt não registra o commit
cd /opt/scpi && git pull

sudo cp ops/secrets/scpi-secrets.env.example /etc/scpi-secrets.env
sudo chown root:root /etc/scpi-secrets.env && sudo chmod 600 /etc/scpi-secrets.env
sudo nano /etc/scpi-secrets.env    # AGE_RECIPIENT, OCI_NAMESPACE, HEALTHCHECK_URL

sudo cp ops/secrets/scpi-secrets-backup.service /etc/systemd/system/
sudo cp ops/secrets/scpi-secrets-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scpi-secrets-backup.timer
```

O script roda como **root** por necessidade: `/root/.pgpass` é 600 root e
`/etc/letsencrypt` não é legível por `ubuntu`.

## Rodar os testes

```bash
bash /opt/scpi/ops/secrets/test-scpi-secrets-backup.sh
```

Não precisa de root, de rede nem de OCI: usa fixtures em `mktemp -d`, stubs de
`oci`/`curl` e uma chave `age` efêmera. Esperado: `TODOS OS TESTES PASSARAM`.

Se der `Permission denied`, o script chegou sem bit de execução — é o
`core.filemode=false` do repo. Corrigir com
`git add --chmod=+x ops/secrets/*.sh` e novo commit.

## Validação — obrigatória antes de confiar no backup

### Execução manual

```bash
sudo systemctl start scpi-secrets-backup.service
journalctl -u scpi-secrets-backup.service -n 40 --no-pager
```

Esperado: as 6 etapas e `Backup de segredos ok: scpi-secrets_<data>.tar.gz.age`,
mais o check `scpi-secrets` verde no healthchecks.io.

### Teste de restore

Baixar e decriptar **na máquina local**, nunca na VM:

```bash
oci os object get --namespace <ns> --bucket-name scpi-backups \
  --name secrets/scpi-secrets_<data>.tar.gz.age --file pacote.age
age -d -i scpi-secrets-key.txt pacote.age > pacote.tar.gz
mkdir restore && tar -xzpf pacote.tar.gz --numeric-owner -C restore
cat restore/MANIFEST.txt
sha256sum restore/opt/scpi/.env
stat -c %a restore/opt/scpi/.env
```

Na VM: `sudo sha256sum /opt/scpi/.env`.

Os dois `sha256sum` têm de ser idênticos e o `stat` tem de retornar `600`.
Divergiu, o backup **não** está pronto.

### Teste de falha

```bash
sudo mv /etc/scpi-backup.env /etc/scpi-backup.env.bak
sudo systemctl start scpi-secrets-backup.service; echo "exit=$?"
sudo mv /etc/scpi-backup.env.bak /etc/scpi-backup.env
sudo systemctl start scpi-secrets-backup.service   # volta ao verde
```

Esperado: falha com `path obrigatório ausente` e **nenhum** ping novo no
healthchecks.io.

Repetir os dois testes a cada rotação de segredo.

## Restore

### Um arquivo

Seguir o bloco do teste de restore acima e copiar de `restore/` o que interessa.
Reinstalar preservando modo:

```bash
sudo install -o root -g root -m 600 restore/etc/scpi-backup.env /etc/scpi-backup.env
```

### Desastre — VM perdida

1. Provisionar VM nova (Ubuntu, mesma versão), instalar Postgres, python e nginx.
2. `git clone` do repositório em `/opt/scpi`.
3. Baixar o pacote do bucket e **decriptar na máquina local** — a chave privada
   não deve chegar perto de um servidor.
4. `scp pacote.tar.gz` para a VM nova.
5. Restaurar os arquivos preservando dono e modo:
   ```bash
   sudo tar -xzpf pacote.tar.gz --numeric-owner -C /
   ```
   O `-z` é explícito de propósito: o `tar` autodetecta compressão ao ler de
   arquivo, mas **não** ao ler de stdin. Se preferir decriptar direto no pipe,
   `age -d -i chave.txt pacote.age | sudo tar -xzpf - --numeric-owner -C /`
   só funciona com o `-z`.
6. `sudo systemctl daemon-reload` e `sudo systemctl enable --now` em
   `scpi-api.service`, `scpi-backup.timer`, `scpi-receipts.timer` e
   `scpi-secrets-backup.timer`.
7. Restaurar o banco pelo runbook de `ops/backup/README.md`.
8. Conferir `/health` da API e o próximo disparo dos três timers com
   `systemctl list-timers --no-pager`.
