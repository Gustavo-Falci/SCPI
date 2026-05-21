"""Geração de PDF legível para o export LGPD Art. 18."""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _estilos():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="Titulo",
            parent=base["Heading1"],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor("#1a365d"),
        )
    )
    base.add(
        ParagraphStyle(
            name="Secao",
            parent=base["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#2c5282"),
        )
    )
    base.add(
        ParagraphStyle(
            name="Rodape",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
        )
    )
    return base


def _secao_titular(titular: dict, estilos) -> list:
    elementos = [Paragraph("1. Identificação do Titular", estilos["Secao"])]
    linhas = [
        ["Nome", titular.get("nome", "—")],
        ["E-mail", titular.get("email", "—")],
        ["RA", str(titular.get("ra", "—"))],
        ["Turno", titular.get("turno", "—")],
        ["Tipo de usuário", titular.get("tipo_usuario", "—")],
    ]
    t = Table(linhas, colWidths=[5 * cm, 11 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(t)
    return elementos


def _secao_biometria(bio: dict, estilos) -> list:
    elementos = [Paragraph("2. Dados Biométricos", estilos["Secao"])]
    if not bio.get("registrada"):
        elementos.append(
            Paragraph("Nenhuma biometria registrada.", estilos["Normal"])
        )
        return elementos
    angulos = ", ".join(bio.get("angulos_cadastrados", [])) or "—"
    consent = bio.get("consentimento_data") or "—"
    revog = bio.get("revogado_em") or "—"
    linhas = [
        ["Status", "Registrada"],
        ["Ângulos cadastrados", angulos],
        ["Consentimento em", consent],
        ["Revogado em", revog],
    ]
    t = Table(linhas, colWidths=[5 * cm, 11 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elementos.append(t)
    elementos.append(Spacer(1, 6))
    # Embeddings faciais e IDs internos (FaceId, S3 path) ficam fora —
    # são metadados de processamento, não dados pessoais do titular.
    elementos.append(
        Paragraph(
            "<i>Observação: o embedding facial e identificadores internos "
            "(FaceId, S3 path) não são incluídos por se tratarem de metadados "
            "de processamento.</i>",
            estilos["Normal"],
        )
    )
    return elementos


def _secao_presencas(presencas: list, estilos) -> list:
    elementos = [
        Paragraph(
            f"3. Histórico de Presenças ({len(presencas)} registros)",
            estilos["Secao"],
        )
    ]
    if not presencas:
        elementos.append(
            Paragraph("Nenhum registro de presença.", estilos["Normal"])
        )
        return elementos
    cabecalho = [["Turma", "Data", "Hora"]]
    linhas = cabecalho + [
        [p.get("turma", "—"), p.get("data", "—"), p.get("hora_registro", "—")]
        for p in presencas
    ]
    t = Table(linhas, colWidths=[8 * cm, 4 * cm, 4 * cm], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f7fafc")],
                ),
            ]
        )
    )
    elementos.append(t)
    return elementos


def gerar_pdf_dados(dados: dict) -> bytes:
    """Gera relatório PDF LGPD Art. 18 a partir dos dados do titular."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Relatório de Dados Pessoais — SCPI",
        author="Sistema SCPI",
    )
    estilos = _estilos()
    elementos = [
        Paragraph("Relatório de Dados Pessoais", estilos["Titulo"]),
        Paragraph(
            "Documento emitido em atendimento à <b>LGPD Art. 18 §1</b> "
            "(direito de acesso aos dados pessoais).",
            estilos["Normal"],
        ),
        Paragraph(
            f"Gerado em: <b>{dados.get('_gerado_em', '—')}</b> · "
            f"Schema: <b>{dados.get('_schema_version', '—')}</b>",
            estilos["Normal"],
        ),
        Spacer(1, 12),
    ]
    elementos += _secao_titular(dados.get("titular", {}), estilos)
    elementos += _secao_biometria(dados.get("biometria", {}), estilos)
    elementos += _secao_presencas(dados.get("presencas", []), estilos)
    elementos.append(Spacer(1, 24))
    elementos.append(
        Paragraph(
            "Este documento é acompanhado de arquivo JSON estruturado "
            "(<i>dados.json</i>) e manifesto de integridade "
            "(<i>INTEGRIDADE.txt</i>) para verificação independente.",
            estilos["Rodape"],
        )
    )
    doc.build(elementos)
    return buffer.getvalue()
