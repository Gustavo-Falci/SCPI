import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
# Adiciona o diretório 'BackEnd' ao sys.path para resolver problemas de importação
# em ambientes onde o diretório de trabalho não é a raiz do projeto.
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
        print("Encerrando processo da câmera...")
        processo_camera.terminate()

atexit.register(encerrar_camera_no_exit)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

# Configuração de CORS (Para o React Native conseguir acessar)
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
    user_email: str
    user_ra: Optional[str] = None

class ChamadaAbrir(BaseModel):
    turma_id: str

@app.get("/teste_reload")
def teste_reload():
    return {"status": "reloaded"}

# --- ENDPOINTS ADMINISTRATIVOS ---

@app.get("/admin/professores")
def admin_listar_professores(current_user: dict = Depends(get_current_user)):
    # Em um sistema real, verificaríamos se current_user['role'] == 'Admin'
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT p.professor_id, u.nome, u.email, p.departamento 
                FROM Professores p
                JOIN Usuarios u ON p.usuario_id = u.usuario_id
                ORDER BY u.nome ASC
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/turmas-completas")
def admin_listar_turmas(current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT t.turma_id, t.nome_disciplina, t.codigo_turma, u.nome as professor_nome,
                (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = t.turma_id) as total_alunos
                FROM Turmas t
                JOIN Professores p ON t.professor_id = p.professor_id
                JOIN Usuarios u ON p.usuario_id = u.usuario_id
                ORDER BY t.nome_disciplina ASC
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TurmaCreate(BaseModel):
    professor_id: str
    codigo_turma: str
    nome_disciplina: str
    periodo_letivo: str
    sala_padrao: str

@app.post("/admin/turmas")
def admin_criar_turma(turma: TurmaCreate, current_user: dict = Depends(get_current_user)):
    try:
        import uuid
        turma_id = str(uuid.uuid4())
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING turma_id
            """, (turma_id, turma.professor_id, turma.codigo_turma, turma.nome_disciplina, turma.periodo_letivo, turma.sala_padrao))
            return {"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class HorarioCreate(BaseModel):
    turma_id: str
    dia_semana: int # 0-6
    horario_inicio: str # "HH:MM"
    horario_fim: str # "HH:MM"
    sala: str

@app.post("/admin/horarios")
def admin_adicionar_horario(h: HorarioCreate, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, horario_fim, sala)
                VALUES (%s, %s, %s, %s, %s)
            """, (h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala))
            return {"mensagem": "Horário adicionado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/turmas/{turma_id}")
def admin_excluir_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor(commit=True) as cur:
            # Exclui horários primeiro por causa da constraint
            cur.execute("DELETE FROM horarios_aulas WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turma_Alunos WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turmas WHERE turma_id = %s", (turma_id,))
            return {"mensagem": "Turma e dependências excluídas com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/horarios-todos")
def admin_listar_todos_horarios(current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT h.horario_id, h.turma_id, h.dia_semana, 
                       to_char(h.horario_inicio, 'HH24:MI') as inicio, 
                       to_char(h.horario_fim, 'HH24:MI') as fim, 
                       h.sala, t.nome_disciplina
                FROM horarios_aulas h
                JOIN Turmas t ON h.turma_id = t.turma_id
            """)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/horarios/{horario_id}")
def admin_excluir_horario(horario_id: int, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM horarios_aulas WHERE horario_id = %s", (horario_id,))
            return {"mensagem": "Horário removido!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/turmas/{turma_id}/importar-alunos")
async def admin_importar_alunos_csv(turma_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        import csv
        import io
        import uuid
        
        content = await file.read()
        decoded = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        importados = 0
        erros = []

        with get_db_cursor(commit=True) as cur:
            for row in csv_reader:
                try:
                    nome = row.get('nome')
                    email = row.get('email')
                    ra = row.get('ra')

                    if not nome or not email or not ra:
                        continue

                    # 1. Cria Usuário (Senha padrão '123' segura com Bcrypt)
                    user_uuid = str(uuid.uuid4())
                    senha_padrao_hash = get_password_hash("123")
                    cur.execute("""
                        INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                        VALUES (%s, %s, %s, %s, 'Aluno')
                        ON CONFLICT (email) DO NOTHING
                        RETURNING usuario_id
                    """, (user_uuid, nome, email, senha_padrao_hash))
                    
                    res_user = cur.fetchone()
                    usuario_id = res_user['usuario_id'] if res_user else None
                    
                    if not usuario_id: # Usuário já existe, busca o ID
                        cur.execute("SELECT usuario_id FROM Usuarios WHERE email = %s", (email,))
                        usuario_id = cur.fetchone()['usuario_id']

                    # 2. Cria Aluno
                    aluno_uuid = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO Alunos (aluno_id, usuario_id, ra)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (ra) DO NOTHING
                        RETURNING aluno_id
                    """, (aluno_uuid, usuario_id, ra))
                    
                    res_aluno = cur.fetchone()
                    aluno_id = res_aluno['aluno_id'] if res_aluno else None

                    if not aluno_id:
                        cur.execute("SELECT aluno_id FROM Alunos WHERE ra = %s", (ra,))
                        aluno_id = cur.fetchone()['aluno_id']

                    # 3. Matricula na Turma
                    cur.execute("""
                        INSERT INTO Turma_Alunos (turma_id, aluno_id)
                        VALUES (%s, %s)
                        ON CONFLICT (turma_id, aluno_id) DO NOTHING
                    """, (turma_id, aluno_id))
                    
                    importados += 1
                except Exception as e:
                    erros.append(f"Erro na linha {row}: {str(e)}")

        return {"mensagem": f"Importação concluída: {importados} alunos matriculados.", "erros": erros}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    # Remove espaços em branco do email para evitar erros de digitação
    email_limpo = form_data.username.strip()

    # Busca usuário de forma insensível a maiúsculas/minúsculas
    with get_db_cursor() as cur:
        cur.execute("SELECT usuario_id, nome, email, senha, tipo_usuario FROM Usuarios WHERE LOWER(email) = LOWER(%s)", (email_limpo,))
        user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Tenta verificar como Bcrypt ou PBKDF2
    try:
        senha_valida = verify_password(form_data.password, user['senha'])
    except Exception:
        senha_valida = (form_data.password == user['senha'])

    if not senha_valida:
         raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Gerar Token
    access_token = create_access_token(data={"sub": str(user['usuario_id']), "email": user['email'], "role": user['tipo_usuario']})

    # Busca RA se for aluno
    ra = None
    if user['tipo_usuario'] == 'Aluno':
        with get_db_cursor() as cur:
            cur.execute("SELECT ra FROM Alunos WHERE usuario_id = %s", (user['usuario_id'],))
            aluno_data = cur.fetchone()
            if aluno_data:
                ra = aluno_data['ra']

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user['tipo_usuario'],
        "user_id": str(user['usuario_id']),
        "user_name": user['nome'],
        "user_email": user['email'],
        "user_ra": ra
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
                raise HTTPException(status_code=404, detail="Aluno não encontrado")

            aluno_id = aluno['aluno_id']

            # 3. Calcula Frequência Geral
            # (Total de presenças / Total de chamadas das turmas que ele participa)
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


@app.get("/aluno/frequencias/{usuario_id}")
def get_frequencias_detalhadas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            # 1. Busca Aluno ID
            cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id = %s", (usuario_id,))
            aluno = cur.fetchone()
            if not aluno:
                raise HTTPException(status_code=404, detail="Aluno não encontrado")
            
            aluno_id = aluno['aluno_id']

            # 2. Busca estatísticas por disciplina
            # Pega todas as turmas que o aluno participa e conta as chamadas totais e presenças dele
            cur.execute("""
                SELECT 
                    t.nome_disciplina as nome,
                    (SELECT COUNT(*) FROM Chamadas ch WHERE ch.turma_id = t.turma_id AND ch.status = 'Fechada') as total_aulas,
                    (SELECT COUNT(*) FROM Presencas p 
                     JOIN Chamadas ch ON p.chamada_id = ch.chamada_id
                     WHERE p.aluno_id = %s AND ch.turma_id = t.turma_id) as presencas
                FROM Turma_Alunos ta
                JOIN Turmas t ON ta.turma_id = t.turma_id
                WHERE ta.aluno_id = %s
            """, (aluno_id, aluno_id))
            
            rows = cur.fetchall()
            
            frequencias = []
            total_presencas_global = 0
            total_chamadas_global = 0

            for row in rows:
                presencas = row['presencas']
                total = row['total_aulas']
                percentual = round((presencas / total * 100)) if total > 0 else 0
                
                frequencias.append({
                    "nome": row['nome'],
                    "presenca": percentual,
                    "total": total,
                    "presencas_count": presencas,
                    "faltas_count": total - presencas
                })
                
                total_presencas_global += presencas
                total_chamadas_global += total

            media_geral = round((total_presencas_global / total_chamadas_global * 100)) if total_chamadas_global > 0 else 0

            return {
                "media_geral": media_geral,
                "frequencias": frequencias
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
    """Retorna as turmas de um professor com flag indicando se está no horário de aula."""
    try:
        import datetime
        agora = datetime.datetime.now()
        dia_semana = agora.weekday() # 0-6 (Seg-Dom)
        hora_atual = agora.time()

        with get_db_cursor() as cur:
            # Busca turmas e seus horários
            cur.execute("""
                SELECT 
                    t.turma_id, 
                    t.nome_disciplina, 
                    t.codigo_turma,
                    h.dia_semana,
                    h.horario_inicio,
                    h.horario_fim
                FROM Turmas t
                LEFT JOIN horarios_aulas h ON t.turma_id = h.turma_id
                WHERE t.professor_id = (SELECT professor_id FROM Professores WHERE usuario_id = %s)
            """, (usuario_id,))
            
            rows = cur.fetchall()
            turmas_dict = {}

            for row in rows:
                t_id = row['turma_id']
                if t_id not in turmas_dict:
                    turmas_dict[t_id] = {
                        "turma_id": t_id,
                        "nome_disciplina": row['nome_disciplina'],
                        "codigo_turma": row['codigo_turma'],
                        "pode_iniciar": False,
                        "proximo_horario": "Sem horário definido"
                    }
                
                # Valida se esta aula está acontecendo AGORA
                if row['dia_semana'] == dia_semana:
                    if row['horario_inicio'] <= hora_atual <= row['horario_fim']:
                        turmas_dict[t_id]["pode_iniciar"] = True
                    
                    # Formata o horário para exibição
                    turmas_dict[t_id]["proximo_horario"] = f"Hoje: {row['horario_inicio'].strftime('%H:%M')} - {row['horario_fim'].strftime('%H:%M')}"
                elif turmas_dict[t_id]["proximo_horario"] == "Sem horário definido" and row['dia_semana'] is not None:
                     dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
                     turmas_dict[t_id]["proximo_horario"] = f"{dias[row['dia_semana']]}: {row['horario_inicio'].strftime('%H:%M')}"

            return {"turmas": list(turmas_dict.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/turmas/{turma_id}/alunos")
def get_alunos_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    a.aluno_id as id,
                    u.nome,
                    u.email,
                    a.ra
                FROM Turma_Alunos ta
                JOIN Alunos a ON ta.aluno_id = a.aluno_id
                JOIN Usuarios u ON a.usuario_id = u.usuario_id
                WHERE ta.turma_id = %s
                ORDER BY u.nome ASC
            """, (turma_id,))
            alunos = cur.fetchall()
            return {"alunos": alunos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alunos/cadastrar-face")
async def cadastrar_aluno_api(
    user_id: Optional[str] = Form(None),
    nome: str = Form(...),
    email: str = Form(...),
    ra: str = Form(...),
    foto: UploadFile = File(...)
):
    """
    Recebe dados e foto do App, salva no S3, indexa no Rekognition e salva no Banco.
    """
    try:
        # 1. Localizar o Aluno (por ID ou por Email/RA)
        with get_db_cursor() as cur:
            if user_id:
                cur.execute("SELECT u.usuario_id FROM Usuarios u WHERE u.usuario_id = %s", (user_id,))
            else:
                cur.execute("SELECT u.usuario_id FROM Usuarios u WHERE u.email = %s", (email,))
            
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="Usuário não localizado para vincular face.")
            
            target_user_id = user['usuario_id']

        # 2. Preparar ID único 
        external_id = formatar_nome_para_external_id(nome)
        filename = f"alunos/{external_id}_{foto.filename}"

        # 3. Salvar arquivo temporariamente para envio
        temp_file = f"temp_{foto.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)

        # 4. Upload para o S3 
        s3_client.upload_file(temp_file, BUCKET_NAME, filename)
        
        resultado_rekognition = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

        if not resultado_rekognition or not resultado_rekognition.get("FaceRecords"):
             os.remove(temp_file)
             raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

        face_id = resultado_rekognition["FaceRecords"][0]["Face"]["FaceId"]

        # 4. Atualizar ou Inserir registro na Coleção de Rostos
        with get_db_cursor(commit=True) as cur:
            # Primeiro, pegamos o aluno_id usando o target_user_id
            cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id = %s", (target_user_id,))
            aluno = cur.fetchone()
            if not aluno:
                raise HTTPException(status_code=404, detail="Perfil de aluno não encontrado para este usuário.")

            aluno_id = aluno['aluno_id']

            # 4. Verificar se já existe biometria para este aluno
            cur.execute("SELECT 1 FROM Colecao_Rostos WHERE aluno_id = %s", (aluno_id,))
            exists = cur.fetchone()

            if exists:
                # Se existe, atualiza
                cur.execute("""
                    UPDATE Colecao_Rostos 
                    SET external_image_id = %s,
                        face_id_rekognition = %s,
                        s3_path_cadastro = %s
                    WHERE aluno_id = %s
                """, (external_id, face_id, filename, aluno_id))
            else:
                # Se não existe, insere novo
                cur.execute("""
                    INSERT INTO Colecao_Rostos (aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro)
                    VALUES (%s, %s, %s, %s)
                """, (aluno_id, external_id, face_id, filename))

            os.remove(temp_file)
            return {"status": "sucesso", "face_id": face_id, "external_id": external_id}

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
        raise HTTPException(status_code=404, detail="Professor não encontrado no banco.")

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
    Recebe foto tirada pelo Aluno, envia pra AWS e se der match, tenta registrar presença.
    """
    if current_user.get("role") != "Aluno":
        raise HTTPException(status_code=403, detail="Apenas alunos podem registrar presença via rosto.")

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
            raise HTTPException(status_code=404, detail="Rosto não reconhecido no sistema.")
            
        match = response['FaceMatches'][0]
        external_image_id = match['Face']['ExternalImageId']
        
        # Registra Presença
        sucesso = registrar_presenca_por_face(external_image_id)
        
        if sucesso:
            return {"mensagem": "Presença confirmada com sucesso!", "aluno": external_image_id}
        else:
            raise HTTPException(status_code=400, detail="Não foi possível registrar a presença. Verifique se há uma chamada aberta para sua turma.")

    except Exception as e:
        if os.path.exists(f"temp_checkin_{foto.filename}"):
            os.remove(f"temp_checkin_{foto.filename}")
        raise HTTPException(status_code=500, detail=str(e))
