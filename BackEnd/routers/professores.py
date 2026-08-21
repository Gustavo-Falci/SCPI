import datetime
import zoneinfo

from fastapi import APIRouter, Depends

from core.helpers import internal_error
from core.security import get_current_user, require_self_or_admin
from repositories.horarios import listar_aulas_hoje_por_professor
from repositories.professores import obter_dashboard_professor
from schemas.respostas.professores import DashboardDoProfessor

router = APIRouter(prefix="/professor", tags=["professores"])


@router.get(
    "/dashboard/{usuario_id}",
    summary="Dashboard do professor: estatísticas e aulas",
    responses={200: {"model": DashboardDoProfessor}},
)
def get_dashboard(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Dados do dashboard do professor: estatísticas, aulas de hoje e chamada ativa.

    Só o próprio professor ou um Admin pode consultar (404 para os demais,
    não 403 — evita enumeração de `usuario_id`). `estatisticas` vem da
    chamada mais recente do professor (zerada com
    `disciplina="Nenhuma chamada recente"` se ele nunca abriu uma);
    `chamada_ativa` só aparece (não-`None`) se houver chamada aberta agora;
    `aulas_hoje` lista as aulas previstas para o dia da semana atual (fuso
    America/Sao_Paulo).
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_dashboard_professor(usuario_id)
        nome = row['prof_nome'] if row and row.get('prof_nome') else "Professor"

        if row and row.get('chamada_id'):
            estatisticas = {
                "total": row['total'] or 0,
                "presentes": row['presentes'] or 0,
                "parciais": row['parciais'] or 0,
                "ausentes": row['ausentes'] or 0,
                "disciplina": row['nome_disciplina'] or "Disciplina",
            }
        else:
            estatisticas = {"total": 0, "presentes": 0, "parciais": 0, "ausentes": 0, "disciplina": "Nenhuma chamada recente"}

        ca_id = row.get("aberta_chamada_id") if row else None
        chamada_ativa = None
        if ca_id:
            chamada_ativa = {
                "chamada_id": ca_id,
                "turma_id": row.get("aberta_turma_id"),
                "turma_nome": row.get("aberta_turma_nome"),
            }

        dia_hoje = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).weekday()
        aulas_hoje = listar_aulas_hoje_por_professor(usuario_id, dia_hoje)

        return {
            "nome": nome,
            "estatisticas": estatisticas,
            "aulas_hoje": aulas_hoje,
            "chamada_ativa": chamada_ativa,
        }
    except Exception as e:
        raise internal_error(e)
