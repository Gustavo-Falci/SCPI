# Bugs Conhecidos, Quirks e Pins Defensivos

## Pins que NÃO podem regredir

- **`fastapi==0.136.1`.** A 0.136.3 é release **malicioso** (MAL-2026-4750): injeta a
  dependência oculta `fastar>=0.9.0` no extra `[standard]` (dependency-confusion, RCE no
  install). O SCPI instala fastapi puro, sem `[standard]`, então `fastar` nunca entrou em
  prod — mas o pacote é genuinamente malicioso, não disputado. **pip-audit usa feed OSV e
  não cobre `MAL-*`**, então o CI passava verde. O Dependabot já derrotou o pin uma vez
  (PR #35, malicioso rodou em prod de 2026-06-04 a 2026-06-16); desde 2026-06-16 há regra
  `ignore` de minor+patch para `fastapi`. Verificado em 2026-06-16 que a 0.137.1 **ainda**
  puxa `fastar` no `[standard]` — cadeia não saneada upstream.
  **Regra geral: versão maliciosa pinada à mão sempre precisa de `ignore` no Dependabot.**
- **`opencv-python` na linha 4.x.** A 5.0 removeu `cv2.CascadeClassifier` do pacote core
  (foi para o contrib) e quebra `scripts/reconhecimento_tempo_real.py`. Dependabot ignora
  `semver-major`. O script já migrou para `FaceDetectorYN` junto do liveness, mas o pin
  segue. Alternativa se precisar do v5: `opencv-contrib-python`.
- **`pydantic-core` ignorado no pip.** É dep transitiva pinada exato pelo `pydantic`; PR
  avulso quebra a resolução (pip-audit falha com "conflicting dependencies"). Para atualizar,
  subir `pydantic` junto.
- **Stack Expo inteira ignorada pelo Dependabot** — ver [[app-mobile.md]].

## Armadilhas ativas do código

- **`get_db_cursor` devolve `None` em vez de levantar** quando o pool não dá conexão
  (`infra/database.py`). Traduzir esse `None` para 403 vira **falta silenciosa**: a câmera
  classifica `definitivo = status < 500` e nunca repete a tentativa. Existe a sentinela
  `DB_INDISPONIVEL`, mas ela foi aplicada **só** aos dois caminhos da câmera e a
  `listar_tokens`/`revogar_token`. O padrão `if not cur: return None` segue em dezenas de
  repositórios, cada um achatando "banco fora" sobre "resultado vazio". Sweep cego toca
  código demais; o critério é "o chamador toma decisão diferente se for banco fora?".
- **`atualizar_senha_por_usuario_id` também zera `primeiro_acesso`.** Por isso o re-hash do
  login usa `atualizar_hash_senha`, que só toca `senha`. **Não unificar as duas.**
- **`camera_token.py` não tem `try/except` em `emitir`/`listar`** — banco fora vira traceback
  cru. Feio, mas não finge sucesso. Risco aceito: `KeyError` de coluna renomeada só aparece
  ao rodar na VM.
- **Token de câmera emitido para a sala errada marca presença na aula errada em silêncio.**
  A sala vem do token, nunca do cliente — conferir na emissão.

## Quirks de ambiente

- **Dev em Windows não testa gunicorn**: `import gunicorn` quebra com
  `ModuleNotFoundError: No module named 'fcntl'`. Verificação só na VM.
- **`requirements.txt` usa pins exatos.** Sem `git pull` antes do `pip install --upgrade`,
  o pip vê as pins antigas e reporta "Already satisfied" sem atualizar nada.
- **`pip install -r requirements.txt --upgrade` NÃO remove pacote que saiu do arquivo.**
  Retirar dependência exige `pip uninstall` explícito na VM.
- **`npm audit fix` no app é proibido**: drifta as resoluções do Expo no lock e ainda deixa
  vulnerabilidade sem patch. Usar `overrides` pinado no `package.json`.
- **`npm audit --dry-run` reporta 0 mudanças** quando `app/node_modules` existe e está
  dessincronizado do lock. Testar em cópia limpa no scratchpad.
- **Violação de CSP no console do portal quase sempre é extensão do browser.** Como
  distinguir: (1) `Invoke-WebRequest https://admin.scpi.me/` e procurar o recurso no HTML
  servido — o portal não pede nada de terceiro desde a PR #89; (2) `'<URL>'` na mensagem do
  Chrome significa `data:` URI, e o portal só carrega fonte por caminho, logo é injeção;
  (3) a coluna Initiator no Network aponta para `chrome-extension://`.
  **Não afrouxar a política de produção por causa da máquina de um dev.**
- **Bit de execução em script novo**: o repo tem `core.filemode=false`, e `git add --chmod=+x`
  já falhou silenciosamente (script entrou como `100644`, `systemctl start` deu `203/EXEC`).
  Conferir com `git ls-files -s` logo após o `git add`. Rodar via `bash arquivo.sh` ignora o
  modo e mascara o problema.
- **`age` no Windows**: decriptar sempre com `age -o arquivo`, nunca `> arquivo` — o redirect
  do PowerShell trata como texto e corrompe o `.tar.gz`.
- **`tar` autodetecta compressão lendo de arquivo, mas não de stdin.** `age -d | tar -xpf -`
  falha com `Archive is compressed. Use -z option`; todo pipe precisa de `-z` explícito.

## Quirks de CI

- **Gitleaks é assimétrico**: o run agendado (segunda 06:00 UTC) escaneia o histórico git
  **completo**; runs de push/PR só escaneiam commits novos. Scan agendado pode falhar com
  `main` limpa. Run de push verde não prova que o agendado passa.
  O workflow **não tem `workflow_dispatch`** — `gh workflow run` falha com HTTP 422.
- **`paths-filter` esconde advisory nova**: `npm-audit-mobile` só roda em PR que toca `app/`.
  Advisory nova em dep do app fica invisível nas PRs e só quebra no push em `main` — foi o
  que deixou `main` vermelha de 2026-07-21 a 2026-07-23 sem nenhuma PR reprovada.

## Bugs de produção já resolvidos (o raciocínio ainda vale)

- **Chamada aberta escolhida globalmente**: `registrar_presenca_por_face` usava
  `WHERE status='Aberta' ORDER BY data_criacao DESC LIMIT 1` e quebrava com 2+ turmas
  simultâneas. Corrigido; fechou de brinde o endpoint órfão `/chamadas/registrar_rosto`, que
  deixava qualquer aluno autenticado marcar a própria presença de qualquer lugar, sem
  liveness.
- **Frequência estourando 100%** (PDF mostrou 21/14 = 150%): o `LEFT JOIN Presencas`
  (numerador) contava todas as chamadas do período enquanto `aulas_dadas` (denominador) só
  contava as pós-matrícula. Numerador e denominador precisam da **mesma janela**; invariante
  `presentes <= dadas` travada por teste.
- **ZIP truncado atrás do gunicorn** — ver `Response` vs `StreamingResponse` em [[patterns.md]].
- **Login travado em produção** (2026-05-19) pelo cookie jar do RN — ver [[seguranca.md]].
- **Relatórios truncando em 50** sem aviso: o endpoint sempre teve `limit=50` default e o
  `buildQuery` do app nunca mandava `limit`/`offset`. **O diagnóstico foi oposto ao sintoma
  relatado** ("está lento/pesado") — desconfiar antes de otimizar.
- **CSP com sintoma mudo**: `script-src 'self'` bloqueia `onclick=` sem levantar exceção
  nenhuma; o handler só não roda. Ficou 2 dias em prod porque a validação carregou a página
  sem abrir nenhum modal. **Validar CSP exige exercitar a UI interativa.**
- **Portal instanciando `main.js` duas vezes** — ver [[patterns.md]].
- **Import CSV do Excel falhando em silêncio** (BOM + `;`) — ver [[patterns.md]].
