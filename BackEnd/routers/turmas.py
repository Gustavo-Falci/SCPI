import datetime

from fastapi import APIRouter, Depends, HTTPException

from core.helpers import internal_error
from core.security import get_current_user, require_self_or_admin
from infra.database import get_db_cursor

router = APIRouter(prefix="/turmas", tags=["turmas"])


@router.get("/{usuario_id}")
def get_turmas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna as turmas de um professor com flag indicando se está no horário de aula."""
    require_self_or_admin(usuario_id, current_user)
    try:
        agora = datetime.datetime.now()
        dia_semana = agora.weekday()
        hora_atual = agora.time()

        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    t.turma_id,
                    t.nome_disciplina,
                    t.codigo_turma,
                    h.dia_semana,
                    h.horario_inicio,
                    h.horario_fim
                FROM Turmas t
                LEFT JOIN horarios_aulas h ON t.turma_id = h.turma_id
                WHERE t.professor_id = (SELECT professor_id FROM Professores WHERE usuario_id = %s)
                """,
                (usuario_id,),
            )

            rows = cur.fetchall()
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
        with get_db_cursor() as cur:
            role = current_user.get("role")
            if role == "Professor":
                cur.execute(
                    """
                    SELECT 1 FROM Turmas t
                    JOIN Professores p ON t.professor_id = p.professor_id
                    WHERE t.turma_id = %s AND p.usuario_id = %s
                    """,
                    (turma_id, current_user.get("sub")),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Professor não é responsável por esta turma.")
            elif role == "Aluno":
                cur.execute(
                    """
                    SELECT 1 FROM Turma_Alunos ta
                    JOIN Alunos a ON ta.aluno_id = a.aluno_id
                    WHERE ta.turma_id = %s AND a.usuario_id = %s
                    """,
                    (turma_id, current_user.get("sub")),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Aluno não matriculado nesta turma.")
            elif role != "Admin":
                raise HTTPException(status_code=403, detail="Acesso negado.")

            cur.execute(
                """
                SELECT
                    a.aluno_id as id,
                    u.nome,
                    u.email,
                    a.ra
                FROM Turma_Alunos ta
                JOIN Alunos a ON ta.aluno_id = a.aluno_id
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                WHERE ta.turma_id = %s
                ORDER BY u.nome ASC
                """,
                (turma_id,),
            )
            alunos = cur.fetchall()
            return {"alunos": alunos}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)
