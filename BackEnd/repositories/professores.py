import uuid

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
                SELECT c.chamada_id, c.turma_id, c.total_aulas
                FROM Chamadas c
                JOIN Professores p ON c.professor_id = p.professor_id
                WHERE p.usuario_id = %s
                ORDER BY c.data_criacao DESC LIMIT 1
            ),
            chamada_aberta AS (
                SELECT c.chamada_id, c.turma_id, t.nome_disciplina
                FROM Chamadas c
                JOIN Professores p ON c.professor_id = p.professor_id
                JOIN Turmas t ON t.turma_id = c.turma_id
                WHERE p.usuario_id = %s AND c.status = 'Aberta'
                ORDER BY c.data_criacao DESC LIMIT 1
            )
            SELECT
                u.nome AS prof_nome,
                lc.chamada_id,
                lc.turma_id,
                lc.total_aulas,
                t.nome_disciplina,
                ca.chamada_id     AS aberta_chamada_id,
                ca.turma_id       AS aberta_turma_id,
                ca.nome_disciplina AS aberta_turma_nome,
                (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = lc.turma_id) AS total,
                (SELECT COUNT(*)
                 FROM Turma_Alunos ta
                 LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = lc.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
                 WHERE ta.turma_id = lc.turma_id AND COALESCE(pc.cnt, 0) = lc.total_aulas) AS presentes,
                (SELECT COUNT(*)
                 FROM Turma_Alunos ta
                 LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = lc.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
                 WHERE ta.turma_id = lc.turma_id AND COALESCE(pc.cnt, 0) > 0 AND COALESCE(pc.cnt, 0) < lc.total_aulas) AS parciais,
                (SELECT COUNT(*)
                 FROM Turma_Alunos ta
                 LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = lc.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
                 WHERE ta.turma_id = lc.turma_id AND COALESCE(pc.cnt, 0) = 0) AS ausentes
            FROM Usuarios u
            LEFT JOIN last_chamada lc ON TRUE
            LEFT JOIN chamada_aberta ca ON TRUE
            LEFT JOIN Turmas t ON t.turma_id = lc.turma_id
            WHERE u.usuario_id = %s
            """,
            (usuario_id, usuario_id, usuario_id),
        )
        return cur.fetchone()


def atualizar_professor(professor_id, nome=None, email=None, departamento=None):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Professores WHERE professor_id = %s", (professor_id,))
        row = cur.fetchone()
        if not row:
            return None
        usuario_id = row["usuario_id"]
        if nome is not None:
            cur.execute("UPDATE Usuarios SET nome = %s WHERE usuario_id = %s", (nome, usuario_id))
        if email is not None:
            cur.execute("UPDATE Usuarios SET email = %s WHERE usuario_id = %s", (email, usuario_id))
        if departamento is not None:
            cur.execute("UPDATE Professores SET departamento = %s WHERE professor_id = %s", (departamento, professor_id))
        return professor_id


def buscar_usuario_id_por_professor_id(professor_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Professores WHERE professor_id = %s", (professor_id,))
        return cur.fetchone()


def importar_professor_csv(nome, email, departamento, senha_hash):
    """Insere usuario+professor em uma transação. Retorna (novo_usuario, email)."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return (False, None)

        user_uuid = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
            VALUES (%s, %s, %s, %s, 'Professor', TRUE)
            ON CONFLICT (email) DO NOTHING
            RETURNING usuario_id
            """,
            (user_uuid, nome, email, senha_hash),
        )
        res_user = cur.fetchone()
        usuario_id = res_user["usuario_id"] if res_user else None
        novo_usuario = res_user is not None

        if not usuario_id:
            cur.execute("SELECT usuario_id FROM Usuarios WHERE email = %s", (email,))
            row = cur.fetchone()
            if not row:
                return (False, None)
            usuario_id = row["usuario_id"]

        if novo_usuario:
            professor_uuid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO Professores (professor_id, usuario_id, departamento)
                VALUES (%s, %s, %s)
                """,
                (professor_uuid, usuario_id, departamento),
            )

        return (novo_usuario, email)
