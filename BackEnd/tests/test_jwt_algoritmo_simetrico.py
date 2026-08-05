"""`cryptography` saiu do requirements.txt porque o SCPI assina JWT em HS256.

O acoplamento não é óbvio e some do radar: `jwt/utils.py` embrulha o import de
`cryptography` em `try/except ModuleNotFoundError`, então PyJWT importa e roda
sem ela — mas só enquanto o algoritmo for SIMÉTRICO. Trocar `ALGORITHM` para
RS256/ES256/PS256 faria `jwt.encode` levantar em RUNTIME, na emissão do token de
login, com uma suíte inteira verde: os testes que exercitam JWT usam o próprio
`ALGORITHM`, então acompanhariam a troca sem reclamar.

Este teste é o alarme: quem mudar o algoritmo tem que devolver a dependência
junto, no mesmo commit.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REQUIREMENTS = BACKEND / "requirements.txt"

# Casa a linha de pin (`cryptography==50.0.0`), não a menção em comentário — o
# requirements.txt documenta em prosa por que ela saiu.
PIN_CRYPTOGRAPHY = re.compile(r"^\s*cryptography\b", re.MULTILINE)


def _algoritmo():
    from core.auth_utils import ALGORITHM

    return ALGORITHM


def test_assinatura_e_simetrica_ou_cryptography_esta_declarada():
    algoritmo = _algoritmo()
    pinada = bool(PIN_CRYPTOGRAPHY.search(REQUIREMENTS.read_text(encoding="utf-8")))

    if algoritmo.startswith("HS"):
        assert not pinada, (
            "ALGORITHM é simétrico (hmac/hashlib da stdlib resolvem), mas "
            "cryptography voltou ao requirements.txt. Se entrou por outro motivo, "
            "documente aqui — senão é superfície de advisory sem uso."
        )
    else:
        assert pinada, (
            f"ALGORITHM = {algoritmo!r} é assimétrico e o PyJWT delega esse caso a "
            "`cryptography`, que NÃO está no requirements.txt. Sem ela jwt.encode "
            "levanta em runtime, na emissão do token de login. Adicione o pin no "
            "mesmo commit da troca de algoritmo."
        )


def test_hs256_assina_e_verifica_sem_cryptography():
    """Prova o que sustenta a remoção: o caminho de assinatura em uso é stdlib."""
    import jwt

    # 32 bytes: abaixo disso o PyJWT emite InsecureKeyLengthWarning (RFC 7518
    # §3.2) e a suíte roda com zero warnings.
    CHAVE = "chave-de-teste-com-32-bytes-ok!!"

    token = jwt.encode({"sub": "1"}, CHAVE, algorithm=_algoritmo())
    assert jwt.decode(token, CHAVE, algorithms=[_algoritmo()])["sub"] == "1"
