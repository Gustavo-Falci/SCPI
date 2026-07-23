"""Máscaras de dado pessoal para documentos que saem do sistema.

O PDF de relatório circula por e-mail e WhatsApp, fora do controle do SCPI.
CPF completo não vai impresso; RA institucional vai, porque sem ele a ata de
uma turma com nomes repetidos fica ambígua.
"""


def _digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())


def _cpf_valido(digitos: str) -> bool:
    """Valida os dois dígitos verificadores do CPF (módulo 11)."""
    if len(digitos) != 11 or len(set(digitos)) == 1:
        return False
    for tamanho in (9, 10):
        soma = sum(int(digitos[i]) * (tamanho + 1 - i) for i in range(tamanho))
        resto = (soma * 10) % 11
        dv = 0 if resto == 10 else resto
        if dv != int(digitos[tamanho]):
            return False
    return True


def mascarar_documento(valor) -> str:
    """Mascara CPF (``***.982.247-**``); devolve qualquer outro valor inteiro."""
    if valor is None:
        return "—"
    texto = str(valor).strip()
    if not texto:
        return "—"
    digitos = _digitos(texto)
    if _cpf_valido(digitos):
        return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
    return texto
