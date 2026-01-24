from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
from typing import List, Optional

from db_operacoes import listar_turmas_professor, cadastrar_novo_aluno, buscar_usuario_por_email, criar_usuario_completo
from rekognition_aws import indexar_rosto_da_imagem_s3
from aws_clientes import s3_client
from config import BUCKET_NAME
from utils import formatar_nome_para_external_id
from auth_utils import verify_password, get_password_hash, create_access_token, decode_access_token

app = FastAPI()

# Configuração de CORS (Para o React Native conseguir acessar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- MODELOS PYDANTIC ---
class UsuarioRegistro(BaseModel):
    nome: str
    email: str
    senha: str
    tipo_usuario: str # 'Professor' ou 'Aluno'
    # Campos opcionais dependendo do tipo
    ra: Optional[str] = None
    departamento: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: str

@app.get("/")
def home():
    return {"mensagem": "API SCPI está rodando!"}

# --- ENDPOINTS DE AUTENTICAÇÃO ---

@app.post("/auth/register")
def register(usuario: UsuarioRegistro):
    # 1. Verificar se usuário já existe
    user_existente = buscar_usuario_por_email(usuario.email.strip())
    if user_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    # 2. Validar dados específicos
    dados_perfil = {}
    if usuario.tipo_usuario == 'Aluno':
        if not usuario.ra:
            raise HTTPException(status_code=400, detail="RA é obrigatório para alunos.")
        dados_perfil['ra'] = usuario.ra
    elif usuario.tipo_usuario == 'Professor':
        dados_perfil['departamento'] = usuario.departamento

    # 3. Criar hash da senha
    senha_hash = get_password_hash(usuario.senha)

    # 4. Salvar no banco
    dados_usuario = {
        "nome": usuario.nome,
        "email": usuario.email,
        "senha_hash": senha_hash,
        "tipo_usuario": usuario.tipo_usuario
    }
    
    sucesso = criar_usuario_completo(dados_usuario, dados_perfil)
    if not sucesso:
        raise HTTPException(status_code=500, detail="B.O no servidor ao criar usuário. Tente novamente.")
    
    return {"mensagem": "Usuário criado com sucesso!"}

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # OAuth2PasswordRequestForm usa 'username' e 'password'
    user = buscar_usuario_por_email(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    
    if not verify_password(form_data.password, user['senha']):
         raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Gerar Token
    access_token = create_access_token(data={"sub": user['email'], "role": user['tipo_usuario']})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_role": user['tipo_usuario']
    }


@app.get("/turmas/{usuario_id}")
def get_turmas(usuario_id: str):
    """Retorna as turmas de um professor usando sua função existente."""
    turmas = listar_turmas_professor(usuario_id)
    if not turmas:
        return {"turmas": []}
    return {"turmas": turmas}

@app.post("/alunos/cadastrar")
async def cadastrar_aluno_api(
    nome: str = Form(...),
    email: str = Form(...),
    ra: str = Form(...),
    turma_id: str = Form(...),
    foto: UploadFile = File(...)
):
    """
    Recebe dados e foto do App, salva no S3, indexa no Rekognition e salva no Banco.
    """
    try:
        # 1. Preparar ID único 
        external_id = formatar_nome_para_external_id(nome)
        filename = f"alunos/{external_id}_{foto.filename}"

        # 2. Salvar arquivo temporariamente para envio
        temp_file = f"temp_{foto.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)

        # 3. Upload para o S3 
        s3_client.upload_file(temp_file, BUCKET_NAME, filename)
        
        resultado_rekognition = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

        if not resultado_rekognition or not resultado_rekognition.get("FaceRecords"):
             os.remove(temp_file)
             raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

        face_id = resultado_rekognition["FaceRecords"][0]["Face"]["FaceId"]

        sucesso = cadastrar_novo_aluno(nome, email, ra, turma_id, external_id, face_id, filename)
        
        os.remove(temp_file)

        if sucesso:
            return {"status": "sucesso", "face_id": face_id, "external_id": external_id}
        else:
            raise HTTPException(status_code=500, detail="Erro ao salvar no banco de dados.")

    except Exception as e:
        if os.path.exists(f"temp_{foto.filename}"):
            os.remove(f"temp_{foto.filename}")
        raise HTTPException(status_code=500, detail=str(e))