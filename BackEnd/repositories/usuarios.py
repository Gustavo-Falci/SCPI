from infra.database import get_db_cursor, logger


def buscar_usuario_por_email(email):
    """Busca usuário pelo email para login."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT usuario_id, nome, email, senha, tipo_usuario FROM Usuarios WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def buscar_usuario_login_por_email(email):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso FROM Usuarios WHERE LOWER(email) = LOWER(%s)",
            (email,),
        )
        return cur.fetchone()


def buscar_usuario_id_por_email_lower(email):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT usuario_id FROM Usuarios WHERE LOWER(email) = %s", (email,))
        return cur.fetchone()


def buscar_usuario_id_por_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT u.usuario_id FROM Usuarios u WHERE u.usuario_id = %s", (usuario_id,))
        return cur.fetchone()


def buscar_usuario_id_por_email_simples(email):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT u.usuario_id FROM Usuarios u WHERE u.email = %s", (email,))
        return cur.fetchone()


def buscar_senha_por_usuario_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT senha FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
        return cur.fetchone()


def buscar_primeiro_acesso_por_usuario_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("SELECT primeiro_acesso FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
        return cur.fetchone()


def atualizar_senha_por_usuario_id(usuario_id, nova_senha_hash):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            "UPDATE Usuarios SET senha = %s, primeiro_acesso = FALSE WHERE usuario_id = %s",
            (nova_senha_hash, usuario_id),
        )
        return cur.rowcount


def atualizar_senha_por_email(email_lower, nova_senha_hash):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            "UPDATE Usuarios SET senha = %s, primeiro_acesso = FALSE WHERE LOWER(email) = %s",
            (nova_senha_hash, email_lower),
        )
        return cur.rowcount


def obter_professor_id(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT professor_id FROM Professores WHERE usuario_id = %s",
            (usuario_id,),
        )
        res = cur.fetchone()
        return res["professor_id"] if res else None


def registrar_presenca_por_face(external_image_id):
    """Registra presença se houver chamada aberta.

    Retorna dict com dados do aluno/turma quando bem-sucedido, ou None.
    """
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None

        cur.execute(
            "SELECT aluno_id FROM Colecao_Rostos WHERE external_image_id = %s",
            (external_image_id,),
        )
        aluno = cur.fetchone()

        if not aluno:
            logger.warning(f"Aluno não encontrado para ID: {external_image_id}")
            return None

        aluno_uuid = aluno["aluno_id"]

        cur.execute(
            """
            SELECT chamada_id, turma_id FROM Chamadas
            WHERE status = 'Aberta' ORDER BY data_criacao DESC LIMIT 1
            """
        )
        chamada = cur.fetchone()

        if not chamada:
            logger.warning("Nenhuma chamada aberta no momento.")
            return None

        cur.execute(
            "SELECT 1 FROM Turma_Alunos WHERE turma_id = %s AND aluno_id = %s",
            (chamada["turma_id"], aluno_uuid),
        )

        if not cur.fetchone():
            logger.warning(f"Aluno {external_image_id} não pertence a esta turma.")
            return None

        cur.execute(
            """
            INSERT INTO Presencas (chamada_id, aluno_id, tipo_registro)
            VALUES (%s, %s, 'Reconhecimento')
            ON CONFLICT (chamada_id, aluno_id) DO NOTHING
            """,
            (chamada["chamada_id"], aluno_uuid),
        )

        if cur.rowcount == 0:
            return None

        logger.info(f"✅ Presença confirmada: {external_image_id}")

        try:
            cur.execute(
                """
                SELECT u.nome, u.email, u.usuario_id, t.nome_disciplina
                FROM Alunos a
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                JOIN Turmas t ON t.turma_id = %s
                WHERE a.aluno_id = %s
                """,
                (chamada["turma_id"], aluno_uuid),
            )
            info = cur.fetchone()
        except Exception as e:
            logger.warning("Não foi possível buscar dados de notificação: %s", e)
            info = None

        return {
            "usuario_id": info["usuario_id"] if info else None,
            "aluno_nome": info["nome"] if info else external_image_id,
            "aluno_email": info["email"] if info else None,
            "turma_nome": info["nome_disciplina"] if info else "Turma",
        }
