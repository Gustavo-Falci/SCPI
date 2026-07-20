import csv
import io
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


def _normalizar_coluna(nome):
    """Header do Excel chega com BOM, espaços e capitalização variada."""
    return (nome or "").strip().lstrip("﻿").lower()


def criar_leitor_csv(decoded, colunas_obrigatorias):
    """DictReader tolerante ao que o Excel produz: BOM, ';' do locale pt-BR e
    header com espaço/maiúscula.

    Levanta ValueError se faltar alguma coluna obrigatória — sem isso o import
    processaria zero linhas em silêncio, sem erro visível para o admin.
    """
    primeira_linha = decoded.split("\n", 1)[0]
    delimitador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","

    leitor = csv.DictReader(io.StringIO(decoded), delimiter=delimitador)
    leitor.fieldnames = [_normalizar_coluna(f) for f in (leitor.fieldnames or [])]

    faltando = [c for c in colunas_obrigatorias if c not in leitor.fieldnames]
    if faltando:
        raise ValueError(
            "CSV sem a(s) coluna(s) obrigatória(s): " + ", ".join(faltando) +
            ". Colunas encontradas: " + (", ".join(leitor.fieldnames) or "nenhuma") + "."
        )
    return leitor
