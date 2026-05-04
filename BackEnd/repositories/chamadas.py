import datetime

from infra.database import get_db_cursor, logger


def fechar_chamadas_abertas_por_turma(turma_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return 0
        cur.execute(
            """
            UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
            WHERE turma_id=%s AND status='Aberta'
            """,
            (turma_id,),
        )
        return cur.rowcount


def abrir_chamada_para_turma(turma_id, professor_id):
    """Fecha qualquer chamada aberta da turma e abre uma nova; retorna chamada_id."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None
        cur.execute(
            """
            UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
            WHERE turma_id=%s AND status='Aberta'
            """,
            (turma_id,),
        )
        cur.execute(
            """
            INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status)
            VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta')
            RETURNING chamada_id
            """,
            (turma_id, professor_id),
        )
        nova = cur.fetchone()
        return nova["chamada_id"] if nova else None


def obter_chamada_aberta_com_disciplina(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT c.chamada_id, t.nome_disciplina
            FROM Chamadas c
            JOIN Turmas t ON t.turma_id = c.turma_id
            WHERE c.turma_id = %s AND c.status = 'Aberta'
            LIMIT 1
            """,
            (turma_id,),
        )
        return cur.fetchone()


def obter_chamada_aberta_por_turma(turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT chamada_id, horario_inicio FROM Chamadas
            WHERE turma_id=%s AND status='Aberta' ORDER BY data_criacao DESC LIMIT 1
            """,
            (turma_id,),
        )
        return cur.fetchone()


def obter_chamada_aberta_por_sala(sala):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT DISTINCT c.chamada_id
            FROM Chamadas c
            JOIN horarios_aulas h ON h.turma_id = c.turma_id
            WHERE c.status = 'Aberta'
            AND h.sala = %s
            AND h.dia_semana = (EXTRACT(DOW FROM CURRENT_DATE)::int + 6) %% 7
            LIMIT 1
            """,
            (sala,),
        )
        return cur.fetchone()


def listar_alunos_da_chamada(chamada_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT
                a.aluno_id as id,
                u.nome,
                CASE WHEN p.presenca_id IS NOT NULL THEN true ELSE false END as presente
            FROM Chamadas c
            JOIN Turma_Alunos ta ON c.turma_id = ta.turma_id
            JOIN Alunos a ON ta.aluno_id = a.aluno_id
            JOIN Usuarios u ON a.usuario_id = u.usuario_id
            LEFT JOIN Presencas p ON a.aluno_id = p.aluno_id AND p.chamada_id = c.chamada_id
            WHERE c.chamada_id = %s
            ORDER BY u.nome ASC
            """,
            (chamada_id,),
        )
        return cur.fetchall()


def listar_historico_chamadas_aluno(aluno_id, turma_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT
                c.chamada_id,
                to_char(c.data_chamada,   'DD/MM/YYYY') AS data_chamada,
                EXTRACT(ISODOW FROM c.data_chamada)::int AS dia_iso,
                to_char(c.horario_inicio, 'HH24:MI')    AS horario_inicio,
                to_char(c.horario_fim,    'HH24:MI')    AS horario_fim,
                CASE WHEN p.presenca_id IS NOT NULL THEN true ELSE false END AS presente,
                COALESCE(p.tipo_registro, '—') AS tipo_registro
            FROM Chamadas c
            LEFT JOIN Presencas p ON p.chamada_id = c.chamada_id AND p.aluno_id = %s
            WHERE c.turma_id = %s AND c.status = 'Fechada'
            ORDER BY c.data_chamada DESC, c.horario_inicio DESC
            """,
            (aluno_id, turma_id),
        )
        return cur.fetchall()


def fechar_chamadas_expiradas(agora=None):
    """Fecha chamadas abertas cujo horario_fim do horario_aula já passou."""
    if agora is None:
        import zoneinfo

        agora = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo"))

    fechadas = []

    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return []
            cur.execute(
                """
                SELECT DISTINCT c.chamada_id, c.turma_id, t.nome_disciplina
                FROM Chamadas c
                JOIN Turmas t ON t.turma_id = c.turma_id
                JOIN horarios_aulas h ON h.turma_id = c.turma_id
                WHERE c.status = 'Aberta'
                  AND c.data_chamada = CURRENT_DATE
                  AND h.dia_semana = %s
                  AND h.horario_fim < %s
                """,
                (agora.weekday(), agora.time()),
            )
            expiradas = cur.fetchall()

            if not expiradas:
                return []

            for row in expiradas:
                cur.execute(
                    """
                    UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                    WHERE chamada_id = %s AND status = 'Aberta'
                    """,
                    (row["chamada_id"],),
                )
                fechadas.append(dict(row))
                logger.info(
                    "Chamada %s (turma %s — %s) encerrada automaticamente por horário.",
                    row["chamada_id"],
                    row["turma_id"],
                    row["nome_disciplina"],
                )
    except Exception as e:
        logger.error("Erro ao fechar chamadas expiradas: %s", e)
        return []

    return fechadas

    return fechadas


def listar_relatorios_chamadas(professor_id=None, turma_id=None, limit=200, offset=0):
    sql = """
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
        if not cur:
            return []
        cur.execute(sql, tuple(params))
        return cur.fetchall()


def obter_relatorio_chamada(chamada_id, professor_id=None):
    sql = """
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
        sql += " AND c.professor_id = %s"
        params.append(professor_id)

    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(sql, tuple(params))
        return cur.fetchone()
