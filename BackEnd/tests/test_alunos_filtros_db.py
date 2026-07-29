"""Integração dos filtros de alunos contra Postgres real (gate SCPI_RUN_DB_TESTS=1).

Toda consulta passa `q=marca` — o sufixo aleatório que a fixture põe no RA de
cada aluno. Sem esse escopo, qualquer dado pré-existente no banco de teste
entraria nas asserções e as tornaria instáveis.
"""


def _nomes(resultado):
    return sorted(item["nome"] for item in resultado["items"])


def test_semestre_recorta_por_matricula(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], semestre="3", limit=50)
    assert _nomes(resultado) == ["Ana Souza"]
    assert resultado["total"] == 1


def test_periodo_letivo_recorta_por_turma(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], periodo_letivo="2026/2", limit=50)
    assert _nomes(resultado) == ["Bruno Lima"]


def test_turma_id_recorta_pela_turma_especifica(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(
        q=pg_academico["marca"], turma_id=pg_academico["turma3"], limit=50
    )
    assert _nomes(resultado) == ["Ana Souza"]


def test_turno_esconde_aluno_sem_turno(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], turno="Matutino", limit=50)
    assert "Diego Reis" not in _nomes(resultado)
    assert len(resultado["items"]) == 3


def test_sem_turma_lista_apenas_nao_matriculados(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], situacao="sem_turma", limit=50)
    assert _nomes(resultado) == ["Carla Dias", "Diego Reis"]


def test_sem_biometria_pega_todos_quando_ninguem_tem_rosto(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], situacao="sem_biometria", limit=50)
    assert len(resultado["items"]) == 4


def test_turmas_count_reflete_matriculas(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=f"RA-mat_s3-{pg_academico['marca']}", limit=50)
    assert resultado["items"][0]["turmas_count"] == 1


def test_tem_biometria_falso_sem_rosto_cadastrado(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=f"RA-mat_s3-{pg_academico['marca']}", limit=50)
    assert resultado["items"][0]["tem_biometria"] is False


def test_total_ignora_limit(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=pg_academico["marca"], limit=1)
    assert len(resultado["items"]) == 1
    assert resultado["total"] == 4


def test_segunda_pagina_traz_o_resto(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    p1 = listar_alunos_para_admin(q=pg_academico["marca"], page=1, limit=2)
    p2 = listar_alunos_para_admin(q=pg_academico["marca"], page=2, limit=2)
    assert _nomes(p1) == ["Ana Souza", "Bruno Lima"]
    assert _nomes(p2) == ["Carla Dias", "Diego Reis"]


def test_contador_de_ocultos_com_filtro_de_semestre(pg_academico):
    from repositories.alunos import contar_alunos_pendentes

    # Semestre 3 esconde Bruno (sem. 5), Carla (sem turma) e Diego (sem turma).
    assert contar_alunos_pendentes(q=pg_academico["marca"], semestre="3") == 3


def test_contador_zero_sem_filtro_de_escopo(pg_academico):
    from repositories.alunos import contar_alunos_pendentes

    assert contar_alunos_pendentes(q=pg_academico["marca"]) == 0


def test_pendentes_lista_quem_o_filtro_escondeu(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(
        q=pg_academico["marca"], situacao="pendentes", semestre="3", limit=50
    )
    assert _nomes(resultado) == ["Bruno Lima", "Carla Dias", "Diego Reis"]


def test_pendentes_com_turno_traz_o_sem_turno(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(
        q=pg_academico["marca"], situacao="pendentes", turno="Matutino", limit=50
    )
    assert _nomes(resultado) == ["Diego Reis"]


def test_busca_textual_encontra_por_ra(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q=f"RA-mat_s3-{pg_academico['marca']}", limit=50)
    assert _nomes(resultado) == ["Ana Souza"]


def test_busca_textual_e_case_insensitive(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(q="ANA SOUZA", limit=50)
    assert "Ana Souza" in _nomes(resultado)


def test_contexto_turma_id_marca_matriculados(pg_academico):
    from repositories.alunos import listar_alunos_para_admin

    resultado = listar_alunos_para_admin(
        q=pg_academico["marca"], contexto_turma_id=pg_academico["turma3"], limit=50
    )
    por_nome = {item["nome"]: item["ja_matriculado"] for item in resultado["items"]}
    assert por_nome["Ana Souza"] is True
    assert por_nome["Bruno Lima"] is False
