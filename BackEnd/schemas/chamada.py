from pydantic import BaseModel


class ChamadaAbrir(BaseModel):
    turma_id: str


class PresencaAluno(BaseModel):
    aluno_id: str
    aulas_presentes: list[int]  # [1, 2] = presente nas aulas 1 e 2; [] = falta total


class FinalizarChamadaPayload(BaseModel):
    alunos: list[PresencaAluno]
