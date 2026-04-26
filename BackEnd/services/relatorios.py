from typing import Optional

from fastapi import HTTPException

from infra.database import get_db_cursor


def resumo_presenca(total: int, presentes: int) -> dict:
    return {
        "ausentes": total - presentes,
        "percentual": round(presentes / total * 100) if total > 0 else 0,
    }


_RELATORIO_LISTA_SQL = """
    SELECT
        c.chamada_id, c.turma_id,
        t.nome_disciplina, t.codigo_turma, t.semestre, t.turno,
        u.nome AS professor_nome,
        to_char(c.data_chamada,   'DD/MM/YYYY') AS data_chamada,
        to_char(c.horario_inicio, 'HH24:MI')    AS horario_inicio,
        to_char(c.horario_fim,    'HH24:MI')    AS horario_fim,
        (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = c.turma_id) AS total_alunos,
        (SELECT COUNT(*) FROM Presencas p  WHERE p.chamada_id  = c.chamada_id) AS presentes
    FROM Chamadas c
    JOIN Turmas     t  ON t.turma_id     = c.turma_id
    JOIN Professores pr ON pr.professor_id = c.professor_id
    JOIN Usuarios    u  ON u.usuario_id   = pr.usuario_id
    WHERE c.status = 'Fechada'
"""


def listar_relatorios(professor_id: Optional[str] = None, turma_id: Optional[str] = None,
                      limit: int = 200, offset: int = 0):
    sql = _RELATORIO_LISTA_SQL
    params = []
    if professor_id:
        sql += " AND c.professor_id = %s"
        params.append(professor_id)
    if turma_id:
        sql += " AND c.turma_id = %s"
        params.append(turma_id)
    sql += " ORDER BY c.data_chamada DESC, c.horario_inicio DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()

    return [{**dict(r), **resumo_presenca(r["total_alunos"], r["presentes"])} for r in rows]


def detalhe_relatorio(chamada_id: str, professor_id: Optional[str] = None):
    sql_chamada = """
        SELECT
            c.chamada_id, c.turma_id,
            t.nome_disciplina, t.codigo_turma, t.semestre, t.turno,
            u.nome AS professor_nome,
            to_char(c.data_chamada,   'DD/MM/YYYY') AS data_chamada,
            to_char(c.horario_inicio, 'HH24:MI')    AS horario_inicio,
            to_char(c.horario_fim,    'HH24:MI')    AS horario_fim
        FROM Chamadas c
        JOIN Turmas     t  ON t.turma_id     = c.turma_id
        JOIN Professores pr ON pr.professor_id = c.professor_id
        JOIN Usuarios    u  ON u.usuario_id   = pr.usuario_id
        WHERE c.chamada_id = %s AND c.status = 'Fechada'
    """
    params = [chamada_id]
    if professor_id:
        sql_chamada += " AND c.professor_id = %s"
        params.append(professor_id)

    with get_db_cursor() as cur:
        cur.execute(sql_chamada, tuple(params))
        chamada = cur.fetchone()
        if not chamada:
            raise HTTPException(status_code=404, detail="Chamada não encontrada.")

        cur.execute(
            """
            SELECT
                al.aluno_id,
                u.nome,
                COALESCE(al.ra, '—')          AS ra,
                CASE WHEN p.presenca_id IS NOT NULL THEN true ELSE false END AS presente,
                COALESCE(p.tipo_registro, '—') AS tipo_registro
            FROM Turma_Alunos ta
            JOIN Alunos   al ON al.aluno_id   = ta.aluno_id
            JOIN Usuarios u  ON u.usuario_id  = al.usuario_id
            LEFT JOIN Presencas p ON p.aluno_id = al.aluno_id AND p.chamada_id = %s
            WHERE ta.turma_id = %s
            ORDER BY u.nome ASC
            """,
            (chamada_id, chamada["turma_id"]),
        )
        alunos = cur.fetchall()

    total = len(alunos)
    presentes = sum(1 for a in alunos if a["presente"])
    return {
        **dict(chamada),
        "total_alunos": total,
        "presentes": presentes,
        **resumo_presenca(total, presentes),
        "alunos": [dict(a) for a in alunos],
    }
