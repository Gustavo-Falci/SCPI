from infra.database import get_db_cursor


def obter_path_biometria_por_usuario(usuario_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT cr.s3_path_cadastro
            FROM Colecao_Rostos cr
            JOIN Alunos a ON cr.aluno_id = a.aluno_id
            WHERE a.usuario_id = %s AND cr.revogado_em IS NULL
            """,
            (usuario_id,),
        )
        return cur.fetchone()


def upsert_rosto(aluno_id, external_id, face_id, filename, angulo='frontal'):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            """
            INSERT INTO Colecao_Rostos (
                aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro,
                angulo, consentimento_biometrico, consentimento_data
            )
            VALUES (%s, %s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (aluno_id, angulo) DO UPDATE SET
                external_image_id = EXCLUDED.external_image_id,
                face_id_rekognition = EXCLUDED.face_id_rekognition,
                s3_path_cadastro = EXCLUDED.s3_path_cadastro,
                consentimento_biometrico = TRUE,
                consentimento_data = CURRENT_TIMESTAMP,
                revogado_em = NULL
            """,
            (aluno_id, external_id, face_id, filename, angulo),
        )
        return True


def revogar_rosto_por_aluno(aluno_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            """
            UPDATE Colecao_Rostos
            SET revogado_em = CURRENT_TIMESTAMP,
                consentimento_biometrico = FALSE,
                face_id_rekognition = NULL,
                s3_path_cadastro = NULL
            WHERE aluno_id = %s
            """,
            (aluno_id,),
        )
        return cur.rowcount


def listar_rostos_ativos_por_aluno(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT face_id_rekognition, s3_path_cadastro, angulo
            FROM Colecao_Rostos
            WHERE aluno_id = %s AND revogado_em IS NULL
            """,
            (aluno_id,),
        )
        return cur.fetchall()


def obter_path_foto_perfil_aluno(aluno_id):
    """Retorna o s3_path_cadastro do primeiro ângulo ativo (foto de referência para export LGPD)."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT s3_path_cadastro
            FROM Colecao_Rostos
            WHERE aluno_id = %s
              AND revogado_em IS NULL
              AND s3_path_cadastro IS NOT NULL
            ORDER BY angulo
            LIMIT 1
            """,
            (aluno_id,),
        )
        row = cur.fetchone()
        return row["s3_path_cadastro"] if row else None
