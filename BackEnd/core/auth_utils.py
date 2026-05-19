from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.responses import Response
import logging
import os
import secrets
import hashlib

import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

_HIBP_API_URL = "https://api.pwnedpasswords.com/range/{prefix}"
_HIBP_TIMEOUT_SECONDS = 2.0

# Configurações de Segurança
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "SECRET_KEY ausente ou fraca. Defina uma chave com pelo menos 32 caracteres em BackEnd/.env. "
        "Gere uma chave segura com: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

ACCESS_COOKIE_NAME = "scpi_access"
REFRESH_COOKIE_NAME = "scpi_refresh"
REFRESH_COOKIE_PATH = "/auth"

_COOKIE_DOMAIN = (os.getenv("AUTH_COOKIE_DOMAIN") or "").strip() or None
_COOKIE_SECURE = os.getenv("ENVIRONMENT", "").strip().lower() == "production"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Seta cookies HttpOnly de autenticação no response.

    scpi_access: SameSite=Lax (permite navegação top-level com cookie),
    scpi_refresh: SameSite=Strict + Path=/auth (só viaja para endpoints de auth).
    Em produção, `Secure` é exigido. Domínio configurável via AUTH_COOKIE_DOMAIN.
    """
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        domain=_COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="strict",
        domain=_COOKIE_DOMAIN,
        path=REFRESH_COOKIE_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove cookies de autenticação. Atributos devem casar com os do set_cookie."""
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        domain=_COOKIE_DOMAIN,
        samesite="lax",
        secure=_COOKIE_SECURE,
        httponly=True,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=_COOKIE_DOMAIN,
        samesite="strict",
        secure=_COOKIE_SECURE,
        httponly=True,
    )

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica se a senha em texto puro bate com o hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Gera o hash da senha."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria um token JWT de acesso (curta duração)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token() -> tuple[str, str, datetime]:
    """Gera um refresh token opaco (não-JWT) e retorna (token_plain, token_hash, expira_em).

    O token plano vai para o cliente; o hash é o que deve ser persistido no banco,
    permitindo revogação por deleção e impedindo vazamento caso o BD seja comprometido.
    """
    token_plain = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token_plain.encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return token_plain, token_hash, expires_at

def hash_refresh_token(token_plain: str) -> str:
    """Hash determinístico para lookup do refresh token no banco."""
    return hashlib.sha256(token_plain.encode("utf-8")).hexdigest()

def senha_comprometida(senha: str) -> bool:
    """Consulta a API Have I Been Pwned (k-anonymity) para verificar vazamento.

    Envia apenas os 5 primeiros caracteres do SHA-1 da senha — o servidor
    devolve sufixos correspondentes e a comparação final é feita localmente,
    de modo que a senha em texto puro nunca trafega.

    Política de falha: fail-open. Se a API estiver indisponível, retornamos
    False para não bloquear alterações de senha legítimas durante quedas
    externas. O evento fica logado para investigação.
    """
    if not senha:
        return False
    try:
        sha1_hash = hashlib.sha1(senha.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]
        response = requests.get(
            _HIBP_API_URL.format(prefix=prefix),
            timeout=_HIBP_TIMEOUT_SECONDS,
            headers={"Add-Padding": "true", "User-Agent": "SCPI-Backend"},
        )
        if response.status_code != 200:
            logger.warning("HIBP retornou status inesperado: %s", response.status_code)
            return False
        for linha in response.text.splitlines():
            parte_hash, _, _ = linha.partition(":")
            if parte_hash.strip().upper() == suffix:
                return True
        return False
    except requests.RequestException as e:
        logger.warning("Falha ao consultar HIBP (fail-open): %s", e)
        return False


def decode_access_token(token: str):
    """Decodifica e valida o token JWT de acesso.

    Exige explicitamente o claim `type == "access"`. Isso impede que tokens
    de outras finalidades (ex.: `password_reset`) — assinados com o mesmo
    SECRET_KEY — sejam aceitos em endpoints protegidos por autenticação.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
