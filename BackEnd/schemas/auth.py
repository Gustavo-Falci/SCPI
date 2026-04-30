from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UsuarioRegistro(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=128)
    tipo_usuario: str = Field(..., pattern=r"^(Professor|Aluno|Admin)$")
    ra: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9]{4,20}$")
    departamento: Optional[str] = Field(None, max_length=100)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_role: str
    user_id: str
    user_name: str
    user_email: str
    user_ra: Optional[str] = None
    primeiro_acesso: bool = False
    face_cadastrada: bool = True


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, max_length=256)


class AlterarSenhaBody(BaseModel):
    senha_atual: str
    nova_senha: str = Field(..., min_length=8, max_length=128)


class PrimeiroAcessoSenhaBody(BaseModel):
    nova_senha: str = Field(..., min_length=8, max_length=128)


class RegisterTokenBody(BaseModel):
    expo_token: str = Field(..., min_length=10, max_length=256)


class EsqueciSenhaBody(BaseModel):
    email: EmailStr


class VerificarCodigoBody(BaseModel):
    email: EmailStr
    codigo: str


class RedefinirSenhaBody(BaseModel):
    reset_token: str
    nova_senha: str = Field(..., min_length=8)
