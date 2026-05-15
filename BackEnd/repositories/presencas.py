from infra.database import get_db_cursor


def contar_presentes_por_chamada(chamada_id):
    with get_db_cursor() as cur:
        if not cur:
            return 0
        cur.execute(
            "SELECT COUNT(DISTINCT aluno_id) AS presentes FROM Presencas WHERE chamada_id=%s",
            (chamada_id,),
        )
        row = cur.fetchone()
        return row["presentes"] if row else 0


def listar_alunos_presenca_chamada(chamada_id, turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT
                al.aluno_id,
                u.nome,
                COALESCE(al.ra, '—')               AS ra,
                c.total_aulas,
                COUNT(p.presenca_id)                AS aulas_presentes_count,
                COUNT(p.presenca_id) > 0            AS presente,
                COALESCE(MAX(p.tipo_registro), '—') AS tipo_registro
            FROM Chamadas c
            JOIN Turma_Alunos ta ON ta.turma_id = c.turma_id
            JOIN Alunos   al ON al.aluno_id   = ta.aluno_id
            JOIN Usuarios u  ON u.usuario_id  = al.usuario_id
            LEFT JOIN Presencas p ON p.aluno_id = al.aluno_id AND p.chamada_id = c.chamada_id
            WHERE c.chamada_id = %s AND c.turma_id = %s
            GROUP BY al.aluno_id, u.nome, al.ra, c.total_aulas
            ORDER BY u.nome ASC
            """,
            (chamada_id, turma_id),
        )
        return cur.fetchall()


def contar_alunos_da_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return 0
        cur.execute("SELECT COUNT(*) as total FROM Turma_Alunos WHERE turma_id=%s", (turma_id,))
        row = cur.fetchone()
        return row["total"] if row else 0


def ajustar_presencas_chamada(chamada_id, alunos_presencas):
    """alunos_presencas: list of dicts with {aluno_id, aulas_presentes: list[int]}"""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return
        for item in alunos_presencas:
            cur.execute(
                "DELETE FROM Presencas WHERE chamada_id=%s AND aluno_id=%s",
                (chamada_id, item["aluno_id"]),
            )
            for num_aula in item.get("aulas_presentes", []):
                cur.execute(
                    """
                    INSERT INTO Presencas (chamada_id, aluno_id, num_aula, tipo_registro)
                    VALUES (%s, %s, %s, 'Manual')
                    """,
                    (chamada_id, item["aluno_id"], num_aula),
                )
