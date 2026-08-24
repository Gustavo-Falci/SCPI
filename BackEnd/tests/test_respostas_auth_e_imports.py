"""Prova de fidelidade dos modelos de saída do lote 5: auth, imports e o dossiê.

Fecha a etapa B. São três famílias com riscos diferentes:

- **auth**: duas rotas emitem segredo no corpo (`/refresh` devolve o par de
  tokens, `/verificar-codigo` devolve o `reset_token`); as outras devolvem só
  `mensagem`, e a mensagem genérica do `/esqueci-senha` é uma decisão de
  segurança — o formato tem que ser idêntico para e-mail que existe e para
  e-mail que não existe, senão a resposta vira oráculo de enumeração.
- **imports CSV**: 200 não significa "tudo entrou". `erros` é lista de textos
  `"Linha N: motivo"` e a linha com erro é pulada.
- **dossiê LGPD**: `formato=json` devolve o corpo estruturado; o default
  (`zip`) devolve bytes, e por isso a rota declara os dois `content`.

Duas rotas de auth não entram: `/auth/register` e `/auth/register-aluno-com-face`
estão desativadas e SEMPRE levantam 403 — documentar um corpo de 200 nelas seria
documentar o que não existe. Ficam em `ROTAS_SEM_200`, e os testes daqui provam
que o 403 é incondicional.
"""
import asyncio
import datetime
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import jwt as _jwt
import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from tests.conformidade_respostas import assert_resposta_conforme

ADMIN = {"sub": "admin@teste.local", "role": "Admin"}
ALUNO_USUARIO_ID = "3f9c1d7a-2b55-4e10-9a88-77c0d1b4e520"
ALUNO = {"sub": ALUNO_USUARIO_ID, "role": "Aluno"}
ALUNO_ID = uuid.UUID("6f3a1c2e-8b44-4d19-9e77-2a5c0d1b4f83")
TURMA_ID = "1b2c3d4e-5f60-4711-8899-aabbccddeeff"


def _pedido(caminho="/auth/teste"):
    """`Request` de verdade: quase toda rota de auth tem `@limiter.limit`, e o
    slowapi recusa `MagicMock` ("parameter `request` must be an instance of
    starlette.requests.Request"). O storage do limiter já é o de memória, pela
    fixture de sessão do conftest."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": caminho,
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.7", 45678),
        }
    )


# --------------------------------------------------------------------------
# auth — as duas rotas desativadas
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "caminho",
    ["/auth/register", "/auth/register-aluno-com-face"],
)
def test_rota_desativada_nunca_devolve_200(caminho):
    """Não há entrada, estado ou role que faça estas rotas devolverem corpo.

    É o que sustenta a isenção em `ROTAS_SEM_200`: se um dia uma delas voltar a
    responder 200, este teste reprova e a isenção deixa de valer.
    """
    from routers.auth import register, register_aluno_com_face
    from schemas.auth import UsuarioRegistro

    if caminho == "/auth/register":
        usuario = UsuarioRegistro(
            nome="Bruno Lima",
            email="bruno@escola.com.br",
            senha="SenhaForte#2026",
            tipo_usuario="Aluno",
        )
        with pytest.raises(HTTPException) as erro:
            register(request=_pedido(caminho), usuario=usuario)
    else:
        with pytest.raises(HTTPException) as erro:
            asyncio.run(register_aluno_com_face(request=_pedido(caminho)))

    assert erro.value.status_code == 403


# --------------------------------------------------------------------------
# auth — sessão e senha
# --------------------------------------------------------------------------
def test_refresh_conforme():
    """A rotação devolve o par novo; o refresh antigo já não vale mais."""
    from routers.auth import refresh_access_token
    from schemas.auth import RefreshRequest

    linha = {
        "usuario_id": ALUNO_USUARIO_ID,
        "email": "bruno@escola.com.br",
        "tipo_usuario": "Aluno",
    }
    with patch("routers.auth.rotacionar_refresh_token", return_value={"row": linha}):
        resposta = refresh_access_token(
            request=_pedido("/auth/refresh"),
            response=Response(),
            body=RefreshRequest(refresh_token="refresh-antigo-com-16-chars"),
            scpi_refresh=None,
        )

    assert resposta["token_type"] == "bearer"
    # O refresh devolvido é o NOVO: devolver o mesmo texto recebido significaria
    # rotação que não rotacionou.
    assert resposta["refresh_token"] != "refresh-antigo-com-16-chars"
    assert_resposta_conforme(resposta, "POST", "/auth/refresh")


def test_logout_conforme():
    """Resposta fixa mesmo quando não havia o que revogar — a limpeza local dos
    cookies é autoritativa por design."""
    from routers.auth import logout
    from schemas.auth import RefreshRequest

    with patch("routers.auth.revogar_refresh_token", return_value=0):
        resposta = logout(
            response=Response(),
            body=RefreshRequest(refresh_token="refresh-de-teste-16"),
            current_user=ALUNO,
            scpi_refresh=None,
        )

    assert_resposta_conforme(resposta, "POST", "/auth/logout")


def test_alterar_senha_conforme():
    from routers.auth import alterar_senha
    from schemas.auth import AlterarSenhaBody

    with patch("routers.auth.buscar_senha_por_usuario_id", return_value={"senha": "hash-antigo"}), \
         patch("routers.auth.verify_password", return_value=True), \
         patch("routers.auth.senha_comprometida", return_value=False), \
         patch("routers.auth.get_password_hash", return_value="hash-novo"), \
         patch("routers.auth.atualizar_senha_por_usuario_id"), \
         patch("routers.auth.revogar_todos_refresh_tokens", return_value=2):
        resposta = alterar_senha(
            AlterarSenhaBody(senha_atual="SenhaAntiga#1", nova_senha="SenhaNova#2026"),
            current_user=ALUNO,
        )

    assert_resposta_conforme(resposta, "POST", "/auth/alterar-senha")


def test_alterar_senha_primeiro_acesso_conforme():
    from routers.auth import alterar_senha_primeiro_acesso
    from schemas.auth import PrimeiroAcessoSenhaBody

    with patch("routers.auth.buscar_primeiro_acesso_por_usuario_id",
               return_value={"primeiro_acesso": True}), \
         patch("routers.auth.senha_comprometida", return_value=False), \
         patch("routers.auth.get_password_hash", return_value="hash-novo"), \
         patch("routers.auth.atualizar_senha_por_usuario_id"), \
         patch("routers.auth.revogar_todos_refresh_tokens", return_value=1):
        resposta = alterar_senha_primeiro_acesso(
            PrimeiroAcessoSenhaBody(nova_senha="SenhaNova#2026"),
            current_user=ALUNO,
        )

    assert_resposta_conforme(resposta, "POST", "/auth/alterar-senha-primeiro-acesso")


@pytest.mark.parametrize("existe", [True, False], ids=["email-existe", "email-nao-existe"])
def test_esqueci_senha_conforme(existe):
    """A resposta é a MESMA nos dois casos — corpo diferente viraria oráculo de
    enumeração de contas. É por isso que o modelo é o genérico `MensagemResposta`
    e não um envelope com "enviado: true/false"."""
    from routers.auth import esqueci_senha
    from schemas.auth import EsqueciSenhaBody

    usuario = {"usuario_id": ALUNO_USUARIO_ID} if existe else None
    with patch("routers.auth.buscar_usuario_id_por_email_lower", return_value=usuario), \
         patch("routers.auth.substituir_codigo_reset"), \
         patch("routers.auth._resend"):
        resposta = esqueci_senha(
            request=_pedido("/auth/esqueci-senha"),
            body=EsqueciSenhaBody(email="bruno@escola.com.br"),
        )

    assert resposta["mensagem"].startswith("Se o e-mail existir")
    assert_resposta_conforme(resposta, "POST", "/auth/esqueci-senha")


def test_verificar_codigo_conforme():
    """Devolve o `reset_token` e nada mais: nem e-mail, nem id do código, nem
    prazo — cada campo extra aqui é dado a mais num corpo que carrega segredo."""
    from routers.auth import verificar_codigo
    from schemas.auth import VerificarCodigoBody

    linha = {
        "id": 77,
        "expires_at": datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=10),
    }
    with patch("routers.auth.buscar_codigo_reset_valido", return_value=linha), \
         patch("routers.auth.marcar_codigo_reset_usado"):
        resposta = verificar_codigo(
            request=_pedido("/auth/verificar-codigo"),
            body=VerificarCodigoBody(email="bruno@escola.com.br", codigo="123456"),
        )

    assert resposta["reset_token"]
    assert_resposta_conforme(resposta, "POST", "/auth/verificar-codigo")


def test_redefinir_senha_conforme():
    from core.auth_utils import ALGORITHM, SECRET_KEY
    from routers.auth import redefinir_senha
    from schemas.auth import RedefinirSenhaBody

    reset_token = _jwt.encode(
        {
            "sub": "bruno@escola.com.br",
            "type": "password_reset",
            "jti": "77",
            "exp": datetime.datetime.now(datetime.timezone.utc) + timedelta(minutes=10),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with patch("routers.auth.consumir_token_reset", return_value=True), \
         patch("routers.auth.senha_comprometida", return_value=False), \
         patch("routers.auth.get_password_hash", return_value="hash-novo"), \
         patch("routers.auth.atualizar_senha_por_email"), \
         patch("routers.auth.buscar_usuario_id_por_email_lower",
               return_value={"usuario_id": ALUNO_USUARIO_ID}), \
         patch("routers.auth.revogar_todos_refresh_tokens", return_value=3):
        resposta = redefinir_senha(
            request=_pedido("/auth/redefinir-senha"),
            body=RedefinirSenhaBody(reset_token=reset_token, nova_senha="SenhaNova#2026"),
        )

    assert_resposta_conforme(resposta, "POST", "/auth/redefinir-senha")


# --------------------------------------------------------------------------
# imports CSV — 200 não quer dizer "tudo entrou"
# --------------------------------------------------------------------------
class _ResultadoFalso:
    """Espelha `ResultadoImport` de `services/import_alunos.py`."""

    def __init__(self):
        self.importados = 2
        self.duplicados = 1
        self.matriculados = 3
        self.emails_enviados = 2
        self.erros = ["Linha 4: RA já cadastrado para outro aluno."]


def _upload_csv():
    arquivo = MagicMock()
    arquivo.filename = "alunos.csv"

    async def _read():
        return b"nome;email;ra\n"

    arquivo.read = _read
    return arquivo


def test_importar_alunos_na_turma_conforme():
    from fastapi import BackgroundTasks

    from routers.admin import admin_importar_alunos_csv

    with patch("routers.admin.processar_csv_alunos", return_value=_ResultadoFalso()):
        resposta = asyncio.run(
            admin_importar_alunos_csv(
                TURMA_ID,
                request=_pedido("/admin/turmas/x/importar-alunos"),
                background_tasks=BackgroundTasks(),
                file=_upload_csv(),
                current_user=ADMIN,
            )
        )

    # Linha com erro não aborta o import: veio 200 com erro dentro.
    assert resposta["erros"] == ["Linha 4: RA já cadastrado para outro aluno."]
    assert_resposta_conforme(resposta, "POST", "/admin/turmas/{turma_id}/importar-alunos")


def test_importar_alunos_global_conforme():
    """Aqui os números vêm separados, e `importados` != `matriculados` é
    situação normal: aluno que já existia e só ganhou matrícula."""
    from fastapi import BackgroundTasks

    from routers.admin import admin_importar_alunos_csv_global

    with patch("routers.admin.processar_csv_alunos", return_value=_ResultadoFalso()):
        resposta = asyncio.run(
            admin_importar_alunos_csv_global(
                request=_pedido("/admin/importar-alunos"),
                background_tasks=BackgroundTasks(),
                file=_upload_csv(),
                current_user=ADMIN,
            )
        )

    assert resposta["importados"] != resposta["matriculados"]
    assert_resposta_conforme(resposta, "POST", "/admin/importar-alunos")


def test_importar_professores_conforme():
    """E-mail repetido conta em `duplicados` e NÃO entra em `erros`."""
    from fastapi import BackgroundTasks

    from routers.admin import admin_importar_professores_csv

    with patch("routers.admin.criar_leitor_csv", return_value=iter([])), \
         patch("routers.admin._processar_professores_csv",
               return_value=(2, 1, 2, ["Linha 5: e-mail inválido."])):
        resposta = asyncio.run(
            admin_importar_professores_csv(
                request=_pedido("/admin/importar-professores"),
                background_tasks=BackgroundTasks(),
                file=_upload_csv(),
                current_user=ADMIN,
            )
        )

    assert resposta["duplicados"] == 1
    assert_resposta_conforme(resposta, "POST", "/admin/importar-professores")


# --------------------------------------------------------------------------
# biometria e dossiê
# --------------------------------------------------------------------------
def test_cadastrar_face_conforme():
    """O corpo sai de `_persistir_biometria`, que é o que roda no threadpool —
    a corrotina da rota só o repassa. `external_id` é o `aluno_id`, nunca o
    nome do aluno."""
    from routers.alunos import _persistir_biometria

    rekognition = {"FaceRecords": [{"Face": {"FaceId": "face-nova-123"}}]}
    with patch("routers.alunos.buscar_usuario_id_por_id",
               return_value={"usuario_id": ALUNO_USUARIO_ID}), \
         patch("routers.alunos.buscar_aluno_por_usuario_id", return_value={"aluno_id": ALUNO_ID}), \
         patch("routers.alunos.s3_client"), \
         patch("routers.alunos.indexar_rosto_da_imagem_s3", return_value=rekognition), \
         patch("routers.alunos.obter_rosto_por_angulo", return_value=None), \
         patch("routers.alunos.upsert_rosto"), \
         patch("routers.alunos.registrar_aceite_se_novo"):
        resposta = _persistir_biometria(
            b"bytes-da-foto",
            "abc.jpg",
            ALUNO_USUARIO_ID,
            "bruno@escola.com.br",
            "frontal",
            "1.0",
            ALUNO,
            "203.0.113.7",
            "app/1.0",
        )

    assert resposta["external_id"] == str(ALUNO_ID)
    assert_resposta_conforme(resposta, "POST", "/alunos/cadastrar-face")


def test_dossie_lgpd_json_conforme():
    """`formato=json` devolve o dossiê direto no corpo. `_schema_version` e
    `_gerado_em` são acrescentados pelo handler, não vêm do banco."""
    from routers.alunos import exportar_meus_dados

    dados = {
        "titular": {
            "nome": "Bruno Lima",
            "email": "bruno@escola.com.br",
            "ra": "2026001",
            "turno": "Noturno",
            "tipo_usuario": "Aluno",
        },
        "biometria": {
            "registrada": True,
            "angulos_cadastrados": ["frontal", "esquerda"],
            "consentimento_data": "2026-08-01T19:30:00-03:00",
            "revogado_em": None,
        },
        "presencas": [
            {"turma": "Cálculo I", "data": "2026-08-12", "hora_registro": "19:05:11"}
        ],
        "consentimentos": [
            {
                "evento": "aceite",
                "politica_versao": "1.0",
                "registrado_em": "2026-08-01T19:30:00-03:00",
                "ip": "203.0.113.7",
                "origem": "app",
            }
        ],
    }
    with patch("routers.alunos.buscar_dados_titular", return_value=dados):
        resposta = exportar_meus_dados(
            ALUNO_USUARIO_ID, formato="json", current_user=ALUNO
        )

    assert resposta["_schema_version"] == "1.0"
    assert resposta["_gerado_em"]
    assert_resposta_conforme(resposta, "GET", "/aluno/meus-dados/{usuario_id}")
