# Biometria, Liveness e Câmera de Sala

## Cadastro multi-ângulo

Cada aluno tem **~4 `FaceId`s distintos** na collection da Rekognition, todos com o mesmo
`ExternalImageId`. Múltiplos ângulos (frontal / esquerda / direita / baixo) aumentam a taxa
de reconhecimento em iluminação e posição variadas.

**`ExternalImageId = str(aluno_id)` (UUID)** desde 2026-07-31 — ver o porquê em
[[decisions.md]]. A chave do S3 acompanhou: `alunos/{aluno_id}/{uuid}.jpg`, sem nome no
caminho.

Regras:

- **Deduplicação usa `ExternalImageId`, nunca `FaceId`** — `FaceId` duplica o mesmo aluno.
- `registrar_presenca_por_face` parseia o valor vindo da AWS como UUID e resolve por
  `aluno_id` com `revogado_em IS NULL`, aproveitando o índice `unique(aluno_id, angulo)`.
- **Gravar qualquer coisa que não seja `str(aluno_id)` em `cadastrar_aluno_api` quebra o
  reconhecimento inteiro.**
- Face legada com ID em formato de nome é **recusada explicitamente** — não casa com nada em
  silêncio.

## Liveness passivo — implementado 2026-07-15, validado em campo 2026-07-16

Fecha o item M1 da auditoria. Abordagens interativas foram descartadas porque o produto é
câmera passiva — ver [[decisions.md]].

Arquitetura:

- `BackEnd/scripts/confirmacao_burst.py` — `ConfirmadorBurst` **puro**: consenso X-de-Y +
  desvio de pose (yaw/pitch via `DetectFaces`). A ideia central é que **foto é plana, então a
  pose não varia**. Expõe `avaliar()` e `avaliar_detalhado()` (métricas para calibração), com
  matriz REGISTRAR / PENDENTE / DESCARTAR.
- `reconhecimento_tempo_real.py` — burst por evento de detecção, `DetectFaces` só para
  matches ainda não registrados, aborto se a chamada mudar. Detector migrado de Haar para
  **YuNet** (`FaceDetectorYN`, modelo ONNX git-ignored em `scripts/models/`, env
  `FACE_MODEL_PATH`), o que também fecha a pendência do OpenCV 5.

Envs: `BURST_FRAMES=5`, `BURST_MIN_MATCHES=3`, `BURST_DURACAO_S=2`,
`LIVENESS_POSE_STD_MIN=2.0`.

**Fail-safe central: sem amostras de pose (<2 em ambos os eixos) NUNCA registra** (PENDENTE),
independente do limiar. Era bug do plano, pego em review e pinado por teste.

Teste de campo (2026-07-16): pessoa real REGISTRAR 100%, foto DESCARTAR 100% →
`LIVENESS_POSE_STD_MIN=2.0` confirmado sem recalibração.

> 🔴 **Esse teste usava foto IMÓVEL.** Com o celular na mão o tremor gera
> `magnitude=2.98 > 2.0` e o gate de pose aprova o spoof (medido 2026-08-06). O fallback
> `ENABLE_TEXTURE=0` portanto **não é mitigação** — os dois gates caem no mesmo ataque.

## Detector de textura (PAD local) — `scripts/anti_spoofing.py`

**Existe e é o gate default.** A intenção era fechar o buraco que a pose-variance não resolve
(foto em tela ou vídeo, que se movem). Spec de 2026-07-19.

> 🔴 **NÃO FECHA.** Bypass confirmado em produção em 2026-08-06 com foto em tela de celular —
> ver a seção de bypass abaixo. As medições de julho desta seção (real 0,999 / foto 0,000)
> foram feitas em close-up com foto imóvel e **não generalizam** para tela em mão a distância.

- Modelo **facenox MiniFASNetV2-SE**, `best_model.onnx` **não-quantizado** (1,9 MB,
  Apache-2.0), rodando em `cv2.dnn`. **O quantizado (626 KB) não serve** — usa
  `DynamicQuantizeLinear`, que o `cv2.dnn` não suporta; o erro de load levanta com essa
  explicação.
- Pré-processamento validado em ground-truth e em câmera real a 2 m: crop com scale **1.4**
  do bbox → `blobFromImage(1/255, 128x128, swapRB=True)` → softmax, **classe 0 = live**.
  Medições: rosto real 0,999 (faixa 0,429–0,986); foto 0,000.
- `DetectorTextura` é **fail-closed**: erro ao carregar o modelo levanta, não degrada calado.
- Envs: `ENABLE_TEXTURE` (default **ligado**), `TEXTURE_MODEL_PATH`,
  `TEXTURE_LIVENESS_MIN` (default `0.08`).
- Com `ENABLE_TEXTURE=off` o `ConfirmadorBurst` cai no `gate="pose"`, descrito no próprio
  código como **fallback paliativo** — a magnitude da variação decide, e sem amostras de pose
  o fail-safe continua valendo (não vivo).

### 🔬 Por que rosto REAL pontua baixo — causa raiz (2026-08-06)

Sintoma: rosto real vivo pontua muito baixo com frequência, na porta, mesmo perto.

**Hipóteses testadas e REJEITADAS — não perseguir de novo:**

- **Classe invertida (`p[1]` seria "live")?** NÃO. Controlando por tamanho, na faixa 60–100px
  onde `real` e `tela` coexistem, `p[0]` dá real **0.0886** contra tela **0.0159** — real acima,
  direção certa. O "tela = 0.97" que sugeria inversão é artefato de rosto de 11–28px (nitidez
  mediana **7,5**, um borrão). **`p[0]` é live, o código está certo.**
- **Crop pequeno sendo ampliado para 128×128?** NÃO é o driver. 24 dos 25 frames reais já têm
  crop nativo ≥128px.

**Causa raiz: o modelo responde a NITIDEZ, não a vida.** Spearman entre nitidez (variância do
laplaciano) e score, dentro de cada label: `real` **ρ=+0.651**, `tela` ρ=−0.785, `video`
ρ=−0.564. Frames reais lidos como VIVO têm nitidez mediana **702**; os lidos como FAKE, **91** —
7,7×, com brilho praticamente idêntico (107 contra 105). Rosto real levemente borrado é lido
como fake, e "pessoa passando pela porta" é exatamente o que borra (obturador lento + movimento).

A calibração de julho ("real 0,999") foi feita em **close-up, parado, nítido** — por isso
parecia sólida e não é.

**Consequência prática: isso não tem conserto por parâmetro.** Limiar não cria nitidez. Ataca-se
na câmera: exposição/obturador mais rápido, mais luz na porta, ou posicionamento que faça a
pessoa desacelerar.

No regime bem resolvido (crop nativo ≥128px), rosto real falha em **11 de 24 frames** contra o
limiar 0.08. Só não vira desastre porque o gate agrega por `max` de 5 frames — quando os 5 saem
borrados, o burst inteiro cai.

### 📐 Números REAIS da câmera da porta (log de produção, 2026-08-06 22h)

Estes vieram do log de produção e **derrubam duas conclusões** tiradas antes deles, das
amostras caseiras. Confie nesta seção, não nas extrapolações.

| medido na porta | valor |
|---|---|
| rosto real (você passando) | **60–75px** |
| `texture_max` do rosto real | 0.7537 |
| rosto do vídeo que PASSOU | 79–91px, `texture_max` **0.2802** |
| rosto do vídeo BARRADO pelo piso | 39–49px |
| magnitude de pose — real | **2.79** |
| magnitude de pose — vídeo | **19.67 / 23.20** |

**Errado #1: "na porta o rosto dá 150–300px".** Dá 60–75px. `TEXTURE_FACE_MIN_PX` teve que
descer de 80 para **50**, senão a pessoa real não passa. A porta está na faixa **marginal** do
modelo (60–91px), não na confortável.

**Errado #2: "vídeo só passa abaixo de ~91px".** Passou com 79–91px. A previsão saiu de 11
frames de uma sessão em casa.

**Descoberta que contradiz o desenho de julho:** a premissa era "foto é plana, então a pose não
varia". O ataque na mão varia **7–8× MAIS** que a pessoa real (19–23 contra 2.79). Se pose vier
a ser usada, o discriminante é **teto**, não piso. Não construir ainda — n=1 de cada lado, e o
atacante derruba segurando firme.

**Teto de tamanho de rosto foi proposto e RECUSADO** (2026-08-06). Funcionaria na amostra do dia
(vídeo 79–91px é maior que o real 60–75px), mas falha no teste de assimetria: para vencer o
**piso** o atacante precisa de rosto maior → mais resolução → textura mais forte (bom para nós);
para vencer o **teto** ele precisa de rosto menor → e abaixo de ~40px o modelo devolve ~0.99
para qualquer coisa. **O teto empurra o ataque para dentro do ponto cego.** Além disso o tamanho
exibido é botão contínuo na mão do atacante, e o do aluno não é.

### Correção parcial: piso de tamanho de rosto (branch aberta, 2026-08-06)

Branch **`fix/piso-tamanho-rosto-textura`** empurrada (2 commits, PR aberto, **não mergeada**).
Spec: `docs/superpowers/specs/2026-08-06-piso-tamanho-rosto-porta-design.md`.

**A ideia:** o gate errava porque respondia uma pergunta que não sabe responder. Abaixo de
`TEXTURE_FACE_MIN_PX` (default **80**, vindo da spec do MiniFASNet e não das amostras),
`DetectorTextura.score()` devolve **`None`** — "não sei" — em vez de um número. `None` não é
"fake": é ausência de prova. `ConfirmadorBurst` já descarta texturas `None` e cai em PENDENTE
quando não sobra nenhuma, então **nenhum estado novo entra** e `confirmacao_burst.py` não é
tocado. O fail-safe pinado na review de julho passou a ser o mecanismo de defesa.

Efeito medido sobre a coleta de 2026-08-06, piso 80 — bursts que **registram presença**:

| piso | `real` | `video` | `tela` |
|---:|---:|---:|---:|
| 0 (antes) | 4/5 | 3/6 | 6/6 |
| **80** | **4/5** | **0/6** | **0/6** |
| 85 | 2/5 | 0/6 | 0/6 |

Fecha os dois ataques **sem custar um burst real** — e a margem é estreita: entre 80 e 85 o
`real` desaba, porque existem bursts reais de 83–84px. Nesta geometria (casa, webcam de
notebook). Na porta deve ser folgada, e é o que a calibração vai dizer.

Também nesta branch: `DetectorTextura.vivo()` removida (zero chamadores, semântica incompatível
com `None`), e a docstring do módulo corrigida — ela afirmava "foto 0.000" e que o módulo cobria
o ataque que a pose não resolve. **Foi essa docstring que sustentou a crença de que o gate
estava fechado.**

🚧 **PENDÊNCIAS antes de valer em produção:**

1. **Calibrar o piso na câmera da porta** — gate de deploy. Coletar só `real` lá
   (`$env:LIVENESS_COND="porta-real"`), olhar o **mínimo** da distribuição (não a mediana: é o
   aluno mais distante que decide quem perde presença). ≥150px → manter 80. <100px → o piso não
   separa nessa geometria e a camada B vira bloqueante.
2. **Flag `--piso`** em `_validar_liveness.py` — fica na `feat/validacao-replay-video`, porque
   importa `rosto_avaliavel`, que só existe depois deste fix mergear.
3. **Risco residual ABERTO: tablet ou tela grande colado na câmera.** Rosto exibido acima do
   piso deixa só a textura de pé, e a evidência de que ela segura ali é **um único burst**
   (154–222px → 0.0010). Tablet nunca foi coletado, apesar de estar no threat model. Só a
   camada B fecha.
4. **Câmera da lousa não é atendida por isto.** Rosto de 20–55px fica todo abaixo do piso:
   nada registraria. Ela precisa de gate geométrico, em spec própria, e ainda não existe.

### 🔴 BYPASS CONFIRMADO EM PRODUÇÃO — foto em tela de celular (2026-08-06)

**O gate de textura não sustenta o liveness sozinho. Os dois gates falham no mesmo ataque.**

Teste ao vivo pelo caminho normal da sala: celular exibindo foto de aluno na frente da
câmera **registrou presença**.

```
🎯 Confirmado (textura): <aluno_id> [matches=5, texture_max=0.8542894124984741,
   tex_limiar=0.08, magnitude=2.983775718984782, pose_limiar=2.0]
```

- `texture_max=0.854` contra limiar `0.08` — passou por **10,7×**.
- `magnitude=2.98` contra `pose_std_min=2.0` — **o fallback de pose também teria aprovado**.
  Logo `ENABLE_TEXTURE=0` NÃO é mitigação.
- `matches=5` — Rekognition casou em todos os frames do burst.

**Por que a pose-variance não pegou:** a premissa "foto é plana, então a pose não varia" só
vale para foto *parada*. Segurando o celular na mão, o tremor produz yaw/pitch suficiente.
Quem se move é o atacante, não a foto. O teste de campo de 2026-07-16 (foto DESCARTAR 100%)
usava foto imóvel e por isso não cobria este caso.

### Medição de replay — resultado (2026-08-06)

Coleta com a ferramenta da branch `feat/validacao-replay-video`. max-por-burst, a grandeza
que `ConfirmadorBurst` compara (`confirmacao_burst.py:77,101`, `max(texturas) >= texture_min`):

| label | max-por-burst | vs. gate 0.08 |
|---|---|---|
| `real` (n=5) | 0.0017 · 0.092 · 0.375 · 0.990 · 0.996 | **1/5 rejeitado**, 1 raspando |
| `video` (n=6) | 0.001 · 0.022 · 0.066 · 0.222 · 0.308 · 0.638 | **3/6 registram presença** |
| `tela` (n=6) | 0.129 · 0.975 · 0.990 · 0.991 · 0.9995 · 1.000 | **6/6 registram presença** |

`R = 0.0017`, `V = 0.638`, folga `0.00×` → **SOBREPOSTO**. Desfecho `R <= V` da tabela do
plano: **camada B obrigatória**.

**Nenhum limiar separa.** Bloquear o vídeo exigiria limiar > 0.638, o que rejeita 3 dos 5
bursts reais (60% de falso-negativo em aluno legítimo). Bloquear foto em tela exigiria > 1.0.

**Piso de bbox também não fecha.** Sensibilidade por tamanho mínimo de rosto: com piso de
70px o vídeo cai para 0.022 (bloqueado), mas `tela` fica em 0.129 (**ainda passa**) e o pior
burst real segue em 0.0017. O desfecho SOBREPOSTO se mantém em todo piso de 0 a 100px.

Dois achados colaterais:

1. **Rosto real sendo rejeitado.** Um burst real com rosto de 136–161px — tamanho bom —
   pontuou 0.0017 (todos os 5 frames entre 0.0000 e 0.0017). Contraluz forte/estourado.
   Em produção esse aluno vira PENDENTE e não registra presença. Problema de
   disponibilidade, independente do spoof.
2. **O modelo colapsa em "live" abaixo de ~30px.** Frames de `tela` <40px: mediana 0.9887.
   Os mesmos ≥40px: mediana 0.0159. Um crop de 11px é um borrão e pontua 1.0000. Quanto
   mais longe a tela, melhor o ataque — mas o bypass de 2026-08-06 não depende disso: o
   burst de 75px também passou (0.129).

**Desvios de protocolo desta coleta** — os números indicam a direção certa e batem com o
ataque ao vivo, mas não são a calibração oficial da matriz:

- `LIVENESS_COND` nunca foi setada: 17 bursts caíram em `sem_cond`, sem quebra por
  distância/aparelho. A matriz de 12 células **continua aberta**.
- Coletado em casa (webcam de notebook, ângulo baixo, luz de teto), não na máquina da sala.
- Sem tablet. 5 bursts de `real` (plano pedia ≥6).

A favor da camada B: nos frames coletados a moldura do celular está inteira no enquadramento
e num deles até os controles do player aparecem. Canny+Hough acha esse retângulo sem esforço.
E `.liveness_samples/` já tem o ataque gravado em PNG — a camada B pode ser desenvolvida e
validada contra dado real.

### Replay de VÍDEO — contexto da medição (aberto em 2026-08-05, medido em 2026-08-06)

O PAD nunca foi medido contra **vídeo** em tela: a calibração de 2026-07-19 só usou foto
(papel e tela). Consenso X-de-Y e pose-variance não cobrem vídeo — ele dá match em todo frame
e tem movimento de cabeça real — então a textura é a única camada em jogo. Threat model:
celular ou tablet a **0,5–3 m**. Branch `feat/validacao-replay-video` instrumenta
`_validar_liveness.py` para medir; falta a coleta manual.

Quatro armadilhas pegas em review, todas produzindo número plausível-porém-errado:

1. **Calibrar em frame solto subestima o atacante.** O gate decide por `max` do burst, então
   UM frame sortudo em 5 já registra presença. A grandeza é **max-por-burst**, e a coleta tem
   que usar a cadência de produção.
2. **`V == 0` exato nunca acontece.** O score vem de softmax sobre float32; fake saturado dá
   ~`2e-09`. O "foto 0,000" desta página é renderização `.3f`, **não zero exato**. Guard por
   igualdade a zero é código morto — usar tolerância e formatar com `:.6g`, senão o limiar
   sugerido imprime `0.0000`, que o gate lê como "passa tudo".
3. **Meio geométrico pode ficar abaixo do limiar em vigor.** Números de julho: `sqrt(0.16 ×
   0.003) = 0.0219` contra `0.08` — recomendaria afrouxar 3,6× sob um check verde. Regra:
   clampar em `max(atual, sugerido)`, nunca recomendar afrouxar.
4. **JPEG falseia PAD de textura.** Qualidade 95 atenua a alta frequência (moiré, grade de
   tela, grão) que o detector usa, enquanto produção pontua BGR cru. Amostra é **PNG**.

A ferramenta é Windows-only (`CAP_DSHOW`) e o shell é PowerShell: runbook usa
`$env:LIVENESS_COND="2m-celular"; python ...`, não a forma POSIX.

`FACE_MATCH_THRESHOLD_SALA` (default **90**) é o limiar de similaridade da Rekognition no
caminho da sala, separado do cadastro.

Manual da equipe em `docs/SCPI-Manual-Liveness.docx` (`docs/` é git-ignored).

## Script de câmera

- Roda **na máquina da sala**, não na VM. Por isso o ONNX do YuNet não entra no backup de
  segredos e `FACE_MODEL_PATH` não existe no `.env` de prod.
- Seleção de câmera por env **`CAMERA_INDEX`** (default `0`). Auto-detect foi proposto e
  rejeitado — ver [[decisions.md]].
- Env vazia cai no default (padrão `_env_int`): `FACE_MODEL_PATH=` vazio no `.env` derrubava
  o boot antes do fix.
- Autenticação por **token de sala** em `camera_tokens` (SHA-256), emitido por
  `scripts/camera_token.py`. O `CAMERA_SERVICE_TOKEN` global e o `CAMERA_SALA` **não existem
  mais**. A sala vem do token — token emitido para a sala errada marca presença na aula
  errada em silêncio.
- **Contabilidade de registro em dois estados** (`scripts/registro_tracker.py`) — o aluno só é
  dado como resolvido **depois** que o servidor responde. Ver o porquê em [[stack.md]].
- O cliente classifica falha como **definitiva se `status < 500`**. Por isso o 503 de
  `GET /chamadas/aberta/sala` precisa ser preservado: `_sincronizar_chamada` retorna cedo em
  5xx e mantém `chamada_id_atual` + tracker; 4xx continua resetando (token revogado é
  definitivo). Mesmo tratamento do timeout.

## Custo

Rekognition em free tier (5.000 chamadas/mês por 12 meses). A câmera-sala re-bursta ~10× a da
porta. Decisão I1: **aceitar e monitorar**, com o back-off (spec pronta) adiado até o contador
mensal se aproximar do teto. P2 — custo de ~US$125/aula/sala — está com os sócios.
