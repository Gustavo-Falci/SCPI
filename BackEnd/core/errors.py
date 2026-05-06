"""
Sistema centralizado de erros do SCPI.

Define códigos de erro padronizados, formato consistente de resposta JSON e
helpers para levantar HTTPException com mensagem amigável em PT-BR.

Formato da resposta de erro:
{
  "detail": "Mensagem amigável em PT-BR",
  "error_code": "CODIGO_DO_ERRO",
  "status_code": 400,
  "field": "campo_opcional"   // só presente em validações
}
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


# ---------------------------------------------------------------------------
# Códigos de erro centralizados
# ---------------------------------------------------------------------------
class ErrorCode:
    """Códigos de erro padronizados (string, estáveis para o frontend)."""

    # Autenticação / autorização
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # Validação
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"

    # Recursos
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Acadêmico
    ALUNO_NOT_FOUND = "ALUNO_NOT_FOUND"
    PROFESSOR_NOT_FOUND = "PROFESSOR_NOT_FOUND"
    TURMA_NOT_FOUND = "TURMA_NOT_FOUND"
    CHAMADA_FORA_HORARIO = "CHAMADA_FORA_HORARIO"
    CHAMADA_JA_ABERTA = "CHAMADA_JA_ABERTA"

    # Biometria
    FACE_NAO_DETECTADA = "FACE_NAO_DETECTADA"
    FACE_NAO_RECONHECIDA = "FACE_NAO_RECONHECIDA"
    FACE_JA_CADASTRADA = "FACE_JA_CADASTRADA"
    CONSENTIMENTO_OBRIGATORIO = "CONSENTIMENTO_OBRIGATORIO"

    # Rate limit
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Servidor
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AWS_ERROR = "AWS_ERROR"


# ---------------------------------------------------------------------------
# Mensagens padrão em PT-BR
# ---------------------------------------------------------------------------
DEFAULT_MESSAGES: dict[str, str] = {
    ErrorCode.INVALID_CREDENTIALS: "E-mail ou senha incorretos.",
    ErrorCode.TOKEN_EXPIRED: "Sua sessão expirou. Faça login novamente.",
    ErrorCode.TOKEN_INVALID: "Token inválido.",
    ErrorCode.UNAUTHORIZED: "Você precisa estar autenticado para acessar este recurso.",
    ErrorCode.FORBIDDEN: "Você não tem permissão para acessar este recurso.",
    ErrorCode.SESSION_EXPIRED: "Sua sessão expirou. Faça login novamente.",
    ErrorCode.VALIDATION_ERROR: "Dados inválidos.",
    ErrorCode.INVALID_INPUT: "Entrada inválida.",
    ErrorCode.MISSING_FIELD: "Campo obrigatório não informado.",
    ErrorCode.NOT_FOUND: "Recurso não encontrado.",
    ErrorCode.ALREADY_EXISTS: "Recurso já existe.",
    ErrorCode.CONFLICT: "Conflito ao processar a solicitação.",
    ErrorCode.ALUNO_NOT_FOUND: "Aluno não encontrado.",
    ErrorCode.PROFESSOR_NOT_FOUND: "Professor não encontrado.",
    ErrorCode.TURMA_NOT_FOUND: "Turma não encontrada.",
    ErrorCode.CHAMADA_FORA_HORARIO: "Você só pode iniciar a chamada durante o horário oficial da aula.",
    ErrorCode.CHAMADA_JA_ABERTA: "Já existe uma chamada aberta para esta turma.",
    ErrorCode.FACE_NAO_DETECTADA: "Não foi possível detectar um rosto na imagem. Tente novamente em local iluminado.",
    ErrorCode.FACE_NAO_RECONHECIDA: "Rosto não reconhecido. Tente novamente.",
    ErrorCode.FACE_JA_CADASTRADA: "Este rosto já está cadastrado para outro usuário.",
    ErrorCode.CONSENTIMENTO_OBRIGATORIO: "É necessário aceitar o consentimento LGPD para o cadastro biométrico.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Muitas requisições em pouco tempo. Aguarde alguns segundos e tente novamente.",
    ErrorCode.INTERNAL_ERROR: "Ocorreu um erro interno. Tente novamente em instantes.",
    ErrorCode.SERVICE_UNAVAILABLE: "Serviço temporariamente indisponível.",
    ErrorCode.AWS_ERROR: "Falha na comunicação com o serviço de reconhecimento. Tente novamente.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_error_payload(
    detail: str,
    error_code: str,
    status_code: int,
    field: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Monta um payload padronizado de erro."""
    payload: dict[str, Any] = {
        "detail": detail,
        "error_code": error_code,
        "status_code": status_code,
    }
    if field is not None:
        payload["field"] = field
    if extra:
        payload.update(extra)
    return payload


def http_error(
    status_code: int,
    error_code: str,
    detail: Optional[str] = None,
    field: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> HTTPException:
    """
    Cria HTTPException com payload padronizado em `detail` (dict).

    Uso:
        raise http_error(404, ErrorCode.ALUNO_NOT_FOUND)
        raise http_error(400, ErrorCode.VALIDATION_ERROR, "Email inválido", field="email")
    """
    msg = detail or DEFAULT_MESSAGES.get(error_code, "Erro inesperado.")
    payload = make_error_payload(msg, error_code, status_code, field)
    return HTTPException(status_code=status_code, detail=payload, headers=headers)


# Atalhos comuns -------------------------------------------------------------
def not_found(error_code: str = ErrorCode.NOT_FOUND, detail: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_404_NOT_FOUND, error_code, detail)


def unauthorized(error_code: str = ErrorCode.UNAUTHORIZED, detail: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_401_UNAUTHORIZED, error_code, detail)


def forbidden(error_code: str = ErrorCode.FORBIDDEN, detail: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_403_FORBIDDEN, error_code, detail)


def bad_request(error_code: str = ErrorCode.VALIDATION_ERROR, detail: Optional[str] = None, field: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_400_BAD_REQUEST, error_code, detail, field=field)


def conflict(error_code: str = ErrorCode.CONFLICT, detail: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_409_CONFLICT, error_code, detail)


def internal_error(error_code: str = ErrorCode.INTERNAL_ERROR, detail: Optional[str] = None) -> HTTPException:
    return http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_code, detail)


# ---------------------------------------------------------------------------
# Handlers de exceção (para o app FastAPI)
# ---------------------------------------------------------------------------
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Handler customizado para slowapi RateLimitExceeded — mantém formato JSON
    consistente com os demais erros (`detail`, `error_code`, `status_code`).

    Tenta também propagar o header `Retry-After` injetado pelo slowapi.
    """
    extra = {"limit": str(exc.detail)} if getattr(exc, "detail", None) else None
    payload = make_error_payload(
        detail=DEFAULT_MESSAGES[ErrorCode.RATE_LIMIT_EXCEEDED],
        error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        extra=extra,
    )
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS, content=payload
    )

    # Propaga `Retry-After` quando slowapi disponibiliza o limite no request.
    try:
        view_limit = getattr(request.state, "view_rate_limit", None)
        if view_limit and hasattr(request.app.state, "limiter"):
            response = request.app.state.limiter._inject_headers(response, view_limit)
    except Exception:
        # Falhas de injeção de header não devem impedir a resposta.
        pass

    return response


__all__ = [
    "ErrorCode",
    "DEFAULT_MESSAGES",
    "make_error_payload",
    "http_error",
    "not_found",
    "unauthorized",
    "forbidden",
    "bad_request",
    "conflict",
    "internal_error",
    "rate_limit_handler",
]
