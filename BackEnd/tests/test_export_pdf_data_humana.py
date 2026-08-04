"""O PDF do export LGPD mostra data legível, não ISO 8601.

Antes das colunas virarem TIMESTAMPTZ o PDF imprimia `2026-08-04T12:00:00`.
Depois passaria a imprimir `2026-08-04T12:00:00-03:00` — pior ainda num
documento que responde a pedido de titular sob o Art. 18.

O JSON do mesmo export continua em ISO de propósito: lá o consumidor é máquina.
"""
import pytest

from infra.export_pdf import _data_humana


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        # Com offset — o formato que as colunas passam a produzir.
        ("2026-08-04T12:00:00-03:00", "04/08/2026 12:00"),
        ("2026-08-04T12:00:00+00:00", "04/08/2026 12:00"),
        # Naive — o formato antigo, que ainda pode vir de dado já exportado.
        ("2026-08-04T12:00:00", "04/08/2026 12:00"),
        ("2026-08-04T12:00:00.123456", "04/08/2026 12:00"),
    ],
)
def test_formata_iso_para_leitura_humana(entrada, esperado):
    assert _data_humana(entrada) == esperado


def test_nao_converte_o_horario_entre_fusos():
    """12:00-03:00 tem de sair 12:00, não 15:00.

    O titular espera ver a hora em que o evento aconteceu para ele, que é o que
    o offset já carrega. Normalizar para UTC aqui mudaria a hora exibida.
    """
    assert _data_humana("2026-08-04T12:00:00-03:00").endswith("12:00")


@pytest.mark.parametrize("vazio", [None, "", 0])
def test_ausencia_vira_travessao(vazio):
    assert _data_humana(vazio) == "—"


def test_valor_impresteavel_passa_direto_em_vez_de_quebrar():
    """PDF de export não pode falhar por causa de um campo mal formatado."""
    assert _data_humana("nao é data") == "nao é data"
