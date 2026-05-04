from infra.database import get_db_cursor


def obter_rosto_ativo_por_aluno(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT face_id_rekognition, s3_path_cadastro
            FROM Colecao_Rostos
            WHERE aluno_id = %s AND revogado_em IS NULL
            """,
            (aluno_id,),
        )
        return cur.fetchone()


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


def existe_rosto_ativo_por_aluno(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute(
            "SELECT 1 FROM Colecao_Rostos WHERE aluno_id = %s AND revogado_em IS NULL",
            (aluno_id,),
        )
        return cur.fetchone() is not None


def existe_qualquer_rosto_por_aluno(aluno_id):
    with get_db_cursor() as cur:
        if not cur:
            return False
        cur.execute("SELECT 1 FROM Colecao_Rostos WHERE aluno_id = %s", (aluno_id,))
        return cur.fetchone() is not None


def upsert_rosto(aluno_id, external_id, face_id, filename):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute("SELECT 1 FROM Colecao_Rostos WHERE aluno_id = %s", (aluno_id,))
        exists = cur.fetchone()

        if exists:
            cur.execute(
                """
                UPDATE Colecao_Rostos
                SET external_image_id = %s,
                    face_id_rekognition = %s,
                    s3_path_cadastro = %s,
                    consentimento_biometrico = TRUE,
                    consentimento_data = CURRENT_TIMESTAMP,
                    revogado_em = NULL
                WHERE aluno_id = %s
                """,
                (external_id, face_id, filename, aluno_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO Colecao_Rostos (
                    aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro,
                    consentimento_biometrico, consentimento_data
                )
                VALUES (%s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                """,
                (aluno_id, external_id, face_id, filename),
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
