"""Presença amarrada à chamada informada (gate SCPI_RUN_DB_TESTS=1).

O caso que motivou: com duas turmas em aula ao mesmo tempo, o backend resolvia
"a chamada aberta mais recente do sistema inteiro" e gravava a presença na aula
de outra sala. Estes testes travam a resolução explícita por chamada_id.
"""
import datetime
from contextlib import contextmanager

from infra.database import get_db_cursor


def _abrir_chamada(turma_id, total_aulas=1):
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Chamadas (turma_id, professor_id, data_chamada, "
            "horario_inicio, total_aulas, status) "
            "VALUES (%s, NULL, CURRENT_DATE, CURRENT_TIME, %s, 'Aberta') "
            "RETURNING chamada_id",
            (turma_id, total_aulas),
        )
        return cur.fetchone()["chamada_id"]


def _fechar_chamada(chamada_id):
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE Chamadas SET status='Fechada' WHERE chamada_id = %s",
            (chamada_id,),
        )


def _cadastrar_rosto(aluno_id, revogado=False):
    """Cria o vínculo biométrico do aluno com ExternalImageId = aluno_id."""
    revogado_em = datetime.datetime.utcnow() if revogado else None
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Colecao_Rostos (aluno_id, external_image_id, "
            "face_id_rekognition, s3_path_cadastro, angulo, "
            "consentimento_biometrico, revogado_em) "
            "VALUES (%s, %s, 'face-teste', 'alunos/teste/foto.jpg', 'frontal', "
            "TRUE, %s)",
            (aluno_id, str(aluno_id), revogado_em),
        )


def _alunos_com_presenca(chamada_id):
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT aluno_id FROM Presencas WHERE chamada_id = %s", (chamada_id,)
        )
        return sorted(str(r["aluno_id"]) for r in cur.fetchall())


def test_grava_na_chamada_informada_mesmo_com_outra_aberta(pg_academico):
    """O teste que o sistema não tinha: duas aulas ao mesmo tempo."""
    from repositories.usuarios import registrar_presenca_por_face

    _cadastrar_rosto(pg_academico["mat_s3"])
    chamada_a = _abrir_chamada(pg_academico["turma3"])
    # Aberta DEPOIS: sob a resolução antiga (ORDER BY data_criacao DESC) era
    # esta que vencia, e o aluno da turma3 era recusado por "não é da turma".
    chamada_b = _abrir_chamada(pg_academico["turma5"])

    resultado = registrar_presenca_por_face(
        str(pg_academico["mat_s3"]), chamada_a
    )

    assert resultado["motivo"] is None
    assert _alunos_com_presenca(chamada_a) == [str(pg_academico["mat_s3"])]
    assert _alunos_com_presenca(chamada_b) == []


def test_chamada_fechada_recusa(pg_academico):
    from repositories.usuarios import (
        MOTIVO_CHAMADA_FECHADA,
        registrar_presenca_por_face,
    )

    _cadastrar_rosto(pg_academico["mat_s3"])
    chamada = _abrir_chamada(pg_academico["turma3"])
    _fechar_chamada(chamada)

    resultado = registrar_presenca_por_face(str(pg_academico["mat_s3"]), chamada)

    assert resultado["motivo"] == MOTIVO_CHAMADA_FECHADA
    assert _alunos_com_presenca(chamada) == []


def test_aluno_de_outra_turma_recusa(pg_academico):
    from repositories.usuarios import (
        MOTIVO_NAO_MATRICULADO,
        registrar_presenca_por_face,
    )

    _cadastrar_rosto(pg_academico["mat_s5"])
    chamada = _abrir_chamada(pg_academico["turma3"])

    resultado = registrar_presenca_por_face(str(pg_academico["mat_s5"]), chamada)

    assert resultado["motivo"] == MOTIVO_NAO_MATRICULADO
    assert _alunos_com_presenca(chamada) == []


def test_reenvio_devolve_ja_registrado_sem_duplicar(pg_academico):
    from repositories.usuarios import (
        MOTIVO_JA_REGISTRADO,
        registrar_presenca_por_face,
    )

    _cadastrar_rosto(pg_academico["mat_s3"])
    chamada = _abrir_chamada(pg_academico["turma3"], total_aulas=2)

    primeiro = registrar_presenca_por_face(str(pg_academico["mat_s3"]), chamada)
    segundo = registrar_presenca_por_face(str(pg_academico["mat_s3"]), chamada)

    assert primeiro["motivo"] is None
    assert segundo["motivo"] == MOTIVO_JA_REGISTRADO
    # total_aulas=2 gera duas linhas na primeira vez e nenhuma na segunda.
    assert len(_alunos_com_presenca(chamada)) == 2


def test_rosto_revogado_recusa(pg_academico):
    from repositories.usuarios import (
        MOTIVO_ROSTO_DESCONHECIDO,
        registrar_presenca_por_face,
    )

    _cadastrar_rosto(pg_academico["mat_s3"], revogado=True)
    chamada = _abrir_chamada(pg_academico["turma3"])

    resultado = registrar_presenca_por_face(str(pg_academico["mat_s3"]), chamada)

    assert resultado["motivo"] == MOTIVO_ROSTO_DESCONHECIDO
    assert _alunos_com_presenca(chamada) == []


def test_aluno_sem_rosto_cadastrado_recusa(pg_academico):
    from repositories.usuarios import (
        MOTIVO_ROSTO_DESCONHECIDO,
        registrar_presenca_por_face,
    )

    chamada = _abrir_chamada(pg_academico["turma3"])

    resultado = registrar_presenca_por_face(str(pg_academico["mat_s3"]), chamada)

    assert resultado["motivo"] == MOTIVO_ROSTO_DESCONHECIDO


def test_external_image_id_nao_uuid_recusa_sem_tocar_no_banco():
    """Face legada (ExternalImageId derivado do nome) ou lixo.

    Sem fixture de propósito: a recusa acontece antes de qualquer conexão.
    """
    from repositories.usuarios import (
        MOTIVO_ROSTO_DESCONHECIDO,
        registrar_presenca_por_face,
    )

    resultado = registrar_presenca_por_face("Joao_da_Silva", 1)

    assert resultado["motivo"] == MOTIVO_ROSTO_DESCONHECIDO


def test_erro_de_banco_devolve_motivo_erro_interno_sem_levantar(monkeypatch):
    """Erro real de banco (deadlock, conexão derrubada, query malformada) não
    pode escapar como exceção não tratada.

    `get_db_cursor` faz rollback e RE-LEVANTA qualquer exceção do corpo do
    `with` (infra/database.py). Sem tratamento aqui, essa exceção subiria até
    o router como um 500 genérico — e a câmera, que usa o 503/MOTIVO_ERRO_INTERNO
    para saber que a falha é transitória e tentar de novo no próximo burst,
    trataria como definitivo. A presença daquele aluno se perderia na aula
    inteira. Este teste não precisa de Postgres: o cursor é falso e o
    `execute` levanta de propósito.
    """
    import repositories.usuarios as usuarios_mod
    from repositories.usuarios import MOTIVO_ERRO_INTERNO, registrar_presenca_por_face

    class _CursorQuebrado:
        def execute(self, *args, **kwargs):
            raise Exception("conexão derrubada no meio da transação")

    @contextmanager
    def _get_db_cursor_quebrado(commit=False):
        yield _CursorQuebrado()

    monkeypatch.setattr(usuarios_mod, "get_db_cursor", _get_db_cursor_quebrado)

    resultado = registrar_presenca_por_face(
        "11111111-1111-1111-1111-111111111111", 1
    )

    assert resultado["motivo"] == MOTIVO_ERRO_INTERNO
