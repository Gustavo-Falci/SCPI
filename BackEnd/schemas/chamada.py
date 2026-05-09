from pydantic import BaseModel, Field, field_validator


class ChamadaAbrir(BaseModel):
    turma_id: str


class PresencaAluno(BaseModel):
    aluno_id: str
    aulas_presentes: list[int] = Field(default_factory=list)  # [1, 2] = aulas 1 e 2; [] = falta total

    @field_validator("aulas_presentes")
    @classmethod
    def aulas_validas(cls, v: list[int]) -> list[int]:
        for n in v:
            if n < 1:
                raise ValueError(f"num_aula deve ser >= 1, recebeu {n}")
        return v


class FinalizarChamadaPayload(BaseModel):
    alunos: list[PresencaAluno]
