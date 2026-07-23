from slowapi import Limiter
from slowapi.util import get_remote_address

# Import com efeito colateral: registra o scheme "scpi-postgres://" no `limits`.
import core.limiter_storage  # noqa: F401

# Storage compartilhado em Postgres (M4). swallow_errors: backstop de fail-open —
# erro no storage não pode bloquear o request.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="scpi-postgres://",
    swallow_errors=True,
)
