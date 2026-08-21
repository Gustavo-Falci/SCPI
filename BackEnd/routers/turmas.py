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
from schemas.respostas.turmas import TurmasDoProfessor

router = APIRouter(prefix="/turmas", tags=["turmas"])


@router.get(
    "/{usuario_id}",
    summary="Lista turmas do professor com status de aula",
    responses={200: {"model": TurmasDoProfessor}},
)
def get_turmas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Turmas do professor com indicador de horário de aula e chamada aberta.

    Só o próprio professor ou um Admin pode consultar (404 para os demais,
    não 403 — evita enumeração de `usuario_id`). Para cada turma calcula, a
    partir do horário atual (fuso America/Sao_Paulo): `pode_iniciar` (existe
    aula prevista agora, pelo dia da semana), `proximo_horario` (texto do
    horário de hoje ou do próximo dia com aula prevista) e
    `chamada_aberta`/`chamada_id` (se já existe chamada aberta agora para a
    turma). Devolve `{"turmas": [...]}`.
    """
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
                    "chamada_aberta": False,
                    "chamada_id": None,
                }

            if row.get('chamada_aberta_id') is not None:
                turmas_dict[t_id]["chamada_aberta"] = True
                turmas_dict[t_id]["chamada_id"] = row['chamada_aberta_id']

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


@router.get(
    "/{turma_id}/alunos",
    summary="Lista alunos matriculados na turma",
)
def get_alunos_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    """Lista os alunos matriculados na turma.

    Professor só vê turma da qual é responsável, aluno só vê turma em que
    está matriculado (ambos 404 se não for o caso, nunca 403 — evita
    enumeração de `turma_id`); Admin vê qualquer turma; qualquer outra role
    leva 403. Devolve `{"alunos": [...]}`.
    """
    try:
        role = current_user.get("role")
        if role == "Professor":
            if not professor_responsavel_por_usuario(turma_id, current_user.get("sub")):
                raise HTTPException(status_code=404, detail="Turma não encontrada.")
        elif role == "Aluno":
            if not aluno_matriculado_por_usuario(turma_id, current_user.get("sub")):
                raise HTTPException(status_code=404, detail="Turma não encontrada.")
        elif role != "Admin":
            raise HTTPException(status_code=403, detail="Acesso negado.")

        alunos = listar_alunos_da_turma(turma_id)
        return {"alunos": alunos}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)
