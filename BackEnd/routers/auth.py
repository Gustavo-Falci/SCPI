import datetime as _dt
import logging
import os
import secrets
from datetime import datetime, timedelta

import resend as _resend
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
import jwt as _jwt

from core.auth_utils import (
    ALGORITHM,
    REFRESH_COOKIE_NAME,
    SECRET_KEY,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_refresh_token,
    hash_reset_code,
    senha_comprometida,
    set_auth_cookies,
    verify_password,
)
from core.helpers import client_ip, internal_error, mask_email
from core.limiter import limiter
from core.security import get_current_user
from repositories.alunos import obter_aluno_e_face_status
from repositories.tokens import (
    buscar_codigo_reset_valido,
    inserir_refresh_token,
    marcar_codigo_reset_usado,
    registrar_tentativa_codigo_invalida,
    revogar_refresh_token,
    revogar_todos_refresh_tokens,
    rotacionar_refresh_token,
    substituir_codigo_reset,
)
from repositories.usuarios import (
    atualizar_senha_por_email,
    atualizar_senha_por_usuario_id,
    buscar_primeiro_acesso_por_usuario_id,
    buscar_senha_por_usuario_id,
    buscar_usuario_id_por_email_lower,
    buscar_usuario_login_por_email,
)
from schemas.auth import (
    AlterarSenhaBody,
    EsqueciSenhaBody,
    PrimeiroAcessoSenhaBody,
    RedefinirSenhaBody,
    RefreshRequest,
    Token,
    UsuarioRegistro,
    VerificarCodigoBody,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

# Tentativas de verificação de código de reset antes de invalidá-lo (lockout
# por conta — complementa o rate-limit por IP, que sozinho é contornável).
_MAX_TENTATIVAS_CODIGO = 5

_RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
if not _RESEND_API_KEY:
    logger.warning(
        "RESEND_API_KEY ausente — envio de e-mails (recuperação de senha, senhas "
        "temporárias) ficará indisponível. Configure a variável em BackEnd/.env."
    )
_resend.api_key = _RESEND_API_KEY
_RESEND_FROM = os.getenv("RESEND_FROM_EMAIL", "SCPI <onboarding@resend.dev>")

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash descartável usado para equalizar o tempo de resposta quando o e-mail não
# existe — sem ele, o caminho "usuário inexistente" retorna instantaneamente
# (pula o verify_password), permitindo enumeração de contas por timing.
_DUMMY_PASSWORD_HASH = get_password_hash("scpi-timing-equalizer-not-a-real-password")


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, usuario: UsuarioRegistro):
    audit_logger.warning(
        "Tentativa de uso de endpoint desabilitado rota=/auth/register ip=%s", client_ip(request)
    )
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post("/register-aluno-com-face")
@limiter.limit("5/minute")
async def register_aluno_com_face(request: Request):
    audit_logger.warning(
        "Tentativa de uso de endpoint desabilitado rota=/auth/register-aluno-com-face ip=%s",
        client_ip(request),
    )
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    email_limpo = form_data.username.strip()

    user = buscar_usuario_login_por_email(email_limpo)

    if not user:
        # Verifica contra um hash descartável para gastar o mesmo tempo de um
        # login real (mitiga enumeração de usuário por timing).
        verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
        audit_logger.warning("Login falhou (usuário inexistente) email=%s ip=%s", mask_email(email_limpo), request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    try:
        senha_valida = verify_password(form_data.password, user['senha'])
    except Exception:
        senha_valida = False

    if not senha_valida:
        audit_logger.warning("Login falhou (senha incorreta) email=%s ip=%s", mask_email(email_limpo), request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    audit_logger.info("Login ok email=%s role=%s ip=%s", mask_email(email_limpo), user['tipo_usuario'], request.client.host)

    access_token = create_access_token(data={"sub": str(user['usuario_id']), "email": user['email'], "role": user['tipo_usuario']})
    refresh_plain, refresh_hash, refresh_exp = create_refresh_token()

    try:
        inserir_refresh_token(refresh_hash, str(user['usuario_id']), refresh_exp)
    except Exception as e:
        raise internal_error(e, "login.persist_refresh_token")

    ra = None
    face_cadastrada = True
    if user['tipo_usuario'] == 'Aluno':
        ra, face_cadastrada = obter_aluno_e_face_status(user['usuario_id'])

    set_auth_cookies(response, access_token, refresh_plain)

    return {
        "access_token": access_token,
        "refresh_token": refresh_plain,
        "token_type": "bearer",
        "user_role": user['tipo_usuario'],
        "user_id": str(user['usuario_id']),
        "user_name": user['nome'],
        "user_email": user['email'],
        "user_ra": ra,
        "primeiro_acesso": bool(user.get('primeiro_acesso', False)),
        "face_cadastrada": bool(face_cadastrada),
    }


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh_access_token(
    request: Request,
    response: Response,
    body: RefreshRequest,
    scpi_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    """Troca um refresh token válido por um novo access token (rotação).

    Aceita o refresh por dois canais:
    - Body `refresh_token` (mobile/legado).
    - Cookie `scpi_refresh` (portal). Quando vier por cookie, novos cookies
      são emitidos no response e o cliente não precisa armazenar o token.
    """
    refresh_plain = body.refresh_token or scpi_refresh
    if not refresh_plain:
        raise HTTPException(status_code=401, detail="Refresh token ausente.")
    came_from_cookie = body.refresh_token is None and scpi_refresh is not None

    token_hash = hash_refresh_token(refresh_plain)
    new_plain, new_hash, new_exp = create_refresh_token()
    try:
        result = rotacionar_refresh_token(token_hash, new_hash, new_exp)
        if not result or result.get("_status") == "invalid":
            raise HTTPException(status_code=401, detail="Refresh token inválido.")
        if result.get("_status") == "reuse":
            # Detecção de reuso: família já foi revogada no repositório. Audita e
            # força novo login em todos os dispositivos.
            audit_logger.warning(
                "Reuso de refresh token detectado — todas as sessões revogadas usuario=%s ip=%s",
                result.get("usuario_id"), client_ip(request),
            )
            raise HTTPException(status_code=401, detail="Sessão inválida. Faça login novamente.")
        if result.get("_status") == "expired":
            raise HTTPException(status_code=401, detail="Refresh token expirado.")

        row = result["row"]
        access_token = create_access_token(
            data={"sub": row["usuario_id"], "email": row["email"], "role": row["tipo_usuario"]}
        )

        if came_from_cookie:
            set_auth_cookies(response, access_token, new_plain)

        return {
            "access_token": access_token,
            "refresh_token": new_plain,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "refresh_access_token")


@router.post("/logout")
def logout(
    response: Response,
    body: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    scpi_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    """Revoga o refresh token informado e limpa cookies de auth (se houver).

    Access token continua válido até expirar; o portal não consegue mais
    apresentá-lo após o clear_auth_cookies remover scpi_access do browser.
    """
    refresh_plain = body.refresh_token or scpi_refresh
    try:
        if refresh_plain:
            token_hash = hash_refresh_token(refresh_plain)
            revogar_refresh_token(token_hash, current_user.get("sub"))
        clear_auth_cookies(response)
        audit_logger.info("Logout usuario=%s", current_user.get("sub"))
        return {"mensagem": "Sessão encerrada."}
    except Exception as e:
        raise internal_error(e, "logout")


@router.post("/alterar-senha")
def alterar_senha(body: AlterarSenhaBody, current_user: dict = Depends(get_current_user)):
    usuario_id = current_user.get("sub")
    try:
        user = buscar_senha_por_usuario_id(usuario_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

        try:
            senha_ok = verify_password(body.senha_atual, user['senha'])
        except Exception:
            senha_ok = False
        if not senha_ok:
            raise HTTPException(status_code=401, detail="Senha atual incorreta.")

        if senha_comprometida(body.nova_senha):
            raise HTTPException(
                status_code=400,
                detail="Esta senha aparece em vazamentos públicos. Escolha outra.",
            )

        nova_hash = get_password_hash(body.nova_senha)
        atualizar_senha_por_usuario_id(usuario_id, nova_hash)
        revogados = revogar_todos_refresh_tokens(usuario_id)
        audit_logger.info("Senha alterada usuario=%s sessoes_revogadas=%s", usuario_id, revogados)
        return {"mensagem": "Senha alterada com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "alterar_senha")


@router.post("/alterar-senha-primeiro-acesso")
def alterar_senha_primeiro_acesso(body: PrimeiroAcessoSenhaBody, current_user: dict = Depends(get_current_user)):
    usuario_id = current_user.get("sub")
    try:
        user = buscar_primeiro_acesso_por_usuario_id(usuario_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if not user["primeiro_acesso"]:
            raise HTTPException(status_code=403, detail="Operação não permitida.")

        if senha_comprometida(body.nova_senha):
            raise HTTPException(
                status_code=400,
                detail="Esta senha aparece em vazamentos públicos. Escolha outra.",
            )

        nova_hash = get_password_hash(body.nova_senha)
        atualizar_senha_por_usuario_id(usuario_id, nova_hash)
        revogados = revogar_todos_refresh_tokens(usuario_id)
        audit_logger.info("Senha primeiro acesso alterada usuario=%s sessoes_revogadas=%s", usuario_id, revogados)
        return {"mensagem": "Senha alterada com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "alterar_senha_primeiro_acesso")


@router.post("/esqueci-senha")
@limiter.limit("3/minute")
def esqueci_senha(request: Request, body: EsqueciSenhaBody):
    email = body.email.strip().lower()
    generic_response = {"mensagem": "Se o e-mail existir, um código de redefinição foi enviado."}

    user = buscar_usuario_id_por_email_lower(email)

    if not user:
        audit_logger.info("Esqueci-senha solicitado para email inexistente email=%s", mask_email(email))
        return generic_response

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Persiste apenas o HMAC do código; o texto puro só vai no e-mail ao titular.
    substituir_codigo_reset(email, hash_reset_code(email, code), expires_at)
    audit_logger.info(
        "Código de redefinição gerado email=%s ip=%s", mask_email(email), client_ip(request)
    )

    try:
        _resend.Emails.send({
            "from": _RESEND_FROM,
            "to": [email],
            "subject": "SCPI — Código de redefinição de senha",
            "html": f"""
                <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#0f1117;border-radius:16px;color:#fff">
                    <h2 style="margin:0 0 8px;color:#4B39EF">SCPI</h2>
                    <p style="color:#aaa;margin:0 0 24px">Sistema de Controle de Presença Inteligente</p>
                    <p style="margin:0 0 16px">Recebemos uma solicitação para redefinir a senha da sua conta.</p>
                    <div style="background:#1a1c1e;border-radius:12px;padding:24px;text-align:center;margin:24px 0;border:1px solid #333">
                        <p style="margin:0 0 8px;font-size:13px;color:#aaa;text-transform:uppercase;letter-spacing:2px">Seu código</p>
                        <p style="margin:0;font-size:40px;font-weight:900;letter-spacing:8px;color:#4B39EF">{code}</p>
                    </div>
                    <p style="color:#aaa;font-size:13px;margin:0">Este código expira em <strong style="color:#fff">15 minutos</strong>. Se não foi você, ignore este e-mail.</p>
                </div>
            """,
        })
    except Exception as e:
        logger.error("Falha ao enviar email de redefinição: %s", e)
        raise HTTPException(status_code=500, detail="Não foi possível enviar o e-mail. Tente novamente.")

    return generic_response


@router.post("/verificar-codigo")
@limiter.limit("5/minute")
def verificar_codigo(request: Request, body: VerificarCodigoBody):
    email = body.email.strip().lower()

    row = buscar_codigo_reset_valido(email, hash_reset_code(email, body.codigo))

    if not row:
        # Código errado/usado: incrementa tentativas do código ativo do email e
        # bloqueia ao atingir o limite (lockout por conta).
        tentativas, bloqueado = registrar_tentativa_codigo_invalida(email, _MAX_TENTATIVAS_CODIGO)
        if bloqueado:
            audit_logger.warning(
                "Código de reset bloqueado por excesso de tentativas email=%s ip=%s",
                mask_email(email), client_ip(request),
            )
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Solicite um novo código de redefinição.",
            )
        audit_logger.warning(
            "Verificação de código falhou (inválido/usado) email=%s tentativas=%s ip=%s",
            mask_email(email), tentativas, client_ip(request),
        )
        raise HTTPException(status_code=400, detail="Código inválido ou já utilizado.")

    if datetime.utcnow() > row["expires_at"]:
        audit_logger.warning(
            "Verificação de código falhou (expirado) email=%s ip=%s",
            mask_email(email), client_ip(request),
        )
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    marcar_codigo_reset_usado(row["id"])
    audit_logger.info(
        "Código de redefinição verificado email=%s ip=%s", mask_email(email), client_ip(request)
    )

    reset_payload = {
        "sub": email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    reset_token = _jwt.encode(reset_payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"reset_token": reset_token}


@router.post("/redefinir-senha")
def redefinir_senha(request: Request, body: RedefinirSenhaBody):
    try:
        payload = _jwt.decode(body.reset_token, SECRET_KEY, algorithms=[ALGORITHM])
    except _jwt.InvalidTokenError:
        audit_logger.warning(
            "Redefinição de senha falhou (token inválido/expirado) ip=%s", client_ip(request)
        )
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    if payload.get("type") != "password_reset":
        audit_logger.warning(
            "Redefinição de senha falhou (tipo de token inválido) ip=%s", client_ip(request)
        )
        raise HTTPException(status_code=400, detail="Token inválido.")

    email = payload.get("sub", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido.")

    if senha_comprometida(body.nova_senha):
        raise HTTPException(
            status_code=400,
            detail="Esta senha aparece em vazamentos públicos. Escolha outra.",
        )

    nova_hash = get_password_hash(body.nova_senha)
    atualizar_senha_por_email(email, nova_hash)

    # Recuperação de conta: derruba todas as sessões existentes (o atacante que
    # motivou o reset não deve manter refresh token válido).
    revogados = 0
    user = buscar_usuario_id_por_email_lower(email)
    if user and user.get("usuario_id"):
        revogados = revogar_todos_refresh_tokens(user["usuario_id"])
    audit_logger.info(
        "Senha redefinida via código email=%s sessoes_revogadas=%s ip=%s",
        mask_email(email), revogados, client_ip(request),
    )

    return {"mensagem": "Senha redefinida com sucesso."}
