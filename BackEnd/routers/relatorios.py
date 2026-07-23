import re
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from core.helpers import internal_error
from core.security import require_role
from infra.relatorio_pdf import gerar_pdf_ata_chamada, gerar_pdf_consolidado, gerar_pdf_frequencia
from repositories.usuarios import obter_professor_id
from services.relatorios import (
    listar_relatorios,
    detalhe_relatorio,
    opcoes_filtros_relatorios,
    frequencia_turma,
)

router = APIRouter(tags=["relatorios"])

TZ = ZoneInfo("America/Sao_Paulo")
_NAO_SEGURO = re.compile(r"[^A-Za-z0-9]+")
TETO_CONSOLIDADO = 2000


def _slug(texto: str) -> str:
    """Reduz um texto livre a algo seguro para nome de arquivo."""
    return _NAO_SEGURO.sub("-", str(texto or "")).strip("-") or "sem-codigo"


def _resposta_pdf(pdf_bytes: bytes, filename: str) -> Response:
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


def _data_para_arquivo(data_chamada: str) -> str:
    """'12/03/2026' -> '20260312'; devolve a data de hoje se vier fora do formato."""
    try:
        return datetime.strptime(data_chamada, "%d/%m/%Y").strftime("%Y%m%d")
    except (ValueError, TypeError):
        return datetime.now(tz=TZ).strftime("%Y%m%d")


def _pdf_da_ata(detalhe: dict) -> Response:
    filename = (
        f"ata-{_slug(detalhe.get('codigo_turma'))}"
        f"-{_data_para_arquivo(detalhe.get('data_chamada'))}.pdf"
    )
    return _resposta_pdf(gerar_pdf_ata_chamada(detalhe), filename)


def _pdf_do_consolidado(itens: list, filtros: dict) -> Response:
    if len(itens) > TETO_CONSOLIDADO:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Recorte muito grande para PDF ({len(itens)} chamadas, "
                f"máximo {TETO_CONSOLIDADO}). Restrinja o período ou a turma."
            ),
        )
    agora = datetime.now(tz=TZ).strftime("%Y%m%d-%H%M")
    return _resposta_pdf(
        gerar_pdf_consolidado(itens, filtros), f"consolidado-chamadas-{agora}.pdf"
    )


def _pdf_da_frequencia(dados: dict, data_inicio, data_fim) -> Response:
    turma = dados.get("turma") or {}
    ini = data_inicio.strftime("%Y%m%d") if data_inicio else "inicio"
    fim = data_fim.strftime("%Y%m%d") if data_fim else datetime.now(tz=TZ).strftime("%Y%m%d")
    filename = f"frequencia-{_slug(turma.get('codigo_turma'))}-{ini}-{fim}.pdf"
    return _resposta_pdf(gerar_pdf_frequencia(dados), filename)


def _fmt_data(d) -> Optional[str]:
    return d.strftime("%d/%m/%Y") if d else None


def _rotulo_turma_pdf(turma_id: Optional[str], itens: list) -> Optional[str]:
    """Rótulo da turma para o filtro do PDF consolidado.

    `nome_disciplina` identifica a disciplina, não a turma — várias turmas
    podem compartilhar a mesma disciplina. A identidade da turma é
    `codigo_turma`, que já vem na mesma linha; junta a disciplina entre
    parênteses quando ela existir, e cai só para o código quando não.
    Se o filtro foi aplicado mas não achou nenhuma chamada, não vira None
    (que _linha_de_filtros lê como "todas" — uma mentira quando há filtro).
    """
    if not turma_id:
        return None
    if not itens:
        return "filtro aplicado (sem chamadas no período)"
    codigo = itens[0].get("codigo_turma")
    disciplina = itens[0].get("nome_disciplina")
    return f"{codigo} ({disciplina})" if disciplina else codigo


@router.get("/professor/relatorios/chamadas")
def listar_relatorios_professor(
    limit: int = 50,
    offset: int = 0,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    turma_id: Optional[str] = None,
    turno: Optional[str] = None,
    semestre: Optional[str] = None,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="Intervalo de datas inválido.")
    if turno is not None and turno not in ("Matutino", "Noturno"):
        raise HTTPException(status_code=400, detail="Turno inválido.")
    # O PDF é o documento do recorte inteiro: a paginação da tela não se aplica.
    # Pede um a mais que o teto só para poder recusar com número exato.
    pdf = formato == "pdf"
    try:
        itens = listar_relatorios(
            professor_id=professor_id, turma_id=turma_id,
            limit=TETO_CONSOLIDADO + 1 if pdf else limit,
            offset=0 if pdf else offset,
            data_inicio=data_inicio, data_fim=data_fim, turno=turno, semestre=semestre,
        )
        if pdf:
            return _pdf_do_consolidado(
                itens,
                {
                    "data_inicio": _fmt_data(data_inicio),
                    "data_fim": _fmt_data(data_fim),
                    "turno": turno,
                    "semestre": semestre,
                    "turma": _rotulo_turma_pdf(turma_id, itens),
                },
            )
        return itens
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "listar_relatorios_professor")


@router.get("/professor/relatorios/filtros")
def opcoes_filtros_relatorios_professor(
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    try:
        return opcoes_filtros_relatorios(professor_id)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "opcoes_filtros_relatorios_professor")


@router.get("/professor/relatorios/chamadas/{chamada_id}")
def detalhe_relatorio_professor(
    chamada_id: str,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    try:
        detalhe = detalhe_relatorio(chamada_id, professor_id=professor_id)
        if formato == "pdf":
            return _pdf_da_ata(detalhe)
        return detalhe
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "detalhe_relatorio_professor")


@router.get("/admin/relatorios/chamadas")
def listar_relatorios_admin(
    turma_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    turno: Optional[str] = None,
    semestre: Optional[str] = None,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Admin")),
):
    pdf = formato == "pdf"
    try:
        itens = listar_relatorios(
            turma_id=turma_id,
            limit=TETO_CONSOLIDADO + 1 if pdf else limit,
            offset=0 if pdf else offset,
            turno=turno, semestre=semestre,
        )
        if pdf:
            return _pdf_do_consolidado(
                itens,
                {
                    "turno": turno,
                    "semestre": semestre,
                    "turma": _rotulo_turma_pdf(turma_id, itens),
                },
            )
        return itens
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "listar_relatorios_admin")


@router.get("/admin/relatorios/chamadas/{chamada_id}")
def detalhe_relatorio_admin(
    chamada_id: str,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        detalhe = detalhe_relatorio(chamada_id)
        if formato == "pdf":
            return _pdf_da_ata(detalhe)
        return detalhe
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "detalhe_relatorio_admin")


@router.get("/professor/relatorios/turmas/{turma_id}/frequencia")
def frequencia_turma_professor(
    turma_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="Intervalo de datas inválido.")
    try:
        dados = frequencia_turma(
            turma_id, professor_id=professor_id,
            data_inicio=data_inicio, data_fim=data_fim,
        )
        if formato == "pdf":
            return _pdf_da_frequencia(dados, data_inicio, data_fim)
        return dados
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "frequencia_turma_professor")


@router.get("/admin/relatorios/turmas/{turma_id}/frequencia")
def frequencia_turma_admin(
    turma_id: str,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: dict = Depends(require_role("Admin")),
):
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(status_code=400, detail="Intervalo de datas inválido.")
    try:
        dados = frequencia_turma(
            turma_id, professor_id=None, data_inicio=data_inicio, data_fim=data_fim
        )
        if formato == "pdf":
            return _pdf_da_frequencia(dados, data_inicio, data_fim)
        return dados
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "frequencia_turma_admin")
