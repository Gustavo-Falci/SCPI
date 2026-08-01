# SCPI — Runbook de Segurança

## Rotação do token de câmera (A6)

Cada sala tem seu próprio token, guardado como hash em `camera_tokens`.

1. Emitir: `cd /opt/scpi/BackEnd && python scripts/camera_token.py emitir --sala "<sala>"`
2. Copiar o token para o `.env` da máquina da câmera (`CAMERA_SERVICE_TOKEN=`).
3. Reiniciar o script de reconhecimento naquela máquina.
4. Revogar o anterior: `python scripts/camera_token.py revogar --id <id>`

`listar` mostra id, sala, criação, último uso e situação — nunca o segredo.
Entre os passos 1 e 3 aquela sala não registra presença. É a consequência
aceita de não haver fallback para um token global.
