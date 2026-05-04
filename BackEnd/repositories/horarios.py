from infra.database import get_db_cursor


def listar_horarios_completos():
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT h.horario_id, h.turma_id, h.dia_semana,
                   to_char(h.horario_inicio, 'HH24:MI') as inicio,
                   to_char(h.horario_fim, 'HH24:MI') as fim,
                   h.sala, t.nome_disciplina, t.turno, t.semestre
            FROM horarios_aulas h
            JOIN Turmas t ON h.turma_id = t.turma_id
            """
        )
        return cur.fetchall()


def inserir_horario(turma_id, dia_semana, horario_inicio, horario_fim, sala):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            """
            INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, horario_fim, sala)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (turma_id, dia_semana, horario_inicio, horario_fim, sala),
        )
        return True


def excluir_horario(horario_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("DELETE FROM horarios_aulas WHERE horario_id = %s", (horario_id,))
        return cur.rowcount


def existe_aula_no_horario_atual_para_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            """
            SELECT 1 FROM horarios_aulas
            WHERE turma_id = %s
              AND dia_semana = (EXTRACT(DOW FROM NOW() AT TIME ZONE 'America/Sao_Paulo')::int + 6) %% 7
              AND horario_inicio <= (NOW() AT TIME ZONE 'America/Sao_Paulo')::time
              AND horario_fim    >= (NOW() AT TIME ZONE 'America/Sao_Paulo')::time
            """,
            (turma_id,),
        )
        return cur.fetchone() is not None


def listar_aulas_hoje_por_aluno(aluno_id, dia_semana, turno=None):
    with get_db_cursor() as cur:
        if not cur:
            return []
        if turno:
            cur.execute(
                """
                SELECT h.horario_id as id, t.nome_disciplina as nome,
                       to_char(h.horario_inicio, 'HH24:MI') || ' - ' || to_char(h.horario_fim, 'HH24:MI') as horario,
                       h.sala
                FROM horarios_aulas h
                JOIN turmas t ON h.turma_id = t.turma_id
                JOIN turma_alunos ta ON t.turma_id = ta.turma_id
                WHERE ta.aluno_id = %s
                AND h.dia_semana = %s
                AND t.turno = %s
                """,
                (aluno_id, dia_semana, turno),
            )
        else:
            cur.execute(
                """
                SELECT h.horario_id as id, t.nome_disciplina as nome,
                       to_char(h.horario_inicio, 'HH24:MI') || ' - ' || to_char(h.horario_fim, 'HH24:MI') as horario,
                       h.sala
                FROM horarios_aulas h
                JOIN turmas t ON h.turma_id = t.turma_id
                JOIN turma_alunos ta ON t.turma_id = ta.turma_id
                WHERE ta.aluno_id = %s
                AND h.dia_semana = %s
                """,
                (aluno_id, dia_semana),
            )
        return cur.fetchall()


def listar_aulas_hoje_por_professor(usuario_id, dia_semana):
    with get_db_cursor() as cur:
        if not cur:
            return []
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
            (usuario_id, dia_semana),
        )
        return cur.fetchall()
