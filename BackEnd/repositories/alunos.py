from infra.database import get_db_cursor, logger


def buscar_aluno_por_usuario_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id = %s", (usuario_id,))
        return cur.fetchone()


def buscar_aluno_completo_por_usuario_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT aluno_id, ra FROM Alunos WHERE usuario_id = %s",
            (usuario_id,),
        )
        return cur.fetchone()


def obter_aluno_e_face_status(usuario_id):
    """Retorna (ra, face_cadastrada) para um usuário Aluno; (None, False) se não houver perfil."""
    with get_db_cursor() as cur:
        if not cur:
            return (None, False)
        cur.execute("SELECT aluno_id, ra FROM Alunos WHERE usuario_id = %s", (usuario_id,))
        aluno_data = cur.fetchone()
        if not aluno_data:
            return (None, False)
        cur.execute(
            "SELECT 1 FROM Colecao_Rostos WHERE aluno_id = %s AND revogado_em IS NULL",
            (aluno_data["aluno_id"],),
        )
        face_cadastrada = cur.fetchone() is not None
        return (aluno_data["ra"], face_cadastrada)


def buscar_usuario_id_por_aluno_id(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Alunos WHERE aluno_id = %s", (aluno_id,))
        return cur.fetchone()


def existe_aluno_por_ra(ra):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute("SELECT 1 FROM Alunos WHERE ra = %s", (ra,))
        return cur.fetchone() is not None


def buscar_aluno_id_por_ra(ra):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT aluno_id FROM Alunos WHERE ra = %s", (ra,))
        row = cur.fetchone()
        return row["aluno_id"] if row else None


def listar_alunos_para_admin(turma_id=None):
    with get_db_cursor() as cur:
        if not cur:
            return []
        if turma_id:
            cur.execute(
                """
                SELECT
                    a.aluno_id, a.ra, u.nome, u.email, a.turno,
                    EXISTS(
                        SELECT 1 FROM Turma_Alunos ta
                        WHERE ta.aluno_id = a.aluno_id AND ta.turma_id = %s
                    ) as ja_matriculado
                FROM Alunos a
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                ORDER BY u.nome
                """,
                (turma_id,),
            )
        else:
            cur.execute(
                """
                SELECT a.aluno_id, a.ra, u.nome, u.email, a.turno, FALSE as ja_matriculado
                FROM Alunos a
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                ORDER BY u.nome
                """
            )
        return cur.fetchall()


def listar_alunos_por_ids(aluno_ids):
    if not aluno_ids:
        return []
    placeholders = ",".join(["%s"] * len(aluno_ids))
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            f"SELECT aluno_id, turno FROM Alunos WHERE aluno_id IN ({placeholders})",
            list(aluno_ids),
        )
        return cur.fetchall()


def obter_dashboard_aluno(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT
                u.nome AS user_nome,
                a.aluno_id,
                a.turno,
                (SELECT COUNT(*) FROM Presencas WHERE aluno_id = a.aluno_id) AS total_presencas,
                (SELECT COUNT(*) FROM Chamadas ch
                 JOIN Turma_Alunos ta ON ch.turma_id = ta.turma_id
                 WHERE ta.aluno_id = a.aluno_id) AS total_chamadas
            FROM Usuarios u
            LEFT JOIN Alunos a ON a.usuario_id = u.usuario_id
            WHERE u.usuario_id = %s
            """,
            (usuario_id,),
        )
        return cur.fetchone()


def listar_frequencias_por_aluno(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT
                t.turma_id,
                t.nome_disciplina AS nome,
                t.codigo_turma,
                COUNT(DISTINCT ch.chamada_id) FILTER (WHERE ch.status = 'Fechada') AS total_aulas,
                COUNT(DISTINCT p.presenca_id) AS presencas
            FROM Turma_Alunos ta
            JOIN Turmas t ON ta.turma_id = t.turma_id
            LEFT JOIN Chamadas ch ON ch.turma_id = t.turma_id AND ch.status = 'Fechada'
            LEFT JOIN Presencas p ON p.chamada_id = ch.chamada_id AND p.aluno_id = ta.aluno_id
            WHERE ta.aluno_id = %s
            GROUP BY t.turma_id, t.nome_disciplina, t.codigo_turma
            """,
            (aluno_id,),
        )
        return cur.fetchall()


def aluno_pertence_turma(turma_id, aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            "SELECT 1 FROM Turma_Alunos WHERE turma_id = %s AND aluno_id = %s",
            (turma_id, aluno_id),
        )
        return cur.fetchone() is not None


def aluno_matriculado_por_usuario(turma_id, usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            """
            SELECT 1 FROM Turma_Alunos ta
            JOIN Alunos a ON ta.aluno_id = a.aluno_id
            WHERE ta.turma_id = %s AND a.usuario_id = %s
            """,
            (turma_id, usuario_id),
        )
        return cur.fetchone() is not None


def atualizar_aluno(aluno_id, nome=None, email=None, ra=None, turno=None):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Alunos WHERE aluno_id = %s", (aluno_id,))
        row = cur.fetchone()
        if not row:
            return None
        usuario_id = row["usuario_id"]
        if nome is not None:
            cur.execute("UPDATE Usuarios SET nome = %s WHERE usuario_id = %s", (nome, usuario_id))
        if email is not None:
            cur.execute("UPDATE Usuarios SET email = %s WHERE usuario_id = %s", (email, usuario_id))
        if ra is not None:
            cur.execute("UPDATE Alunos SET ra = %s WHERE aluno_id = %s", (ra, aluno_id))
        if turno is not None:
            cur.execute("UPDATE Alunos SET turno = %s WHERE aluno_id = %s", (turno, aluno_id))
        return aluno_id


def excluir_aluno_em_cascata(aluno_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Alunos WHERE aluno_id = %s", (aluno_id,))
        row = cur.fetchone()
        if not row:
            return None
        usuario_id = row["usuario_id"]
        cur.execute("DELETE FROM Colecao_Rostos WHERE aluno_id = %s", (aluno_id,))
        cur.execute("DELETE FROM Turma_Alunos WHERE aluno_id = %s", (aluno_id,))
        cur.execute("DELETE FROM Presencas WHERE aluno_id = %s", (aluno_id,))
        cur.execute("DELETE FROM Alunos WHERE aluno_id = %s", (aluno_id,))
        cur.execute("DELETE FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
        return usuario_id


def criar_aluno_com_usuario(usuario_id, aluno_id, nome, email, senha_hash, ra, turno):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
            VALUES (%s, %s, %s, %s, 'Aluno', TRUE)
            """,
            (usuario_id, nome, email, senha_hash),
        )
        cur.execute(
            """
            INSERT INTO Alunos (aluno_id, usuario_id, ra, turno)
            VALUES (%s, %s, %s, %s)
            """,
            (aluno_id, usuario_id, ra, turno),
        )
        return aluno_id


def importar_aluno_csv(turma_id, nome, email, ra, turno, senha_hash):
    """Insere usuário+aluno+matrícula em uma transação. Retorna (novo_usuario, email)."""
    import uuid

    with get_db_cursor(commit=True) as cur:
        if not cur:
            return (False, None)

        user_uuid = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
            VALUES (%s, %s, %s, %s, 'Aluno', TRUE)
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
                return None
            usuario_id = row["usuario_id"]

        aluno_uuid = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO Alunos (aluno_id, usuario_id, ra, turno)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ra) DO UPDATE SET turno = EXCLUDED.turno WHERE Alunos.turno IS NULL
            RETURNING aluno_id
            """,
            (aluno_uuid, usuario_id, ra, turno),
        )
        res_aluno = cur.fetchone()
        aluno_id = res_aluno["aluno_id"] if res_aluno else None

        if not aluno_id:
            cur.execute("SELECT aluno_id FROM Alunos WHERE ra = %s", (ra,))
            row = cur.fetchone()
            if not row:
                return None
            aluno_id = row["aluno_id"]

        cur.execute(
            """
            INSERT INTO Turma_Alunos (turma_id, aluno_id)
            VALUES (%s, %s)
            ON CONFLICT (turma_id, aluno_id) DO NOTHING
            """,
            (turma_id, aluno_id),
        )

        return (novo_usuario, email)
