import docx
import pytest

from gerar_manuais import (
    Callout,
    Codigo,
    ErroDeFonte,
    Lista,
    Manual,
    Paragrafo,
    Tabela,
    Titulo,
    gerar_docx,
    partir_inline,
    parse,
    nome_saida,
    numerar,
    validar,
)

FONTE_MINIMA = """---
titulo: Manual de Teste
subtitulo: Subtítulo do manual
versao: "1.0"
data: 2026-08-18
---

## Introdução

Primeiro parágrafo.

### Uma seção

Segundo parágrafo.
"""


def test_front_matter_vira_meta():
    manual = parse(FONTE_MINIMA)
    assert manual.meta["titulo"] == "Manual de Teste"
    assert manual.meta["subtitulo"] == "Subtítulo do manual"
    assert manual.meta["versao"] == "1.0"
    assert manual.meta["data"] == "2026-08-18"


def test_titulos_viram_blocos_com_nivel():
    blocos = parse(FONTE_MINIMA).blocos
    titulos = [b for b in blocos if isinstance(b, Titulo)]
    assert [(t.nivel, t.texto) for t in titulos] == [
        (1, "Introdução"),
        (2, "Uma seção"),
    ]


def test_paragrafos_preservam_ordem():
    blocos = parse(FONTE_MINIMA).blocos
    paragrafos = [b.texto for b in blocos if isinstance(b, Paragrafo)]
    assert paragrafos == ["Primeiro parágrafo.", "Segundo parágrafo."]


def test_linhas_seguidas_viram_um_paragrafo_so():
    fonte = FONTE_MINIMA.replace("Primeiro parágrafo.", "Uma linha\ne a continuação dela")
    paragrafos = [b.texto for b in parse(fonte).blocos if isinstance(b, Paragrafo)]
    assert paragrafos[0] == "Uma linha e a continuação dela"


def test_fonte_sem_front_matter_falha():
    with pytest.raises(ErroDeFonte, match="front-matter"):
        parse("## Introdução\n\nTexto.\n")


def test_front_matter_incompleto_falha():
    fonte = FONTE_MINIMA.replace('versao: "1.0"\n', "")
    with pytest.raises(ErroDeFonte, match="versao"):
        parse(fonte)


CABECALHO = """---
titulo: T
subtitulo: S
versao: "1.0"
data: 2026-08-18
---

"""


def test_tabela_com_cabecalho_e_linhas():
    fonte = CABECALHO + (
        "| Peça | Onde fica |\n"
        "|---|---|\n"
        "| scpi-api | systemd |\n"
        "| nginx | /etc/nginx |\n"
    )
    tabela = [b for b in parse(fonte).blocos if isinstance(b, Tabela)][0]
    assert tabela.cabecalho == ["Peça", "Onde fica"]
    assert tabela.linhas == [["scpi-api", "systemd"], ["nginx", "/etc/nginx"]]


def test_tabela_com_numero_de_colunas_errado_falha():
    fonte = CABECALHO + "| A | B |\n|---|---|\n| só uma |\n"
    with pytest.raises(ErroDeFonte, match="colunas"):
        parse(fonte)


def test_tabela_com_separador_espacado():
    fonte = CABECALHO + (
        "| Peça | Onde fica |\n"
        "| --- | --- |\n"
        "| scpi-api | systemd |\n"
        "| nginx | /etc/nginx |\n"
    )
    tabela = [b for b in parse(fonte).blocos if isinstance(b, Tabela)][0]
    assert tabela.cabecalho == ["Peça", "Onde fica"]
    assert tabela.linhas == [["scpi-api", "systemd"], ["nginx", "/etc/nginx"]]


def test_tabela_com_separador_alinhamento():
    fonte = CABECALHO + (
        "| Esquerda | Centro | Direita |\n"
        "| :--- | :---: | ---: |\n"
        "| A | B | C |\n"
    )
    tabela = [b for b in parse(fonte).blocos if isinstance(b, Tabela)][0]
    assert tabela.cabecalho == ["Esquerda", "Centro", "Direita"]
    assert tabela.linhas == [["A", "B", "C"]]


def test_linha_com_pipe_mas_separador_invalido_vira_paragrafo():
    fonte = CABECALHO + "| abc | def |\n| xyz | uvw |\n"
    blocos = parse(fonte).blocos
    assert len(blocos) == 1
    assert isinstance(blocos[0], Paragrafo)
    assert "| abc | def |" in blocos[0].texto


def test_bloco_de_codigo_preserva_linhas_e_linguagem():
    fonte = CABECALHO + "```bash\ncd /opt/scpi\ngit pull\n```\n"
    codigo = [b for b in parse(fonte).blocos if isinstance(b, Codigo)][0]
    assert codigo.linguagem == "bash"
    assert codigo.linhas == ["cd /opt/scpi", "git pull"]


def test_codigo_nao_vira_paragrafo():
    fonte = CABECALHO + "```\n## isto nao e titulo\n```\n"
    assert not [b for b in parse(fonte).blocos if isinstance(b, Titulo)]


def test_bloco_de_codigo_sem_fechamento_falha():
    fonte = CABECALHO + "```bash\ncd /opt/scpi\n"
    with pytest.raises(ErroDeFonte, match="não fechado"):
        parse(fonte)


def test_callout_reconhece_rotulo():
    fonte = CABECALHO + "> **Pegadinha:** o plano gratuito usa HEAD.\n"
    callout = [b for b in parse(fonte).blocos if isinstance(b, Callout)][0]
    assert callout.rotulo == "Pegadinha"
    assert callout.texto == "o plano gratuito usa HEAD."


def test_citacao_sem_rotulo_conhecido_vira_callout_sem_rotulo():
    fonte = CABECALHO + "> texto solto de citação.\n"
    callout = [b for b in parse(fonte).blocos if isinstance(b, Callout)][0]
    assert callout.rotulo == ""
    assert callout.texto == "texto solto de citação."


def test_listas_marcada_e_numerada():
    fonte = CABECALHO + "- primeiro\n- segundo\n\n1. um\n2. dois\n"
    listas = [b for b in parse(fonte).blocos if isinstance(b, Lista)]
    assert listas[0].ordenada is False and listas[0].itens == ["primeiro", "segundo"]
    assert listas[1].ordenada is True and listas[1].itens == ["um", "dois"]


def test_partir_inline_separa_negrito_e_codigo():
    assert partir_inline("use **git pull** no `/opt/scpi` agora") == [
        ("normal", "use "),
        ("negrito", "git pull"),
        ("normal", " no "),
        ("codigo", "/opt/scpi"),
        ("normal", " agora"),
    ]


def test_partir_inline_sem_marcacao():
    assert partir_inline("texto simples") == [("normal", "texto simples")]


def test_numeracao_hierarquica():
    blocos = [
        Titulo(1, "Introdução"),
        Titulo(2, "Visão geral"),
        Titulo(1, "Backup"),
        Titulo(2, "Peças"),
        Titulo(3, "Na VM"),
        Titulo(2, "Comandos"),
    ]
    assert [t.numero for t in numerar(blocos)] == ["1", "1.1", "2", "2.1", "2.1.1", "2.2"]


def test_numeracao_ignora_blocos_que_nao_sao_titulo():
    blocos = [Titulo(1, "A"), Paragrafo("texto"), Titulo(1, "B")]
    assert [b.numero for b in numerar(blocos) if isinstance(b, Titulo)] == ["1", "2"]


def test_validar_avisa_sobre_confirmar_pendente():
    manual = Manual(meta={}, blocos=[Paragrafo("O OCID é ⚠️ CONFIRMAR com o Gustavo.")])
    avisos = validar(manual, fontes_conhecidas=set())
    assert any("CONFIRMAR" in a for a in avisos)


def test_validar_aceita_referencia_para_manual_existente():
    manual = Manual(meta={}, blocos=[Paragrafo("Ver 07-banco-de-dados.md, seção Migrations.")])
    assert validar(manual, fontes_conhecidas={"07-banco-de-dados.md"}) == []


def test_validar_falha_em_referencia_para_manual_inexistente():
    manual = Manual(meta={}, blocos=[Paragrafo("Ver 99-inexistente.md para detalhes.")])
    with pytest.raises(ErroDeFonte, match="99-inexistente.md"):
        validar(manual, fontes_conhecidas={"07-banco-de-dados.md"})


def test_nome_de_saida_derivado_da_fonte():
    assert nome_saida("01-ambiente-dev.md") == "SCPI-Manual-Ambiente-Dev.docx"
    assert nome_saida("11-fluxo-ci.md") == "SCPI-Manual-Fluxo-Ci.docx"


def test_numeracao_falha_ao_pular_nivel():
    blocos = [Titulo(1, "A"), Titulo(3, "B")]
    with pytest.raises(ErroDeFonte, match="B"):
        numerar(blocos)


def test_numeracao_falha_ao_comcar_em_nivel_2():
    blocos = [Titulo(2, "X")]
    with pytest.raises(ErroDeFonte):
        numerar(blocos)


def test_gerar_docx_produz_arquivo_legivel(tmp_path):
    fonte = CABECALHO + (
        "## Introdução\n\nTexto de abertura.\n\n"
        "### Peças\n\n"
        "| Peça | Função |\n|---|---|\n| scpi-api | serve a API |\n\n"
        "> **Importante:** não remover o HEAD da rota.\n\n"
        "```bash\nsystemctl status scpi-api\n```\n"
    )
    manual = parse(fonte)
    numerar(manual.blocos)
    destino = tmp_path / "saida.docx"
    gerar_docx(manual, destino)

    assert destino.exists()
    documento = docx.Document(str(destino))
    textos = [p.text for p in documento.paragraphs]
    assert "T" in textos[0]
    assert "1 Introdução" in textos
    assert "1.1 Peças" in textos
    assert any("Importante" in t for t in textos)
    assert any("systemctl status scpi-api" in t for t in textos)
    assert len(documento.tables) == 1
    assert documento.tables[0].cell(0, 0).text == "Peça"


def test_estilos_de_titulo_sao_heading_do_word(tmp_path):
    manual = parse(CABECALHO + "## Um\n\ntexto\n\n### Dois\n\ntexto\n")
    numerar(manual.blocos)
    destino = tmp_path / "s.docx"
    gerar_docx(manual, destino)
    estilos = {p.text: p.style.name for p in docx.Document(str(destino)).paragraphs}
    assert estilos["1 Um"] == "Heading 1"
    assert estilos["1.1 Dois"] == "Heading 2"
