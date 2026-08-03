# Verificação de receipts de push

O envio de push devolve um **ticket**, não a confirmação de entrega. O receipt
— que diz se o push chegou ou se o device sumiu — só fica disponível alguns
minutos depois, numa chamada separada (`getReceipts`).

Sem consultar receipt, token de app desinstalado nunca é podado: fica na tabela
para sempre e cada envio gasta uma requisição à toa. O `DeviceNotRegistered` que
aparece no ticket cobre só parte dos casos; o resto só aparece no receipt.

**Estes units já estão instalados e rodando na VM desde antes de serem
versionados.** Este diretório foi criado em 2026-08-03 para que o repo reflita o
que existe em produção — o runbook de restauração em `ops/secrets/README.md`
manda habilitar `scpi-receipts.timer`, e até então a definição não existia em
lugar nenhum do repositório.

## Peças

| Peça | Onde |
|---|---|
| Envio, registra os tickets | `BackEnd/services/notificacoes.py` → `registrar_tickets_pendentes` |
| Tabela de pendentes | `PushReceiptsPendentes` (`ensure_push_receipts_table`) |
| Job que consulta e poda | `BackEnd/scripts/verificar_receipts.py` |
| Agendamento | `scpi-receipts.timer` (este diretório) |

## Diferença entre o que está na VM e o que está aqui

O unit em produção tem a URL do healthchecks.io **inline**:

```ini
Environment=HC_URL=https://hc-ping.com/<uuid>
```

A versão deste diretório usa `EnvironmentFile=/etc/scpi-receipts.env`, seguindo
a mesma regra já documentada em `ops/backup/scpi-backup.env.example`: a URL de
ping é segredo, porque quem a tem consegue mandar ping de sucesso e mascarar um
job que parou. Inline, ela ficaria no git para sempre e legível por qualquer
usuário local (units em `/etc/systemd/system/` costumam ser 644).

Para alinhar a VM a esta versão:

```bash
# 1. Guarde a URL atual antes de sobrescrever o unit
systemctl cat scpi-receipts.service | grep HC_URL

# 2. Crie o arquivo de config
sudo cp /opt/scpi/ops/receipts/scpi-receipts.env.example /etc/scpi-receipts.env
sudo nano /etc/scpi-receipts.env          # cole a URL do passo 1 em HC_URL=
sudo chown root:root /etc/scpi-receipts.env
sudo chmod 600 /etc/scpi-receipts.env

# 3. Substitua os units
sudo cp /opt/scpi/ops/receipts/scpi-receipts.service /etc/systemd/system/
sudo cp /opt/scpi/ops/receipts/scpi-receipts.timer   /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Rode uma vez à mão e confirme que o ping saiu
sudo systemctl start scpi-receipts.service
journalctl -u scpi-receipts.service -n 20 --no-pager
```

O passo 4 é obrigatório: se o `EnvironmentFile` não for lido, `$HC_URL` fica
vazio e o `curl` do `ExecStopPost` falha — o healthchecks para de receber ping e
alerta sozinho, mas é melhor descobrir agora do que pelo alerta.

## Conferir

```bash
systemctl list-timers scpi-receipts.timer --no-pager
journalctl -u scpi-receipts.service -n 30 --no-pager
```

Linha esperada a cada execução:

```
Receipts: N pendentes, M podados, K processados.
Receipts: X órfão(s) antigo(s) limpo(s).
```

Só a segunda linha aparecendo é o caso normal com zero pendentes — a primeira é
emitida apenas quando há tickets a processar.

## Envs do script (opcionais, com default no código)

| Env | Default | Para quê |
|---|---|---|
| `RECEIPTS_IDADE_MIN_S` | `900` | idade mínima do ticket antes de consultar — a Expo não tem o receipt de imediato |
| `RECEIPTS_IDADE_MAX_S` | `86400` | depois disso o pendente é dado por perdido e apagado |
| `RECEIPTS_LIMITE` | `1000` | teto de tickets por ciclo (a API da Expo aceita 1000 por lote) |

## Por que `User=ubuntu` e não `root`

Diferente dos backups, este job não lê `/etc` nem escreve fora de `/opt/scpi`.
Precisa só do venv e do `.env` do projeto, ambos legíveis pelo `ubuntu`.

## Falhas

O script sai com código 1 sem conexão ao banco, e o Sentry é inicializado como
`verificar_receipts` (ver `core/observabilidade.py`). Falha de transporte num
lote do `getReceipts` é logada e ignorada — aqueles tickets ficam pendentes e
entram no ciclo seguinte, que é o comportamento desejado.
