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

# `style="` na marcação e abertura de bloco <style>. `el.style.x = ...` em JS
# não casa — e não deve: CSSOM é o caminho permitido para valor contínuo.
ESTILO_INLINE = re.compile(r"""\sstyle\s*=\s*["']|<style[\s>]""")


def _e_comentario(linha: str) -> bool:
    """Linha de comentário JS/CSS/HTML.

    Os guardas textuais deste projeto já falharam três vezes acusando a própria
    documentação do padrão proibido. Filtrar comentário resolve isso sem isentar
    arquivos inteiros — o que enfraqueceria o guarda sobre código real.
    """
    s = linha.strip()
    return s.startswith(("//", "/*", "*", "<!--"))

# `onload`/`onerror` em <img> e afins seguiriam bloqueados igual; nada é isento.
#
# `node_modules/` fora: são as devDependencies do build do Tailwind, milhares de
# arquivos que nunca chegam ao browser. `tailwind.config.js` também não é
# servido. Varrê-los custaria segundos e acusaria handler inline em código de
# terceiro que não roda no portal.
_IGNORAR = {"node_modules", "vendor"}
ARQUIVOS = sorted(
    p
    for p in [*PORTAL.rglob("*.js"), *PORTAL.rglob("*.html")]
    if not _IGNORAR & set(p.parts) and p.name != "tailwind.config.js"
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


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
def test_arquivo_do_portal_nao_tem_estilo_inline(arquivo):
    """`style="..."` e `<style>` são bloqueados pelo mesmo `style-src 'self'`.

    Atributo `style=` cai na mesma regra do `onclick=` — hash não vale para
    atributo. Bloco `<style>` aceitaria hash, mas o portal não usa nonce nem
    hash, então também é bloqueado.

    Valor contínuo (largura de barra, duração de toast) deve ser escrito por
    CSSOM: `el.style.width = ...` NÃO é bloqueado, a política filtra a marcação.
    """
    achados = [
        f"linha {n}: {linha.strip()[:120]}"
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1)
        if not _e_comentario(linha) and ESTILO_INLINE.search(linha)
    ]
    assert not achados, (
        f"{arquivo.relative_to(PORTAL.parent)} tem estilo inline, que o CSP bloqueia.\n"
        "Use classe em css/app.css, ou el.style.<prop> quando o valor for contínuo:\n  "
        + "\n  ".join(achados)
    )


@pytest.mark.parametrize("pagina", ["index.html", "privacy.html"])
@pytest.mark.parametrize("diretiva", ["script-src", "style-src"])
def test_csp_do_portal_continua_sem_unsafe_inline(pagina, diretiva):
    """Se alguém 'resolver' o bug afrouxando o CSP, os guardas acima viram decorativos."""
    html = (PORTAL / pagina).read_text(encoding="utf-8")
    csp = re.search(r"Content-Security-Policy\"\s+content=\"([^\"]+)\"", html)
    assert csp, f"meta do CSP sumiu de portal/{pagina}"
    alvo = next(d for d in csp.group(1).split(";") if d.strip().startswith(diretiva))
    assert "'unsafe-inline'" not in alvo, f"{pagina}: {diretiva} afrouxado"
    assert "'unsafe-hashes'" not in alvo, f"{pagina}: {diretiva} afrouxado"
