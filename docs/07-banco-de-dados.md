---
titulo: Manual do Banco de Dados
subtitulo: Modelo de dados, migrations e operação do PostgreSQL
versao: "1.0"
data: 2026-08-18
---

## Introdução

### Para quem é este manual

Este manual é para quem precisa entender, consultar ou alterar o banco de dados do SCPI. Ele descreve o modelo de dados tabela a tabela, como o schema é criado e evoluído, quais índices existem e por quê, e as armadilhas que já custaram incidente em produção.

O objetivo é que a leitura, sem nenhuma conversa com o desenvolvedor anterior, seja suficiente para ler uma consulta do sistema, escrever uma nova, diagnosticar uma migration que quebrou o boot e saber o que **não** fazer com uma conexão aberta no banco de produção.

### Como ler

Os capítulos de modelo de dados e de migrations são os que valem uma leitura contínua na primeira vez: o resto do manual pressupõe que você sabe o que é uma chamada, o que é uma presença e quem cria as tabelas.

Depois disso, os capítulos de armadilhas, verificação, problemas conhecidos e referência rápida são os que você reabre no dia a dia.

### De onde cada comando roda

Esta é a convenção mais importante do manual, e vale para todos os capítulos:

- **Cada bloco declara de onde parte, na frase imediatamente antes dele.** Blocos de shell partem quase sempre da raiz do repositório, a pasta `SCPI/` criada pelo clone, ou de `BackEnd/` quando a frase disser isso.
- Um bloco que começa com `cd` usa caminho **relativo à raiz**. Rodar `cd BackEnd` duas vezes seguidas falha, porque a segunda procuraria `BackEnd/BackEnd`.
- **Todo bloco de SQL deste manual é para colar em um cliente de banco**, o DBeaver, com a conexão escolhida por você. Nenhum deles é executado por script, por teste ou por ferramenta automatizada. Antes de rodar qualquer um, confira em qual conexão o DBeaver está: a mesma consulta que é inofensiva no banco local pode ser destrutiva no de produção.

> **Atenção:** o `.env` da máquina de desenvolvimento aponta o `DB_HOST` para o banco de **produção**. Qualquer comando que abra conexão a partir do repositório, inclusive os testes com o gate de banco ligado, vai para produção por padrão. Confira o destino antes, sempre.

Quatro rótulos aparecem ao longo do texto:

- **Importante** — informação que muda o resultado do passo.
- **Pegadinha** — comportamento que já custou tempo a alguém e não é óbvio pelo código.
- **Atenção** — risco de estrago real, inclusive em produção.
- **Quando usar** — critério para escolher entre dois caminhos.

### O que não está aqui

- **Backup, restore e a rotina de cópia diária** estão no Manual de Operações (`docs/SCPI-Manual-Operacoes.docx`), que cobre o timer da VM, o bucket na nuvem, a retenção e o restore já testado. Este manual não repete esse procedimento; o capítulo de backup e restore só diz onde ele mora e o que você precisa saber antes de abrir aquele documento.
- **Montar o banco local, criar o `.env` e subir a API pela primeira vez** estão no Manual de Ambiente de Desenvolvimento.
- **As credenciais de produção**, o cofre cifrado e a rotação de chaves estão no Manual de Contas e Segredos. Aqui você aprende **onde** a credencial do banco mora, nunca o valor dela.

> **Atenção:** nenhum valor de segredo aparece neste manual, por decisão de projeto.

## Visão geral do banco

### O que é e onde roda

O SCPI usa **PostgreSQL**. Em produção, o banco fica na **própria VM da API**, acessível em `127.0.0.1`, desde 2026-06-15. A versão de referência de produção é a 16, e o serviço do CI que roda os testes de integração é a imagem `postgres:16`.

A API é o **único** componente que fala com o banco. Portal, aplicativo mobile e script da câmera só conversam por HTTP com a API.

### Sem ORM

Não há ORM no projeto. Todo o SQL é escrito à mão, dentro de `BackEnd/repositories/`, e é **sempre parametrizado** — a auditoria de segurança confirmou ausência de SQL injection, e essa é uma propriedade a manter, não a reavaliar.

A divisão de camadas é rígida:

| Camada | Pasta | Responsabilidade |
|---|---|---|
| Repositórios | `BackEnd/repositories/` | Único lugar onde existe SQL de aplicação |
| Serviços | `BackEnd/services/` | Regra de negócio, sem SQL |
| Regras puras | `BackEnd/core/` | Funções sem acesso a rede ou banco, testáveis de mesa |
| Infraestrutura | `BackEnd/infra/` | Conexão, pool e migrations |

### Conexão e pool

`BackEnd/infra/database.py` monta a URL de conexão a partir de cinco variáveis obrigatórias e falha imediatamente se qualquer uma faltar.

| Variável | Papel | Default |
|---|---|---|
| `DB_HOST` | Endereço do servidor | Sem default, obrigatória |
| `DB_PORT` | Porta | Sem default, obrigatória |
| `DB_NAME` | Nome do banco | Sem default, obrigatória |
| `DB_USER` | Usuário | Sem default, obrigatória |
| `DB_PASSWORD` | Senha | Sem default, obrigatória |
| `DB_POOL_MIN` | Conexões mínimas do pool | 1 |
| `DB_POOL_MAX` | Conexões máximas do pool | 10 |
| `DB_CONNECT_TIMEOUT` | Segundos para abrir conexão | 3 |

O acesso passa por um `ThreadedConnectionPool` do psycopg2, criado de forma preguiçosa e protegido por lock de thread. Toda conexão do pool nasce com o fuso da sessão fixado em `America/Sao_Paulo`, e conexões obtidas do pool devem ser devolvidas com `release_connection`, nunca fechadas com `close`.

Existe um caminho alternativo: se o `psycopg2` não estiver instalado, o módulo importa `pg8000` e embrulha o cursor para devolver dicionários. Ele existe para não travar ambiente sem binário compilado, e não é o caminho de produção.

### O contrato do cursor

Quase todo repositório usa o gerenciador de contexto `get_db_cursor`, que abre a conexão, entrega um cursor que devolve dicionários, faz commit quando pedido, desfaz a transação em caso de exceção e devolve a conexão ao pool no final.

```python
with get_db_cursor(commit=True) as cur:
    cur.execute("UPDATE Turmas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
```

> **Pegadinha:** quando o pool não consegue dar conexão, `get_db_cursor` **devolve `None` em vez de levantar exceção**. O padrão `if not cur: return None` está espalhado por dezenas de repositórios, e ele achata "banco fora do ar" em cima de "consultei e não achei nada", que têm resposta HTTP bem diferente: 503 contra 404 ou 403.

Para os casos em que essa diferença importa existe a sentinela `DB_INDISPONIVEL`, também em `infra/database.py`. Ela foi aplicada aos dois caminhos da câmera e às rotinas de token de câmera, e não a todos os repositórios: um sweep cego tocaria código demais. O critério para adotá-la em um repositório novo é uma pergunta só — o chamador toma decisão diferente se for banco fora do ar?

> **Importante:** por que isso importa tanto na câmera: o script classifica a resposta como definitiva quando o status é menor que 500 e **não repete a tentativa**. Um blip de banco traduzido em 403 vira falta silenciosa do aluno, sem nova chance no mesmo burst.

## Modelo de dados

### Como as tabelas se encaixam

O núcleo é acadêmico. Uma pessoa é uma linha em `Usuarios`; se for aluno, ganha uma linha em `Alunos`, se for professor, uma em `Professores`. Turma é a disciplina ofertada, matrícula é a ligação entre aluno e turma, chamada é uma sessão de aula concreta e presença é o registro de um aluno em uma aula dentro daquela chamada.

```text
Usuarios --1:1-- Alunos --N:M (Turma_Alunos)-- Turmas --1:N-- Horarios_Aulas
    |               |                            |
    +--1:1-- Professores ------------------------+
                    |                            |
                    +--------- Chamadas ---------+
                                   |
                               Presencas
                                   |
Alunos --1:N-- Colecao_Rostos      |
    +--1:N-- ConsentimentosLGPD ---+
```

O conjunto completo, depois de todas as migrations, são dezessete tabelas. O dump `schema_inicial.sql` traz doze delas; as cinco restantes nascem só pelas migrations, e são `ConsentimentosLGPD`, `PushReceiptsPendentes`, `camera_tokens`, `login_attempts` e `rate_limit_buckets`.

### Tabelas do núcleo acadêmico

| Tabela | Chave primária | Papel |
|---|---|---|
| `Usuarios` | `usuario_id` uuid | Identidade e credencial de qualquer pessoa do sistema |
| `Professores` | `professor_id` uuid | Perfil de professor, um por usuário |
| `Alunos` | `aluno_id` uuid | Perfil de aluno, um por usuário |
| `Turmas` | `turma_id` uuid | Disciplina ofertada, com código único |
| `Turma_Alunos` | `turma_aluno_id` serial | Matrícula do aluno na turma |
| `Horarios_Aulas` | `horario_id` uuid | Grade semanal da turma, com sala |
| `Chamadas` | `chamada_id` serial | Uma sessão de aula, aberta e depois fechada |
| `Presencas` | `presenca_id` serial | Um aluno presente em uma aula da chamada |

#### Usuarios

Guarda `nome`, `email` único, `senha` já hasheada, `tipo_usuario`, `data_cadastro` e `primeiro_acesso`.

O `tipo_usuario` é `varchar(50)` **sem CHECK**: os três valores gravados pelo código são `Admin`, `Professor` e `Aluno`, escritos literalmente nos inserts de `repositories/alunos.py`, `repositories/professores.py` e `scripts/criar_admin.py`. Nada no banco impede um quarto valor entrar por SQL manual, e nenhuma rota reconheceria esse perfil.

O `primeiro_acesso` nasce verdadeiro para aluno e professor criados pelo administrador, e é o que dispara a tela de troca de senha no aplicativo.

> **Pegadinha:** `atualizar_senha_por_usuario_id` também zera `primeiro_acesso`. Por isso o re-hash automático da senha no login usa `atualizar_hash_senha`, que só toca a coluna `senha`. Não unifique as duas funções.

#### Professores e Alunos

Ambas têm `usuario_id` **único** com chave estrangeira para `Usuarios` e `ON DELETE CASCADE`: apagar o usuário apaga o perfil.

`Alunos` acrescenta `ra`, que é único no banco inteiro, e `turno`, restrito por CHECK a `Matutino` ou `Noturno`. O RA é o identificador que aparece nos relatórios em PDF; o CPF não circula em documento que sai do sistema, por decisão registrada em `core/mascaras.py`.

`Professores` acrescenta apenas `data_admissao`. Havia uma coluna `departamento`, removida pela migration `ensure_professor_departamento_dropped` por ser cosmética e não alimentar nenhuma regra.

#### Turmas e Turma_Alunos

`Turmas` tem `codigo_turma` único, `nome_disciplina`, `periodo_letivo`, `sala_padrao`, `turno`, `semestre` e o `professor_id` responsável.

`Turma_Alunos` é a matrícula, com unicidade em `(turma_id, aluno_id)` e a coluna `data_associacao`.

> **Importante:** `data_associacao` não é decorativa. É a data que o cálculo de frequência usa como início da janela do aluno: só chamadas a partir dela contam no denominador. Reimportar o CSV de uma turma é seguro justamente porque o insert usa `ON CONFLICT DO NOTHING` e preserva a data original.

#### Horarios_Aulas

Grade semanal da turma: `dia_semana`, `horario_inicio`, `horario_fim` e `sala`. É por esta tabela que a câmera descobre com qual chamada sincronizar — a consulta casa `sala` com `dia_semana`, porque a mesma sala tem várias turmas no mesmo dia.

A chave estrangeira de `turma_id` aqui é a única do schema **sem** `ON DELETE CASCADE`: apagar uma turma com horários cadastrados falha por violação de chave estrangeira, em vez de levar os horários junto.

#### Chamadas

Uma linha por sessão de aula: `turma_id`, `professor_id`, `data_chamada`, `horario_inicio`, `horario_fim`, `status`, `data_criacao` e `total_aulas`.

O `status` é `varchar(50)` com default `Aberta`, e o valor terminal usado pelo sistema é `Fechada`. A transição é de mão única: encerrar é commit, não há endpoint de reabertura, e a navegação do aplicativo é dirigida por esse estado.

Existe um **índice único parcial** garantindo no máximo uma chamada `Aberta` por turma. Ele é defesa contra corrida entre dois pedidos simultâneos de abertura, e é também o motivo pelo qual uma chamada esquecida aberta bloqueia a próxima da mesma turma.

#### Presencas

Esta é a tabela que mais gera confusão, e a razão está na seção seguinte.

| Coluna | Tipo | Papel |
|---|---|---|
| `presenca_id` | serial | Chave primária |
| `chamada_id` | integer | Chave estrangeira para a chamada, com cascade |
| `aluno_id` | uuid | Chave estrangeira para o aluno, com cascade |
| `hora_registro` | timestamptz | Momento do registro |
| `tipo_registro` | varchar(50) | `Reconhecimento` ou `Manual` |
| `num_aula` | smallint | Qual aula da chamada, começando em 1 |

A restrição de unicidade é `(chamada_id, aluno_id, num_aula)`.

### Presença é por aula, não por chamada

Uma chamada representa um encontro que pode valer **várias aulas** — é o caso comum de aulas geminadas. Por isso `chamadas.total_aulas` diz quantas aulas aquele encontro vale, e `presencas.num_aula` diz de qual delas é aquele registro. Ambas são `smallint NOT NULL DEFAULT 1`, de modo que dados anteriores à mudança viraram automaticamente "uma aula, aula número 1".

A restrição antiga era `(chamada_id, aluno_id)` — um aluno, uma presença por chamada. A migration derruba essa restrição pelo nome antigo e cria a de três colunas.

> **Importante:** qualquer contagem de frequência tem que somar linhas de `Presencas`, não chamadas distintas. Contar chamadas subestima a presença de quem esteve nas duas aulas de um encontro geminado, e é exatamente o tipo de erro que passa despercebido porque o número continua plausível.

O ajuste manual do professor faz merge por `num_aula`: aulas que já tinham presença mantêm o `tipo_registro` original, tipicamente `Reconhecimento`; aulas novas marcadas na tela entram como `Manual`; aulas desmarcadas são apagadas.

> **Pegadinha:** o `README.md` credita a presença por aula ao arquivo `BackEnd/migrations/001_presenca_por_aula.sql`. Esse arquivo existe, mas **nada no repositório o executa** — nem a API, nem o CI, nem um script de deploy. O que roda de verdade é a etapa `ensure_presenca_por_aula` de `BackEnd/infra/migrations.py`, cujo SQL é equivalente. O arquivo avulso é um resquício histórico.

### Por que professor_id é nullable

`turmas.professor_id` e `chamadas.professor_id` aceitam nulo **de propósito**. A regra do projeto é: excluir um professor **orfana** as turmas e as chamadas dele, e **preserva** toda a presença já registrada.

O motivo é direto. A presença é o histórico de frequência do aluno, e o aluno não tem nada a ver com a saída do professor. Cascatear a exclusão pela cadeia professor, turma, chamada e presença apagaria frequência de gente que continua matriculada, para resolver um problema administrativo de outra pessoa.

A migration `ensure_chamada_professor_nullable` existe só para isso: `chamadas.professor_id` nascia `NOT NULL`, e sem essa alteração excluir um professor com chamadas dava violação de not-null. A coluna de `turmas` já era nullable.

O caminho correto de exclusão está em `repositories/professores.py`, na função `excluir_professor_em_cascata`, e faz quatro passos nesta ordem:

1. `UPDATE Turmas SET professor_id = NULL` para o professor.
2. `UPDATE Chamadas SET professor_id = NULL` para o professor.
3. `DELETE FROM Professores`.
4. `DELETE FROM Usuarios`.

> **Atenção:** as duas chaves estrangeiras estão declaradas no banco como `ON DELETE CASCADE`, não como `ON DELETE SET NULL`. O orfanamento é garantido **só pelo código da aplicação**, pelos dois updates acima. Um `DELETE FROM professores` digitado à mão no DBeaver não passa por eles: o banco cascateia para `turmas`, de lá para `chamadas`, de lá para `presencas`, e apaga o histórico de frequência em silêncio, sem erro nenhum. Excluir professor é operação de aplicação, nunca de cliente SQL.

A exclusão de **aluno** é deliberadamente diferente e destrutiva, porque atende a pedido de eliminação de dado pessoal: `excluir_aluno_em_cascata` apaga rostos, matrículas, presenças, o perfil e o usuário.

### Biometria e LGPD

| Tabela | Papel |
|---|---|
| `Colecao_Rostos` | Vínculo entre o aluno e cada face indexada no serviço de reconhecimento |
| `ConsentimentosLGPD` | Trilha append-only de aceite e revogação de consentimento |

`Colecao_Rostos` guarda `external_image_id`, `face_id_rekognition`, `s3_path_cadastro`, `data_indexacao`, `angulo`, e as três colunas de consentimento: `consentimento_biometrico`, `consentimento_data` e `revogado_em`.

A restrição de unicidade é `(aluno_id, angulo)`. Ela substituiu uma unicidade antiga sobre `external_image_id`, que impedia o cadastro multi-ângulo. Os ângulos válidos são fixados em `core/regras.py`, no conjunto `ANGULOS_VALIDOS`, com quatro valores: frontal, esquerda, direita e baixo. O default da coluna é frontal.

O cadastro de um rosto é um upsert sobre aluno e ângulo que, ao atualizar, também marca o consentimento como verdadeiro, carimba a data e **limpa** `revogado_em`. Revogar não apaga a linha: preenche `revogado_em`, e a auditoria de biometria conta esse registro como revogado, não como ausente.

`ConsentimentosLGPD` é **append-only**: nunca sofre update nem delete, e revogar consentimento é inserir um evento novo. As colunas são `evento`, `politica_versao`, `registrado_em`, `ip`, `user_agent` e `origem`. A versão da política vive em `core/config.py`, não em variável de ambiente.

A migration que cria a tabela também faz **backfill**: quem já tinha biometria ativa recebe um evento de aceite com `politica_versao` igual a `legado` e `origem` igual a `backfill`. O rótulo é honesto de propósito — não se inventa prova de um aceite versionado que nunca houve.

> **Atenção:** a chave estrangeira de `ConsentimentosLGPD.aluno_id` **não declara `ON DELETE`**, e nenhum código do projeto apaga linhas dessa tabela. Como `excluir_aluno_em_cascata` não a toca, excluir um aluno que tenha qualquer registro de consentimento viola a chave estrangeira e a transação inteira volta atrás: a exclusão fica **bloqueada**. O erro é tratado, não é um 500 — `internal_error` reconhece a violação e devolve **400** com `error_code` `FOREIGN_KEY_VIOLATION`. O problema prático é a mensagem que chega ao administrador: ela diz apenas que uma referência é inválida e **não menciona consentimento**, então quem recebe o erro não tem pista do que fazer. Ver o capítulo de problemas conhecidos.

### Autenticação e sessão

| Tabela | Papel | Limpeza |
|---|---|---|
| `RefreshTokens` | Refresh tokens ativos, indexados pelo hash | Purga diária do agendador |
| `PasswordResetCodes` | Códigos de recuperação de senha | Nenhuma purga automática |
| `login_attempts` | Contador e bloqueio de login por conta | Purga diária do agendador |
| `camera_tokens` | Token de serviço da câmera, um por sala | Revogação manual por linha de comando |

`RefreshTokens` tem o **hash** do token como chave primária, nunca o token em claro, e guarda `usuario_id`, `expires_at`, `created_at` e `revoked_at`.

`PasswordResetCodes` guarda o **HMAC** do código de seis dígitos, não o código. A coluna `code` nasceu `varchar(6)` e foi alargada para `varchar(64)` pela própria migration quando o armazenamento virou HMAC. Há ainda `tentativas`, contador de erro que dispara o bloqueio da conta, e `token_consumido_em`, que tornou de uso único o JWT gerado a partir do código — antes o código era de uso único mas o token que ele emitia valia por quinze minutos e servia para quantas trocas de senha o portador quisesse.

> **Pegadinha:** a limpeza diária do agendador purga `RefreshTokens`, `rate_limit_buckets` e `login_attempts`. **`PasswordResetCodes` não é purgada por nada.** Pedir um código novo apenas marca os anteriores como usados; as linhas ficam. A tabela cresce indefinidamente, devagar, e ninguém percebe até alguém olhar o tamanho dela.

`camera_tokens` guarda `sala`, `token_hash` único, `descricao`, `criado_em`, `ultimo_uso_em` e `revogado_em`. Ela substituiu um token global de variável de ambiente: com a sala no banco, um token vazado só serve para a sala dele, e a revogação é individual.

> **Atenção:** a sala vem do token, nunca do cliente. Um token emitido para a sala errada marca presença na aula errada em silêncio, sem erro nenhum. Confira a sala no momento da emissão.

### Infraestrutura

| Tabela | Papel |
|---|---|
| `PushTokens` | Token de push do aplicativo, um por usuário |
| `PushReceiptsPendentes` | Tickets de envio aguardando confirmação de entrega |
| `rate_limit_buckets` | Contadores do rate limit, compartilhados entre workers |

`rate_limit_buckets` existe porque a API roda com quatro workers em produção. Um limitador em memória contaria separado em cada worker, e o limite efetivo seria quatro vezes o configurado. A tabela é `key`, `count` e `expires_at`, e o storage vive em `core/limiter_storage.py`.

`PushReceiptsPendentes` é consumida por um job separado, versionado em `ops/receipts/`, que confere os recibos e apaga os tickets já resolvidos.

## Migrations

### Onde ficam e o que são

As migrations vivem em **`BackEnd/infra/migrations.py`**, escritas em **Python**, não em arquivos SQL avulsos. Cada uma é uma função `ensure_*` idempotente que abre um cursor com commit e executa o DDL.

São **vinte e uma etapas**, listadas em ordem na constante `_ETAPAS` do próprio módulo, e a primeira é `ensure_base_schema`.

| Etapa | O que faz |
|---|---|
| `ensure_base_schema` | Cria as nove tabelas do núcleo acadêmico e de biometria |
| `ensure_professor_departamento_dropped` | Remove a coluna cosmética de departamento |
| `ensure_chamada_professor_nullable` | Torna `chamadas.professor_id` nullable |
| `ensure_refresh_tokens_table` | Cria `RefreshTokens` e o índice por usuário |
| `ensure_lgpd_columns` | Acrescenta consentimento e revogação em `Colecao_Rostos` |
| `ensure_multi_angle_faces` | Coluna de ângulo e unicidade por aluno mais ângulo |
| `ensure_push_tokens_table` | Cria `PushTokens` |
| `ensure_push_receipts_table` | Cria `PushReceiptsPendentes` |
| `ensure_primeiro_acesso_column` | Acrescenta `primeiro_acesso` em `Usuarios` |
| `ensure_reset_codes_table` | Cria `PasswordResetCodes`, alarga `code` e adiciona `tentativas` |
| `ensure_reset_token_consumo` | Acrescenta `token_consumido_em` |
| `ensure_timestamptz_tokens` | Converte as datas das duas tabelas de token |
| `ensure_rate_limit_table` | Cria `rate_limit_buckets` e o índice de expiração |
| `ensure_login_attempts_table` | Cria `login_attempts` |
| `ensure_camera_tokens_table` | Cria `camera_tokens` |
| `ensure_presenca_por_aula` | Acrescenta `total_aulas` e `num_aula` e troca a unicidade |
| `ensure_chamada_aberta_unica` | Cria o índice único parcial de chamada aberta |
| `ensure_indices_filtros_alunos` | Dois índices para os filtros da aba Alunos |
| `ensure_indices_performance` | Os seis índices do caminho quente e dos relatórios |
| `ensure_consentimentos_table` | Cria a trilha de consentimento e faz o backfill |
| `ensure_timestamptz_restante` | Converte as demais colunas de data do schema |

### Quando rodam

A função `run_all` é chamada no ciclo de vida da aplicação, ou seja, **no startup da API**. Não existe comando manual de migration no fluxo normal: subir a API é aplicar o schema.

Isso vale inclusive para banco vazio. A primeira etapa cria as tabelas base com `CREATE TABLE IF NOT EXISTS`, então um banco recém-criado se auto-monta na primeira subida.

| Característica | Comportamento | Motivo |
|---|---|---|
| Idempotência | Rodar de novo não quebra nem duplica | Os quatro workers do gunicorn sobem juntos em produção |
| Advisory lock | A execução é serializada no próprio Postgres | Sem ele, workers concorrentes colidiam no `CREATE TABLE` |
| Fail-loud | Qualquer falha aborta o boot com `RuntimeError` | Schema incompleto com a API no ar gera erros 500 aleatórios longe da causa |

O advisory lock usa uma chave numérica fixa e arbitrária, declarada no topo do módulo. Antes dele, os quatro workers competiam e o erro típico era `duplicate key pg_type_typname_nsp_index`.

### Fail-loud e o restart loop

Esta é a característica que mais assusta quem pega o sistema pela primeira vez, e ela é **intencional**.

Se qualquer etapa falhar, ou se o banco simplesmente não responder, a aplicação levanta `RuntimeError` e a API **não sobe**. Sob systemd, o serviço não sobe, é reiniciado, falha de novo, e entra em **restart loop**.

A alternativa — registrar o erro no log e subir mesmo assim — é pior: o schema fica pela metade, a API atende, e os erros 500 aparecem horas depois, em rotas que não têm relação óbvia com a coluna que faltou. O sintoma chega longe da causa. Preferimos não subir.

A mensagem da exceção carrega o **nome da etapa**, de propósito:

```text
Migration ensure_push_tokens_table falhou: <erro do psycopg2>
```

#### Diagnosticar o restart loop

Com acesso à VM de produção — o caminho de acesso será documentado no Manual da VM de Produção:

```bash
sudo journalctl -u scpi-api -n 100 --no-pager | grep -i "migration\|RuntimeError"
```

A leitura da saída tem três casos, e cada um leva a um lugar diferente:

| O que aparece | Significa | Onde agir |
|---|---|---|
| `Migrations: sem conexão com o banco` | O banco não respondeu; nenhuma etapa chegou a rodar | Serviço do PostgreSQL, rede, ou o bloco de variáveis de banco do `.env` |
| `Migration <etapa> falhou` | Uma etapa específica quebrou | A função `ensure_*` daquele nome, em `BackEnd/infra/migrations.py` |
| Nenhuma das duas, mas o serviço reinicia | O boot morreu antes das migrations | Variável obrigatória ausente; ver o Manual de Ambiente de Desenvolvimento |

> **Importante:** se a API não sobe e o erro cita uma etapa `ensure_alguma_coisa`, o problema é migration, não código de aplicação. Ler o nome da etapa é o primeiro passo; abrir a função daquele nome é o segundo.

Com a causa identificada, a saída depende do caso. Banco fora do ar é problema de infraestrutura e o serviço volta sozinho quando o banco voltar, porque o systemd continua tentando. Etapa quebrada exige corrigir a função — e como as etapas são idempotentes, basta reiniciar o serviço depois do ajuste.

> **Atenção:** a tentação de "só comentar a etapa que falha para o serviço subir" é exatamente o cenário que o fail-loud existe para impedir. Uma etapa comentada deixa o schema incompleto e devolve o problema em forma de erro 500 aleatório, semanas depois.

### Escrever uma migration nova

Quatro regras, todas com teste automatizado cobrando:

- A função tem que ser **idempotente**. Use `IF NOT EXISTS` no `CREATE`, `ADD COLUMN IF NOT EXISTS` e `DROP CONSTRAINT IF EXISTS`. Para adicionar restrição, que não aceita `IF NOT EXISTS`, o projeto usa um bloco anônimo consultando `pg_constraint` — há dois exemplos prontos no arquivo.
- O nome tem que entrar em `_ETAPAS`, **na posição certa**. Há teste comparando o conjunto de funções `ensure_*` definidas com o conteúdo da lista, e outro exigindo que `ensure_base_schema` continue em primeiro lugar.
- A lista guarda **nomes em texto**, não referências à função. Isso não é estilo: os testes de pipeline substituem etapas por dublês, e uma lista de referências capturaria as funções originais no import, fazendo a substituição virar um efeito nulo e silencioso.
- Coluna de data nova nasce **`TIMESTAMPTZ`**. Ver o capítulo de armadilhas.

> **Pegadinha:** `ALTER COLUMN ... TYPE` reescreve a tabela inteira sob bloqueio exclusivo. As duas migrations de conversão de fuso consultam `information_schema.columns` antes e pulam a coluna se ela já estiver convertida. Essa guarda não é cosmética: sem ela, **todo boot da API** travaria as tabelas de autenticação enquanto reescrevia.

### O papel do schema_inicial.sql

O arquivo `schema_inicial.sql`, na raiz do repositório, é um **dump** das tabelas base. Aplicá-lo é opcional, e nenhum código do projeto o executa.

> **Quando usar:** aplique o dump apenas se quiser inspecionar o schema num cliente antes de subir a API, ou reproduzir um estado específico. Para o fluxo normal, crie o banco vazio e deixe a API montar tudo.

> **Atenção:** o dump está **atrasado** em relação ao schema real. Ele traz doze das dezessete tabelas, faltando `ConsentimentosLGPD`, `PushReceiptsPendentes`, `camera_tokens`, `login_attempts` e `rate_limit_buckets`, não contém dez dos índices atuais, mostra a coluna de código de recuperação ainda como `varchar(6)` sem `tentativas` nem `token_consumido_em`, e todas as colunas de data aparecem como `timestamp` sem fuso, antes das duas migrations de conversão. Um banco montado só a partir dele e nunca visitado pela API está incompleto. Trate o dump como registro histórico, não como especificação.

## Acesso ao banco

### A ferramenta é o DBeaver

O cliente de banco usado no projeto é o **DBeaver**. É nele que se inspeciona schema, se roda consulta de diagnóstico e se executa o SQL de verificação entregue por quem estava desenvolvendo.

As credenciais de conexão são as mesmas variáveis de banco que a API usa. Em produção elas vivem em `/opt/scpi/.env`; na máquina de desenvolvimento, no `.env` da raiz do repositório. O manual não traz nenhum valor: veja o Manual de Contas e Segredos para saber como recuperá-los.

> **Atenção:** o `.env` da máquina de desenvolvimento aponta para o banco de **produção**. Uma conexão do DBeaver montada copiando o que está nesse arquivo é, por padrão, uma conexão de produção. Nomeie as conexões de forma inconfundível e confira qual está selecionada antes de qualquer comando que escreva.

### Não se sobe Docker

O projeto **não** usa Docker para banco local, nem para teste. Não sugira subir contêiner como caminho: não existe arquivo para isso e a decisão é deliberada.

### Como se valida SQL contra banco real

A suíte de testes dos repositórios usa **cursor simulado**. Isso significa que ela verifica qual SQL foi montada e com quais parâmetros, mas **nunca executa** a consulta. Erro de sintaxe, coluna inexistente e tipo incompatível passam verdes.

Verificação contra banco real tem três caminhos, nesta ordem de preferência:

1. **Teste de integração no CI.** Rodam apenas com o gate `SCPI_RUN_DB_TESTS` ligado, e o CI o liga contra um serviço `postgres:16` descartável, com banco, usuário e senha próprios. É o único lugar onde as migrations rodam de ponta a ponta contra Postgres de verdade.
2. **SQL avulso entregue para rodar à mão** no DBeaver, com os olhos de quem tem a conexão aberta e sabe em qual banco está.
3. **Pular a validação**, quando os dois primeiros não se aplicam.

> **Atenção:** nunca ligue o gate `SCPI_RUN_DB_TESTS` na máquina local. O `.env` de desenvolvimento aponta o `DB_HOST` para produção, e as fixtures de integração executam `TRUNCATE` nas tabelas. Ligar o gate localmente apaga dados de produção.

As fixtures que fazem esse `TRUNCATE` são `pg` e `pg_academico`, em `BackEnd/tests/conftest.py`. Sem o gate, elas pulam o teste sem sequer tentar conectar — é por isso que a suíte local termina com dezenas de testes pulados, e isso é o resultado esperado, não uma falha.

## Índices e desempenho

### Os índices que existem

Além das chaves primárias e das restrições de unicidade, que o Postgres indexa sozinho, as migrations criam os índices abaixo.

| Índice | Tabela e colunas | Criado por | Para quê |
|---|---|---|---|
| `idx_refresh_usuario` | `RefreshTokens (usuario_id)` | `ensure_refresh_tokens_table` | Revogar todas as sessões de um usuário |
| `idx_consent_aluno` | `ConsentimentosLGPD (aluno_id, registrado_em DESC)` | `ensure_consentimentos_table` | Último evento de consentimento do aluno |
| `ix_rate_limit_buckets_expires` | `rate_limit_buckets (expires_at)` | `ensure_rate_limit_table` | Purga diária dos contadores vencidos |
| `uq_chamada_aberta_por_turma` | `Chamadas (turma_id)`, parcial | `ensure_chamada_aberta_unica` | Impedir duas chamadas abertas na mesma turma |
| `idx_turma_alunos_aluno` | `Turma_Alunos (aluno_id)` | `ensure_indices_filtros_alunos` | Escopo e contagem de turmas na aba Alunos |
| `idx_turmas_semestre` | `Turmas (semestre)` | `ensure_indices_filtros_alunos` | Recorte por semestre na aba Alunos |
| `idx_horarios_sala_dia` | `Horarios_Aulas (sala, dia_semana)` | `ensure_indices_performance` | Caminho quente da câmera |
| `idx_horarios_turma` | `Horarios_Aulas (turma_id)` | `ensure_indices_performance` | Junção de grade por turma |
| `idx_presencas_aluno` | `Presencas (aluno_id)` | `ensure_indices_performance` | Histórico de frequência do aluno |
| `idx_chamadas_turma_status` | `Chamadas (turma_id, status)` | `ensure_indices_performance` | Chamada aberta de uma turma |
| `idx_chamadas_professor` | `Chamadas (professor_id)` | `ensure_indices_performance` | Relatórios por professor |
| `idx_chamadas_data` | `Chamadas (data_chamada)` | `ensure_indices_performance` | Relatórios por período |

Os seis últimos são os do lote conhecido internamente como P3, e o índice de sala com dia da semana é o que mais importa: a consulta que resolve com qual chamada a câmera deve sincronizar roda **a cada burst**, de poucos em poucos segundos, por sala, durante a aula inteira. Sem índice, cada rosto reconhecido custava uma varredura completa de `Horarios_Aulas`.

> **Importante:** `idx_presencas_aluno` não é redundante com a unicidade de chamada, aluno e número da aula. Um índice composto só serve consulta que começa pela primeira coluna, e o histórico do aluno começa por `aluno_id`, não por `chamada_id`.

### Conferir se estão sendo usados

O repositório traz a consulta pronta em **`ops/sql/verificar_indices_p3.sql`**. Ela é para colar no DBeaver, conectado ao banco cujo desempenho você quer avaliar.

> **Quando usar:** rode a verificação **depois de uma aula real**, não logo após o deploy. O contador `idx_scan` é acumulado desde o último reset das estatísticas, e um índice recém-criado começa em zero mesmo estando perfeito.

A primeira consulta do arquivo mede o uso de cada um dos seis índices:

```sql
SELECT s.relname                                   AS tabela,
       s.indexrelname                              AS indice,
       s.idx_scan                                  AS varreduras,
       s.idx_tup_read                              AS tuplas_lidas,
       s.idx_tup_fetch                             AS tuplas_buscadas,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS tamanho
  FROM pg_stat_user_indexes s
 WHERE s.indexrelname IN (
           'idx_horarios_sala_dia',
           'idx_horarios_turma',
           'idx_presencas_aluno',
           'idx_chamadas_turma_status',
           'idx_chamadas_professor',
           'idx_chamadas_data'
       )
 ORDER BY s.idx_scan DESC, s.indexrelname;
```

A segunda dá o contexto, comparando varredura sequencial com varredura por índice em cada tabela quente:

```sql
SELECT relname     AS tabela,
       seq_scan    AS varreduras_sequenciais,
       seq_tup_read,
       idx_scan    AS varreduras_por_indice,
       n_live_tup  AS linhas_vivas
  FROM pg_stat_user_tables
 WHERE lower(relname) IN ('horarios_aulas', 'presencas', 'chamadas', 'turma_alunos')
 ORDER BY relname;
```

A terceira diz desde quando os contadores acumulam, o que muda a leitura das duas anteriores:

```sql
SELECT stats_reset FROM pg_stat_database WHERE datname = current_database();
```

Como interpretar o resultado:

- `idx_scan` maior que zero depois de uma aula real: o índice está sendo usado, fim.
- `idx_scan` igual a zero depois de uma aula real: ou a consulta não casa com o índice, ou a tabela é pequena demais e o planejador prefere varredura sequencial.
- `seq_scan` alto com `n_live_tup` baixo: normal. O planejador ignora índice em tabela pequena, e isso não invalida o índice, só adia o ganho.

### A prova direta, independente do contador

A quarta parte do arquivo pede o plano de execução, que responde sem depender de contador acumulado. O esperado na saída é a linha `Index Scan using idx_horarios_sala_dia`; `Seq Scan` é o sinal ruim.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM horarios_aulas WHERE sala = 'Sala 101' AND dia_semana = 1;
```

> **Pegadinha:** os literais desse bloco são exemplos. Troque a sala e o dia por valores que **existam** no banco em que você está — o plano de uma consulta que não casa com linha nenhuma não prova nada.

O arquivo traz um segundo bloco de `EXPLAIN`, sobre `Chamadas`, escrito com `turma_id = 1`. **Esse literal está errado** e a consulta falha: `chamadas.turma_id` é `uuid`, e comparar com inteiro dá `operator does not exist: uuid = integer`. Use um identificador real de turma, com cast:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM Chamadas
 WHERE turma_id = '00000000-0000-0000-0000-000000000000'::uuid
   AND status = 'Aberta';
```

## Backup e restore

Backup e restore **não** são cobertos aqui. O procedimento completo — a cópia diária do PostgreSQL na VM, o timer que a dispara, o bucket na nuvem com retenção de trinta dias, o alerta de monitoramento quando a cópia falha e o restore já testado ponta a ponta — está no **Manual de Operações** (`docs/SCPI-Manual-Operacoes.docx`), que é o documento a abrir quando for preciso restaurar.

Três coisas valem saber antes de ir para lá:

- O backup do **banco** e o backup dos **segredos** são rotinas distintas, com timers e destinos diferentes. Restaurar o banco não devolve o `.env`.
- O restore foi testado, o que significa que existe um procedimento conhecido e não uma esperança. Siga o documento, não improvise a partir de um dump qualquer.
- Nada deste manual deve ser executado contra produção sem que exista uma cópia recente e verificada.

> **Atenção:** o schema é reconstruído sozinho pelas migrations em banco vazio, mas os **dados** não. As migrations montam tabelas e índices; presença registrada, matrícula e biometria só voltam pelo restore.

## Armadilhas do SQL neste projeto

### O sinal de porcentagem literal

Esta é a armadilha que mais dói, porque o teste não pega e o sintoma é em produção.

O psycopg2 varre a **consulta inteira** procurando os marcadores de parâmetro, e a varredura não distingue código de comentário. Um `%` literal em qualquer lugar da string — inclusive dentro de um comentário — faz o `execute` estourar com `IndexError: tuple index out of range` em tempo de execução.

Escrever `100%` num comentário derrubou o PDF de frequência em produção com erro 500, em 2026-07-24.

A regra é: **todo `%` literal em SQL vira `%%`**, ou a frase é reescrita sem ele.

> **Pegadinha:** **o cursor simulado dos testes não pega isso.** Ele aceita qualquer string e não interpreta nada. A mesma cegueira vale para descompasso entre o número de marcadores e o número de parâmetros: o dublê aceita, o Postgres não.

Por isso existe uma **guarda textual** no projeto: o teste `test_repo_sql_nao_tem_percent_literal_nao_escapado`, em `BackEnd/tests/test_frequencia_turma.py`, captura a SQL montada pelo repositório, remove os marcadores e os escapes válidos, e falha se sobrar algum sinal de porcentagem.

```python
resto = sql.replace("%s", "").replace("%%", "")
assert "%" not in resto, "há um % literal não escapado na SQL (use %% ou reescreva)"
```

> **Importante:** guarda textual varre texto e não distingue código de documentação. Um teste que procura um padrão proibido precisa **isentar o arquivo que documenta o padrão** — isso já quebrou o CI três vezes num único dia, em 2026-08-03. A convenção do projeto é manter uma constante de isenções no topo do teste, com o motivo escrito.

### Lista de identificadores em ANY

`ANY(%s)` com uma lista de strings do Python vira um vetor de texto no Postgres, e comparar com coluna `uuid` dá `operator does not exist: uuid = text`.

A forma correta é sempre com cast explícito:

```sql
WHERE aluno_id = ANY(%s::uuid[])
```

> **Pegadinha:** o caso de valor único, com um marcador simples e uma string, **funciona** — o literal chega sem tipo definido e o Postgres o coage para `uuid`. É justamente isso que faz a armadilha parecer inexistente até o dia em que alguém troca a consulta de um identificador para uma lista.

### Coluna de data nasce com fuso

Toda coluna de data nova é **`TIMESTAMPTZ`**. Numa coluna sem fuso, `NOW()` grava a hora de parede da sessão enquanto um valor vindo do Python grava UTC; misturar as duas fontes deixa os valores deslocados entre si pelo offset do fuso do banco, que em produção é `America/Sao_Paulo`.

Isso foi bug real: a purga comparava a data de expiração, gravada em UTC, com a de criação, gravada em hora local, e apagava refresh token três horas fora da hora certa.

As duas migrations de conversão existem por isso, e usam cláusulas **diferentes** de propósito. As colunas de expiração são reinterpretadas como UTC; todas as demais, como o fuso da sessão. Uniformizar as duas parece limpeza e desloca os dados.

> **Importante:** há um teste que aplica deliberadamente a cláusula errada e **exige** que o deslocamento apareça, para pegar quem tentar unificar as duas migrations. Um teste que demonstra o erro vale mais que um que só confirma o acerto.

Há ainda uma fonte única para "agora" no código, `core/tempo.py`, com guarda textual proibindo o uso do relógio UTC ingênuo do Python.

### O que os testes de repositório realmente provam

Vale repetir, porque é o que separa "teste verde" de "consulta correta": a suíte de repositórios prova que a SQL montada **contém** os trechos esperados e recebe os parâmetros esperados. Ela não prova que a SQL é válida, que as colunas existem, nem que o resultado é o certo.

Consulta nova com risco de erro de sintaxe ou de tipo precisa de um dos três caminhos descritos no capítulo de acesso ao banco.

## Verificação

Estas são as provas de que a camada de banco está inteira. Nenhuma delas conecta em banco de produção, e nenhuma exige conta de terceiros.

| Prova | Como conferir | Resultado esperado |
|---|---|---|
| Migrations com fiação correta | `python -m pytest tests/test_migrations_fail_loud.py -q` em `BackEnd/` | Testes passando, sem conectar em banco |
| Suíte de migrations completa | Os onze arquivos de teste de migration em `BackEnd/tests/` | 18 passando e 35 pulados na máquina de referência |
| Etapa nova registrada | O teste que compara as funções `ensure_*` com a lista de etapas | Passa; falha se você criou a função e esqueceu de listar |
| Guarda do sinal de porcentagem | `python -m pytest tests/test_frequencia_turma.py -q` em `BackEnd/` | 17 passando na máquina de referência |
| Schema aplicado em banco vazio | Subir a API e ler o log | Migrations aplicadas, sem exceção de etapa `ensure_*` |
| Banco alcançável pela API | Abrir a rota `/health` da API local | Status 200, com o campo de banco em `ok` |
| Banco inacessível é detectado | Mesma rota com o banco parado | Status 503, com o detalhe só no log |
| Índices em uso | O arquivo de verificação no DBeaver, depois de uma aula real | `idx_scan` maior que zero nos índices do caminho quente |

Os 35 testes pulados são os de integração, que dependem do gate de banco. Suíte verde com pulados é o resultado correto em máquina local; a execução real deles é no CI.

O bloco abaixo roda a partir da raiz do repositório, com o ambiente virtual ativo, e é o que confere a camada de migrations inteira de uma vez:

```bash
cd BackEnd
python -m pytest tests/test_migration*.py -q
```

## Problemas conhecidos

### Tabela de sintomas

| Sintoma | Causa | Solução |
|---|---|---|
| Serviço em restart loop após deploy, log cita uma etapa que falhou | Migration quebrou; o boot é fail-loud de propósito | Abrir a função `ensure_*` daquele nome em `BackEnd/infra/migrations.py`, corrigir e reiniciar. Nunca comentar a etapa |
| Serviço em restart loop, log cita ausência de conexão com o banco | Banco fora do ar ou variáveis de banco erradas | Conferir o serviço do PostgreSQL e o bloco de banco do `.env`. O serviço volta sozinho quando o banco voltar |
| API sobe, mas a rota de saúde responde 503 | Banco inacessível ou credencial errada | Conferir as cinco variáveis obrigatórias de banco. A resposta não traz detalhe: o erro está no log |
| Excluir aluno devolve 400 com `error_code` `FOREIGN_KEY_VIOLATION` e a mensagem genérica de referência inválida | O aluno tem registro em `ConsentimentosLGPD`; a chave estrangeira não tem `ON DELETE` e a exclusão em cascata não apaga a trilha, então a transação volta atrás | A exclusão fica bloqueada e a mensagem não cita consentimento. Confirmar a causa consultando `ConsentimentosLGPD` pelo `aluno_id` no DBeaver. Destravar exige decisão de produto sobre a retenção do consentimento, porque essa é a rota do direito ao esquecimento da LGPD |
| Histórico de frequência sumiu depois de excluir um professor | Exclusão feita à mão no banco; a chave estrangeira é `ON DELETE CASCADE` e cascateia até `presencas` | Restaurar do backup. Excluir professor **só** pela aplicação, que anula `professor_id` antes de apagar |
| Erro 500 em produção com `IndexError: tuple index out of range` na consulta | Sinal de porcentagem literal não escapado na SQL, possivelmente dentro de comentário | Trocar por `%%`. Acrescentar o repositório à guarda textual |
| `operator does not exist: uuid = text` | Lista de strings passada para um `ANY` sem cast | Usar `ANY(%s::uuid[])` |
| `operator does not exist: uuid = integer` ao pedir o plano de execução | O literal `turma_id = 1` do arquivo de verificação de índices | Trocar por um identificador real de turma, com cast |
| Datas deslocadas em horas entre duas colunas da mesma tabela | Coluna sem fuso recebendo hora do banco e hora do Python | Converter para `TIMESTAMPTZ`, com a cláusula do grupo certo |
| Teste de repositório verde e consulta quebrada em produção | O cursor simulado não executa SQL nenhuma | Validar pelos três caminhos do capítulo de acesso ao banco |
| Abrir chamada devolve 409 com a mensagem de que já existe uma chamada aberta para a turma | Índice único parcial de chamada aberta por turma; a violação é traduzida em 409 com mensagem própria | Fechar a chamada esquecida. Não existe endpoint de reabertura, por decisão de design |
| Frequência do aluno menor que o esperado em aula geminada | Contagem por chamada em vez de por linha de `Presencas` | Somar linhas de `Presencas`, respeitando o número da aula |
| Tabela de códigos de recuperação de senha crescendo sem parar | Nenhuma rotina purga `PasswordResetCodes` | Purga manual no DBeaver, ou acrescentar a limpeza ao ciclo diário do agendador |
| `duplicate key pg_type_typname_nsp_index` no startup | Workers concorrentes sem o advisory lock | Não deve ocorrer no código atual; se ocorrer, conferir se o lock ainda é tomado antes de aplicar as etapas |

### Onde a documentação diverge do código

O critério, em qualquer divergência, é o **código**.

- O `README.md` credita a presença por aula ao arquivo `BackEnd/migrations/001_presenca_por_aula.sql`. Nenhum código do repositório executa esse arquivo. Quem aplica a mudança é a etapa `ensure_presenca_por_aula`.
- O `README.md` lista doze tabelas do schema base e menciona em prosa mais três criadas por migration. O total real é dezessete, e ficam de fora da contagem dele as tabelas de tentativa de login e de recibos de push pendentes.
- O `schema_inicial.sql` não reflete o schema atual: ele tem doze das dezessete tabelas, faltando cinco, e faltam ainda dez dos índices atuais e algumas colunas, entre elas `tentativas` e `token_consumido_em`. Todas as datas nele ainda são sem fuso.
- A intenção documentada é que excluir professor **orfane** turmas e chamadas, mas as chaves estrangeiras estão declaradas como `ON DELETE CASCADE`. A garantia é do código da aplicação, não do banco.
- O arquivo de verificação de índices traz um plano de execução com `turma_id = 1`, comparação impossível numa coluna `uuid`.

## Referência rápida

### As tabelas em uma linha cada

| Tabela | Chave primária | Uma linha por |
|---|---|---|
| `Usuarios` | `usuario_id` | Pessoa com acesso ao sistema |
| `Professores` | `professor_id` | Professor |
| `Alunos` | `aluno_id` | Aluno |
| `Turmas` | `turma_id` | Disciplina ofertada |
| `Turma_Alunos` | `turma_aluno_id` | Matrícula de um aluno numa turma |
| `Horarios_Aulas` | `horario_id` | Faixa da grade semanal de uma turma |
| `Chamadas` | `chamada_id` | Encontro de aula, aberto e depois fechado |
| `Presencas` | `presenca_id` | Aluno presente numa aula da chamada |
| `Colecao_Rostos` | `colecao_rosto_id` | Face indexada de um aluno, por ângulo |
| `ConsentimentosLGPD` | `consentimento_id` | Evento de aceite ou revogação |
| `RefreshTokens` | `token_hash` | Refresh token emitido |
| `PasswordResetCodes` | `id` | Código de recuperação de senha emitido |
| `PushTokens` | `usuario_id` | Dispositivo de push do usuário |
| `PushReceiptsPendentes` | `ticket_id` | Envio de push aguardando recibo |
| `camera_tokens` | `id` | Token de serviço de uma sala |
| `login_attempts` | `email` | Conta com falhas de login acumuladas |
| `rate_limit_buckets` | `key` | Contador de rate limit em janela |

### Invariantes que não podem ser quebrados

- Uma chamada aberta por turma, no máximo.
- Uma presença por combinação de chamada, aluno e número da aula.
- Um RA por aluno, um e-mail por usuário, um código por turma.
- Um ângulo por aluno em `Colecao_Rostos`.
- `ConsentimentosLGPD` só recebe inserção.
- Presença sobrevive à exclusão do professor.

### Comandos do dia a dia

| Ação | Comando | Onde roda |
|---|---|---|
| Aplicar o schema em banco vazio | Subir a API; as migrations rodam no startup | `BackEnd/` |
| Rodar a suíte de migrations | `python -m pytest tests/test_migration*.py -q` | `BackEnd/` |
| Rodar a guarda do sinal de porcentagem | `python -m pytest tests/test_frequencia_turma.py -q` | `BackEnd/` |
| Ver por que o serviço não sobe | `sudo journalctl -u scpi-api -n 100 --no-pager` | VM de produção |
| Aplicar o dump histórico, se necessário | `psql -U postgres -d scpi_db -f schema_inicial.sql` | Raiz do repositório |
| Conferir uso dos índices | Colar `ops/sql/verificar_indices_p3.sql` no cliente | DBeaver |

### Mapa de segredos

Nenhum valor aparece neste manual, e nenhum deve aparecer em commit.

| Segredo | Onde mora | Como obter |
|---|---|---|
| Senha do banco de produção | `/opt/scpi/.env` na VM | Cofre de segredos cifrado. Ver o Manual de Contas e Segredos |
| Senha do banco local | `.env` da raiz do repositório | Você define ao instalar o PostgreSQL local |
| Demais variáveis de banco | Mesmo arquivo do respectivo ambiente | Ver o Manual de Ambiente de Desenvolvimento |
| Credenciais do banco de teste do CI | `.github/workflows/tests.yml` | Descartáveis, criadas e destruídas a cada execução |
| Chave do backup cifrado | Fora da VM, com a chave pública na VM | Ver o Manual de Contas e Segredos |

> **Atenção:** o `.env` está no `.gitignore`, mas isso não protege contra credencial colada dentro de código, de teste ou de arquivo de exemplo. Há varredura de segredos no CI, e o exame agendado percorre o histórico completo do repositório.

### Arquivos-fonte deste manual

Cada afirmação foi conferida contra um destes arquivos ou contra a saída de um comando executado na máquina de referência.

| Arquivo | O que fixa |
|---|---|
| `schema_inicial.sql` | Colunas, tipos, restrições e chaves estrangeiras do dump histórico |
| `BackEnd/infra/migrations.py` | As vinte e uma etapas, a ordem, o advisory lock e o fail-loud |
| `BackEnd/infra/database.py` | Variáveis obrigatórias, pool, fuso da sessão e o contrato do cursor |
| `BackEnd/repositories/professores.py` | A exclusão que orfana turmas e chamadas |
| `BackEnd/repositories/alunos.py` | A exclusão de aluno e os inserts de usuário |
| `BackEnd/repositories/presencas.py` | Merge de presença por número da aula |
| `BackEnd/repositories/rostos.py` | Upsert de rosto por aluno e ângulo |
| `BackEnd/repositories/tokens.py` | Purga de refresh token e ciclo do código de recuperação |
| `BackEnd/repositories/consentimentos.py` | Que a trilha de consentimento só recebe inserção |
| `BackEnd/services/agendador.py` | O que a limpeza diária purga e o que não purga |
| `BackEnd/core/regras.py` | Ângulos válidos e o limiar único de frequência |
| `BackEnd/tests/conftest.py` | O gate de banco e as fixtures que fazem truncate |
| `BackEnd/tests/test_migrations_fail_loud.py` | Que a falha aborta o boot com o nome da etapa |
| `BackEnd/tests/test_frequencia_turma.py` | A guarda textual do sinal de porcentagem |
| `ops/sql/verificar_indices_p3.sql` | As consultas de uso de índice, para o DBeaver |
| `docs/runbooks/deploy.md` | Onde fica o banco em produção e como ler o restart loop |
| `.github/workflows/tests.yml` | Versão do Postgres do CI e o gate de integração |
| `.env.example` | Os nomes e os defaults das variáveis de banco |
