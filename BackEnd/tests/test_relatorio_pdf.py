"""Testes do gerador de PDF dos relatórios de chamada."""
import base64
import datetime
import re
import zlib

from infra.relatorio_pdf import gerar_pdf_ata_chamada


def _textos_desenhados(pdf: bytes) -> str:
    """Extrai os strings efetivamente desenhados no PDF (operadores Tj)."""
    saida = []
    for bruto in re.findall(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        try:
            dados = zlib.decompress(base64.a85decode(bruto.strip(), adobe=True))
        except Exception:
            continue
        for trecho in re.findall(rb"\((?:\\.|[^\\()])*\)\s*Tj", dados):
            saida.append(trecho.decode("latin-1", "replace"))
    return "\n".join(saida)


def _aluno(nome, ra, presentes, total=2, tipo="Reconhecimento"):
    return {
        "aluno_id": f"id-{ra}",
        "nome": nome,
        "ra": ra,
        "total_aulas": total,
        "aulas_presentes_count": presentes,
        "presente": presentes > 0,
        "tipo_registro": tipo if presentes > 0 else "—",
    }


DETALHE = {
    "chamada_id": "c1",
    "turma_id": "t1",
    "nome_disciplina": "Cálculo I",
    "codigo_turma": "TURMA-3B",
    "semestre": "2026.1",
    "turno": "Noturno",
    "professor_nome": "Ana Souza",
    "data_chamada": "12/03/2026",
    "horario_inicio": "19:00",
    "horario_fim": "20:40",
    "total_aulas": 2,
    "total_alunos": 3,
    "presentes": 3,
    "ausentes": 3,
    "percentual": 50,
    "alunos": [
        _aluno("Ana Beatriz Lima", "529.982.247-25", 2),
        _aluno("Bruno Carvalho", "2023001234", 1, tipo="Manual"),
        _aluno("Carla Dias", "2023005678", 0),
    ],
}


def test_ata_retorna_pdf_valido():
    pdf = gerar_pdf_ata_chamada(DETALHE)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_ata_sem_alunos_nao_estoura():
    pdf = gerar_pdf_ata_chamada({**DETALHE, "alunos": [], "total_alunos": 0, "percentual": 0})
    assert pdf.startswith(b"%PDF-")


def test_ata_com_acentuacao_nao_estoura():
    detalhe = {
        **DETALHE,
        "nome_disciplina": "Introdução à Computação",
        "professor_nome": "João Conceição",
        "alunos": [_aluno("Íris D'Ávila Gonçalves", "2023009999", 2)],
    }
    pdf = gerar_pdf_ata_chamada(detalhe)
    assert pdf.startswith(b"%PDF-")


def _paginas(pdf: bytes) -> int:
    """Lê /Count do catálogo de páginas — reportlab não comprime por padrão."""
    m = re.search(rb"/Count (\d+)", pdf)
    assert m, "não achei /Count no PDF"
    return int(m.group(1))


def test_ata_com_60_alunos_gera_mais_de_uma_pagina():
    alunos = [_aluno(f"Aluno Numero {i:02d}", f"20230000{i:02d}", i % 3) for i in range(60)]
    pdf = gerar_pdf_ata_chamada({**DETALHE, "alunos": alunos, "total_alunos": 60})
    # Exercita repeatRows (header repetido) e o NumberedCanvas (total de páginas).
    assert _paginas(pdf) > 1
    assert pdf.startswith(b"%PDF-")


def test_ata_com_campos_ausentes_usa_travessao():
    minimo = {"alunos": [], "total_aulas": 0, "total_alunos": 0, "percentual": 0}
    pdf = gerar_pdf_ata_chamada(minimo)
    assert pdf.startswith(b"%PDF-")


def test_ata_com_xml_chars_em_nome_disciplina_e_professor():
    """Regressão para escapar < > & em título, chip e metadados (Finding 1)."""
    detalhe = {
        **DETALHE,
        "nome_disciplina": "Algoritmos <Avançado>",
        "professor_nome": "Ana <Souza",
        "turno": "Noturno & Diurno",
    }
    pdf = gerar_pdf_ata_chamada(detalhe)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")


def test_ata_mascara_cpf_no_texto_desenhado():
    """Garantia de privacidade: um CPF válido nunca aparece em claro no PDF da ata."""
    pdf = gerar_pdf_ata_chamada(DETALHE)
    texto = _textos_desenhados(pdf)
    assert texto, "extração de texto do PDF não retornou nada — recipe falhou em silêncio"
    assert "***.982.247-**" in texto
    assert "529.982.247-25" not in texto
    assert "52998224725" not in texto


from infra.relatorio_pdf import gerar_pdf_consolidado


def _chamada(i, presentes_alunos=20, ausentes=3, parciais=2, total_alunos=25):
    return {
        "chamada_id": f"c{i}",
        "nome_disciplina": "Cálculo I",
        "codigo_turma": "TURMA-3B",
        "semestre": "2026.1",
        "turno": "Noturno",
        "professor_nome": "Ana Souza",
        "data_chamada": f"{(i % 28) + 1:02d}/03/2026",
        "horario_inicio": "19:00",
        "horario_fim": "20:40",
        "total_aulas": 2,
        "total_alunos": total_alunos,
        "presentes": presentes_alunos * 2,
        "presentes_alunos": presentes_alunos,
        "ausentes_alunos": ausentes,
        "parciais_alunos": parciais,
        "ausentes": total_alunos * 2 - presentes_alunos * 2,
        "percentual": 80,
    }


FILTROS = {
    "data_inicio": "01/03/2026",
    "data_fim": "22/07/2026",
    "turno": "Noturno",
    "semestre": "2026.1",
    "turma": None,
}


def test_consolidado_retorna_pdf_valido():
    pdf = gerar_pdf_consolidado([_chamada(i) for i in range(5)], FILTROS)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_consolidado_sem_chamadas_nao_estoura():
    pdf = gerar_pdf_consolidado([], FILTROS)
    assert pdf.startswith(b"%PDF-")


def test_consolidado_sem_filtros_nao_estoura():
    pdf = gerar_pdf_consolidado([_chamada(1)], {})
    assert pdf.startswith(b"%PDF-")


def test_consolidado_longo_gera_mais_de_uma_pagina():
    pdf = gerar_pdf_consolidado([_chamada(i) for i in range(70)], FILTROS)
    assert _paginas(pdf) > 1


def test_consolidado_sem_chamadas_frequencia_usa_cinza_nao_vermelho():
    # Finding 2: sem chamadas no recorte, freq_media cai para 0 por divisão por
    # zero — isso não é "ninguém compareceu", é "sem dado". Não pode pintar de
    # vermelho como se fosse uma frequência real ruim.
    from unittest.mock import patch

    from infra import relatorio_pdf

    with patch.object(relatorio_pdf, "_kpis", wraps=relatorio_pdf._kpis) as m:
        relatorio_pdf.gerar_pdf_consolidado([], FILTROS)
    itens_kpi = m.call_args.args[0]
    freq = next(i for i in itens_kpi if i[0] == "Frequência média")
    assert freq[2] == relatorio_pdf.CINZA


def test_consolidado_com_chamadas_mantem_verde_ou_vermelho():
    # Com dado real, a cor continua refletindo o limiar — não deve virar cinza.
    from unittest.mock import patch

    from infra import relatorio_pdf

    baixa = _chamada(1, presentes_alunos=1, ausentes=24, parciais=0, total_alunos=25)
    with patch.object(relatorio_pdf, "_kpis", wraps=relatorio_pdf._kpis) as m:
        relatorio_pdf.gerar_pdf_consolidado([baixa], FILTROS)
    itens_kpi = m.call_args.args[0]
    freq = next(i for i in itens_kpi if i[0] == "Frequência média")
    assert freq[2] == relatorio_pdf.VERMELHO


from infra.relatorio_pdf import gerar_pdf_frequencia

FREQUENCIA = {
    "turma": {
        "turma_id": "t1",
        "nome_disciplina": "Cálculo I",
        "codigo_turma": "TURMA-3B",
        "turno": "Noturno",
        "semestre": "2026.1",
        "professor_nome": "Ana Souza",
    },
    "periodo": {"data_inicio": "2026-03-01", "data_fim": "2026-07-22"},
    "totais": {"total_alunos": 3, "chamadas": 5, "aulas_dadas": 10,
               "presencas": 13, "percentual": 43},
    "alunos": [
        {"aluno_id": "a3", "nome": "Carla Dias", "ra": "529.982.247-25",
         "aulas_presentes": 0, "aulas_dadas": 10, "chamadas_count": 5,
         "percentual": 0, "situacao": "Risco"},
        {"aluno_id": "a2", "nome": "Bruno Carvalho", "ra": "2023001234",
         "aulas_presentes": 5, "aulas_dadas": 10, "chamadas_count": 5,
         "percentual": 50, "situacao": "Risco"},
        {"aluno_id": "a1", "nome": "Ana Beatriz Lima", "ra": "2023005678",
         "aulas_presentes": 8, "aulas_dadas": 10, "chamadas_count": 5,
         "percentual": 80, "situacao": "Regular"},
    ],
}


def test_frequencia_retorna_pdf_valido():
    pdf = gerar_pdf_frequencia(FREQUENCIA)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_frequencia_sem_alunos_nao_estoura():
    pdf = gerar_pdf_frequencia({**FREQUENCIA, "alunos": []})
    assert pdf.startswith(b"%PDF-")


def test_frequencia_sem_periodo_nao_estoura():
    pdf = gerar_pdf_frequencia({**FREQUENCIA, "periodo": {"data_inicio": None, "data_fim": None}})
    assert pdf.startswith(b"%PDF-")


def test_frequencia_com_60_alunos_gera_mais_de_uma_pagina():
    alunos = [
        {"aluno_id": f"a{i}", "nome": f"Aluno Numero {i:02d}", "ra": f"20230000{i:02d}",
         "aulas_presentes": i % 11, "aulas_dadas": 10, "chamadas_count": 5,
         "percentual": (i % 11) * 10, "situacao": "Regular" if (i % 11) * 10 >= 75 else "Risco"}
        for i in range(60)
    ]
    pdf = gerar_pdf_frequencia({**FREQUENCIA, "alunos": alunos})
    assert _paginas(pdf) > 1


def test_frequencia_mascara_cpf_no_texto_desenhado():
    """Garantia de privacidade: um CPF válido nunca aparece em claro no PDF de frequência."""
    pdf = gerar_pdf_frequencia(FREQUENCIA)
    texto = _textos_desenhados(pdf)
    assert texto, "extração de texto do PDF não retornou nada — recipe falhou em silêncio"
    assert "***.982.247-**" in texto
    assert "529.982.247-25" not in texto
    assert "52998224725" not in texto


def test_frequencia_com_periodo_como_datetime_date():
    """Testa _periodo_por_extenso com objetos datetime.date (não strings ISO).

    Os routers passam whatever FastAPI parsed, que é datetime.date para
    data_inicio/data_fim. Este teste verifica que gerar_pdf_frequencia
    manipula date objects corretamente, não só strings.
    """
    pdf = gerar_pdf_frequencia({
        **FREQUENCIA,
        "periodo": {
            "data_inicio": datetime.date(2026, 3, 1),
            "data_fim": datetime.date(2026, 7, 22),
        },
    })
    assert pdf.startswith(b"%PDF-")
