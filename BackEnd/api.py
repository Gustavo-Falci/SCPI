from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import os
import shutil

from db_repositorio import (
    buscar_usuario_por_email,
    criar_usuario_rh,
    criar_usuario_funcionario,
    cadastrar_funcionario_com_foto,
    registrar_ponto_facial,
    registrar_ponto_manual,
    listar_funcionarios_empresa,
    listar_registros_funcionario,
    listar_registros_empresa_dia,
    buscar_empresa_por_cnpj,
    criar_empresa_db,
    criar_setor_db,
    listar_setores_empresa,
    buscar_perfil_usuario,
    buscar_empresa_por_id,
    buscar_funcionario_por_usuario,
)
from rekognition_servico import indexar_rosto_da_imagem_s3, reconhecer_funcionario_por_bytes
from aws_conexao import s3_client
from config import BUCKET_NAME
from formatadores import formatar_nome_para_external_id
from auth import verify_password, get_password_hash, create_access_token, decode_access_token

app = FastAPI(title="API Ponto Facial Empresarial")

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security = HTTPBearer()

# --- AUTH DEPENDENCY ---

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida o token JWT e retorna os dados do usuário."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    return payload

# --- MODELS ---

class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: str
    usuario_id: str
    empresa_id: str

class EmpresaCreate(BaseModel):
    nome: str
    cnpj: str
    plano: str = "Basico"

class SetorCreate(BaseModel):
    nome: str

class FuncionarioCreate(BaseModel):
    nome: str
    email: str
    matricula: str
    empresa_id: str
    setor_id: str
    cargo: Optional[str] = None

class PontoManual(BaseModel):
    funcionario_id: str
    tipo: str
    empresa_id: str

class UsuarioRH(BaseModel):
    nome: str
    email: str
    senha: str
    tipo_usuario: str = "RH"  # 'RH' ou 'Admin'
    empresa_id: str

# --- AUTH ---

@app.post("/auth/register")
def register_admin_rh(usuario: UsuarioRH):
    user_existente = buscar_usuario_por_email(usuario.email.strip())
    if user_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    senha_hash = get_password_hash(usuario.senha)
    dados_usuario = {
        "nome": usuario.nome,
        "email": usuario.email,
        "senha_hash": senha_hash,
        "tipo_usuario": usuario.tipo_usuario,
        "empresa_id": usuario.empresa_id,
    }

    sucesso = criar_usuario_rh(dados_usuario)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao criar usuário.")

    return {"mensagem": "Usuário RH/Admin criado com sucesso!"}

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = buscar_usuario_por_email(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    if not user.get("ativo", True):
        raise HTTPException(status_code=403, detail="Usuário desativado.")

    if not verify_password(form_data.password, user.get("senha", "")):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    access_token = create_access_token(data={
        "sub": user["email"],
        "role": user["tipo_usuario"],
        "usuario_id": user["usuario_id"],
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user["tipo_usuario"],
        "usuario_id": user["usuario_id"],
        "empresa_id": user.get("empresa_id", ""),
    }

# --- USUARIOS ---

@app.get("/usuarios/me")
def perfil_usuario(current_user: dict = Depends(get_current_user)):
    """Retorna o perfil completo do usuário logado."""
    perfil = buscar_perfil_usuario(current_user["usuario_id"])
    if not perfil:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return perfil

@app.get("/usuarios/me/funcionario")
def dados_funcionario_logado(current_user: dict = Depends(get_current_user)):
    """Retorna o funcionario_id do usuário logado (apenas para tipo Funcionario)."""
    func = buscar_funcionario_por_usuario(current_user["usuario_id"])
    if not func:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado para este usuário.")
    return func

# --- EMPRESAS ---

@app.post("/empresas", dependencies=[Depends(get_current_user)])
def criar_empresa(empresa: EmpresaCreate):
    existente = buscar_empresa_por_cnpj(empresa.cnpj)
    if existente:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado.")

    empresa_id = str(uuid.uuid4())
    sucesso = criar_empresa_db(empresa_id, empresa.nome, empresa.cnpj, empresa.plano)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao criar empresa.")

    return {"mensagem": "Empresa criada com sucesso!", "empresa_id": empresa_id}

@app.get("/empresas/{empresa_id}", dependencies=[Depends(get_current_user)])
def obter_empresa(empresa_id: str):
    """Retorna os dados de uma empresa pelo ID."""
    empresa = buscar_empresa_por_id(empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa

# --- SETORES ---

@app.post("/empresas/{empresa_id}/setores", dependencies=[Depends(get_current_user)])
def criar_setor(empresa_id: str, setor: SetorCreate):
    setor_id = str(uuid.uuid4())
    sucesso = criar_setor_db(setor_id, empresa_id, setor.nome)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao criar setor.")

    return {"mensagem": "Setor criado com sucesso!", "setor_id": setor_id}

@app.get("/setores/{empresa_id}", dependencies=[Depends(get_current_user)])
def listar_setores(empresa_id: str):
    """Lista todos os setores de uma empresa."""
    setores = listar_setores_empresa(empresa_id)
    return {"setores": setores}

# --- FUNCIONARIOS ---

@app.post("/funcionarios", dependencies=[Depends(get_current_user)])
async def cadastrar_funcionario_api(
    nome: str = Form(...),
    email: str = Form(...),
    matricula: str = Form(...),
    empresa_id: str = Form(...),
    setor_id: str = Form(...),
    cargo: Optional[str] = Form(None),
    foto: UploadFile = File(...),
):
    """
    Recebe dados e foto, salva no S3, indexa no Rekognition e salva no Banco.
    """
    try:
        usuario_existente = buscar_usuario_por_email(email.strip())
        if usuario_existente:
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        external_id = formatar_nome_para_external_id(nome)
        filename = f"funcionarios/{empresa_id}/{external_id}_{foto.filename}"

        temp_file = f"temp_{foto.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)

        s3_client.upload_file(temp_file, BUCKET_NAME, filename)

        resultado = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

        if not resultado or not resultado.get("FaceRecords"):
            os.remove(temp_file)
            raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

        face_id = resultado["FaceRecords"][0]["Face"]["FaceId"]

        sucesso = cadastrar_funcionario_com_foto(nome, email, matricula, empresa_id, setor_id, cargo, external_id, face_id, filename)

        os.remove(temp_file)

        if not sucesso:
            raise HTTPException(status_code=500, detail="Erro ao salvar no banco.")

        return {"status": "sucesso", "face_id": face_id, "external_id": external_id}

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(f"temp_{foto.filename}"):
            os.remove(f"temp_{foto.filename}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/funcionarios/{empresa_id}", dependencies=[Depends(get_current_user)])
def listar_funcionarios(empresa_id: str):
    funcionarios = listar_funcionarios_empresa(empresa_id)
    return {"funcionarios": funcionarios}

# --- PONTO ---

@app.post("/ponto/registrar")
async def registrar_ponto(foto: UploadFile = File(...)):
    """Registra ponto via reconhecimento facial."""
    try:
        image_bytes = foto.file.read()
        resultado = reconhecer_funcionario_por_bytes(image_bytes)

        if not resultado:
            raise HTTPException(status_code=404, detail="Rosto não reconhecido.")

        ponto = registrar_ponto_facial(resultado)
        if not ponto:
            raise HTTPException(status_code=500, detail="Erro ao registrar ponto no banco.")

        return ponto
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ponto/manual", dependencies=[Depends(get_current_user)])
def ponto_manual(ponto: PontoManual):
    registro = registrar_ponto_manual(ponto.funcionario_id, ponto.tipo, ponto.empresa_id)
    if not registro:
        raise HTTPException(status_code=500, detail="Erro ao registrar ponto.")
    return registro

@app.get("/ponto/historico/{funcionario_id}", dependencies=[Depends(get_current_user)])
def historico_ponto(funcionario_id: str):
    registros = listar_registros_funcionario(funcionario_id)
    return {"registros": registros}

@app.get("/ponto/hoje/{empresa_id}", dependencies=[Depends(get_current_user)])
def ponto_dia(empresa_id: str):
    registros = listar_registros_empresa_dia(empresa_id)
    return {"registros": registros}

@app.get("/")
def home():
    return {"mensagem": "API Ponto Facial Empresarial está rodando!"}
