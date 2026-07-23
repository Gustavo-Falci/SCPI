"""Testes dos endpoints de relatório com formato=pdf (chamada direta, sem TestClient)."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.responses import Response

DETALHE = {
    "chamada_id": "c1",
    "turma_id": "t1",
    "nome_disciplina": "Cálculo I",
    "codigo_turma": "TURMA 3/B",
    "semestre": "2026.1",
    "turno": "Noturno",
    "professor_nome": "Ana Souza",
    "data_chamada": "12/03/2026",
    "horario_inicio": "19:00",
    "horario_fim": "20:40",
    "total_aulas": 2,
    "total_alunos": 0,
    "presentes": 0,
    "ausentes": 0,
    "percentual": 0,
    "alunos": [],
}


def test_ata_professor_sem_formato_continua_json():
    from routers.relatorios import detalhe_relatorio_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.detalhe_relatorio", return_value=DETALHE):
        out = detalhe_relatorio_professor(
            chamada_id="c1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert out == DETALHE


def test_ata_professor_formato_pdf_retorna_response_pdf():
    from routers.relatorios import detalhe_relatorio_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.detalhe_relatorio", return_value=DETALHE):
        out = detalhe_relatorio_professor(
            chamada_id="c1",
            formato="pdf",
            current_user={"sub": "u1", "role": "Professor"},
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"
    assert out.body.startswith(b"%PDF-")


def test_ata_nome_de_arquivo_sanitiza_codigo_da_turma():
    from routers.relatorios import detalhe_relatorio_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.detalhe_relatorio", return_value=DETALHE):
        out = detalhe_relatorio_professor(
            chamada_id="c1",
            formato="pdf",
            current_user={"sub": "u1", "role": "Professor"},
        )
    disposicao = out.headers["content-disposition"]
    # 'TURMA 3/B' não pode virar caminho nem quebrar o header.
    assert "/" not in disposicao.split("filename=")[1]
    assert 'filename="ata-TURMA-3-B-20260312.pdf"' == disposicao.split("; ")[1]


def test_ata_admin_formato_pdf_retorna_response_pdf():
    from routers.relatorios import detalhe_relatorio_admin

    with patch("routers.relatorios.detalhe_relatorio", return_value=DETALHE):
        out = detalhe_relatorio_admin(
            chamada_id="c1", formato="pdf", current_user={"sub": "u1", "role": "Admin"}
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"


def test_admin_nao_filtra_por_professor():
    from routers.relatorios import detalhe_relatorio_admin

    with patch("routers.relatorios.detalhe_relatorio", return_value=DETALHE) as m:
        detalhe_relatorio_admin(
            chamada_id="c1", current_user={"sub": "u1", "role": "Admin"}
        )
    m.assert_called_once_with("c1")


def test_cors_expoe_content_disposition():
    # Sem isso o portal (admin.scpi.me -> api.scpi.me) não lê o nome do arquivo.
    # Checagem no fonte: importar api.py instancia clientes AWS e o agendador,
    # efeitos colaterais que os testes desta suíte evitam de propósito.
    from pathlib import Path

    fonte = (Path(__file__).resolve().parents[1] / "api.py").read_text(encoding="utf-8")
    assert 'expose_headers=["Content-Disposition"]' in fonte


CHAMADA = {
    "chamada_id": "c1",
    "nome_disciplina": "Cálculo I",
    "codigo_turma": "TURMA-3B",
    "semestre": "2026.1",
    "turno": "Noturno",
    "professor_nome": "Ana Souza",
    "data_chamada": "12/03/2026",
    "total_aulas": 2,
    "total_alunos": 25,
    "presentes": 40,
    "presentes_alunos": 20,
    "ausentes_alunos": 3,
    "parciais_alunos": 2,
    "ausentes": 10,
    "percentual": 80,
}


def test_consolidado_professor_formato_pdf():
    from routers.relatorios import listar_relatorios_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]):
        out = listar_relatorios_professor(
            formato="pdf", current_user={"sub": "u1", "role": "Professor"}
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"
    assert out.body.startswith(b"%PDF-")
    assert out.headers["content-disposition"].startswith('attachment; filename="consolidado-chamadas-')


def test_consolidado_pdf_ignora_paginacao_da_tela():
    from routers.relatorios import listar_relatorios_professor, TETO_CONSOLIDADO

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]) as m:
        listar_relatorios_professor(
            formato="pdf", limit=8, offset=16,
            current_user={"sub": "u1", "role": "Professor"},
        )
    kwargs = m.call_args.kwargs
    assert kwargs["limit"] == TETO_CONSOLIDADO + 1
    assert kwargs["offset"] == 0


def test_consolidado_acima_do_teto_retorna_400():
    from routers.relatorios import listar_relatorios_professor, TETO_CONSOLIDADO

    demais = [CHAMADA] * (TETO_CONSOLIDADO + 1)
    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=demais):
        with pytest.raises(HTTPException) as exc:
            listar_relatorios_professor(
                formato="pdf", current_user={"sub": "u1", "role": "Professor"}
            )
    assert exc.value.status_code == 400


def test_consolidado_json_continua_paginando():
    from routers.relatorios import listar_relatorios_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]) as m:
        listar_relatorios_professor(
            limit=8, offset=16, current_user={"sub": "u1", "role": "Professor"}
        )
    assert m.call_args.kwargs["limit"] == 8
    assert m.call_args.kwargs["offset"] == 16


def test_consolidado_admin_formato_pdf():
    from routers.relatorios import listar_relatorios_admin

    with patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]):
        out = listar_relatorios_admin(
            formato="pdf", current_user={"sub": "u1", "role": "Admin"}
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"


def test_consolidado_admin_pdf_ignora_paginacao_da_tela():
    from routers.relatorios import listar_relatorios_admin, TETO_CONSOLIDADO

    with patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]) as m:
        listar_relatorios_admin(
            formato="pdf", limit=8, offset=16,
            current_user={"sub": "u1", "role": "Admin"},
        )
    kwargs = m.call_args.kwargs
    assert kwargs["limit"] == TETO_CONSOLIDADO + 1
    assert kwargs["offset"] == 0


def test_consolidado_admin_acima_do_teto_retorna_400():
    from routers.relatorios import listar_relatorios_admin, TETO_CONSOLIDADO

    demais = [CHAMADA] * (TETO_CONSOLIDADO + 1)
    with patch("routers.relatorios.listar_relatorios", return_value=demais):
        with pytest.raises(HTTPException) as exc:
            listar_relatorios_admin(
                formato="pdf", current_user={"sub": "u1", "role": "Admin"}
            )
    assert exc.value.status_code == 400


def test_consolidado_professor_pdf_rotula_turma_com_codigo_e_disciplina():
    # Finding 1: nome_disciplina não identifica a turma (várias turmas podem
    # compartilhar disciplina) — o rótulo do filtro precisa citar codigo_turma.
    from routers.relatorios import listar_relatorios_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]), \
         patch("routers.relatorios.gerar_pdf_consolidado", return_value=b"%PDF-1.4") as m:
        listar_relatorios_professor(
            formato="pdf", turma_id="t1",
            current_user={"sub": "u1", "role": "Professor"},
        )
    filtros = m.call_args.args[1]
    assert filtros["turma"] == "TURMA-3B (Cálculo I)"


def test_consolidado_professor_pdf_turma_sem_chamadas_nao_vira_todas():
    # turma_id filtrado mas itens vazio: None renderizaria "todas", que é falso.
    from routers.relatorios import listar_relatorios_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.listar_relatorios", return_value=[]), \
         patch("routers.relatorios.gerar_pdf_consolidado", return_value=b"%PDF-1.4") as m:
        listar_relatorios_professor(
            formato="pdf", turma_id="t1",
            current_user={"sub": "u1", "role": "Professor"},
        )
    filtros = m.call_args.args[1]
    assert filtros["turma"] == "filtro aplicado (sem chamadas no período)"


def test_consolidado_admin_pdf_rotula_turma_com_codigo_e_disciplina():
    from routers.relatorios import listar_relatorios_admin

    with patch("routers.relatorios.listar_relatorios", return_value=[CHAMADA]), \
         patch("routers.relatorios.gerar_pdf_consolidado", return_value=b"%PDF-1.4") as m:
        listar_relatorios_admin(
            formato="pdf", turma_id="t1",
            current_user={"sub": "u1", "role": "Admin"},
        )
    filtros = m.call_args.args[1]
    assert filtros["turma"] == "TURMA-3B (Cálculo I)"


def test_consolidado_admin_pdf_turma_sem_chamadas_nao_vira_todas():
    from routers.relatorios import listar_relatorios_admin

    with patch("routers.relatorios.listar_relatorios", return_value=[]), \
         patch("routers.relatorios.gerar_pdf_consolidado", return_value=b"%PDF-1.4") as m:
        listar_relatorios_admin(
            formato="pdf", turma_id="t1",
            current_user={"sub": "u1", "role": "Admin"},
        )
    filtros = m.call_args.args[1]
    assert filtros["turma"] == "filtro aplicado (sem chamadas no período)"


FREQ = {
    "turma": {"turma_id": "t1", "nome_disciplina": "Cálculo I", "codigo_turma": "TURMA 3/B",
              "turno": "Noturno", "semestre": "2026.1", "professor_nome": "Ana Souza"},
    "periodo": {"data_inicio": None, "data_fim": None},
    "totais": {"total_alunos": 0, "chamadas": 0, "aulas_dadas": 0, "presencas": 0,
               "percentual": 0},
    "alunos": [],
}


def test_frequencia_professor_formato_pdf():
    from routers.relatorios import frequencia_turma_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.frequencia_turma", return_value=FREQ):
        out = frequencia_turma_professor(
            turma_id="t1", formato="pdf",
            current_user={"sub": "u1", "role": "Professor"},
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"
    assert out.body.startswith(b"%PDF-")
    assert 'filename="frequencia-TURMA-3-B' in out.headers["content-disposition"]


def test_frequencia_sem_formato_continua_json():
    from routers.relatorios import frequencia_turma_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.frequencia_turma", return_value=FREQ):
        out = frequencia_turma_professor(
            turma_id="t1", current_user={"sub": "u1", "role": "Professor"}
        )
    assert out == FREQ


def test_frequencia_admin_formato_pdf():
    from routers.relatorios import frequencia_turma_admin

    with patch("routers.relatorios.frequencia_turma", return_value=FREQ):
        out = frequencia_turma_admin(
            turma_id="t1", formato="pdf", current_user={"sub": "u1", "role": "Admin"}
        )
    assert isinstance(out, Response)
    assert out.media_type == "application/pdf"
    assert 'filename="frequencia-TURMA-3-B' in out.headers["content-disposition"]


def test_frequencia_professor_pdf_bola_regressao_404_nao_gera():
    """Testa que 404 da turma não pertencer ao professor não gera PDF.

    Regressão BOLA: formato=pdf não deve contornar validação de propriedade.
    O service frequencia_turma levanta 404 ANTES do if formato=="pdf",
    e este teste verifica que gerar_pdf_frequencia nunca é chamado.
    """
    from routers.relatorios import frequencia_turma_professor

    with patch("routers.relatorios.obter_professor_id", return_value="p1"), \
         patch("routers.relatorios.frequencia_turma", side_effect=HTTPException(status_code=404, detail="Turma não encontrada.")), \
         patch("routers.relatorios.gerar_pdf_frequencia") as mock_gerar_pdf:
        with pytest.raises(HTTPException) as exc:
            frequencia_turma_professor(
                turma_id="t-de-outro", formato="pdf",
                current_user={"sub": "u1", "role": "Professor"},
            )
    assert exc.value.status_code == 404
    assert not mock_gerar_pdf.called
