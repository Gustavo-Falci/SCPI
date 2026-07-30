"""Trilha de consentimento LGPD — append-only.

Nenhuma função aqui faz UPDATE ou DELETE: revogar é inserir um evento novo.
O estado atual do aluno é o último evento registrado.
"""
from infra.database import get_db_cursor


def registrar_evento(aluno_id, evento, politica_versao, ip=None, user_agent=None, origem="app"):
    """Insere um evento ('aceite' ou 'revogacao') na trilha."""
    ua = user_agent[:300] if user_agent else None
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return False
        cur.execute(
            """
            INSERT INTO ConsentimentosLGPD
                (aluno_id, evento, politica_versao, ip, user_agent, origem)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (aluno_id, evento, politica_versao, ip, ua, origem),
        )
        return True


def obter_ultimo_evento(aluno_id):
    """Evento mais recente do aluno, ou None se nunca houve registro.

    O desempate por consentimento_id importa: o backfill grava com o timestamp
    antigo do cadastro e pode colidir com outro evento no mesmo instante.
    """
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            """
            SELECT evento, politica_versao, registrado_em
            FROM ConsentimentosLGPD
            WHERE aluno_id = %s
            ORDER BY registrado_em DESC, consentimento_id DESC
            LIMIT 1
            """,
            (aluno_id,),
        )
        return cur.fetchone()


def listar_trilha(aluno_id):
    """Histórico completo do aluno em ordem cronológica (export LGPD Art. 18, II)."""
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT evento, politica_versao, registrado_em, ip, origem
            FROM ConsentimentosLGPD
            WHERE aluno_id = %s
            ORDER BY registrado_em ASC, consentimento_id ASC
            """,
            (aluno_id,),
        )
        return cur.fetchall()
