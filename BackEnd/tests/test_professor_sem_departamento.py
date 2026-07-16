"""Garante que o fluxo de professor não referencia mais `departamento`."""
from unittest.mock import patch


def test_criar_professor_admin_sem_campo_departamento():
    from schemas.admin import CriarProfessorAdmin, AtualizarProfessorAdmin
    assert "departamento" not in CriarProfessorAdmin.model_fields
    assert "departamento" not in AtualizarProfessorAdmin.model_fields


def test_registro_usuario_sem_campo_departamento():
    from schemas.auth import UsuarioRegistro
    assert "departamento" not in UsuarioRegistro.model_fields


def test_admin_criar_professor_chama_repo_sem_departamento():
    from routers.admin import admin_criar_professor
    from schemas.admin import CriarProfessorAdmin

    dados = CriarProfessorAdmin(nome="Prof Teste", email="prof@escola.com")
    captured = {}

    def fake_criar(usuario_id, professor_id, nome, email, senha_hash):
        captured["args"] = (usuario_id, professor_id, nome, email, senha_hash)
        return professor_id

    class _BG:
        def add_task(self, *a, **k):
            pass

    with patch("routers.admin.buscar_usuario_por_email", return_value=None), \
         patch("routers.admin.gerar_senha_temporaria", return_value="Temp123456!!"), \
         patch("routers.admin.get_password_hash", return_value="hash"), \
         patch("routers.admin.criar_professor_com_usuario", side_effect=fake_criar), \
         patch("routers.admin.audit"), \
         patch("routers.admin.client_ip", return_value="1.2.3.4"):
        resp = admin_criar_professor(
            dados=dados,
            request=object(),
            background_tasks=_BG(),
            current_user={"sub": "admin1"},
        )

    # 5 args posicionais, nenhum deles departamento
    assert len(captured["args"]) == 5
    assert resp["email"] == "prof@escola.com"
