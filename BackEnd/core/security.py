from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.auth_utils import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(*roles: str):
    """Dependency factory: exige que o usuário autenticado tenha uma das roles informadas."""
    def _checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado para este perfil.")
        return current_user
    return _checker


def require_self_or_admin(usuario_id: str, current_user: dict) -> None:
    """Garante que o usuário autenticado é o dono do recurso ou um Admin."""
    if current_user.get("sub") != usuario_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")
