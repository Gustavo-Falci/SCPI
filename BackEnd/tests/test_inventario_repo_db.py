"""Inventário biométrico: SQL sem banco + integração sob gate SCPI_RUN_DB_TESTS."""
from unittest.mock import MagicMock, patch


def _mock_cursor(fetchall_return=None):
    cur = MagicMock()
    cur.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    cm = MagicMock()
    cm.__enter__.return_value = cur
    cm.__exit__.return_value = False
    return cm, cur


def test_sql_traz_revogados_e_dados_do_aluno():
    cm, cur = _mock_cursor()
    with patch("repositories.rostos.get_db_cursor", return_value=cm):
        from repositories.rostos import listar_inventario_biometrico
        listar_inventario_biometrico()

    sql = cur.execute.call_args[0][0]
    # Sem WHERE de revogado: o revogado é justamente o que a auditoria procura.
    assert "revogado_em" in sql
    assert "WHERE" not in sql.upper()
    assert "JOIN Alunos" in sql
    assert "JOIN Usuarios" in sql
    assert "%" not in sql.replace("%s", "")


def test_sem_cursor_retorna_lista_vazia():
    cm = MagicMock()
    cm.__enter__.return_value = None
    cm.__exit__.return_value = False
    with patch("repositories.rostos.get_db_cursor", return_value=cm):
        from repositories.rostos import listar_inventario_biometrico
        assert listar_inventario_biometrico() == []


def test_integracao_traz_ativo_e_revogado(pg_academico):
    """Contra Postgres real: o join com aluno e o revogado_em vêm certos."""
    from infra.database import get_db_cursor
    from repositories.rostos import listar_inventario_biometrico

    aluno_id = pg_academico["mat_s3"]
    marca = pg_academico["marca"]
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO Colecao_Rostos (aluno_id, external_image_id, "
            "face_id_rekognition, s3_path_cadastro, angulo) "
            "VALUES (%s, %s, %s, %s, 'frontal'), (%s, %s, %s, %s, 'esquerda')",
            (aluno_id, f"ana-{marca}", f"face-ativa-{marca}", f"alunos/ativa-{marca}.jpg",
             aluno_id, f"ana-{marca}", f"face-revogada-{marca}", f"alunos/revogada-{marca}.jpg"),
        )
        cur.execute(
            "UPDATE Colecao_Rostos SET revogado_em = NOW() "
            "WHERE face_id_rekognition = %s",
            (f"face-revogada-{marca}",),
        )

    try:
        linhas = [r for r in listar_inventario_biometrico()
                  if str(r["aluno_id"]) == str(aluno_id)]
        por_face = {r["face_id_rekognition"]: r for r in linhas}

        assert por_face[f"face-ativa-{marca}"]["revogado_em"] is None
        assert por_face[f"face-revogada-{marca}"]["revogado_em"] is not None
        assert por_face[f"face-ativa-{marca}"]["nome"] == "Ana Souza"
        assert por_face[f"face-ativa-{marca}"]["angulo"] == "frontal"
    finally:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM Colecao_Rostos WHERE aluno_id = %s::uuid", (aluno_id,))
