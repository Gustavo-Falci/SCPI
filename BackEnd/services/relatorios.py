from typing import Optional

from fastapi import HTTPException

from repositories.chamadas import (
    listar_relatorios_chamadas,
    obter_relatorio_chamada,
)
from repositories.presencas import listar_alunos_presenca_chamada


def resumo_presenca(total: int, presentes: int) -> dict:
    return {
        "ausentes": total - presentes,
        "percentual": round(presentes / total * 100) if total > 0 else 0,
    }


def listar_relatorios(professor_id: Optional[str] = None, turma_id: Optional[str] = None,
                      limit: int = 200, offset: int = 0):
    rows = listar_relatorios_chamadas(
        professor_id=professor_id, turma_id=turma_id, limit=limit, offset=offset
    )
    return [{**dict(r), **resumo_presenca(r["total_alunos"], r["presentes"])} for r in rows]


def detalhe_relatorio(chamada_id: str, professor_id: Optional[str] = None):
    chamada = obter_relatorio_chamada(chamada_id, professor_id=professor_id)
    if not chamada:
        raise HTTPException(status_code=404, detail="Chamada não encontrada.")

    alunos = listar_alunos_presenca_chamada(chamada_id, chamada["turma_id"])

    total = len(alunos)
    presentes = sum(1 for a in alunos if a["presente"])
    return {
        **dict(chamada),
        "total_alunos": total,
        "presentes": presentes,
        **resumo_presenca(total, presentes),
        "alunos": [dict(a) for a in alunos],
    }
