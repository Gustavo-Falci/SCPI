# SCPI — Identidade Visual

**Sistema de Controle de Presença Inteligente**

---

## Conceito

O símbolo central é um **frame de escaneamento biométrico** — os quatro cantos em "L" remetem ao visor de uma câmera no ato de enquadrar um rosto para reconhecimento. Dentro do frame, uma silhueta facial com **nós de detecção** conectados por linhas finas representa os pontos de referência que o AWS Rekognition mapeia (olhos, sobrancelhas, nariz, boca, queixo). Uma **linha de varredura horizontal** em verde cruza o rosto no nível do nariz, sinalizando reconhecimento ativo. O **badge de checkmark** no canto inferior direito confirma: presença registrada.

A identidade une dois mundos — **tecnologia** (scan, nodes, verde de "OK") e **academia** (azul de confiança, tipografia sólida, hierarquia clara).

---

## Arquivo principal

`logo-concept.svg` — lockup horizontal, 480 × 150 px, fundo transparente.

---

## Paleta de Cores

| Papel                | Nome        | Hex         | Uso                                     |
| -------------------- | ----------- | ----------- | --------------------------------------- |
| **Primária**  | Deep Blue   | `#1E40AF` | Frame, silhueta, elementos estruturais  |
| **Accent**     | Emerald     | `#10B981` | Scan line, badge, underline do wordmark |
| **Node**       | Mid Blue    | `#3B82F6` | Pontos e linhas de detecção facial    |
| **Texto**      | Near Black  | `#0F172A` | Wordmark "SCPI"                         |
| **Tagline**    | Slate       | `#475569` | "PRESENÇA INTELIGENTE"                 |
| **Descriptor** | Light Slate | `#94A3B8` | Linha de detalhe inferior               |
| **Separator**  | Border      | `#CBD5E1` | Linha divisória vertical               |

### Uso em fundos escuros

- Wordmark: `#F8FAFC`
- Frame + silhueta: `#60A5FA` (blue-400)
- Tagline: `#94A3B8`
- Accent: `#10B981` (mantém)
- Badge: `#10B981` (mantém)

---

## Tipografia

| Elemento        | Fonte               | Peso | Tamanho | Espaçamento |
| --------------- | ------------------- | ---- | ------- | ------------ |
| Wordmark "SCPI" | Arial Black / Inter | 900  | 65 px   | −1.5        |
| Tagline         | Arial / Inter       | 400  | 11.5 px | +3.8         |
| Descriptor      | Arial / Inter       | 400  | 8.5 px  | +1.8         |

**Substituições web-safe:** Arial Black → fallback para Arial Bold → Helvetica Neue Bold.

**Alternativa recomendada (Google Fonts):** `Inter` (variable, wght 400–900) — geométrica, legível, técnica, open source.

---

## Anatomia do Símbolo

```
┌──┐          ┌──┐
│  ←  frame   →  │
│                 │
│  ●───●  ← brows│
│  ●   ●  ← eyes │
│    ●    ← nose  │  ── scan line (verde) ──
│  ●   ●  ← mouth│
│    ●    ← chin  │
│                 │
└──┘          └──●✓  ← badge (verde, checkmark)
```

### Proporções

- Frame interno: 126 × 128 px (no SVG de referência)
- Comprimentos dos cantos "L": 24 px cada leg
- Traço do frame: 3 px
- Traço da silhueta: 2.2 px
- Raio do badge: 14 px
- Raio dos nós maiores (olhos/nariz): 2.8 px

---

## Variantes

### 1. Lockup Horizontal (principal)

`logo-concept.svg` — ícone à esquerda, wordmark à direita. Uso: cabeçalhos, splash screen, documentação.

### 2. Ícone isolado

Exportar apenas a região `0 0 150 150` do SVG. Uso: favicon, ícone do app mobile, avatar.

### 3. Monochromatic (preto)

Trocar `#1E40AF` → `#0F172A`, `#10B981` → `#0F172A`, `#3B82F6` → `#334155`. Uso: impressão B&W, bordados, gravação.

### 4. Monochromatic (branco)

Todos os elementos em `#FFFFFF`. Uso: sobre fundos sólidos escuros, camisetas.

### 5. Ícone + Wordmark vertical

Símbolo centralizado acima de "SCPI" e tagline — uso: splash screen mobile, cartão.

---

## Espaçamento mínimo (clear space)

Mínimo de **½ da altura do badge** (≈ 7 px no SVG de referência) em todos os lados do lockup. Nenhum elemento externo deve invadir essa zona.

### Tamanho mínimo

| Variante          | Mínimo      |
| ----------------- | ------------ |
| Lockup horizontal | 240 × 75 px |
| Ícone isolado    | 32 × 32 px  |

Abaixo do mínimo, usar apenas o wordmark "SCPI" sem o ícone.

---

## O que evitar

- Distorcer proporções do frame ou da silhueta
- Trocar o verde do scan line por outra cor (rompe a semântica "presença = verde")
- Usar o logo sobre fundos que causem contraste < 3:1 com o frame azul
- Adicionar efeitos de sombra pesados ao ícone — o badge já tem sombra sutil intencional
- Girar o logo — o frame de scan tem orientação semântica (câmera = horizontal)
- Substituir "SCPI" por acrônimo expandido no wordmark (texto longo quebra a hierarquia)

---

## Aplicações sugeridas

| Contexto                    | Variante               | Fundo         |
| --------------------------- | ---------------------- | ------------- |
| App mobile — splash screen | Ícone + vertical      | `#0F172A`   |
| App mobile — header        | Ícone isolado         | transparente  |
| Admin portal — sidebar     | Lockup horizontal      | `#1E293B`   |
| Documentação / README     | Lockup horizontal      | branco        |
| Favicon / PWA icon          | Ícone isolado (64 px) | `#1E40AF`   |
| Apresentação TCC          | Lockup horizontal      | branco/escuro |

---

## Tokens de design (referência para o sistema)

```json
{
  "color": {
    "brand-primary":    "#1E40AF",
    "brand-accent":     "#10B981",
    "brand-node":       "#3B82F6",
    "text-primary":     "#0F172A",
    "text-secondary":   "#475569",
    "text-tertiary":    "#94A3B8",
    "surface-border":   "#CBD5E1"
  },
  "font": {
    "wordmark-family":  "Arial Black, Inter, sans-serif",
    "wordmark-weight":  "900",
    "body-family":      "Inter, Arial, sans-serif"
  },
  "radius": {
    "badge":            "50%",
    "accent-line":      "1.4px"
  }
}
```
