import datetime
import zoneinfo

from fastapi import APIRouter, Depends, HTTPException

from core.helpers import internal_error
from core.security import get_current_user, require_self_or_admin
from repositories.alunos import aluno_matriculado_por_usuario
from repositories.turmas import (
    listar_alunos_da_turma,
    listar_turmas_com_horarios_por_professor,
    professor_responsavel_por_usuario,
)

router = APIRouter(prefix="/turmas", tags=["turmas"])


@router.get("/{usuario_id}")
def get_turmas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna as turmas de um professor com flag indicando se está no horário de aula."""
    require_self_or_admin(usuario_id, current_user)
    try:
        agora = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo"))
        dia_semana = agora.weekday()
        hora_atual = agora.time()

        rows = listar_turmas_com_horarios_por_professor(usuario_id)
        turmas_dict = {}

        for row in rows:
            t_id = row['turma_id']
            if t_id not in turmas_dict:
                turmas_dict[t_id] = {
                    "turma_id": t_id,
                    "nome_disciplina": row['nome_disciplina'],
                    "codigo_turma": row['codigo_turma'],
                    "pode_iniciar": False,
                    "proximo_horario": "Sem horário definido",
                }

            if row['dia_semana'] == dia_semana:
                happening_now = row['horario_inicio'] <= hora_atual <= row['horario_fim']
                if happening_now:
                    turmas_dict[t_id]["pode_iniciar"] = True
                    turmas_dict[t_id]["proximo_horario"] = f"Hoje: {row['horario_inicio'].strftime('%H:%M')} - {row['horario_fim'].strftime('%H:%M')}"
                elif not turmas_dict[t_id]["pode_iniciar"]:
                    turmas_dict[t_id]["proximo_horario"] = f"Hoje: {row['horario_inicio'].strftime('%H:%M')} - {row['horario_fim'].strftime('%H:%M')}"
            elif turmas_dict[t_id]["proximo_horario"] == "Sem horário definido" and row['dia_semana'] is not None:
                dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                turmas_dict[t_id]["proximo_horario"] = f"{dias[row['dia_semana']]}: {row['horario_inicio'].strftime('%H:%M')}"

        return {"turmas": list(turmas_dict.values())}
    except Exception as e:
        raise internal_error(e)


@router.get("/{turma_id}/alunos")
def get_alunos_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        role = current_user.get("role")
        if role == "Professor":
            if not professor_responsavel_por_usuario(turma_id, current_user.get("sub")):
                raise HTTPException(status_code=403, detail="Professor não é responsável por esta turma.")
        elif role == "Aluno":
            if not aluno_matriculado_por_usuario(turma_id, current_user.get("sub")):
                raise HTTPException(status_code=403, detail="Aluno não matriculado nesta turma.")
        elif role != "Admin":
            raise HTTPException(status_code=403, detail="Acesso negado.")

        alunos = listar_alunos_da_turma(turma_id)
        return {"alunos": alunos}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)
