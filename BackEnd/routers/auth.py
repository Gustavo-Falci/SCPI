import datetime as _dt
import logging
import os
import secrets
from datetime import datetime, timedelta

import resend as _resend
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt as _jwt

from core.auth_utils import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from core.helpers import internal_error, mask_email
from core.limiter import limiter
from core.security import get_current_user
from repositories.alunos import obter_aluno_e_face_status
from repositories.tokens import (
    buscar_codigo_reset_valido,
    inserir_refresh_token,
    marcar_codigo_reset_usado,
    revogar_refresh_token,
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

_resend.api_key = os.getenv("RESEND_API_KEY", "")
_RESEND_FROM = os.getenv("RESEND_FROM_EMAIL", "SCPI <onboarding@resend.dev>")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, usuario: UsuarioRegistro):
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post("/register-aluno-com-face")
@limiter.limit("5/minute")
async def register_aluno_com_face(request: Request):
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    email_limpo = form_data.username.strip()

    user = buscar_usuario_login_por_email(email_limpo)

    if not user:
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
def refresh_access_token(request: Request, body: RefreshRequest):
    """Troca um refresh token válido por um novo access token (rotação)."""
    token_hash = hash_refresh_token(body.refresh_token)
    new_plain, new_hash, new_exp = create_refresh_token()
    try:
        result = rotacionar_refresh_token(token_hash, new_hash, new_exp)
        if not result or result.get("_status") == "invalid":
            raise HTTPException(status_code=401, detail="Refresh token inválido.")
        if result.get("_status") == "expired":
            raise HTTPException(status_code=401, detail="Refresh token expirado.")

        row = result["row"]
        access_token = create_access_token(
            data={"sub": row["usuario_id"], "email": row["email"], "role": row["tipo_usuario"]}
        )

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
def logout(body: RefreshRequest, current_user: dict = Depends(get_current_user)):
    """Revoga o refresh token informado. Access token continua válido até expirar."""
    token_hash = hash_refresh_token(body.refresh_token)
    try:
        revogar_refresh_token(token_hash, current_user.get("sub"))
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

        nova_hash = get_password_hash(body.nova_senha)
        atualizar_senha_por_usuario_id(usuario_id, nova_hash)
        audit_logger.info("Senha alterada usuario=%s", usuario_id)
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

        nova_hash = get_password_hash(body.nova_senha)
        atualizar_senha_por_usuario_id(usuario_id, nova_hash)
        audit_logger.info("Senha primeiro acesso alterada usuario=%s", usuario_id)
        return {"mensagem": "Senha alterada com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "alterar_senha_primeiro_acesso")


@router.post("/esqueci-senha")
def esqueci_senha(body: EsqueciSenhaBody):
    email = body.email.strip().lower()
    generic_response = {"mensagem": "Se o e-mail existir, um código de redefinição foi enviado."}

    user = buscar_usuario_id_por_email_lower(email)

    if not user:
        audit_logger.info("Esqueci-senha solicitado para email inexistente email=%s", mask_email(email))
        return generic_response

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    substituir_codigo_reset(email, code, expires_at)

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
def verificar_codigo(body: VerificarCodigoBody):
    email = body.email.strip().lower()

    row = buscar_codigo_reset_valido(email, body.codigo)

    if not row:
        raise HTTPException(status_code=400, detail="Código inválido ou já utilizado.")

    if datetime.utcnow() > row["expires_at"]:
        raise HTTPException(status_code=400, detail="Código expirado. Solicite um novo.")

    marcar_codigo_reset_usado(row["id"])

    reset_payload = {
        "sub": email,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    reset_token = _jwt.encode(reset_payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"reset_token": reset_token}


@router.post("/redefinir-senha")
def redefinir_senha(body: RedefinirSenhaBody):
    try:
        payload = _jwt.decode(body.reset_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Token inválido.")

    email = payload.get("sub", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido.")

    nova_hash = get_password_hash(body.nova_senha)
    atualizar_senha_por_email(email, nova_hash)

    return {"mensagem": "Senha redefinida com sucesso."}
