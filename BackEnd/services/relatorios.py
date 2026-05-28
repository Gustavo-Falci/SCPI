from typing import Optional

from fastapi import HTTPException

from repositories.chamadas import (
    listar_relatorios_chamadas,
    obter_relatorio_chamada,
    listar_opcoes_filtros_relatorios,
)
from repositories.presencas import listar_alunos_presenca_chamada


def resumo_presenca(total_alunos: int, total_aulas: int, presentes: int) -> dict:
    total_slots = total_alunos * total_aulas
    return {
        "ausentes": total_slots - presentes,
        "percentual": round(presentes / total_slots * 100) if total_slots > 0 else 0,
    }


def listar_relatorios(professor_id: Optional[str] = None, turma_id: Optional[str] = None,
                      limit: int = 200, offset: int = 0,
                      data_inicio=None, data_fim=None, turno=None, semestre=None):
    rows = listar_relatorios_chamadas(
        professor_id=professor_id, turma_id=turma_id, limit=limit, offset=offset,
        data_inicio=data_inicio, data_fim=data_fim, turno=turno, semestre=semestre,
    )
    return [{**dict(r), **resumo_presenca(r["total_alunos"], r["total_aulas"], r["presentes"])} for r in rows]


def opcoes_filtros_relatorios(professor_id: str):
    return listar_opcoes_filtros_relatorios(professor_id)


def detalhe_relatorio(chamada_id: str, professor_id: Optional[str] = None):
    chamada = obter_relatorio_chamada(chamada_id, professor_id=professor_id)
    if not chamada:
        raise HTTPException(status_code=404, detail="Chamada não encontrada.")

    alunos = listar_alunos_presenca_chamada(chamada_id, chamada["turma_id"])
    total_aulas = chamada["total_aulas"]
    total_alunos = len(alunos)
    presentes = sum(a["aulas_presentes_count"] for a in alunos)
    return {
        **dict(chamada),
        "total_alunos": total_alunos,
        "total_aulas": total_aulas,
        "presentes": presentes,
        **resumo_presenca(total_alunos, total_aulas, presentes),
        "alunos": [dict(a) for a in alunos],
    }
