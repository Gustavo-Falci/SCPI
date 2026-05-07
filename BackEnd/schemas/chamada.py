from pydantic import BaseModel


class ChamadaAbrir(BaseModel):
    turma_id: str


class PresencaAluno(BaseModel):
    aluno_id: str
    presente: bool


class FinalizarChamadaPayload(BaseModel):
    alunos: list[PresencaAluno]
