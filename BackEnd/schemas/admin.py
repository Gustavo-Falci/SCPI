from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class TurmaCreate(BaseModel):
    professor_id: Optional[str] = Field(None, max_length=64)
    codigo_turma: str = Field(..., min_length=1, max_length=30)
    nome_disciplina: str = Field(..., min_length=2, max_length=120)
    periodo_letivo: str = Field(..., min_length=1, max_length=20)
    sala_padrao: str = Field(..., min_length=1, max_length=30)
    turno: str = Field(..., pattern=r"^(Matutino|Noturno)$")
    semestre: str = Field(..., min_length=1, max_length=10)


class AtribuirProfessor(BaseModel):
    professor_id: Optional[str] = None


class HorarioCreate(BaseModel):
    turma_id: str = Field(..., min_length=1, max_length=64)
    dia_semana: int = Field(..., ge=0, le=6)
    horario_inicio: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    horario_fim: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    sala: str = Field(..., min_length=1, max_length=30)


class MatricularAlunos(BaseModel):
    aluno_ids: List[str]


class CriarProfessorAdmin(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    departamento: Optional[str] = Field(None, max_length=100)


class CriarAlunoAdmin(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    ra: str = Field(..., pattern=r"^[A-Za-z0-9]{4,20}$")
    turno: Optional[str] = Field(None, pattern=r"^(Matutino|Noturno)$")
