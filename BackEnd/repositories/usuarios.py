import uuid

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


# Motivos de recusa. O router mapeia para status/error_code e a câmera loga.
# Sem eles, "não registrou" chega no campo sem causa — com uma máquina por
# sala, isso é indepurável.
MOTIVO_ROSTO_DESCONHECIDO = "rosto_desconhecido"
MOTIVO_CHAMADA_FECHADA = "chamada_fechada"
MOTIVO_NAO_MATRICULADO = "nao_matriculado"
MOTIVO_JA_REGISTRADO = "ja_registrado"
MOTIVO_ERRO_INTERNO = "erro_interno"


def registrar_presenca_por_face(external_image_id, chamada_id):
    """Registra presença do aluno na chamada informada.

    `external_image_id` é o aluno_id (UUID) gravado como ExternalImageId na
    collection do Rekognition. A chamada vem explícita de quem reconheceu — a
    câmera sabe qual é a chamada da sala dela. Resolver "a chamada aberta mais
    recente" globalmente gravava a presença na aula de outra sala sempre que
    duas turmas estavam em aula ao mesmo tempo.

    Devolve SEMPRE dict e nunca levanta: quem decide status HTTP é o router.
    Sucesso traz motivo=None mais os dados de notificação; recusa traz só o
    motivo.
    """
    try:
        aluno_uuid = str(uuid.UUID(str(external_image_id)))
    except (ValueError, AttributeError, TypeError):
        # Face legada (ExternalImageId derivado do nome) ou lixo. Recusa
        # explícita em vez de um WHERE que silenciosamente não casa com nada.
        logger.warning("ExternalImageId não é UUID: %r", external_image_id)
        return {"motivo": MOTIVO_ROSTO_DESCONHECIDO}

    # O try envolve o `with` INTEIRO, e não só o corpo dele: o commit roda no
    # ENCERRAMENTO do context manager (infra/database.py), depois do corpo. Com
    # o try por dentro, uma falha nesse commit — exatamente o cenário "conexão
    # derrubada no meio da transação" que este catch existe para cobrir —
    # nascia fora do alcance dele, o get_db_cursor re-levantava e a exceção
    # escapava, tornando falso o contrato "sempre dict, nunca levanta".
    # MOTIVO_ERRO_INTERNO vira 503 no router e a câmera trata como transitório,
    # tentando de novo no próximo burst; um 500 genérico seria tratado como
    # definitivo e a presença daquele aluno se perderia na aula inteira.
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                # Banco fora: transitório. Não é "rosto desconhecido" — a câmera
                # precisa distinguir para tentar de novo no próximo burst.
                return {"motivo": MOTIVO_ERRO_INTERNO}

            # Resolve por aluno_id, não por external_image_id: aproveita o
            # prefixo do unique(aluno_id, angulo) e dispensa índice novo. O
            # revogado_em cobre o caso de um FaceId sobreviver a uma
            # revogação LGPD.
            cur.execute(
                "SELECT 1 FROM Colecao_Rostos "
                "WHERE aluno_id = %s AND revogado_em IS NULL LIMIT 1",
                (aluno_uuid,),
            )
            if not cur.fetchone():
                logger.warning("Rosto sem cadastro ativo: aluno=%s", aluno_uuid)
                return {"motivo": MOTIVO_ROSTO_DESCONHECIDO}

            cur.execute(
                "SELECT chamada_id, turma_id, total_aulas FROM Chamadas "
                "WHERE chamada_id = %s AND status = 'Aberta'",
                (chamada_id,),
            )
            chamada = cur.fetchone()
            if not chamada:
                logger.warning("Chamada %s não está aberta.", chamada_id)
                return {"motivo": MOTIVO_CHAMADA_FECHADA}

            cur.execute(
                "SELECT 1 FROM Turma_Alunos WHERE turma_id = %s AND aluno_id = %s",
                (chamada["turma_id"], aluno_uuid),
            )
            if not cur.fetchone():
                logger.warning(
                    "Aluno %s não pertence à turma da chamada %s.", aluno_uuid, chamada_id
                )
                return {"motivo": MOTIVO_NAO_MATRICULADO}

            total_aulas = chamada.get("total_aulas", 1) or 1

            rows_inserted = 0
            for num_aula in range(1, total_aulas + 1):
                cur.execute(
                    """
                    INSERT INTO Presencas (chamada_id, aluno_id, num_aula, tipo_registro)
                    VALUES (%s, %s, %s, 'Reconhecimento')
                    ON CONFLICT (chamada_id, aluno_id, num_aula) DO NOTHING
                    """,
                    (chamada["chamada_id"], aluno_uuid, num_aula),
                )
                rows_inserted += cur.rowcount

            if rows_inserted == 0:
                return {"motivo": MOTIVO_JA_REGISTRADO}

            logger.info(
                "✅ Presença confirmada: aluno=%s chamada=%s", aluno_uuid, chamada_id
            )

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
                "motivo": None,
                "usuario_id": info["usuario_id"] if info else None,
                # Fallback "Aluno" e não o external_image_id: com UUID, o antigo
                # fallback colocaria um UUID no corpo do e-mail ao titular.
                "aluno_nome": info["nome"] if info else "Aluno",
                "aluno_email": info["email"] if info else None,
                "turma_nome": info["nome_disciplina"] if info else "Turma",
            }
    except Exception as e:
        # Erro real de banco (deadlock, conexão derrubada, query malformada) —
        # inclusive a falha do commit no encerramento do `with` acima, que antes
        # ficava fora do alcance deste catch.
        logger.error(
            "Erro ao registrar presença: aluno=%s chamada=%s erro=%s",
            aluno_uuid, chamada_id, e,
        )
        return {"motivo": MOTIVO_ERRO_INTERNO}
