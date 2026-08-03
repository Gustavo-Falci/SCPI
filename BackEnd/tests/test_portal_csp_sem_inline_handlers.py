"""Guarda textual: o portal não pode ter handler de evento inline.

O CSP do portal (`portal/index.html`) fixa `script-src 'self'`, sem
`'unsafe-inline'` nem `'unsafe-hashes'`. Nesse modo o browser BLOQUEIA
atributos `onclick=`/`onchange=`/etc — e hash/nonce não valem para atributo,
só para bloco <script>. O sintoma é mudo do lado do JS: nenhuma exceção sobe,
o handler simplesmente nunca roda (foi assim que os botões X e Cancelar dos
modais pararam de fechar).

Teste textual porque não há runtime de browser na suíte: o único jeito de pegar
a regressão é ler os arquivos. Mesma classe de guarda do `%` literal em SQL.
"""
import re
from pathlib import Path

import pytest

PORTAL = Path(__file__).resolve().parents[2] / "portal"

# Espaço antes evita casar com substring de outro atributo (ex.: `data-on=`).
INLINE_HANDLER = re.compile(r"""\son[a-z]+\s*=\s*["']""")

# `onload`/`onerror` em <img> e afins seguiriam bloqueados igual; nada é isento.
ARQUIVOS = sorted(
    [p for p in PORTAL.rglob("*.js") if "vendor" not in p.parts]
    + list(PORTAL.rglob("*.html"))
)


def test_encontrou_os_arquivos_do_portal():
    """Sem isto, um rglob vazio faria o teste abaixo passar por engano."""
    assert len(ARQUIVOS) >= 5


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
def test_arquivo_do_portal_nao_tem_handler_inline(arquivo):
    texto = arquivo.read_text(encoding="utf-8")
    achados = [
        f"linha {n}: {linha.strip()[:120]}"
        for n, linha in enumerate(texto.splitlines(), 1)
        if INLINE_HANDLER.search(linha)
    ]
    assert not achados, (
        f"{arquivo.relative_to(PORTAL.parent)} tem handler inline, que o CSP bloqueia.\n"
        "Use addEventListener ou delegação por data-attribute:\n  "
        + "\n  ".join(achados)
    )


def test_csp_do_portal_continua_sem_unsafe_inline_em_script_src():
    """Se alguém 'resolver' o bug afrouxando o CSP, o guarda acima vira decorativo."""
    html = (PORTAL / "index.html").read_text(encoding="utf-8")
    csp = re.search(r"Content-Security-Policy\"\s+content=\"([^\"]+)\"", html)
    assert csp, "meta do CSP sumiu de portal/index.html"
    script_src = next(d for d in csp.group(1).split(";") if d.strip().startswith("script-src"))
    assert "'unsafe-inline'" not in script_src
    assert "'unsafe-hashes'" not in script_src
