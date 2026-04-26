from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core.helpers import internal_error
from core.security import require_role
from repositories.usuarios import obter_professor_id
from services.relatorios import listar_relatorios, detalhe_relatorio

router = APIRouter(tags=["relatorios"])


@router.get("/professor/relatorios/chamadas")
def listar_relatorios_professor(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    try:
        return listar_relatorios(professor_id=professor_id, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "listar_relatorios_professor")


@router.get("/professor/relatorios/chamadas/{chamada_id}")
def detalhe_relatorio_professor(
    chamada_id: str,
    current_user: dict = Depends(require_role("Professor")),
):
    professor_id = obter_professor_id(current_user.get("sub"))
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado.")
    try:
        return detalhe_relatorio(chamada_id, professor_id=professor_id)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "detalhe_relatorio_professor")


@router.get("/admin/relatorios/chamadas")
def listar_relatorios_admin(
    turma_id: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        return listar_relatorios(turma_id=turma_id, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "listar_relatorios_admin")


@router.get("/admin/relatorios/chamadas/{chamada_id}")
def detalhe_relatorio_admin(
    chamada_id: str,
    current_user: dict = Depends(require_role("Admin")),
):
    try:
        return detalhe_relatorio(chamada_id)
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "detalhe_relatorio_admin")
