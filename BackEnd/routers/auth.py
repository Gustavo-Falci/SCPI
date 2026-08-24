import logging
import os
import secrets
from datetime import timedelta

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
    verificar_e_atualizar_senha,
    verify_password,
)
from core.helpers import client_ip, internal_error, mask_email
from core.limiter import limiter
from core.security import get_current_user
from core.tempo import agora_utc
from repositories.alunos import obter_aluno_e_face_status
from repositories.tokens import (
    buscar_codigo_reset_valido,
    consumir_token_reset,
    inserir_refresh_token,
    marcar_codigo_reset_usado,
    registrar_tentativa_codigo_invalida,
    revogar_refresh_token,
    revogar_todos_refresh_tokens,
    rotacionar_refresh_token,
    substituir_codigo_reset,
)
from repositories.usuarios import (
    atualizar_hash_senha,
    atualizar_senha_por_email,
    atualizar_senha_por_usuario_id,
    buscar_primeiro_acesso_por_usuario_id,
    buscar_senha_por_usuario_id,
    buscar_usuario_id_por_email_lower,
    buscar_usuario_login_por_email,
)
from repositories.auth_lockout import esta_bloqueado, registrar_falha, limpar_falhas
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
from schemas.respostas.auth import CodigoVerificado, SessaoRenovada, SessaoValida
from schemas.respostas.comum import MensagemResposta

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


@router.post("/register", summary="Endpoint desabilitado (cadastro é exclusivo do Admin)")
@limiter.limit("5/minute")
def register(request: Request, usuario: UsuarioRegistro):
    """Rota desativada: sempre devolve 403.

    Cadastro de usuário só acontece pelo painel do Admin. Esta rota só existe
    para não quebrar chamadas antigas de clientes desatualizados — toda
    tentativa é registrada em log de auditoria (nível warning) com o IP de
    origem, útil para detectar cliente desatualizado tentando usá-la.
    """
    audit_logger.warning(
        "Tentativa de uso de endpoint desabilitado rota=/auth/register ip=%s", client_ip(request)
    )
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post(
    "/register-aluno-com-face",
    summary="Endpoint desabilitado (cadastro com face é exclusivo do Admin)",
)
@limiter.limit("5/minute")
async def register_aluno_com_face(request: Request):
    """Rota desativada: sempre devolve 403.

    Sucessora do fluxo antigo de autocadastro de aluno com biometria; o
    cadastro de face hoje é feito via `/alunos/cadastrar-face`, autenticado.
    Mantida só para não quebrar clientes antigos — cada tentativa é
    registrada em log de auditoria (nível warning) com o IP de origem.
    """
    audit_logger.warning(
        "Tentativa de uso de endpoint desabilitado rota=/auth/register-aluno-com-face ip=%s",
        client_ip(request),
    )
    raise HTTPException(
        status_code=403,
        detail="Cadastros de usuários são realizados exclusivamente pelo administrador do sistema.",
    )


@router.post("/login", response_model=Token, summary="Autentica usuário e abre sessão")
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Valida email/senha (form OAuth2 padrão) e abre sessão.

    Em caso de sucesso: seta os cookies `HttpOnly` `scpi_access` e
    `scpi_refresh` (usados pelo portal) **e** devolve `access_token` e
    `refresh_token` no corpo (usados pelo app mobile, que guarda em
    storage próprio em vez de cookie). Também devolve dados básicos do
    usuário (`user_role`, `user_id`, `user_name`, `user_email`), e, quando
    `Aluno`, `user_ra` e `face_cadastrada`.

    Bloqueado por lockout progressivo por conta (`esta_bloqueado`/
    `registrar_falha`) — complementa o rate-limit por IP, que sozinho não
    pega brute-force distribuído entre IPs. Email/senha errados devolvem
    sempre a mesma mensagem 401 genérica, e o tempo de resposta é
    equalizado com um hash descartável quando o email não existe, para não
    permitir enumeração de contas por timing. Migra silenciosamente o hash
    da senha para a política de iterações atual quando necessário — falha
    nessa migração não derruba o login.

    Rota isenta de CSRF por design (junto com `/auth/refresh`): o cookie jar
    do React Native motivou a isenção.
    """
    email_limpo = form_data.username.strip()
    email_key = email_limpo.lower()

    # Lockout por conta (B1): pega brute-force distribuído entre IPs, que o
    # rate-limit por IP não cobre.
    if esta_bloqueado(email_key):
        audit_logger.warning(
            "Login bloqueado (lockout de conta) email=%s ip=%s",
            mask_email(email_limpo), request.client.host,
        )
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Tente novamente mais tarde.",
        )

    user = buscar_usuario_login_por_email(email_limpo)

    if not user:
        # Verifica contra um hash descartável para gastar o mesmo tempo de um
        # login real (mitiga enumeração de usuário por timing).
        verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
        registrar_falha(email_key)
        audit_logger.warning("Login falhou (usuário inexistente) email=%s ip=%s", mask_email(email_limpo), request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    try:
        senha_valida, hash_novo = verificar_e_atualizar_senha(form_data.password, user['senha'])
    except Exception:
        senha_valida, hash_novo = False, None

    if not senha_valida:
        registrar_falha(email_key)
        audit_logger.warning("Login falhou (senha incorreta) email=%s ip=%s", mask_email(email_limpo), request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if hash_novo:
        # Migração transparente para a política atual de iterações (A3). Falha
        # aqui não pode derrubar um login legítimo — o hash antigo continua válido.
        try:
            atualizar_hash_senha(user['usuario_id'], hash_novo)
        except Exception:
            logger.warning("Falha ao regravar hash de senha usuario=%s", user['usuario_id'])

    audit_logger.info("Login ok email=%s role=%s ip=%s", mask_email(email_limpo), user['tipo_usuario'], request.client.host)
    limpar_falhas(email_key)

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


@router.post(
    "/refresh",
    summary="Renova o access token a partir do refresh token",
    responses={200: {"model": SessaoRenovada}},
)
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
      `HttpOnly` (`scpi_access`/`scpi_refresh`) são emitidos no response e o
      cliente não precisa armazenar o token.

    A cada troca o refresh token antigo é invalidado e um novo é emitido
    (rotação); reusar um refresh token já trocado é tratado como sinal de
    roubo — todas as sessões da família são revogadas e o chamador recebe
    401 "Sessão inválida. Faça login novamente." Devolve 401 também quando o
    refresh está ausente, é inválido ou expirou.

    Rota isenta de CSRF por design (junto com `/auth/login`): o cookie jar
    do React Native motivou a isenção.
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


@router.get(
    "/session",
    summary="Confirma se a sessão atual ainda é válida",
    responses={200: {"model": SessaoValida}},
)
@limiter.limit("60/minute")
def validar_sessao(request: Request, current_user: dict = Depends(get_current_user)):
    """Confirma que o access token/cookie ainda é válido.

    Devolve `usuario_id`, `email` e `role` extraídos do token — nada é
    consultado no banco. Usado no boot do portal para decidir entre login e
    dashboard sem confiar no perfil guardado em localStorage. Não toca no
    refresh token — validar sessão não pode disparar rotação nem detecção de
    reuso entre abas. Access token ausente/expirado/inválido devolve 401 (via
    `get_current_user`).
    """
    return {
        "usuario_id": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role"),
    }


@router.post(
    "/logout",
    summary="Encerra a sessão (revoga refresh token e cookies)",
    responses={200: {"model": MensagemResposta}},
)
def logout(
    response: Response,
    body: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    scpi_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    """Revoga o refresh token informado e limpa cookies de auth (se houver).

    Access token continua válido até expirar; o portal não consegue mais
    apresentá-lo após o clear_auth_cookies remover scpi_access do browser.
    Exige sessão válida (`get_current_user`). Sempre devolve
    `{"mensagem": "Sessão encerrada."}`, mesmo quando o refresh token já
    estava revogado/expirado ou o banco está fora do ar (nesse caso
    `revogados` fica None/0 no log de auditoria, sem afetar a resposta ao
    cliente — a limpeza local dos cookies/tokens é autoritativa por design).
    """
    refresh_plain = body.refresh_token or scpi_refresh
    try:
        revogados = None
        if refresh_plain:
            token_hash = hash_refresh_token(refresh_plain)
            revogados = revogar_refresh_token(token_hash, current_user.get("sub"))
        clear_auth_cookies(response)
        # revogados=0 não é erro (token já revogado/expirado), mas precisa
        # aparecer no log: sem isso, uma revogação que não revogou nada (banco
        # fora do ar, cursor None → rowcount 0) fica indistinguível de logout
        # bem-sucedido. A resposta ao cliente não muda — a limpeza local dos
        # cookies/tokens é autoritativa por design.
        audit_logger.info(
            "Logout usuario=%s revogados=%s", current_user.get("sub"), revogados
        )
        return {"mensagem": "Sessão encerrada."}
    except Exception as e:
        raise internal_error(e, "logout")


@router.post(
    "/alterar-senha",
    summary="Troca a senha do usuário autenticado",
    responses={200: {"model": MensagemResposta}},
)
def alterar_senha(body: AlterarSenhaBody, current_user: dict = Depends(get_current_user)):
    """Troca a senha de quem já está logado, exigindo a senha atual.

    Exige sessão válida (`get_current_user`). Devolve 404 se o usuário não
    for encontrado, 401 se `senha_atual` não confere, 400 se `nova_senha`
    aparece em vazamentos públicos (checagem via `senha_comprometida`). Em
    sucesso, revoga TODOS os refresh tokens do usuário (todas as sessões
    ativas em outros dispositivos são derrubadas) e devolve
    `{"mensagem": "Senha alterada com sucesso."}`.
    """
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


@router.post(
    "/alterar-senha-primeiro-acesso",
    summary="Define a senha definitiva no primeiro acesso (sem senha atual)",
    responses={200: {"model": MensagemResposta}},
)
def alterar_senha_primeiro_acesso(body: PrimeiroAcessoSenhaBody, current_user: dict = Depends(get_current_user)):
    """Troca a senha temporária do primeiro acesso, sem exigir a senha atual.

    Exige sessão válida (`get_current_user`) e que a flag `primeiro_acesso`
    do usuário ainda esteja ativa — devolve 403 se já foi usada antes (não
    é um caminho de troca de senha comum, é de uso único). Devolve 404 se o
    usuário não for encontrado, 400 se `nova_senha` aparece em vazamentos
    públicos. Em sucesso, revoga TODOS os refresh tokens do usuário e
    devolve `{"mensagem": "Senha alterada com sucesso."}`.
    """
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


@router.post(
    "/esqueci-senha",
    summary="Envia código de redefinição de senha por e-mail",
    responses={200: {"model": MensagemResposta}},
)
@limiter.limit("3/minute")
def esqueci_senha(request: Request, body: EsqueciSenhaBody):
    """Primeiro passo da recuperação: gera e envia por e-mail um código de 6
    dígitos, válido por 15 minutos.

    Devolve sempre a mesma mensagem genérica
    `{"mensagem": "Se o e-mail existir, um código de redefinição foi
    enviado."}`, exista ou não o email — evita enumeração de contas. Persiste
    apenas o HMAC do código (`hash_reset_code`); o texto puro só vai no
    e-mail. Envio via Resend; falha no envio devolve 500 (o código já foi
    persistido nesse caso). Segue com `/auth/verificar-codigo`.
    """
    email = body.email.strip().lower()
    generic_response = {"mensagem": "Se o e-mail existir, um código de redefinição foi enviado."}

    user = buscar_usuario_id_por_email_lower(email)

    if not user:
        audit_logger.info("Esqueci-senha solicitado para email inexistente email=%s", mask_email(email))
        return generic_response

    code = str(secrets.randbelow(900000) + 100000)
    expires_at = agora_utc() + timedelta(minutes=15)

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


@router.post(
    "/verificar-codigo",
    summary="Valida o código recebido por e-mail e emite reset_token",
    responses={200: {"model": CodigoVerificado}},
)
@limiter.limit("5/minute")
def verificar_codigo(request: Request, body: VerificarCodigoBody):
    """Segundo passo da recuperação: confere o código de 6 dígitos enviado
    por `/auth/esqueci-senha` e, se válido, marca-o como usado e devolve um
    `reset_token` (JWT de 15 minutos, com `jti` = id do código consumido)
    para usar em `/auth/redefinir-senha`.

    Devolve 400 "Código inválido ou já utilizado." quando o código não
    confere/já foi usado/não existe, e 400 "Código expirado." quando o prazo
    de 15 minutos passou. Lockout por conta: acumula tentativas inválidas do
    código ativo e, ao atingir `_MAX_TENTATIVAS_CODIGO` (5), devolve 429 e
    exige solicitar um novo código.
    """
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

    # Ambos aware: expires_at é TIMESTAMPTZ e agora_utc() tem tzinfo.
    if agora_utc() > row["expires_at"]:
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
        # jti = id do código consumido, como string (RFC 7519 — PyJWT valida o
        # tipo no decode): é o que amarra este token a uma única troca de senha
        # (A4).
        "jti": str(row["id"]),
        "exp": agora_utc() + timedelta(minutes=15),
    }
    reset_token = _jwt.encode(reset_payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"reset_token": reset_token}


@router.post(
    "/redefinir-senha",
    summary="Define a nova senha a partir do reset_token",
    responses={200: {"model": MensagemResposta}},
)
def redefinir_senha(request: Request, body: RedefinirSenhaBody):
    """Terceiro e último passo da recuperação: troca a senha usando o
    `reset_token` emitido por `/auth/verificar-codigo`.

    Devolve 400 "Token inválido ou expirado." para token malformado/expirado,
    de tipo errado, sem `jti` (formato anterior ao endurecimento A4, nunca
    aceito), ou já consumido — a mensagem é deliberadamente a mesma nesses
    casos para não confirmar ao atacante se o token chegou a ser válido.
    Devolve 400 "Esta senha aparece em vazamentos públicos." se a nova senha
    falhar `senha_comprometida`. O consumo do token (uso único) só acontece
    depois de todas as checagens que não escrevem nada, para não queimar o
    token de quem digitou senha vazada na primeira tentativa. Em sucesso,
    revoga TODOS os refresh tokens do usuário e devolve
    `{"mensagem": "Senha redefinida com sucesso."}`.
    """
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

    if payload.get("jti") is None:
        # Sem camada de compatibilidade: token emitido antes do A4 (sem jti)
        # nunca é aceito. Mesma mensagem de token expirado de propósito — ver
        # nota abaixo, no claim atômico.
        audit_logger.warning(
            "Redefinição de senha falhou (token sem jti) ip=%s", client_ip(request)
        )
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    email = payload.get("sub", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido.")

    if senha_comprometida(body.nova_senha):
        raise HTTPException(
            status_code=400,
            detail="Esta senha aparece em vazamentos públicos. Escolha outra.",
        )

    # Claim atômico: só agora, depois de todas as checagens que não escrevem
    # nada. Consumir antes de senha_comprometida queimaria o reset_token de
    # quem digitou uma senha vazada na primeira tentativa, sem ter trocado
    # senha nenhuma (forçaria pedir código novo por e-mail à toa). O claim
    # continua sendo a última coisa antes da escrita — uso único e segurança
    # sob concorrência ficam idênticos.
    try:
        codigo_id = int(payload["jti"])
    except (TypeError, ValueError):
        codigo_id = None

    if codigo_id is None or not consumir_token_reset(codigo_id):
        # Mesma mensagem de token expirado de propósito: distinguir "já usado"
        # confirmaria ao atacante que aquele token existiu e foi válido.
        audit_logger.warning(
            "Redefinição de senha falhou (token já consumido ou inválido) ip=%s",
            client_ip(request),
        )
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

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
