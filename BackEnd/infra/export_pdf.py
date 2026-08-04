"""Geração de PDF legível para o export LGPD Art. 18."""
import io
from datetime import datetime

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


def _data_humana(valor) -> str:
    """ISO 8601 → `dd/mm/aaaa HH:MM`. Devolve o original se não parsear.

    O JSON do export mantém ISO (é o formato de máquina); só o PDF, que é o
    documento que o titular lê, ganha a versão legível.

    Ficou necessário quando as colunas viraram TIMESTAMPTZ: antes o
    `.isoformat()` produzia `2026-08-04T12:00:00`, agora sai
    `2026-08-04T12:00:00-03:00`. Nenhum dos dois é aceitável num documento de
    resposta a titular, e o segundo é pior.
    """
    if not valor:
        return "—"
    try:
        return datetime.fromisoformat(str(valor)).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(valor)


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
    consent = _data_humana(bio.get("consentimento_data"))
    revog = _data_humana(bio.get("revogado_em"))
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


def _secao_consentimentos(trilha: list, estilos) -> list:
    elementos = [
        Paragraph(
            f"4. Histórico de Consentimento ({len(trilha)} eventos)",
            estilos["Secao"],
        )
    ]
    if not trilha:
        elementos.append(
            Paragraph("Nenhum evento de consentimento registrado.", estilos["Normal"])
        )
        return elementos
    cabecalho = [["Evento", "Versão da política", "Data", "IP", "Origem"]]
    linhas = cabecalho + [
        [
            "Aceite" if c.get("evento") == "aceite" else "Revogação",
            c.get("politica_versao", "—"),
            _data_humana(c.get("registrado_em")),
            c.get("ip") or "—",
            c.get("origem", "—"),
        ]
        for c in trilha
    ]
    t = Table(linhas, colWidths=[3 * cm, 3.5 * cm, 4.5 * cm, 3 * cm, 2 * cm], repeatRows=1)
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
    elementos.append(Spacer(1, 6))
    elementos.append(
        Paragraph(
            "<i>Versão \"legado\" indica consentimento anterior ao versionamento "
            "da política de privacidade.</i>",
            estilos["Normal"],
        )
    )
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
    elementos += _secao_consentimentos(dados.get("consentimentos", []), estilos)
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
