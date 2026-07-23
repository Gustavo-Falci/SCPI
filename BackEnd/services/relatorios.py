from typing import Optional

from fastapi import HTTPException

from repositories.chamadas import (
    listar_relatorios_chamadas,
    obter_relatorio_chamada,
    listar_opcoes_filtros_relatorios,
    listar_frequencia_turma,
    obter_turma_relatorio,
)
from repositories.presencas import listar_alunos_presenca_chamada
from repositories.turmas import professor_responsavel_pela_turma
from core.regras import LIMITE_FREQUENCIA


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


def frequencia_turma(turma_id: str, professor_id: Optional[str] = None,
                     data_inicio=None, data_fim=None) -> dict:
    """Frequência acumulada por aluno de uma turma, no período informado."""
    turma = obter_turma_relatorio(turma_id)
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    # 404 e não 403: para um professor que não é dono, a turma não existe.
    if professor_id and not professor_responsavel_pela_turma(turma_id, professor_id):
        raise HTTPException(status_code=404, detail="Turma não encontrada.")

    linhas = [dict(r) for r in listar_frequencia_turma(turma_id, data_inicio, data_fim)]
    for aluno in linhas:
        dadas = aluno.get("aulas_dadas") or 0
        presentes = aluno.get("aulas_presentes") or 0
        aluno["percentual"] = round(presentes / dadas * 100) if dadas else 0
        aluno["situacao"] = "Regular" if aluno["percentual"] >= LIMITE_FREQUENCIA else "Risco"
    linhas.sort(key=lambda a: (a["percentual"], a["nome"]))

    aulas_dadas = linhas[0]["aulas_dadas"] if linhas else 0
    chamadas = linhas[0]["chamadas_count"] if linhas else 0
    presencas = sum(a["aulas_presentes"] for a in linhas)
    slots = aulas_dadas * len(linhas)
    return {
        "turma": dict(turma),
        "periodo": {"data_inicio": data_inicio, "data_fim": data_fim},
        "totais": {
            "total_alunos": len(linhas),
            "chamadas": chamadas,
            "aulas_dadas": aulas_dadas,
            "presencas": presencas,
            "percentual": round(presencas / slots * 100) if slots else 0,
        },
        "alunos": linhas,
    }
