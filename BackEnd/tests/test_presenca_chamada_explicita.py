"""Presença amarrada à chamada informada (gate SCPI_RUN_DB_TESTS=1).

O caso que motivou: com duas turmas em aula ao mesmo tempo, o backend resolvia
"a chamada aberta mais recente do sistema inteiro" e gravava a presença na aula
de outra sala. Estes testes travam a resolução explícita por chamada_id.
"""
from core.tempo import agora_utc
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
    revogado_em = agora_utc() if revogado else None
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


ALUNO_UUID_FALSO = "11111111-1111-1111-1111-111111111111"


class _CursorQuebrado:
    """Cursor cuja primeira query já morre (conexão derrubada, deadlock)."""

    rowcount = 0

    def execute(self, *args, **kwargs):
        raise Exception("conexão derrubada no meio da transação")


class _CursorOk:
    """Cursor falso que responde o bastante para o fluxo chegar ao commit.

    Responde por trecho do SQL em vez de por ordem de chamada: assim o teste
    não quebra quando as consultas mudam de posição dentro da função.
    """

    rowcount = 1

    def __init__(self):
        self._ultimo_sql = ""

    def execute(self, sql, params=None):
        self._ultimo_sql = sql

    def fetchone(self):
        if "FROM Chamadas" in self._ultimo_sql:
            return {"chamada_id": 1, "turma_id": "turma-1", "total_aulas": 1}
        if "FROM Alunos" in self._ultimo_sql:
            return {
                "nome": "Ana Souza", "email": "ana@teste.local",
                "usuario_id": "usuario-1", "nome_disciplina": "Cálculo I",
            }
        # Colecao_Rostos / Turma_Alunos: basta ser verdadeiro.
        return {"?column?": 1}


def _fabricar_get_db_cursor(cursor, ao_commitar=None):
    """Substituto de `get_db_cursor` com a MESMA estrutura da implementação real.

    `infra/database.py` faz `yield cursor` e SÓ DEPOIS `conn.commit()` — ou
    seja, o commit roda no ENCERRAMENTO do context manager, fora do corpo do
    `with`. Um stub que só produz o cursor não consegue reproduzir a falha do
    commit, e um teste escrito em cima dele passa mesmo com a função deixando a
    exceção escapar. Quando o corpo do `with` levanta, o commit não é
    alcançado (a real faz rollback e re-levanta) — este stub reproduz isso
    naturalmente.
    """

    @contextmanager
    def _fake_get_db_cursor(commit=False):
        yield cursor
        if commit and ao_commitar is not None:
            ao_commitar()

    return _fake_get_db_cursor


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

    monkeypatch.setattr(
        usuarios_mod, "get_db_cursor", _fabricar_get_db_cursor(_CursorQuebrado())
    )

    resultado = registrar_presenca_por_face(ALUNO_UUID_FALSO, 1)

    assert resultado["motivo"] == MOTIVO_ERRO_INTERNO


def test_falha_na_busca_de_notificacao_nao_ameaca_a_presenca(monkeypatch):
    """A busca de dados de notificação é best-effort e não pode derrubar a
    presença já gravada.

    Enquanto essa consulta rodava dentro do `with` de escrita, uma falha dela
    deixava a transação ABORTADA no Postgres — e o `conn.commit()` do
    encerramento virava um ROLLBACK silencioso (psycopg2 não levanta nesse
    caso). As presenças sumiam, mas a função devolvia motivo=None, o router
    respondia 200 e a câmera marcava o aluno como definitivo: o aluno
    desaparecia da chamada inteira sem erro em lugar nenhum.

    A ordem dos eventos é o coração do teste: o commit da escrita tem que
    acontecer ANTES da leitura de notificação, em transação separada.
    """
    import repositories.usuarios as usuarios_mod
    from repositories.usuarios import registrar_presenca_por_face

    eventos = []

    @contextmanager
    def _get_db_cursor_leitura_quebrada(commit=False):
        if commit:
            yield _CursorOk()
            eventos.append("commit_da_escrita")
        else:
            eventos.append("leitura_de_notificacao")
            yield _CursorQuebrado()

    monkeypatch.setattr(
        usuarios_mod, "get_db_cursor", _get_db_cursor_leitura_quebrada
    )

    resultado = registrar_presenca_por_face(ALUNO_UUID_FALSO, 1)

    assert resultado["motivo"] is None
    assert eventos == ["commit_da_escrita", "leitura_de_notificacao"]
    # Defaults: o e-mail simplesmente não sai, mas a presença está gravada.
    assert resultado["aluno_nome"] == "Aluno"
    assert resultado["aluno_email"] is None
    assert resultado["usuario_id"] is None
    assert resultado["turma_nome"] == "Turma"


def test_falha_no_commit_de_encerramento_tambem_vira_erro_interno(monkeypatch):
    """O caminho que o stub antigo não conseguia enxergar: o commit falha.

    O commit é executado pelo `get_db_cursor` DEPOIS do corpo do `with`. Com o
    `try/except` só por dentro do `with`, a exceção do commit nascia fora do
    alcance do catch, o `get_db_cursor` a re-levantava e ela escapava da
    função — o contrato "devolve SEMPRE dict e nunca levanta" era falso
    justamente no cenário que o catch dizia cobrir (conexão derrubada no meio
    da transação). Para a câmera, essa exceção viraria um 500 genérico
    (definitivo) em vez de 503 (transitório), e o aluno ficaria ausente na aula
    inteira sem ninguém perceber.
    """
    import repositories.usuarios as usuarios_mod
    from repositories.usuarios import MOTIVO_ERRO_INTERNO, registrar_presenca_por_face

    def _commit_quebrado():
        raise Exception("conexão derrubada ao confirmar a transação")

    monkeypatch.setattr(
        usuarios_mod,
        "get_db_cursor",
        _fabricar_get_db_cursor(_CursorOk(), ao_commitar=_commit_quebrado),
    )

    resultado = registrar_presenca_por_face(ALUNO_UUID_FALSO, 1)

    assert resultado["motivo"] == MOTIVO_ERRO_INTERNO
