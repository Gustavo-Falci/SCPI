import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
# Adiciona o diretÃ³rio 'BackEnd' ao sys.path para resolver problemas de importaÃ§Ã£o
# em ambientes onde o diretÃ³rio de trabalho nÃ£o Ã© a raiz do projeto.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import subprocess
import signal
import atexit
from typing import List, Optional

from db_operacoes import listar_turmas_professor, cadastrar_novo_aluno, buscar_usuario_por_email, criar_usuario_completo, obter_professor_id
from rekognition_aws import indexar_rosto_da_imagem_s3, reconhecer_aluno_por_bytes
from database import get_db_cursor
from db_operacoes import registrar_presenca_por_face
from aws_clientes import s3_client
from config import BUCKET_NAME
from utils import formatar_nome_para_external_id
from auth_utils import verify_password, get_password_hash, create_access_token, decode_access_token

app = FastAPI()

# --- GERENCIAMENTO DE PROCESSO DE RECONHECIMENTO ---
processo_camera = None

def encerrar_camera_no_exit():
    global processo_camera
    if processo_camera:
        print("Encerrando processo da cÃ¢mera...")
        processo_camera.terminate()

atexit.register(encerrar_camera_no_exit)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invÃ¡lido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

# ConfiguraÃ§Ã£o de CORS (Para o React Native conseguir acessar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    user_id: str
    user_name: str

class ChamadaAbrir(BaseModel):
    turma_id: str

@app.get("/teste_reload")
def teste_reload():
    return {"status": "reloaded"}

@app.get("/")
def home():
    return {"mensagem": "API SCPI estÃ¡ rodando!"}

# --- ENDPOINTS DE AUTENTICAÃÃO ---

@app.post("/auth/register")
def register(usuario: UsuarioRegistro):
    # 1. Verificar se usuÃ¡rio jÃ¡ existe
    user_existente = buscar_usuario_por_email(usuario.email.strip())
    if user_existente:
        raise HTTPException(status_code=400, detail="Email jÃ¡ cadastrado.")

    # 2. Validar dados especÃ­ficos
    dados_perfil = {}
    if usuario.tipo_usuario == 'Aluno':
        if not usuario.ra:
            raise HTTPException(status_code=400, detail="RA Ã© obrigatÃ³rio para alunos.")
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
        raise HTTPException(status_code=500, detail="B.O no servidor ao criar usuÃ¡rio. Tente novamente.")
    
    return {"mensagem": "UsuÃ¡rio criado com sucesso!"}

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = buscar_usuario_por_email(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Para testes gerados pelo setup_teste.py, a senha está em texto limpo '123'
    if user['senha'] == '123':
        if form_data.password != '123':
            raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    else:
        if not verify_password(form_data.password, user['senha']):
             raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Gerar Token
    access_token = create_access_token(data={"sub": str(user['usuario_id']), "email": user['email'], "role": user['tipo_usuario']})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user['tipo_usuario'],
        "user_id": str(user['usuario_id']),
        "user_name": user['nome']
    }


@app.get("/aluno/dashboard/{usuario_id}")
def get_dashboard_aluno(usuario_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            # 1. Nome do aluno
            cur.execute("SELECT nome FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
            user = cur.fetchone()
            nome = user['nome'] if user else "Aluno"

            # 2. Busca Aluno ID
            cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id = %s", (usuario_id,))
            aluno = cur.fetchone()

            if not aluno:
                raise HTTPException(status_code=404, detail="Aluno nÃ£o encontrado")

            aluno_id = aluno['aluno_id']

            # 3. Calcula FrequÃªncia Geral
            # (Total de presenÃ§as / Total de chamadas das turmas que ele participa)
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM Presencas WHERE aluno_id = %s) as total_presencas,
                    (SELECT COUNT(*) FROM Chamadas ch
                     JOIN Turma_Alunos ta ON ch.turma_id = ta.turma_id
                     WHERE ta.aluno_id = %s) as total_chamadas
            """, (aluno_id, aluno_id))
            freq_data = cur.fetchone()

            frequencia = 0
            if freq_data['total_chamadas'] > 0:
                frequencia = round((freq_data['total_presencas'] / freq_data['total_chamadas']) * 100)

            # 4. Busca aulas de hoje reais para o aluno
            import datetime
            dia_hoje = datetime.datetime.now().weekday()
            cur.execute("""
                SELECT h.horario_id as id, t.nome_disciplina as nome,
                       to_char(h.horario_inicio, 'HH24:MI') || ' - ' || to_char(h.horario_fim, 'HH24:MI') as horario,
                       h.sala
                FROM horarios_aulas h
                JOIN turmas t ON h.turma_id = t.turma_id
                JOIN turma_alunos ta ON t.turma_id = ta.turma_id
                WHERE ta.aluno_id = %s
                AND h.dia_semana = %s
            """, (aluno_id, dia_hoje))
            aulas_hoje = cur.fetchall()

            return {
                "nome": nome,
                "frequencia_geral": frequencia,
                "aulas_hoje": aulas_hoje
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/professor/dashboard/{usuario_id}")
def get_dashboard(usuario_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            # 1. Nome do professor
            cur.execute("SELECT nome FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
            user = cur.fetchone()
            nome = user['nome'] if user else "Professor"

            # 2. Busca última chamada aberta (ou última realizada) para pegar estatísticas
            cur.execute("""
                SELECT chamada_id, turma_id FROM Chamadas
                WHERE professor_id = (SELECT professor_id FROM Professores WHERE usuario_id = %s)
                ORDER BY data_criacao DESC LIMIT 1
            """, (usuario_id,))
            chamada = cur.fetchone()

            estatisticas = {"total": 0, "presentes": 0, "ausentes": 0, "disciplina": "Nenhuma chamada recente"}

            if chamada:
                # Total de alunos na turma
                cur.execute("SELECT COUNT(*) as total FROM Turma_Alunos WHERE turma_id = %s", (chamada['turma_id'],))
                estatisticas['total'] = cur.fetchone()['total']

                # Total de presentes
                cur.execute("SELECT COUNT(*) as presentes FROM Presencas WHERE chamada_id = %s", (chamada['chamada_id'],))
                estatisticas['presentes'] = cur.fetchone()['presentes']
                estatisticas['ausentes'] = estatisticas['total'] - estatisticas['presentes']

                # Nome da disciplina
                cur.execute("SELECT nome_disciplina FROM Turmas WHERE turma_id = %s", (chamada['turma_id'],))
                estatisticas['disciplina'] = cur.fetchone()['nome_disciplina']

            # 3. Busca aulas de hoje reais
            import datetime
            dia_hoje = datetime.datetime.now().weekday()
            cur.execute("""
                SELECT h.horario_id as id, t.nome_disciplina as nome,
                       to_char(h.horario_inicio, 'HH24:MI') || ' - ' || to_char(h.horario_fim, 'HH24:MI') as horario,
                       h.sala
                FROM horarios_aulas h
                JOIN turmas t ON h.turma_id = t.turma_id
                WHERE t.professor_id = (SELECT professor_id FROM Professores WHERE usuario_id = %s)
                AND h.dia_semana = %s
            """, (usuario_id, dia_hoje))
            aulas_hoje = cur.fetchall()

            return {
                "nome": nome,
                "estatisticas": estatisticas,
                "aulas_hoje": aulas_hoje
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/turmas/{usuario_id}")
def get_turmas(usuario_id: str):
    """Retorna as turmas de um professor usando sua funÃ§Ã£o existente."""
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
        # 1. Preparar ID Ãºnico 
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
# --- ENDPOINTS DE CHAMADAS ---

@app.post("/chamadas/abrir")
def abrir_chamada(dados: ChamadaAbrir, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "Professor":
        raise HTTPException(status_code=403, detail="Apenas professores podem abrir chamadas.")
    
    usuario_id = current_user.get("sub")
    professor_id = obter_professor_id(usuario_id)
    
    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor nÃ£o encontrado no banco.")

    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: raise Exception("Erro ao conectar no banco")
            
            # Fecha qualquer chamada aberta desta turma
            cur.execute("""
                UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME 
                WHERE turma_id=%s AND status='Aberta'
            """, (dados.turma_id,))
            
            # Abre nova chamada
            cur.execute("""
                INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta')
                RETURNING chamada_id
            """, (dados.turma_id, professor_id))
            
            nova_chamada = cur.fetchone()

            # Iniciar reconhecimento facial automaticamente (Headless)
            global processo_camera
            if processo_camera is None or processo_camera.poll() is not None:
                script_path = os.path.join(os.path.dirname(__file__), "reconhecimento_tempo_real.py")
                processo_camera = subprocess.Popen([sys.executable, script_path])
                print(f"Processo de reconhecimento iniciado (PID: {processo_camera.pid})")

            return {"mensagem": "Chamada aberta com sucesso!", "chamada_id": nova_chamada['chamada_id']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao abrir chamada: {str(e)}")


@app.post("/chamadas/fechar/{turma_id}")
def fechar_chamada(turma_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "Professor":
        raise HTTPException(status_code=403, detail="Apenas professores podem fechar chamadas.")

    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: raise Exception("Erro ao conectar no banco")
            
            cur.execute("""
                UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                WHERE turma_id=%s AND status='Aberta'
            """, (turma_id,))

            # Encerrar reconhecimento facial
            global processo_camera
            if processo_camera and processo_camera.poll() is None:
                processo_camera.terminate()
                print(f"Processo de reconhecimento (PID: {processo_camera.pid}) encerrado.")
                processo_camera = None

            return {"mensagem": "Chamada encerrada com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fechar chamada: {str(e)}")


@app.get("/chamadas/status/{turma_id}")
def status_chamada(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            if not cur: raise Exception("Erro ao conectar no banco")
            
            # 1. Verifica se tem chamada aberta
            cur.execute("""
                SELECT chamada_id, horario_inicio FROM Chamadas 
                WHERE turma_id=%s AND status='Aberta' ORDER BY data_criacao DESC LIMIT 1
            """, (turma_id,))
            chamada = cur.fetchone()
            
            if not chamada:
                return {"status": "Fechada", "total_alunos": 0, "presentes": 0, "ausentes": 0}
            
            chamada_id = chamada['chamada_id']

            # 2. Busca total de alunos na turma
            cur.execute("SELECT COUNT(*) as total FROM Turma_Alunos WHERE turma_id=%s", (turma_id,))
            total_alunos = cur.fetchone()['total']

            # 3. Busca total de presentes
            cur.execute("SELECT COUNT(*) as presentes FROM Presencas WHERE chamada_id=%s", (chamada_id,))
            presentes = cur.fetchone()['presentes']

            ausentes = total_alunos - presentes

            return {
                "status": "Aberta",
                "chamada_id": chamada_id,
                "horario_inicio": chamada['horario_inicio'],
                "total_alunos": total_alunos,
                "presentes": presentes,
                "ausentes": ausentes
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar status: {str(e)}")


@app.get("/chamadas/{chamada_id}/alunos")
def listar_alunos_chamada(chamada_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            if not cur: raise Exception("Erro ao conectar no banco")
            
            cur.execute("""
                SELECT 
                    a.aluno_id as id,
                    u.nome,
                    CASE WHEN p.presenca_id IS NOT NULL THEN true ELSE false END as presente
                FROM Chamadas c
                JOIN Turma_Alunos ta ON c.turma_id = ta.turma_id
                JOIN Alunos a ON ta.aluno_id = a.aluno_id
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                LEFT JOIN Presencas p ON a.aluno_id = p.aluno_id AND p.chamada_id = c.chamada_id
                WHERE c.chamada_id = %s
                ORDER BY u.nome ASC
            """, (chamada_id,))
            
            alunos = cur.fetchall()
            return {"alunos": alunos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar alunos: {str(e)}")



@app.post("/chamadas/registrar_rosto")
async def registrar_rosto_aluno(
    foto: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Recebe foto tirada pelo Aluno, envia pra AWS e se der match, tenta registrar presenÃ§a.
    """
    if current_user.get("role") != "Aluno":
        raise HTTPException(status_code=403, detail="Apenas alunos podem registrar presenÃ§a via rosto.")

    try:
        # Salva arquivo temp
        temp_file = f"temp_checkin_{foto.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
            
        with open(temp_file, "rb") as image_file:
            image_bytes = image_file.read()

        # Chama a AWS
        # A funcao buscar_faces_rekognition precisa ser ajustada para aceitar bytes no rekognition_aws.py
        # Vamos importar a s3_client e rekognition_client
        from config import COLLECTION_ID
        from aws_clientes import rekognition_client
        
        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=90
        )
        
        os.remove(temp_file)

        if not response.get('FaceMatches'):
            raise HTTPException(status_code=404, detail="Rosto nÃ£o reconhecido no sistema.")
            
        match = response['FaceMatches'][0]
        external_image_id = match['Face']['ExternalImageId']
        
        # Registra PresenÃ§a
        sucesso = registrar_presenca_por_face(external_image_id)
        
        if sucesso:
            return {"mensagem": "PresenÃ§a confirmada com sucesso!", "aluno": external_image_id}
        else:
            raise HTTPException(status_code=400, detail="NÃ£o foi possÃ­vel registrar a presenÃ§a. Verifique se hÃ¡ uma chamada aberta para sua turma.")

    except Exception as e:
        if os.path.exists(f"temp_checkin_{foto.filename}"):
            os.remove(f"temp_checkin_{foto.filename}")
        raise HTTPException(status_code=500, detail=str(e))
