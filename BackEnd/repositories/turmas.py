from psycopg2.extras import execute_values

from infra.database import get_db_cursor


def listar_turmas_completas():
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT t.turma_id, t.nome_disciplina, t.codigo_turma, t.turno, t.semestre,
            COALESCE(u.nome, 'Sem professor') as professor_nome,
            (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = t.turma_id) as total_alunos
            FROM Turmas t
            LEFT JOIN Professores p ON t.professor_id = p.professor_id
            LEFT JOIN Usuarios u ON p.usuario_id = u.usuario_id
            ORDER BY t.semestre ASC, t.nome_disciplina ASC
            """
        )
        return cur.fetchall()


def criar_turma(turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao, turno, semestre):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao, turno, semestre)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING turma_id
            """,
            (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao, turno, semestre),
        )
        return turma_id


def atribuir_professor_turma(turma_id, professor_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute("UPDATE Turmas SET professor_id = %s WHERE turma_id = %s", (professor_id, turma_id))
        return cur.rowcount


def excluir_turma_em_cascata(turma_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute("DELETE FROM horarios_aulas WHERE turma_id = %s", (turma_id,))
        cur.execute("DELETE FROM Turma_Alunos WHERE turma_id = %s", (turma_id,))
        cur.execute("DELETE FROM Turmas WHERE turma_id = %s", (turma_id,))
        return True


def obter_turno_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT turno FROM Turmas WHERE turma_id = %s", (turma_id,))
        return cur.fetchone()


def obter_turma_basica(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT nome_disciplina, codigo_turma FROM Turmas WHERE turma_id = %s",
            (turma_id,),
        )
        return cur.fetchone()


def matricular_alunos_em_turma(turma_id, aluno_ids):
    """Insere matrículas; retorna o número de novas linhas inseridas."""
    if not aluno_ids:
        return 0
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        execute_values(
            cur,
            "INSERT INTO Turma_Alunos (turma_id, aluno_id, data_associacao) VALUES %s ON CONFLICT (turma_id, aluno_id) DO NOTHING",
            [(turma_id, aid) for aid in aluno_ids],
            template="(%s, %s, NOW())",
        )
        return cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0


def professor_responsavel_pela_turma(turma_id, professor_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            "SELECT 1 FROM Turmas WHERE turma_id = %s AND professor_id = %s",
            (turma_id, professor_id),
        )
        return cur.fetchone() is not None


def professor_responsavel_por_usuario(turma_id, usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            """
            SELECT 1 FROM Turmas t
            JOIN Professores p ON t.professor_id = p.professor_id
            WHERE t.turma_id = %s AND p.usuario_id = %s
            """,
            (turma_id, usuario_id),
        )
        return cur.fetchone() is not None


def listar_turmas_com_horarios_por_professor(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
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
        return cur.fetchall()


def listar_alunos_da_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
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
        return cur.fetchall()


def obter_turma_id_por_chamada(chamada_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT turma_id FROM Chamadas WHERE chamada_id = %s", (chamada_id,))
        row = cur.fetchone()
        return row["turma_id"] if row else None


def listar_alunos_com_push_token_da_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT u.usuario_id, pt.expo_token
            FROM Turma_Alunos ta
            JOIN Alunos a ON a.aluno_id = ta.aluno_id
            JOIN Usuarios u ON u.usuario_id = a.usuario_id
            LEFT JOIN PushTokens pt ON pt.usuario_id = u.usuario_id::text
            WHERE ta.turma_id = %s
            """,
            (turma_id,),
        )
        return cur.fetchall()
