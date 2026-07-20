"""Core da importação de alunos por CSV, compartilhado pelas rotas com e sem turma."""
import logging
from dataclasses import dataclass, field

from fastapi import HTTPException

from core.auth_utils import get_password_hash
from core.csv_utils import (
    EMAIL_REGEX,
    MAX_CSV_BYTES,
    RA_REGEX,
    criar_leitor_csv,
    validar_celula_csv,
)
from core.helpers import gerar_senha_temporaria
from repositories.alunos import importar_aluno_csv
from repositories.turmas import mapear_codigos_turma

logger = logging.getLogger(__name__)


@dataclass
class ResultadoImport:
    importados: int = 0
    duplicados: int = 0
    matriculados: int = 0
    emails_enviados: int = 0
    erros: list = field(default_factory=list)


def _decodificar(conteudo):
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(conteudo) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV muito grande (limite: 2 MB).")
    try:
        # utf-8-sig descarta o BOM que o Excel grava — sem isso a primeira coluna
        # do header vira "﻿nome" e nenhuma linha é reconhecida.
        return conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV deve estar em UTF-8.")


def _resolver_turma(codigo, mapa):
    """Retorna turma_id ou None. Levanta ValueError se o código não existir."""
    if not codigo:
        return None
    turma_id = mapa.get(codigo)
    if not turma_id:
        raise ValueError(f"turma '{codigo}' não encontrada.")
    return turma_id


def processar_csv_alunos(conteudo, turma_id_fixo=None, on_novo_usuario=None):
    """Processa o CSV e devolve ResultadoImport.

    turma_id_fixo: usado pela rota por turma; ignora a coluna `turma` do CSV.
    on_novo_usuario: callback (email, nome, senha_temporaria) para cada usuário novo.
    """
    decoded = _decodificar(conteudo)
    try:
        reader = criar_leitor_csv(decoded, ["nome", "email", "ra"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    mapa_turmas = {} if turma_id_fixo else mapear_codigos_turma()
    res = ResultadoImport()

    for linha_num, row in enumerate(reader, start=2):  # 1 = header
        try:
            nome = validar_celula_csv(row.get("nome", ""), "nome")
            email = validar_celula_csv(row.get("email", ""), "email")
            ra = validar_celula_csv(row.get("ra", ""), "ra")
            turno = validar_celula_csv(row.get("turno", ""), "turno")
            codigo_turma = validar_celula_csv(row.get("turma", ""), "turma")

            if not nome or not email or not ra:
                continue

            if len(nome) < 3:
                raise ValueError("Nome deve ter ao menos 3 caracteres.")
            if not EMAIL_REGEX.match(email):
                raise ValueError("E-mail em formato inválido.")
            if not RA_REGEX.match(ra):
                raise ValueError("RA deve ter de 4 a 20 caracteres alfanuméricos.")

            if turno not in ("Matutino", "Noturno"):
                turno = None

            # Resolve a turma antes de qualquer escrita: código inválido não grava nada.
            turma_id = turma_id_fixo or _resolver_turma(codigo_turma, mapa_turmas)

            senha_temporaria = gerar_senha_temporaria()
            senha_hash = get_password_hash(senha_temporaria)

            novo_usuario, _email, matriculado = importar_aluno_csv(
                turma_id, nome, email, ra, turno, senha_hash
            )

            if novo_usuario:
                res.importados += 1
                if on_novo_usuario:
                    on_novo_usuario(email, nome, senha_temporaria)
                    res.emails_enviados += 1
            else:
                res.duplicados += 1

            if matriculado:
                res.matriculados += 1
        except ValueError as ve:
            res.erros.append(f"Linha {linha_num}: {ve}")
        except Exception as e:
            res.erros.append(f"Linha {linha_num}: erro inesperado ({type(e).__name__}).")
            logger.warning("Erro na importação CSV aluno linha %s: %s", linha_num, e)

    return res
