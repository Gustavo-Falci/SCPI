"""Contraste do texto do portal contra os fundos do tema (WCAG 2.1 AA).

O portal é dark e as labels são de 10-12px. Texto pequeno exige **4,5:1** — o
limite frouxo de 3:1 só vale para ≥24px, ou ≥18,66px em negrito, e nenhuma
label se qualifica. `text-gray-500/600/700` reprovavam: o pior caso era
gray-700 sobre card-hover, a 1,66:1.

Em vez de proibir nomes de classe, o teste **recalcula** o contraste: qualquer
`text-gray-N` que sobre no código é convertido para hex e medido. Assim
gray-300 e gray-400 continuam válidos (passam), e nenhuma regra arbitrária de
vocabulário precisa ser mantida à mão.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PORTAL = RAIZ / "portal"
CONFIG = PORTAL / "js" / "tailwind-config.js"

# Mínimo da WCAG 2.1 AA para texto normal (1.4.3).
AA_TEXTO_PEQUENO = 4.5

# Escala cinza padrão do Tailwind 3.4 — só os tons que o portal usa ou poderia
# usar. Um tom fora desta tabela faz o teste falhar explicitamente, em vez de
# passar por omissão.
GRAY_TAILWIND = {
    "50": "#f9fafb", "100": "#f3f4f6", "200": "#e5e7eb", "300": "#d1d5db",
    "400": "#9ca3af", "500": "#6b7280", "600": "#4b5563", "700": "#374151",
    "800": "#1f2937", "900": "#111827", "950": "#030712",
}

CLASSE_GRAY = re.compile(r"text-gray-(\d{2,3})\b")


def _luminancia(hex_cor: str) -> float:
    hex_cor = hex_cor.lstrip("#")
    canais = [int(hex_cor[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contraste(cor_a: str, cor_b: str) -> float:
    maior, menor = sorted([_luminancia(cor_a), _luminancia(cor_b)], reverse=True)
    return (maior + 0.05) / (menor + 0.05)


def _cores_do_config() -> dict[str, str]:
    """Lê os hex direto do tailwind-config.js — a fonte da verdade do tema."""
    texto = CONFIG.read_text(encoding="utf-8")
    return {
        nome.strip("'\""): valor
        for nome, valor in re.findall(r"'?([\w-]+)'?:\s*'(#[0-9a-fA-F]{6})'", texto)
    }


def _fundos() -> dict[str, str]:
    cores = _cores_do_config()
    return {n: cores[n] for n in ("surface", "card", "card-hover")}


def _arquivos_portal():
    """Arquivos que APLICAM classes.

    `tailwind-config.js` fica de fora: ele declara as cores e o comentário dele
    cita os `text-gray-*` que foram substituídos — a varredura é textual e leria
    a documentação como uso.
    """
    arquivos = [p for p in PORTAL.rglob("*.js") if "vendor" not in p.parts]
    arquivos += list(PORTAL.rglob("*.html"))
    return [p for p in arquivos if p != CONFIG]


def test_contraste_conhece_o_algoritmo():
    """Âncora: valores canônicos da WCAG. Se isto quebrar, a fórmula regrediu."""
    assert round(_contraste("#ffffff", "#000000"), 2) == 21.0
    assert round(_contraste("#777777", "#ffffff"), 2) == 4.48


@pytest.mark.parametrize("token", ["muted", "faint"])
def test_token_de_texto_passa_aa_em_todos_os_fundos(token):
    cores = _cores_do_config()
    assert token in cores, f"token '{token}' sumiu de tailwind-config.js"
    reprovados = {
        nome: round(_contraste(cores[token], fundo), 2)
        for nome, fundo in _fundos().items()
        if _contraste(cores[token], fundo) < AA_TEXTO_PEQUENO
    }
    assert not reprovados, f"'{token}' abaixo de {AA_TEXTO_PEQUENO}:1 em {reprovados}"


def test_faint_mantem_margem_sobre_o_limite():
    """Passar raspando deixa o tema refém de qualquer ajuste de fundo."""
    cores = _cores_do_config()
    pior = min(_contraste(cores["faint"], f) for f in _fundos().values())
    assert pior >= 5.0, f"faint a {pior:.2f}:1 — pouca folga para mexer nos fundos"


def test_muted_e_mais_claro_que_faint():
    """A hierarquia visual entre os dois tons precisa sobreviver ao conserto."""
    cores = _cores_do_config()
    assert _luminancia(cores["muted"]) > _luminancia(cores["faint"])


@pytest.mark.parametrize("arquivo", _arquivos_portal(), ids=lambda p: p.name)
def test_gray_remanescente_no_portal_passa_aa(arquivo):
    """Mede cada text-gray-N que sobrou contra o fundo mais claro (pior caso)."""
    pior_fundo = max(_fundos().values(), key=_luminancia)
    texto = arquivo.read_text(encoding="utf-8")

    reprovados = []
    for n, linha in enumerate(texto.splitlines(), 1):
        for tom in CLASSE_GRAY.findall(linha):
            assert tom in GRAY_TAILWIND, f"tom gray-{tom} fora da tabela conhecida"
            razao = _contraste(GRAY_TAILWIND[tom], pior_fundo)
            if razao < AA_TEXTO_PEQUENO:
                reprovados.append(f"linha {n}: text-gray-{tom} a {razao:.2f}:1")

    assert not reprovados, (
        f"{arquivo.relative_to(RAIZ)} tem texto abaixo de {AA_TEXTO_PEQUENO}:1 "
        f"sobre {pior_fundo}. Use text-muted ou text-faint:\n  " + "\n  ".join(reprovados)
    )
