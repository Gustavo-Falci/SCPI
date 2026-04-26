import datetime

from fastapi import APIRouter, Depends

from core.helpers import internal_error
from core.security import get_current_user, require_self_or_admin
from infra.database import get_db_cursor

router = APIRouter(prefix="/professor", tags=["professores"])


@router.get("/dashboard/{usuario_id}")
def get_dashboard(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                WITH last_chamada AS (
                    SELECT c.chamada_id, c.turma_id
                    FROM Chamadas c
                    JOIN Professores p ON c.professor_id = p.professor_id
                    WHERE p.usuario_id = %s
                    ORDER BY c.data_criacao DESC LIMIT 1
                )
                SELECT
                    u.nome AS prof_nome,
                    lc.chamada_id,
                    lc.turma_id,
                    t.nome_disciplina,
                    (SELECT COUNT(*) FROM Turma_Alunos WHERE turma_id = lc.turma_id) AS total,
                    (SELECT COUNT(*) FROM Presencas WHERE chamada_id = lc.chamada_id) AS presentes
                FROM Usuarios u
                LEFT JOIN last_chamada lc ON TRUE
                LEFT JOIN Turmas t ON t.turma_id = lc.turma_id
                WHERE u.usuario_id = %s
                """,
                (usuario_id, usuario_id),
            )
            row = cur.fetchone()
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
            cur.execute(
                """
                SELECT h.horario_id as id, t.nome_disciplina as nome,
                       to_char(h.horario_inicio, 'HH24:MI') || ' - ' || to_char(h.horario_fim, 'HH24:MI') as horario,
                       h.sala
                FROM horarios_aulas h
                JOIN turmas t ON h.turma_id = t.turma_id
                WHERE t.professor_id = (SELECT professor_id FROM Professores WHERE usuario_id = %s)
                AND h.dia_semana = %s
                """,
                (usuario_id, dia_hoje),
            )
            aulas_hoje = cur.fetchall()

            return {"nome": nome, "estatisticas": estatisticas, "aulas_hoje": aulas_hoje}
    except Exception as e:
        raise internal_error(e)
