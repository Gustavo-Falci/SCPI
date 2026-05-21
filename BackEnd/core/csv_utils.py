import re

MAX_CSV_BYTES = 2 * 1024 * 1024  # 2 MB — limite para evitar DoS por upload grande
CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RA_REGEX = re.compile(r"^[A-Za-z0-9]{4,20}$")


def validar_celula_csv(valor: str, campo: str) -> str:
    """Valida tamanho e bloqueia prefixos de CSV injection (=, +, -, @, TAB, CR)."""
    if valor is None:
        return ""
    valor = valor.strip().lstrip("﻿")  # remove BOM se primeiro campo
    if len(valor) > 200:
        raise ValueError(f"Campo '{campo}' excede 200 caracteres.")
    if valor and valor[0] in CSV_INJECTION_PREFIXES:
        raise ValueError(
            f"Campo '{campo}' começa com caractere proibido ({valor[0]!r}). "
            "Possível CSV injection."
        )
    return valor
