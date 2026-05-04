from infra.database import get_db_cursor


def listar_professores_para_admin():
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT p.professor_id, u.nome, u.email, p.departamento
            FROM Professores p
            JOIN Usuarios u ON p.usuario_id = u.usuario_id
            ORDER BY u.nome ASC
            """
        )
        return cur.fetchall()


def criar_professor_com_usuario(usuario_id, professor_id, nome, email, senha_hash, departamento):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
            VALUES (%s, %s, %s, %s, 'Professor', TRUE)
            """,
            (usuario_id, nome, email, senha_hash),
        )
        cur.execute(
            """
            INSERT INTO Professores (professor_id, usuario_id, departamento)
            VALUES (%s, %s, %s)
            """,
            (professor_id, usuario_id, departamento),
        )
        return professor_id


def excluir_professor_em_cascata(professor_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Professores WHERE professor_id = %s", (professor_id,))
        row = cur.fetchone()
        if not row:
            return None
        usuario_id = row["usuario_id"]
        cur.execute("UPDATE Turmas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
        cur.execute("UPDATE Chamadas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
        cur.execute("DELETE FROM Professores WHERE professor_id = %s", (professor_id,))
        cur.execute("DELETE FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
        return usuario_id


def obter_dashboard_professor(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
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
        return cur.fetchone()
