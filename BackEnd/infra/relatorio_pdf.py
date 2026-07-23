"""Geração dos PDFs de relatório de chamada (Ata, Consolidado, Frequência).

Separado de infra/export_pdf.py de propósito: aquele é o documento legal do
export LGPD, com paleta e estrutura próprias, e não deve mudar junto com o
layout destes relatórios.
"""
import datetime
import io
import zoneinfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.mascaras import mascarar_documento
from core.regras import LIMITE_FREQUENCIA

ACCENT = colors.HexColor("#4B39EF")
HEADER_BG = colors.HexColor("#2D2D3A")
ZEBRA = colors.HexColor("#F7F7FA")
TOTAL_BG = colors.HexColor("#EDEDF5")
BORDA = colors.HexColor("#E5E5EF")
VERDE = colors.HexColor("#15803D")
AMBAR = colors.HexColor("#B45309")
VERMELHO = colors.HexColor("#B91C1C")
CINZA = colors.HexColor("#6B7280")

TZ = zoneinfo.ZoneInfo("America/Sao_Paulo")

MARGEM = 1.8 * cm
LARGURA_UTIL = A4[0] - 2 * MARGEM              # 17,4 cm

_ESTILO_CELULA = ParagraphStyle(
    name="celula", fontName="Helvetica", fontSize=8, leading=9.5
)
_ESTILO_TITULO = ParagraphStyle(
    name="titulo_doc", fontName="Helvetica-Bold", fontSize=15, leading=18
)
_ESTILO_META = ParagraphStyle(
    name="meta", fontName="Helvetica", fontSize=8.5, leading=11, textColor=CINZA
)
_ESTILO_NOTA = ParagraphStyle(
    name="nota", fontName="Helvetica-Oblique", fontSize=7.5, leading=9.5, textColor=CINZA
)


def _txt(valor, padrao="—"):
    """Normaliza qualquer valor vindo do banco para texto imprimível."""
    if valor is None:
        return padrao
    texto = str(valor).strip()
    return texto or padrao


def _escapar_xml(texto):
    """Escapa &, <, > para que reportlab não interprete como markup."""
    return _txt(texto).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _celula(texto):
    """Célula de texto que quebra linha — nomes longos não podem vazar da coluna."""
    return Paragraph(_escapar_xml(texto), _ESTILO_CELULA)


class _NumberedCanvas(pdfcanvas.Canvas):
    """Rodapé com 'Pág. X de Y' — o total só existe depois da última página."""

    rodape_esquerda = "SCPI"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estados = []

    def showPage(self):
        self._estados.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._estados)
        for estado in self._estados:
            self.__dict__.update(estado)
            self._rodape(total)
            super().showPage()
        super().save()

    def _rodape(self, total):
        largura = self._pagesize[0]
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(CINZA)
        self.drawString(MARGEM, 1.1 * cm, self.rodape_esquerda)
        self.drawRightString(
            largura - MARGEM, 1.1 * cm, f"Pág. {self._pageNumber} de {total}"
        )
        self.restoreState()


def _fabrica_canvas(rodape_esquerda):
    return type(
        "_NumberedCanvasDoc", (_NumberedCanvas,), {"rodape_esquerda": rodape_esquerda}
    )


def _moldura(titulo_documento):
    """Faixa de cabeçalho desenhada em toda página."""

    def desenhar(canv, doc):
        largura, altura = doc.pagesize
        canv.saveState()
        canv.setFont("Helvetica-Bold", 15)
        canv.setFillColor(ACCENT)
        canv.drawString(MARGEM, altura - 1.35 * cm, "SCPI")
        canv.setFont("Helvetica", 9)
        canv.setFillColor(CINZA)
        canv.drawRightString(largura - MARGEM, altura - 1.3 * cm, titulo_documento)
        canv.setStrokeColor(ACCENT)
        canv.setLineWidth(2)
        canv.line(MARGEM, altura - 1.6 * cm, largura - MARGEM, altura - 1.6 * cm)
        canv.restoreState()

    return desenhar


def _agora_str():
    return datetime.datetime.now(tz=TZ).strftime("%d/%m/%Y %H:%M")


def _documento(titulo, rodape_esquerda, elementos):
    """Monta o PDF e devolve os bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=2.4 * cm,
        bottomMargin=1.8 * cm,
        title=titulo,
        author="Sistema SCPI",
    )
    moldura = _moldura(titulo)
    doc.build(
        elementos,
        onFirstPage=moldura,
        onLaterPages=moldura,
        canvasmaker=_fabrica_canvas(rodape_esquerda),
    )
    return buffer.getvalue()


def _bloco_identificacao(titulo, chip, linhas_meta):
    """Título do documento + chip opcional (turno) + linhas de metadado."""
    titulo_escapado = _escapar_xml(titulo)
    chip_escapado = _escapar_xml(chip) if chip else ""
    cinza_hex = CINZA.hexval()
    cabecalho = (
        titulo_escapado
        if not chip_escapado
        else f"{titulo_escapado}  <font size=8 color='{cinza_hex}'>[{chip_escapado}]</font>"
    )
    elementos = [Paragraph(cabecalho, _ESTILO_TITULO)]
    for linha in linhas_meta:
        elementos.append(Paragraph(_escapar_xml(linha), _ESTILO_META))
    elementos.append(Spacer(1, 10))
    return elementos


def _kpis(itens):
    """itens: lista de (label, valor, cor_ou_None). Faixa de números grandes."""
    valores = [_txt(v) for _, v, _ in itens]
    labels = [l.upper() for l, _, _ in itens]
    largura_col = LARGURA_UTIL / len(itens)
    t = Table([valores, labels], colWidths=[largura_col] * len(itens))
    estilo = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 15),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 6.5),
        ("TEXTCOLOR", (0, 1), (-1, 1), CINZA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDA),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, BORDA),
    ]
    for i, (_, _, cor) in enumerate(itens):
        if cor is not None:
            estilo.append(("TEXTCOLOR", (i, 0), (i, 0), cor))
    t.setStyle(TableStyle(estilo))
    return t


def _tabela(cabecalho, linhas, col_widths, estilos_extra=None):
    """Tabela padrão: header escuro repetido a cada página, zebra clara."""
    t = Table([cabecalho] + linhas, colWidths=col_widths, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, BORDA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    t.setStyle(TableStyle(estilo + list(estilos_extra or [])))
    return t


def _status_aluno(presentes, total_aulas):
    """(rótulo, cor) do aluno na chamada."""
    if presentes <= 0:
        return "Ausente", VERMELHO
    if total_aulas and presentes >= total_aulas:
        return "Presente", VERDE
    return "Parcial", AMBAR


def gerar_pdf_ata_chamada(detalhe: dict) -> bytes:
    """Ata de Presença de uma chamada — retorno de services.relatorios.detalhe_relatorio."""
    alunos = detalhe.get("alunos") or []
    total_aulas = detalhe.get("total_aulas") or 0
    percentual = detalhe.get("percentual") or 0

    presentes_count = sum(
        1 for a in alunos if total_aulas and a.get("aulas_presentes_count", 0) >= total_aulas
    )
    ausentes_count = sum(1 for a in alunos if a.get("aulas_presentes_count", 0) == 0)
    parciais_count = len(alunos) - presentes_count - ausentes_count

    elementos = _bloco_identificacao(
        _txt(detalhe.get("nome_disciplina")),
        _txt(detalhe.get("turno"), padrao=""),
        [
            f"Prof. {_txt(detalhe.get('professor_nome'))} · "
            f"{_txt(detalhe.get('codigo_turma'))} · "
            f"Semestre {_txt(detalhe.get('semestre'))}",
            f"{_txt(detalhe.get('data_chamada'))} · "
            f"{_txt(detalhe.get('horario_inicio'))}–{_txt(detalhe.get('horario_fim'))} · "
            f"{total_aulas} aula(s)",
        ],
    )

    elementos.append(
        _kpis(
            [
                ("Alunos", detalhe.get("total_alunos", len(alunos)), None),
                ("Presentes", presentes_count, VERDE),
                ("Ausentes", ausentes_count, VERMELHO),
                ("Parciais", parciais_count, AMBAR),
                ("Frequência", f"{percentual}%", VERDE if percentual >= LIMITE_FREQUENCIA else VERMELHO),
            ]
        )
    )
    elementos.append(Spacer(1, 14))

    linhas, estilos_extra = [], []
    for i, a in enumerate(alunos, start=1):
        presentes = a.get("aulas_presentes_count", 0)
        rotulo, cor = _status_aluno(presentes, total_aulas)
        estilos_extra.append(("TEXTCOLOR", (4, i), (4, i), cor))
        estilos_extra.append(("FONTNAME", (4, i), (4, i), "Helvetica-Bold"))
        linhas.append(
            [
                _celula(a.get("nome")),
                _celula(mascarar_documento(a.get("ra"))),
                f"{presentes}/{total_aulas}",
                _txt(a.get("tipo_registro")),
                rotulo,
            ]
        )

    if linhas:
        estilos_extra.append(("ALIGN", (2, 0), (2, -1), "CENTER"))
        elementos.append(
            _tabela(
                ["ALUNO", "RA", "AULAS", "TIPO", "STATUS"],
                linhas,
                [7.0 * cm, 3.6 * cm, 1.8 * cm, 2.6 * cm, 2.4 * cm],
                estilos_extra,
            )
        )
    else:
        elementos.append(Paragraph("Nenhum aluno matriculado nesta turma.", _ESTILO_META))

    elementos.append(Spacer(1, 26))
    elementos.append(
        KeepTogether(
            _tabela(
                ["", ""],
                [["___________________________________", "___________________________________"],
                 ["Assinatura do Professor", "Coordenação"]],
                [8.7 * cm, 8.7 * cm],
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white]),
                    ("LINEBELOW", (0, 0), (-1, -1), 0, colors.white),
                    ("TEXTCOLOR", (0, 0), (-1, -1), CINZA),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ],
            )
        )
    )

    return _documento(
        "Ata de Presença",
        f"SCPI · emitido {_agora_str()}",
        elementos,
    )


def _linha_de_filtros(filtros: dict) -> str:
    """Escreve o recorte do documento por extenso — sem isso o PDF não se explica."""
    inicio, fim = filtros.get("data_inicio"), filtros.get("data_fim")
    if inicio and fim:
        periodo = f"{inicio} a {fim}"
    elif inicio:
        periodo = f"a partir de {inicio}"
    elif fim:
        periodo = f"até {fim}"
    else:
        periodo = "todo o histórico"
    return (
        f"Período: {periodo} · "
        f"Turno: {_txt(filtros.get('turno'), 'todos')} · "
        f"Semestre: {_txt(filtros.get('semestre'), 'todos')} · "
        f"Turma: {_txt(filtros.get('turma'), 'todas')}"
    )


def gerar_pdf_consolidado(itens: list, filtros: dict) -> bytes:
    """Consolidado das chamadas de um período — retorno de services.relatorios.listar_relatorios."""
    total_chamadas = len(itens)
    total_aulas = sum(i.get("total_aulas") or 0 for i in itens)
    slots = sum((i.get("total_alunos") or 0) * (i.get("total_aulas") or 0) for i in itens)
    presencas = sum(i.get("presentes") or 0 for i in itens)
    # Média ponderada pelo tamanho da turma, não média das percentagens.
    freq_media = round(presencas / slots * 100) if slots else 0

    elementos = _bloco_identificacao(
        "Consolidado de Chamadas",
        None,
        [_linha_de_filtros(filtros or {})],
    )
    elementos.append(
        _kpis(
            [
                ("Chamadas", total_chamadas, None),
                ("Aulas", total_aulas, None),
                ("Presenças", presencas, VERDE),
                ("Frequência média", f"{freq_media}%",
                 CINZA if slots == 0
                 else (VERDE if freq_media >= LIMITE_FREQUENCIA else VERMELHO)),
            ]
        )
    )
    elementos.append(Spacer(1, 14))

    linhas, estilos_extra = [], []
    for i, item in enumerate(itens, start=1):
        percentual = item.get("percentual") or 0
        estilos_extra.append(
            (
                "TEXTCOLOR", (8, i), (8, i),
                VERDE if percentual >= LIMITE_FREQUENCIA else VERMELHO,
            )
        )
        linhas.append(
            [
                _txt(item.get("data_chamada")),
                _celula(item.get("nome_disciplina")),
                _celula(item.get("codigo_turma")),
                _celula(item.get("professor_nome")),
                _txt(item.get("total_alunos"), "0"),
                _txt(item.get("presentes_alunos"), "0"),
                _txt(item.get("ausentes_alunos"), "0"),
                _txt(item.get("parciais_alunos"), "0"),
                f"{percentual}%",
            ]
        )

    if linhas:
        indice_total = len(linhas) + 1
        linhas.append(
            ["TOTAL", f"{total_chamadas} chamada(s)", "", "", "", "", "", "", f"{freq_media}%"]
        )
        estilos_extra += [
            ("ALIGN", (4, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, indice_total), (-1, indice_total), TOTAL_BG),
            ("FONTNAME", (0, indice_total), (-1, indice_total), "Helvetica-Bold"),
        ]
        elementos.append(
            _tabela(
                ["DATA", "DISCIPLINA", "TURMA", "PROFESSOR", "ALUNOS", "P", "A", "PARC", "FREQ"],
                linhas,
                [2.0 * cm, 3.9 * cm, 2.3 * cm, 3.4 * cm, 1.4 * cm,
                 1.0 * cm, 1.0 * cm, 1.2 * cm, 1.2 * cm],
                estilos_extra,
            )
        )
    else:
        elementos.append(
            Paragraph("Nenhuma chamada encontrada para este recorte.", _ESTILO_META)
        )

    return _documento(
        "Consolidado de Chamadas",
        f"SCPI · emitido {_agora_str()}",
        elementos,
    )


def _periodo_por_extenso(periodo: dict) -> str:
    """Datas ISO do endpoint viradas em texto pt-BR."""
    def br(iso):
        if not iso:
            return None
        texto = str(iso)[:10]
        try:
            return datetime.datetime.strptime(texto, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return texto

    inicio, fim = br(periodo.get("data_inicio")), br(periodo.get("data_fim"))
    if inicio and fim:
        return f"{inicio} a {fim}"
    if inicio:
        return f"a partir de {inicio}"
    if fim:
        return f"até {fim}"
    return "todo o histórico da turma"


def gerar_pdf_frequencia(dados: dict) -> bytes:
    """Frequência por aluno de uma turma — retorno de services.relatorios.frequencia_turma."""
    turma = dados.get("turma") or {}
    totais = dados.get("totais") or {}
    alunos = dados.get("alunos") or []
    percentual_turma = totais.get("percentual") or 0

    elementos = _bloco_identificacao(
        _txt(turma.get("nome_disciplina")),
        _txt(turma.get("turno"), padrao=""),
        [
            f"Prof. {_txt(turma.get('professor_nome'))} · "
            f"{_txt(turma.get('codigo_turma'))} · "
            f"Semestre {_txt(turma.get('semestre'))}",
            f"Período: {_periodo_por_extenso(dados.get('periodo') or {})} · "
            f"{_txt(totais.get('chamadas'), '0')} chamada(s) · "
            f"{_txt(totais.get('aulas_dadas'), '0')} aula(s) dada(s)",
        ],
    )

    em_risco = sum(1 for a in alunos if a.get("situacao") == "Risco")
    elementos.append(
        _kpis(
            [
                ("Alunos", totais.get("total_alunos", len(alunos)), None),
                ("Regulares", len(alunos) - em_risco, VERDE),
                ("Em risco", em_risco, VERMELHO),
                ("Frequência da turma", f"{percentual_turma}%",
                 VERDE if percentual_turma >= LIMITE_FREQUENCIA else VERMELHO),
            ]
        )
    )
    elementos.append(Spacer(1, 14))

    linhas, estilos_extra = [], []
    for i, a in enumerate(alunos, start=1):
        percentual = a.get("percentual") or 0
        cor = VERDE if percentual >= LIMITE_FREQUENCIA else VERMELHO
        estilos_extra.append(("TEXTCOLOR", (4, i), (5, i), cor))
        estilos_extra.append(("FONTNAME", (5, i), (5, i), "Helvetica-Bold"))
        linhas.append(
            [
                _celula(a.get("nome")),
                _celula(mascarar_documento(a.get("ra"))),
                _txt(a.get("aulas_presentes"), "0"),
                _txt(a.get("aulas_dadas"), "0"),
                f"{percentual}%",
                _txt(a.get("situacao")),
            ]
        )

    if linhas:
        estilos_extra.append(("ALIGN", (2, 0), (-1, -1), "CENTER"))
        elementos.append(
            _tabela(
                ["ALUNO", "RA", "ASSISTIDAS", "DADAS", "FREQ", "SITUAÇÃO"],
                linhas,
                [6.0 * cm, 3.4 * cm, 2.2 * cm, 1.8 * cm, 1.6 * cm, 2.4 * cm],
                estilos_extra,
            )
        )
    else:
        elementos.append(
            Paragraph("Nenhum aluno matriculado nesta turma.", _ESTILO_META)
        )

    elementos.append(Spacer(1, 12))
    elementos.append(
        Paragraph(
            f"Critério: considera-se em situação regular o aluno com frequência igual "
            f"ou superior a {LIMITE_FREQUENCIA}% das aulas dadas no período acima.",
            _ESTILO_NOTA,
        )
    )

    return _documento(
        "Frequência por Aluno",
        f"SCPI · emitido {_agora_str()}",
        elementos,
    )
