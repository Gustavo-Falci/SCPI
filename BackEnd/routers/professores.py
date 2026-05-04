import datetime

from fastapi import APIRouter, Depends

from core.helpers import internal_error
from core.security import get_current_user, require_self_or_admin
from repositories.horarios import listar_aulas_hoje_por_professor
from repositories.professores import obter_dashboard_professor

router = APIRouter(prefix="/professor", tags=["professores"])


@router.get("/dashboard/{usuario_id}")
def get_dashboard(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_dashboard_professor(usuario_id)
        nome = row['prof_nome'] if row and row.get('prof_nome') else "Professor"

        if row and row.get('chamada_id'):
            total = row['total'] or 0
            presentes = row['presentes'] or 0
            estatisticas = {
                "total": total,
                "presentes": presentes,
                "ausentes": total - presentes,
                "disciplina": row['nome_disciplina'] or "Disciplina",
            }
        else:
            estatisticas = {"total": 0, "presentes": 0, "ausentes": 0, "disciplina": "Nenhuma chamada recente"}

        dia_hoje = datetime.datetime.now().weekday()
        aulas_hoje = listar_aulas_hoje_por_professor(usuario_id, dia_hoje)

        return {"nome": nome, "estatisticas": estatisticas, "aulas_hoje": aulas_hoje}
    except Exception as e:
        raise internal_error(e)
