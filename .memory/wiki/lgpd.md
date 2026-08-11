# LGPD — Consentimento, Portabilidade, Revogação

O sistema trata **biometria facial de alunos**, que é dado pessoal sensível. Tudo aqui tem
efeito jurídico, não só técnico.

## Trilha de consentimento — em prod desde 2026-07-30

Tabela `ConsentimentosLGPD`, **append-only**. Fechou três lacunas: o backend não validava
consentimento (o app mandava `"true"` hardcoded), não havia versionamento de política, e o
perfil não mostrava estado nenhum.

Decisões com porquê em [[decisions.md]]:
- versão da política em `BackEnd/core/config.py`, não em env;
- backfill como aceite `'legado'`, nunca mapeado para `'1.0'`.

Outros pontos:

- **`SCPI_PRIVACY_URL` precisa do `?app=1`**: `https://admin.scpi.me/privacy.html?app=1`.
  O param faz o script no fim de `privacy.html` remover o link "Voltar ao Portal" — sem ele
  o aluno é levado à área administrativa. O documento é único de propósito (duplicar texto
  jurídico faz as versões divergirem).
- **Falha fechada no app**: `usePoliticaPrivacidade` bloqueia o checkbox se o fetch falhar.
  Se o card mostrar "Tentar novamente", o backend não tem `GET /politica-privacidade` — não
  é bug do app.
- **Ordem de deploy: backend SEMPRE antes do app.** App novo sem o endpoint = ninguém
  cadastra biometria. App **antigo** contra backend novo recebe **422** no cadastro de rosto
  (`politica_versao` é `Form(...)` obrigatório); login, presença e chamada seguem normais.

## Export do titular (Art. 18)

`GET /aluno/meus-dados/{usuario_id}` com `?formato=zip` (default) ou `?formato=json`
(retrocompat). O ZIP traz:

- `dados.pdf` (reportlab, legível para leigo),
- `dados.json` (estruturado, com `_schema_version`),
- `foto-<angulo>.jpg` para **todos** os ângulos ativos (mudou de foto única em 2026-07-24),
- `INTEGRIDADE.txt` (SHA-256 + HMAC-SHA256 do JSON canônico),
- `LEIA-ME.txt`.

Módulos: `BackEnd/infra/export_pdf.py`, `export_zip.py`, `export_integridade.py`.

- **`SCPI_EXPORT_HMAC_KEY` (32 bytes hex) é obrigatória** — sem ela o FastAPI recusa subir.
  Trocar a chave invalida o HMAC de exports antigos (o SHA-256 continua verificável).
- Datas no PDF são formatadas por `infra/export_pdf.py::_data_humana()` para
  `04/08/2026 12:00`. O JSON do mesmo export segue **ISO**, porque lá o consumidor é máquina.
  (Motivo: com `TIMESTAMPTZ` o PDF passaria a imprimir `2026-08-04T12:00:00-03:00` cru num
  documento de resposta a titular.)
- Ao adicionar campo novo: atualizar `buscar_dados_titular` em `repositories/alunos.py`,
  o `_schema_version` e os módulos PDF/JSON.
- **Retorno via `Response(content=...)`** — ver o incidente do ZIP truncado em [[patterns.md]].

## Revogação de biometria (Art. 18 VI)

`DELETE /aluno/biometria/{usuario_id}` (`revogar_biometria`): apaga os FaceIds da Rekognition
+ os objetos no S3 + grava evento de `revogacao` na trilha. Botão "Excluir minha biometria
(LGPD)" em `app/app/aluno/perfil.tsx`. Protegido por `require_self_or_admin`.

**Presenças passadas ficam** (Art. 7º V — base legal distinta da do dado biométrico).

## Pendências jurídicas

- **`portal/privacy.html` sem controlador identificado**: seções 1 e 2 ainda com
  placeholders (nome da instituição, CNPJ, endereço, e-mail de contato, os 3 campos do DPO).
  Política sem controlador é frágil independente do versionamento. Levantado 2026-07-30, não
  tocado. **Precisa dos dados, não de código.**
- **Alternativa não-biométrica de presença** — em aberto com os sócios. Ver [[decisions.md]].
- **LGPD comercial adiada**: retenção de biometria pós-desligamento, consentimento de
  responsável para menores, minuta de DPA.
- DPIA registra a transferência internacional e a geo derivada pelo Sentry — ver
  [[seguranca.md]].
