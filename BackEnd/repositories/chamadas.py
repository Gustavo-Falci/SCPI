import datetime
import math
from datetime import datetime as dt, date

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
    """Fecha qualquer chamada aberta da turma e abre uma nova; retorna chamada_id.

    Serializa execução concorrente por turma via advisory lock transacional —
    evita race condition entre dois cliques rápidos do professor que poderiam
    criar duas chamadas com status='Aberta'. Idempotente: se ainda houver
    chamada aberta após o lock, devolve a existente.
    """
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None

        # Bloqueio cooperativo por turma — liberado no fim da transação.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (str(turma_id),))

        # Idempotência: se já existe aberta para a turma, devolve-a sem recriar.
        cur.execute(
            "SELECT chamada_id FROM Chamadas WHERE turma_id=%s AND status='Aberta' LIMIT 1",
            (turma_id,),
        )
        existente = cur.fetchone()
        if existente:
            return existente["chamada_id"]

        cur.execute(
            """
            SELECT horario_inicio, horario_fim
            FROM horarios_aulas
            WHERE turma_id = %s
              AND dia_semana = (EXTRACT(DOW FROM NOW() AT TIME ZONE 'America/Sao_Paulo')::int + 6) %% 7
            LIMIT 1
            """,
            (turma_id,),
        )
        horario = cur.fetchone()

        total_aulas = 1
        if horario and horario["horario_fim"] and horario["horario_inicio"]:
            inicio = dt.combine(date.today(), horario["horario_inicio"])
            fim    = dt.combine(date.today(), horario["horario_fim"])
            duracao_min = (fim - inicio).total_seconds() / 60
            total_aulas = max(1, math.ceil(duracao_min / 50))

        cur.execute(
            """
            INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, total_aulas, status)
            VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, %s, 'Aberta')
            RETURNING chamada_id
            """,
            (turma_id, professor_id, total_aulas),
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
                a.aluno_id AS id,
                u.nome,
                c.total_aulas,
                COALESCE(
                    ARRAY_AGG(p.num_aula ORDER BY p.num_aula)
                        FILTER (WHERE p.presenca_id IS NOT NULL),
                    ARRAY[]::smallint[]
                ) AS aulas_presentes
            FROM Chamadas c
            JOIN Turma_Alunos ta ON c.turma_id = ta.turma_id
            JOIN Alunos a ON ta.aluno_id = a.aluno_id
            JOIN Usuarios u ON a.usuario_id = u.usuario_id
            LEFT JOIN Presencas p
                ON a.aluno_id = p.aluno_id AND p.chamada_id = c.chamada_id
            WHERE c.chamada_id = %s
            GROUP BY a.aluno_id, u.nome, c.total_aulas
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
                c.total_aulas,
                (SELECT COUNT(*) FROM Presencas p2
                 WHERE p2.chamada_id = c.chamada_id AND p2.aluno_id = %s) AS aulas_presentes_count,
                CASE WHEN (
                    SELECT COUNT(*) FROM Presencas p3
                    WHERE p3.chamada_id = c.chamada_id AND p3.aluno_id = %s
                ) > 0 THEN true ELSE false END AS presente,
                COALESCE(
                    (SELECT p.tipo_registro FROM Presencas p
                     WHERE p.chamada_id = c.chamada_id AND p.aluno_id = %s
                     LIMIT 1),
                    '—'
                ) AS tipo_registro
            FROM Chamadas c
            WHERE c.turma_id = %s AND c.status = 'Fechada'
            ORDER BY c.data_chamada DESC, c.horario_inicio DESC
            """,
            (aluno_id, aluno_id, aluno_id, turma_id),
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


def listar_relatorios_chamadas(professor_id=None, turma_id=None, limit=200, offset=0,
                               data_inicio=None, data_fim=None, turno=None, semestre=None):
    sql = """
        SELECT
            c.chamada_id, c.turma_id,
            t.nome_disciplina, t.codigo_turma, t.semestre, t.turno,
            u.nome AS professor_nome,
            to_char(c.data_chamada,   'DD/MM/YYYY') AS data_chamada,
            to_char(c.horario_inicio, 'HH24:MI')    AS horario_inicio,
            to_char(c.horario_fim,    'HH24:MI')    AS horario_fim,
            c.total_aulas,
            (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = c.turma_id) AS total_alunos,
            (SELECT COUNT(*) FROM Presencas p  WHERE p.chamada_id  = c.chamada_id) AS presentes,
            (SELECT COUNT(*)
             FROM Turma_Alunos ta
             LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = c.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
             WHERE ta.turma_id = c.turma_id AND COALESCE(pc.cnt, 0) = c.total_aulas) AS presentes_alunos,
            (SELECT COUNT(*)
             FROM Turma_Alunos ta
             LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = c.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
             WHERE ta.turma_id = c.turma_id AND COALESCE(pc.cnt, 0) = 0) AS ausentes_alunos,
            (SELECT COUNT(*)
             FROM Turma_Alunos ta
             LEFT JOIN (SELECT aluno_id, COUNT(*) AS cnt FROM Presencas WHERE chamada_id = c.chamada_id GROUP BY aluno_id) pc ON pc.aluno_id = ta.aluno_id
             WHERE ta.turma_id = c.turma_id AND COALESCE(pc.cnt, 0) > 0 AND COALESCE(pc.cnt, 0) < c.total_aulas) AS parciais_alunos
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
    if data_inicio:
        sql += " AND c.data_chamada >= %s"
        params.append(data_inicio)
    if data_fim:
        sql += " AND c.data_chamada <= %s"
        params.append(data_fim)
    if turno:
        sql += " AND t.turno = %s"
        params.append(turno)
    if semestre:
        sql += " AND t.semestre = %s"
        params.append(semestre)
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
            to_char(c.horario_fim,    'HH24:MI')    AS horario_fim,
            c.total_aulas
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


def obter_chamada_por_id(chamada_id):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT c.chamada_id, c.turma_id, c.total_aulas, t.nome_disciplina
            FROM Chamadas c
            JOIN Turmas t ON t.turma_id = c.turma_id
            WHERE c.chamada_id = %s
            """,
            (chamada_id,),
        )
        return cur.fetchone()


def listar_opcoes_filtros_relatorios(professor_id):
    """Opções de filtro derivadas das chamadas Fechadas do professor.

    Mantém as opções coerentes com os dados existentes, independente de
    paginação ou filtros aplicados na listagem.
    """
    with get_db_cursor() as cur:
        if not cur:
            return {"turmas": [], "turnos": [], "semestres": []}
        cur.execute(
            """
            SELECT DISTINCT t.turma_id, t.nome_disciplina, t.codigo_turma,
                            t.turno, t.semestre
            FROM Chamadas c
            JOIN Turmas t ON t.turma_id = c.turma_id
            WHERE c.status = 'Fechada' AND c.professor_id = %s
            ORDER BY t.nome_disciplina ASC
            """,
            (professor_id,),
        )
        rows = cur.fetchall()

    turmas = [
        {"turma_id": r["turma_id"], "nome_disciplina": r["nome_disciplina"],
         "codigo_turma": r["codigo_turma"]}
        for r in rows
    ]
    turnos = sorted({r["turno"] for r in rows if r["turno"]})
    semestres = sorted({r["semestre"] for r in rows if r["semestre"]}, reverse=True)
    return {"turmas": turmas, "turnos": turnos, "semestres": semestres}


def obter_turma_relatorio(turma_id):
    """Cabeçalho da turma para o relatório de frequência."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT t.turma_id, t.nome_disciplina, t.codigo_turma, t.turno, t.semestre,
                   COALESCE(u.nome, '—') AS professor_nome
            FROM Turmas t
            LEFT JOIN Professores pr ON pr.professor_id = t.professor_id
            LEFT JOIN Usuarios    u  ON u.usuario_id   = pr.usuario_id
            WHERE t.turma_id = %s
            """,
            (turma_id,),
        )
        return cur.fetchone()


def listar_frequencia_turma(turma_id, data_inicio=None, data_fim=None):
    """Frequência acumulada de cada aluno da turma nas chamadas fechadas do período.

    LEFT JOIN em Presencas de propósito: aluno com zero presença precisa
    aparecer na lista — é justamente quem o documento existe para mostrar.

    Sem ORDER BY de propósito: services.relatorios.frequencia_turma reordena
    por (percentual, nome), então qualquer ordenação aqui seria descartada.
    """
    filtro_datas = ""
    params_datas = []
    if data_inicio:
        filtro_datas += " AND c.data_chamada >= %s"
        params_datas.append(data_inicio)
    if data_fim:
        filtro_datas += " AND c.data_chamada <= %s"
        params_datas.append(data_fim)

    sql = f"""
        WITH chamadas_periodo AS (
            SELECT c.chamada_id, c.total_aulas
            FROM Chamadas c
            WHERE c.turma_id = %s AND c.status = 'Fechada'{filtro_datas}
        )
        SELECT
            al.aluno_id,
            u.nome,
            COALESCE(al.ra, '—') AS ra,
            COALESCE((SELECT SUM(cp.total_aulas) FROM chamadas_periodo cp), 0) AS aulas_dadas,
            COALESCE((SELECT COUNT(*) FROM chamadas_periodo cp), 0) AS chamadas_count,
            COUNT(p.presenca_id) AS aulas_presentes
        FROM Turma_Alunos ta
        JOIN Alunos   al ON al.aluno_id  = ta.aluno_id
        JOIN Usuarios u  ON u.usuario_id = al.usuario_id
        LEFT JOIN Presencas p
               ON p.aluno_id = al.aluno_id
              AND p.chamada_id IN (SELECT chamada_id FROM chamadas_periodo)
        WHERE ta.turma_id = %s
        GROUP BY al.aluno_id, u.nome, al.ra
    """
    params = tuple([turma_id] + params_datas + [turma_id])

    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(sql, params)
        return cur.fetchall()
