"""O CSS do portal é artefato versionado — precisa bater com a fonte.

O portal deixou de carregar o build de browser do Tailwind (que gerava as
regras em runtime, lendo o DOM) e passou a servir `css/tailwind.css`, compilado
pelo CLI e commitado. A troca elimina ~120 KB de JS, mas cria uma classe de bug
nova: alguém adiciona uma classe no HTML/JS, esquece de rodar `npm run build`, e
o elemento sobe sem estilo — em produção, calado.

A verificação forte (recompilar e comparar) mora no CI, que tem Node; ver o job
`portal css` em .github/workflows/tests.yml. Aqui ficam as checagens que rodam
sem Node e pegam os erros mais comuns antes disso.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PORTAL = RAIZ / "portal"
CSS = PORTAL / "css" / "tailwind.css"
CONFIG = PORTAL / "tailwind.config.js"
INDEX = PORTAL / "index.html"


def _css_sem_escapes() -> str:
    """Tailwind escapa `[`, `/`, `:` e `.` no seletor (`.text-\\[10px\\]`).

    Tirar as barras invertidas deixa a busca por nome de classe direta.
    """
    return CSS.read_text(encoding="utf-8").replace("\\", "")


def test_css_compilado_existe_e_nao_esta_vazio():
    assert CSS.exists(), "portal/css/tailwind.css não existe — rodou `npm run build`?"
    assert CSS.stat().st_size > 5000, "CSS suspeito de estar truncado"


def test_index_carrega_o_css_e_nao_o_build_de_browser():
    html = INDEX.read_text(encoding="utf-8")
    assert 'href="css/tailwind.css"' in html
    assert "vendor/tailwind" not in html, "o build de browser do Tailwind voltou"
    assert "js/tailwind-config.js" not in html, "config do build de browser voltou"


def test_tailwind_vem_antes_do_app_css():
    """app.css precisa vencer as utilitárias em caso de empate de especificidade."""
    html = INDEX.read_text(encoding="utf-8")
    assert html.index('href="css/tailwind.css"') < html.index('href="css/app.css"')


@pytest.mark.parametrize(
    "classe",
    [
        # Tokens do tema — se sumirem, a config não foi lida.
        "bg-surface", "bg-card", "text-muted", "text-faint", "bg-accent",
        # Valores arbitrários: exercitam o escape do seletor.
        "min-h-[100dvh]", "text-[10px]", "text-[11px]",
        # Montadas por variável em JS (`class="${cls}"`). Só entram porque os
        # valores aparecem como string literal na fonte; é o caso que quebra
        # primeiro se alguém trocar por concatenação.
        "bg-amber-500/10", "text-amber-500", "bg-indigo-500/10", "text-red-400",
        # Variante em elemento gerado por JS.
        "hover:bg-accent-dark",
    ],
)
def test_classe_essencial_esta_no_css(classe):
    assert f".{classe}" in _css_sem_escapes(), (
        f"'{classe}' não saiu no CSS — o scanner do Tailwind não a encontrou. "
        "Ela é montada por concatenação em vez de aparecer literal na fonte?"
    )


def test_nenhuma_classe_montada_por_concatenacao():
    """`'text-' + cor` é invisível para o scanner e some do CSS sem aviso.

    O portal usa `class="${cls}"` com `cls` vindo de ternário de literais, que
    funciona. O que não funciona é remontar o nome da classe por pedaços.
    """
    suspeito = re.compile(
        r"""['"`](?:bg|text|border|ring|from|to|via)-['"`]\s*\+"""  # 'text-' + x
        r"""|['"`](?:bg|text|border|ring)-\$\{"""                    # `text-${x}`
    )
    achados = []
    for arquivo in PORTAL.rglob("*.js"):
        # tailwind.config.js documenta este antipadrão em comentário; a busca é
        # textual e não distingue exemplo de uso. E ele não gera markup.
        if {"node_modules", "vendor"} & set(arquivo.parts) or arquivo == CONFIG:
            continue
        for n, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if suspeito.search(linha):
                achados.append(f"{arquivo.relative_to(RAIZ)}:{n}: {linha.strip()[:100]}")

    assert not achados, (
        "classe montada por concatenação — o Tailwind não vai gerá-la:\n  "
        + "\n  ".join(achados)
    )


def test_config_cobre_os_arquivos_que_tem_classe():
    """`content` sem js/** deixaria quase toda a interface sem estilo.

    O portal monta HTML em template string dentro de js/; varrer só o index.html
    geraria um CSS que parece certo e cobre 10% da tela.
    """
    config = CONFIG.read_text(encoding="utf-8")
    content = re.search(r"content:\s*\[(.*?)\]", config, re.S)
    assert content, "bloco `content` sumiu de tailwind.config.js"
    alvos = content.group(1)
    assert "./index.html" in alvos
    assert "./js/**/*.js" in alvos
