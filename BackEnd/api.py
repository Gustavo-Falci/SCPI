import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
# Adiciona o diretório 'BackEnd' ao sys.path para resolver problemas de importação
# em ambientes onde o diretório de trabalho não é a raiz do projeto.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import logging
import shutil
import os
import subprocess
import signal
import atexit
from typing import List, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("scpi.api")
audit_logger = logging.getLogger("scpi.audit")

# ---- Upload policy ----
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png"}


async def validate_image_upload(foto: UploadFile) -> bytes:
    """Valida content-type e tamanho da imagem, retornando os bytes já lidos.

    Deve ser chamada antes de qualquer gravação em disco/S3.
    """
    if foto.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(status_code=400, detail="Apenas imagens JPEG ou PNG são permitidas.")
    content = await foto.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Imagem muito grande (limite: 5 MB).")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")
    return content


def internal_error(exc: Exception, context: str = "unknown") -> HTTPException:
    """Loga internamente a exceção e devolve 500 genérico ao cliente (sem vazar stack)."""
    logger.exception("Erro interno em %s: %s", context, exc)
    return HTTPException(status_code=500, detail="Erro interno do servidor.")

from db_operacoes import listar_turmas_professor, cadastrar_novo_aluno, buscar_usuario_por_email, criar_usuario_completo, obter_professor_id
from rekognition_aws import indexar_rosto_da_imagem_s3, reconhecer_aluno_por_bytes, deletar_rosto
from database import get_db_cursor
from db_operacoes import registrar_presenca_por_face
from aws_clientes import s3_client
from config import BUCKET_NAME
from utils import formatar_nome_para_external_id
from auth_utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    hash_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

app = FastAPI()


def _ensure_lgpd_columns():
    """Adiciona colunas de consentimento/revogação de biometria (idempotente)."""
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                ALTER TABLE Colecao_Rostos
                ADD COLUMN IF NOT EXISTS consentimento_biometrico BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            cur.execute(
                """
                ALTER TABLE Colecao_Rostos
                ADD COLUMN IF NOT EXISTS consentimento_data TIMESTAMP NULL
                """
            )
            cur.execute(
                """
                ALTER TABLE Colecao_Rostos
                ADD COLUMN IF NOT EXISTS revogado_em TIMESTAMP NULL
                """
            )
    except Exception as e:
        logger.error("Falha ao aplicar colunas LGPD: %s", e)


def _ensure_refresh_tokens_table():
    """Cria a tabela RefreshTokens se ainda não existir.

    Guarda apenas o hash SHA-256 do token opaco — o plain nunca é persistido.
    """
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS RefreshTokens (
                    token_hash VARCHAR(128) PRIMARY KEY,
                    usuario_id VARCHAR(64) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMP NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_refresh_usuario ON RefreshTokens (usuario_id)"
            )
    except Exception as e:
        logger.error("Falha ao criar tabela RefreshTokens: %s", e)


def _ensure_push_tokens_table():
    """Cria a tabela PushTokens para armazenar tokens Expo de notificação push."""
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS PushTokens (
                    usuario_id VARCHAR(64) PRIMARY KEY,
                    expo_token TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    except Exception as e:
        logger.error("Falha ao criar tabela PushTokens: %s", e)


@app.on_event("startup")
def _on_startup():
    _ensure_refresh_tokens_table()
    _ensure_lgpd_columns()
    _ensure_push_tokens_table()


# ---- Rate limiting (por IP) ----
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


def require_role(*roles: str):
    """Dependency factory: exige que o usuário autenticado tenha uma das roles informadas."""
    def _checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Acesso negado para este perfil.")
        return current_user
    return _checker


def require_self_or_admin(usuario_id: str, current_user: dict) -> None:
    """Garante que o usuário autenticado é o dono do recurso ou um Admin."""
    if current_user.get("sub") != usuario_id and current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Acesso negado a este recurso.")


# Configuração de CORS — origens vêm de ALLOWED_ORIGINS (separadas por vírgula)
_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _raw_origins:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    # Fallback apenas para desenvolvimento local (não inclui wildcard)
    _allowed_origins = [
        "http://localhost:8081",
        "http://localhost:19006",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


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


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, max_length=256)

class ChamadaAbrir(BaseModel):
    turma_id: str

@app.get("/teste_reload")
def teste_reload():
    return {"status": "reloaded"}

# --- ENDPOINTS ADMINISTRATIVOS ---

@app.get("/admin/professores")
def admin_listar_professores(current_user: dict = Depends(require_role("Admin"))):
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
        raise internal_error(e)

@app.get("/admin/turmas-completas")
def admin_listar_turmas(current_user: dict = Depends(require_role("Admin"))):
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT t.turma_id, t.nome_disciplina, t.codigo_turma, t.turno, t.semestre, u.nome as professor_nome,
                (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = t.turma_id) as total_alunos
                FROM Turmas t
                JOIN Professores p ON t.professor_id = p.professor_id
                JOIN Usuarios u ON p.usuario_id = u.usuario_id
                ORDER BY t.semestre ASC, t.nome_disciplina ASC
            """)
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)

class TurmaCreate(BaseModel):
    professor_id: str = Field(..., min_length=1, max_length=64)
    codigo_turma: str = Field(..., min_length=1, max_length=30)
    nome_disciplina: str = Field(..., min_length=2, max_length=120)
    periodo_letivo: str = Field(..., min_length=1, max_length=20)
    sala_padrao: str = Field(..., min_length=1, max_length=30)
    turno: str = Field(..., pattern=r"^(Matutino|Vespertino|Noturno|Integral)$")
    semestre: str = Field(..., min_length=1, max_length=10)

@app.post("/admin/turmas")
def admin_criar_turma(turma: TurmaCreate, current_user: dict = Depends(require_role("Admin"))):
    try:
        import uuid
        turma_id = str(uuid.uuid4())
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao, turno, semestre)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING turma_id
            """, (turma_id, turma.professor_id, turma.codigo_turma, turma.nome_disciplina, turma.periodo_letivo, turma.sala_padrao, turma.turno, turma.semestre))
            return {"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}
    except Exception as e:
        raise internal_error(e)

class HorarioCreate(BaseModel):
    turma_id: str = Field(..., min_length=1, max_length=64)
    dia_semana: int = Field(..., ge=0, le=6)
    horario_inicio: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    horario_fim: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    sala: str = Field(..., min_length=1, max_length=30)

@app.post("/admin/horarios")
def admin_adicionar_horario(h: HorarioCreate, current_user: dict = Depends(require_role("Admin"))):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("""
                INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, horario_fim, sala)
                VALUES (%s, %s, %s, %s, %s)
            """, (h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala))
            return {"mensagem": "Horário adicionado com sucesso!"}
    except Exception as e:
        raise internal_error(e)

@app.delete("/admin/turmas/{turma_id}")
def admin_excluir_turma(turma_id: str, current_user: dict = Depends(require_role("Admin"))):
    try:
        with get_db_cursor(commit=True) as cur:
            # Exclui horários primeiro por causa da constraint
            cur.execute("DELETE FROM horarios_aulas WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turma_Alunos WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turmas WHERE turma_id = %s", (turma_id,))
            return {"mensagem": "Turma e dependências excluídas com sucesso!"}
    except Exception as e:
        raise internal_error(e)

@app.get("/admin/horarios-todos")
def admin_listar_todos_horarios(current_user: dict = Depends(require_role("Admin"))):
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT h.horario_id, h.turma_id, h.dia_semana, 
                       to_char(h.horario_inicio, 'HH24:MI') as inicio, 
                       to_char(h.horario_fim, 'HH24:MI') as fim, 
                       h.sala, t.nome_disciplina, t.turno, t.semestre
                FROM horarios_aulas h
                JOIN Turmas t ON h.turma_id = t.turma_id
            """)
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)

@app.delete("/admin/horarios/{horario_id}")
def admin_excluir_horario(horario_id: int, current_user: dict = Depends(require_role("Admin"))):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM horarios_aulas WHERE horario_id = %s", (horario_id,))
            return {"mensagem": "Horário removido!"}
    except Exception as e:
        raise internal_error(e)

class MatricularAlunos(BaseModel):
    aluno_ids: List[str]


@app.get("/admin/alunos")
def admin_listar_alunos(turma_id: Optional[str] = None, current_user: dict = Depends(require_role("Admin"))):
    """
    Lista todos os alunos cadastrados. Se `turma_id` for informado, também
    marca cada aluno com `ja_matriculado=True/False` para a turma em questão.
    """
    try:
        with get_db_cursor() as cur:
            if turma_id:
                cur.execute("""
                    SELECT
                        a.aluno_id, a.ra, u.nome, u.email,
                        EXISTS(
                            SELECT 1 FROM Turma_Alunos ta
                            WHERE ta.aluno_id = a.aluno_id AND ta.turma_id = %s
                        ) as ja_matriculado
                    FROM Alunos a
                    JOIN Usuarios u ON a.usuario_id = u.usuario_id
                    ORDER BY u.nome
                """, (turma_id,))
            else:
                cur.execute("""
                    SELECT a.aluno_id, a.ra, u.nome, u.email, FALSE as ja_matriculado
                    FROM Alunos a
                    JOIN Usuarios u ON a.usuario_id = u.usuario_id
                    ORDER BY u.nome
                """)
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)


@app.post("/admin/turmas/{turma_id}/matricular-alunos")
def admin_matricular_alunos(turma_id: str, dados: MatricularAlunos, current_user: dict = Depends(require_role("Admin"))):
    """
    Matricula um ou mais alunos já cadastrados em uma turma.
    Idempotente: alunos já matriculados são ignorados silenciosamente.
    """
    if not dados.aluno_ids:
        raise HTTPException(status_code=400, detail="Nenhum aluno selecionado.")
    try:
        matriculados = 0
        with get_db_cursor(commit=True) as cur:
            for aluno_id in dados.aluno_ids:
                cur.execute("""
                    INSERT INTO Turma_Alunos (turma_id, aluno_id)
                    VALUES (%s, %s)
                    ON CONFLICT (turma_id, aluno_id) DO NOTHING
                """, (turma_id, aluno_id))
                if cur.rowcount and cur.rowcount > 0:
                    matriculados += 1
        return {"mensagem": f"{matriculados} aluno(s) matriculado(s) com sucesso.", "total_enviados": len(dados.aluno_ids)}
    except Exception as e:
        raise internal_error(e)


@app.post("/admin/turmas/{turma_id}/importar-alunos")
async def admin_importar_alunos_csv(turma_id: str, file: UploadFile = File(...), current_user: dict = Depends(require_role("Admin"))):
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
        raise internal_error(e)

@app.get("/")
def home():
    return {"mensagem": "API SCPI está rodando!"}

# --- ENDPOINTS DE AUTENTICAÇÃO ---

@app.post("/auth/register")
@limiter.limit("5/minute")
def register(request: Request, usuario: UsuarioRegistro):
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


@app.post("/auth/register-aluno-com-face")
@limiter.limit("5/minute")
async def register_aluno_com_face(
    request: Request,
    nome: str = Form(..., min_length=3, max_length=100),
    email: EmailStr = Form(...),
    senha: str = Form(..., min_length=8, max_length=128),
    ra: str = Form(..., pattern=r"^[A-Za-z0-9]{4,20}$"),
    foto: UploadFile = File(...),
    consentimento_biometrico: bool = Form(...),
):
    """
    Cadastro atômico de Aluno: a face é validada no Rekognition ANTES
    de qualquer gravação no banco. Se a face falhar, nenhum registro é criado.
    """
    import uuid as _uuid

    if not consentimento_biometrico:
        raise HTTPException(
            status_code=400,
            detail="É necessário consentimento explícito para processar dados biométricos (LGPD art. 11).",
        )

    email_limpo = email.strip()
    if not ra:
        raise HTTPException(status_code=400, detail="RA é obrigatório para alunos.")
    if buscar_usuario_por_email(email_limpo):
        raise HTTPException(status_code=400, detail="Email já cadastrado.")

    # Valida tipo e tamanho ANTES de gravar em disco
    image_bytes = await validate_image_upload(foto)

    import uuid as _uuid_fname
    ext = ".jpg" if foto.content_type in {"image/jpeg", "image/jpg"} else ".png"
    safe_basename = f"{_uuid_fname.uuid4().hex}{ext}"
    external_id = formatar_nome_para_external_id(nome)
    s3_filename = f"alunos/{external_id}_{safe_basename}"
    temp_file = f"temp_{safe_basename}"
    face_id_indexado = None

    try:
        # 1. Salvar arquivo temporário e enviar ao S3
        with open(temp_file, "wb") as buffer:
            buffer.write(image_bytes)
        s3_client.upload_file(temp_file, BUCKET_NAME, s3_filename)

        # 2. Validar face no Rekognition ANTES de tocar no banco
        resultado = indexar_rosto_da_imagem_s3(s3_filename, external_id, detection_attributes="ALL")
        if not resultado or not resultado.get("FaceRecords"):
            raise HTTPException(
                status_code=400,
                detail="Nenhum rosto detectado na imagem. Nada foi salvo — tente novamente."
            )
        face_id_indexado = resultado["FaceRecords"][0]["Face"]["FaceId"]

        # 3. Só agora gravamos no banco, em uma única transação
        senha_hash = get_password_hash(senha)
        usuario_uuid = str(_uuid.uuid4())
        aluno_uuid = str(_uuid.uuid4())

        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                    VALUES (%s, %s, %s, %s, 'Aluno')
                    """,
                    (usuario_uuid, nome, email_limpo, senha_hash),
                )
                cur.execute(
                    """
                    INSERT INTO Alunos (aluno_id, usuario_id, ra)
                    VALUES (%s, %s, %s)
                    """,
                    (aluno_uuid, usuario_uuid, ra),
                )
                cur.execute(
                    """
                    INSERT INTO Colecao_Rostos (
                        aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro,
                        consentimento_biometrico, consentimento_data
                    )
                    VALUES (%s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                    """,
                    (aluno_uuid, external_id, face_id_indexado, s3_filename),
                )
        except Exception as db_err:
            # Rollback do rosto na AWS para não deixar lixo órfão
            deletar_rosto(face_id_indexado)
            raise internal_error(db_err, "register_aluno_com_face.db_insert")

        return {"status": "sucesso", "mensagem": "Conta criada com biometria facial!"}

    except HTTPException:
        raise
    except Exception as e:
        if face_id_indexado:
            deletar_rosto(face_id_indexado)
        raise internal_error(e)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@app.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # Remove espaços em branco do email para evitar erros de digitação
    email_limpo = form_data.username.strip()

    # Busca usuário de forma insensível a maiúsculas/minúsculas
    with get_db_cursor() as cur:
        cur.execute("SELECT usuario_id, nome, email, senha, tipo_usuario FROM Usuarios WHERE LOWER(email) = LOWER(%s)", (email_limpo,))
        user = cur.fetchone()

    if not user:
        audit_logger.warning("Login falhou (usuário inexistente) email=%s ip=%s", email_limpo, request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    # Tenta verificar como Bcrypt ou PBKDF2
    try:
        senha_valida = verify_password(form_data.password, user['senha'])
    except Exception:
        senha_valida = False

    if not senha_valida:
        audit_logger.warning("Login falhou (senha incorreta) email=%s ip=%s", email_limpo, request.client.host)
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    audit_logger.info("Login ok email=%s role=%s ip=%s", email_limpo, user['tipo_usuario'], request.client.host)

    # Gerar Token de acesso (curta duração) e refresh token (longa duração, opaco)
    access_token = create_access_token(data={"sub": str(user['usuario_id']), "email": user['email'], "role": user['tipo_usuario']})
    refresh_plain, refresh_hash, refresh_exp = create_refresh_token()

    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO RefreshTokens (token_hash, usuario_id, expires_at)
                VALUES (%s, %s, %s)
                """,
                (refresh_hash, str(user['usuario_id']), refresh_exp),
            )
    except Exception as e:
        raise internal_error(e, "login.persist_refresh_token")

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
        "refresh_token": refresh_plain,
        "token_type": "bearer",
        "user_role": user['tipo_usuario'],
        "user_id": str(user['usuario_id']),
        "user_name": user['nome'],
        "user_email": user['email'],
        "user_ra": ra
    }


@app.post("/auth/refresh")
@limiter.limit("30/minute")
def refresh_access_token(request: Request, body: RefreshRequest):
    """Troca um refresh token válido por um novo access token (rotação)."""
    token_hash = hash_refresh_token(body.refresh_token)
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                SELECT rt.usuario_id, rt.expires_at, rt.revoked_at,
                       u.email, u.tipo_usuario
                FROM RefreshTokens rt
                JOIN Usuarios u ON u.usuario_id::text = rt.usuario_id
                WHERE rt.token_hash = %s
                """,
                (token_hash,),
            )
            row = cur.fetchone()

            if not row or row.get("revoked_at") is not None:
                raise HTTPException(status_code=401, detail="Refresh token inválido.")

            import datetime as _dt
            if row["expires_at"] < _dt.datetime.utcnow():
                raise HTTPException(status_code=401, detail="Refresh token expirado.")

            # Rotação: revoga o atual e emite um novo
            cur.execute(
                "UPDATE RefreshTokens SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = %s",
                (token_hash,),
            )
            new_plain, new_hash, new_exp = create_refresh_token()
            cur.execute(
                "INSERT INTO RefreshTokens (token_hash, usuario_id, expires_at) VALUES (%s, %s, %s)",
                (new_hash, row["usuario_id"], new_exp),
            )

            access_token = create_access_token(
                data={"sub": row["usuario_id"], "email": row["email"], "role": row["tipo_usuario"]}
            )

            return {
                "access_token": access_token,
                "refresh_token": new_plain,
                "token_type": "bearer",
            }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "refresh_access_token")


@app.post("/auth/logout")
def logout(body: RefreshRequest, current_user: dict = Depends(get_current_user)):
    """Revoga o refresh token informado. Access token continua válido até expirar naturalmente."""
    token_hash = hash_refresh_token(body.refresh_token)
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                UPDATE RefreshTokens
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE token_hash = %s AND usuario_id = %s AND revoked_at IS NULL
                """,
                (token_hash, current_user.get("sub")),
            )
        audit_logger.info("Logout usuario=%s", current_user.get("sub"))
        return {"mensagem": "Sessão encerrada."}
    except Exception as e:
        raise internal_error(e, "logout")


class RegisterTokenBody(BaseModel):
    expo_token: str = Field(..., min_length=10, max_length=256)


@app.post("/notificacoes/registrar-token")
def registrar_push_token(body: RegisterTokenBody, current_user: dict = Depends(get_current_user)):
    """Salva ou atualiza o Expo push token do usuário autenticado."""
    usuario_id = current_user.get("sub")
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO PushTokens (usuario_id, expo_token, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (usuario_id) DO UPDATE
                    SET expo_token = EXCLUDED.expo_token,
                        updated_at = CURRENT_TIMESTAMP
                """,
                (usuario_id, body.expo_token),
            )
        logger.info("Push token registrado para usuario=%s", usuario_id)
        return {"mensagem": "Token registrado com sucesso."}
    except Exception as e:
        raise internal_error(e, "registrar_push_token")


def _enviar_notificacoes_presenca(usuario_id: str, aluno_nome: str, aluno_email: str, turma_nome: str) -> None:
    """Tarefa de background: dispara push + email após confirmação de presença."""
    from notificacoes import send_expo_push, send_email_resend
    import datetime

    hora = datetime.datetime.now().strftime("%H:%M")

    if usuario_id:
        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT expo_token FROM PushTokens WHERE usuario_id = %s", (usuario_id,))
                row = cur.fetchone()
                if row:
                    send_expo_push([row["expo_token"]], "Presença Confirmada ✓",
                                   f"Sua presença em {turma_nome} foi registrada às {hora}.")
        except Exception as e:
            logger.error("Erro ao enviar push: %s", e)

    if aluno_email:
        send_email_resend(aluno_email, aluno_nome, turma_nome, hora)


def _notificar_alunos_presentes(chamada_id: str, turma_nome: str) -> None:
    """Tarefa de background: ao fechar chamada, notifica via push + email todos os alunos presentes."""
    from notificacoes import send_expo_push, send_email_resend
    import datetime

    hora = datetime.datetime.now().strftime("%H:%M")

    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT u.usuario_id, u.nome, u.email
                FROM Presencas p
                JOIN Alunos a ON a.aluno_id = p.aluno_id
                JOIN Usuarios u ON u.usuario_id = a.usuario_id
                WHERE p.chamada_id = %s
            """, (chamada_id,))
            alunos = cur.fetchall()
    except Exception as e:
        logger.error("Erro ao buscar alunos presentes para notificação: %s", e)
        return

    for aluno in alunos:
        usuario_id = aluno["usuario_id"]
        nome = aluno["nome"]
        email = aluno["email"]

        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT expo_token FROM PushTokens WHERE usuario_id = %s", (usuario_id,))
                row = cur.fetchone()
                if row:
                    send_expo_push(
                        [row["expo_token"]],
                        "Presença Confirmada ✓",
                        f"Sua presença em {turma_nome} foi registrada às {hora}.",
                    )
        except Exception as e:
            logger.error("Erro ao enviar push para %s: %s", usuario_id, e)

        if email:
            send_email_resend(email, nome, turma_nome, hora)


@app.get("/aluno/dashboard/{usuario_id}")
def get_dashboard_aluno(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
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
        raise internal_error(e)


@app.get("/aluno/frequencias/{usuario_id}")
def get_frequencias_detalhadas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
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
        raise internal_error(e)


@app.get("/professor/dashboard/{usuario_id}")
def get_dashboard(usuario_id: str, current_user: dict = Depends(get_current_user)):
    require_self_or_admin(usuario_id, current_user)
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
        raise internal_error(e)


@app.get("/turmas/{usuario_id}")
def get_turmas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna as turmas de um professor com flag indicando se está no horário de aula."""
    require_self_or_admin(usuario_id, current_user)
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
        raise internal_error(e)

@app.get("/turmas/{turma_id}/alunos")
def get_alunos_turma(turma_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with get_db_cursor() as cur:
            # Autorização: Admin sempre; Professor precisa ser dono da turma;
            # Aluno precisa estar matriculado na turma.
            role = current_user.get("role")
            if role == "Professor":
                cur.execute(
                    """
                    SELECT 1 FROM Turmas t
                    JOIN Professores p ON t.professor_id = p.professor_id
                    WHERE t.turma_id = %s AND p.usuario_id = %s
                    """,
                    (turma_id, current_user.get("sub")),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Professor não é responsável por esta turma.")
            elif role == "Aluno":
                cur.execute(
                    """
                    SELECT 1 FROM Turma_Alunos ta
                    JOIN Alunos a ON ta.aluno_id = a.aluno_id
                    WHERE ta.turma_id = %s AND a.usuario_id = %s
                    """,
                    (turma_id, current_user.get("sub")),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Aluno não matriculado nesta turma.")
            elif role != "Admin":
                raise HTTPException(status_code=403, detail="Acesso negado.")

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
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@app.post("/alunos/cadastrar-face")
@limiter.limit("10/minute")
async def cadastrar_aluno_api(
    request: Request,
    user_id: Optional[str] = Form(None),
    nome: str = Form(..., min_length=3, max_length=100),
    email: EmailStr = Form(...),
    ra: str = Form(..., pattern=r"^[A-Za-z0-9]{4,20}$"),
    foto: UploadFile = File(...),
    consentimento_biometrico: bool = Form(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Recebe dados e foto do App, salva no S3, indexa no Rekognition e salva no Banco.
    """
    if not consentimento_biometrico:
        raise HTTPException(
            status_code=400,
            detail="É necessário consentimento explícito para processar dados biométricos (LGPD art. 11).",
        )

    # Valida tipo e tamanho da imagem primeiro
    image_bytes = await validate_image_upload(foto)

    import uuid as _uuid_fname
    ext = ".jpg" if foto.content_type in {"image/jpeg", "image/jpg"} else ".png"
    safe_basename = f"{_uuid_fname.uuid4().hex}{ext}"
    temp_file = f"temp_{safe_basename}"

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

        # Autorização: Aluno só pode cadastrar a própria face; Admin libera geral.
        if current_user.get("role") == "Aluno" and str(target_user_id) != current_user.get("sub"):
            raise HTTPException(status_code=403, detail="Aluno só pode cadastrar a própria face.")
        if current_user.get("role") not in {"Aluno", "Admin"}:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        # 2. Preparar ID único
        external_id = formatar_nome_para_external_id(nome)
        filename = f"alunos/{external_id}_{safe_basename}"

        # 3. Salvar arquivo temporariamente para envio
        with open(temp_file, "wb") as buffer:
            buffer.write(image_bytes)

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
                # Se existe, atualiza — renova consentimento e limpa revogação anterior
                cur.execute("""
                    UPDATE Colecao_Rostos
                    SET external_image_id = %s,
                        face_id_rekognition = %s,
                        s3_path_cadastro = %s,
                        consentimento_biometrico = TRUE,
                        consentimento_data = CURRENT_TIMESTAMP,
                        revogado_em = NULL
                    WHERE aluno_id = %s
                """, (external_id, face_id, filename, aluno_id))
            else:
                cur.execute("""
                    INSERT INTO Colecao_Rostos (
                        aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro,
                        consentimento_biometrico, consentimento_data
                    )
                    VALUES (%s, %s, %s, %s, TRUE, CURRENT_TIMESTAMP)
                """, (aluno_id, external_id, face_id, filename))

            os.remove(temp_file)
            return {"status": "sucesso", "face_id": face_id, "external_id": external_id}

    except HTTPException:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise internal_error(e, "cadastrar_aluno_api")

def _gerar_url_presigned(s3_key: str, expira_segundos: int = 300) -> Optional[str]:
    """Gera URL temporária para acessar objeto no S3 privado (padrão: 5 min)."""
    if not s3_key:
        return None
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expira_segundos,
        )
    except Exception as e:
        logger.error("Erro ao gerar URL presigned: %s", e)
        return None


@app.get("/aluno/biometria-foto/{usuario_id}")
def obter_foto_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna URL temporária (presigned) da foto cadastrada — só dono ou Admin."""
    require_self_or_admin(usuario_id, current_user)
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT cr.s3_path_cadastro
                FROM Colecao_Rostos cr
                JOIN Alunos a ON cr.aluno_id = a.aluno_id
                WHERE a.usuario_id = %s AND cr.revogado_em IS NULL
                """,
                (usuario_id,),
            )
            row = cur.fetchone()
            if not row or not row.get("s3_path_cadastro"):
                raise HTTPException(status_code=404, detail="Biometria não encontrada.")
            url = _gerar_url_presigned(row["s3_path_cadastro"])
            if not url:
                raise HTTPException(status_code=500, detail="Falha ao gerar URL temporária.")
            return {"url": url, "expira_em_segundos": 300}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "obter_foto_biometria")


# --- LGPD: REVOGAÇÃO DE BIOMETRIA ---

@app.delete("/aluno/biometria/{usuario_id}")
def revogar_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """
    Permite ao aluno (ou Admin) revogar o consentimento e apagar a biometria cadastrada.
    Remove a face no Rekognition, marca o registro como revogado e limpa o S3.
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id = %s", (usuario_id,))
            aluno = cur.fetchone()
            if not aluno:
                raise HTTPException(status_code=404, detail="Aluno não encontrado.")

            cur.execute(
                """
                SELECT face_id_rekognition, s3_path_cadastro
                FROM Colecao_Rostos
                WHERE aluno_id = %s AND revogado_em IS NULL
                """,
                (aluno["aluno_id"],),
            )
            rosto = cur.fetchone()
            if not rosto:
                raise HTTPException(status_code=404, detail="Nenhuma biometria ativa para este aluno.")

            try:
                deletar_rosto(rosto["face_id_rekognition"])
            except Exception as e:
                logger.warning("Falha ao deletar face no Rekognition: %s", e)

            try:
                if rosto.get("s3_path_cadastro"):
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=rosto["s3_path_cadastro"])
            except Exception as e:
                logger.warning("Falha ao deletar objeto no S3: %s", e)

            cur.execute(
                """
                UPDATE Colecao_Rostos
                SET revogado_em = CURRENT_TIMESTAMP,
                    consentimento_biometrico = FALSE,
                    face_id_rekognition = NULL,
                    s3_path_cadastro = NULL
                WHERE aluno_id = %s
                """,
                (aluno["aluno_id"],),
            )

        audit_logger.info("Biometria revogada usuario=%s por=%s", usuario_id, current_user.get("sub"))
        return {"mensagem": "Biometria revogada e removida com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "revogar_biometria")


# --- ENDPOINTS DE CHAMADAS ---

@app.post("/chamadas/abrir")
def abrir_chamada(dados: ChamadaAbrir, current_user: dict = Depends(require_role("Professor"))):
    import datetime

    usuario_id = current_user.get("sub")
    professor_id = obter_professor_id(usuario_id)

    if not professor_id:
        raise HTTPException(status_code=404, detail="Professor não encontrado no banco.")

    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: raise Exception("Erro ao conectar no banco")

            # 1. Professor precisa ser dono da turma
            cur.execute(
                "SELECT 1 FROM Turmas WHERE turma_id = %s AND professor_id = %s",
                (dados.turma_id, professor_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="Você não é o professor responsável por esta turma.")

            # 2. Precisa existir um horário de aula ativo AGORA para essa turma
            agora = datetime.datetime.now()
            cur.execute(
                """
                SELECT 1 FROM horarios_aulas
                WHERE turma_id = %s
                  AND dia_semana = %s
                  AND horario_inicio <= %s
                  AND horario_fim   >= %s
                """,
                (dados.turma_id, agora.weekday(), agora.time(), agora.time()),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=403,
                    detail="Fora do horário de aula. A chamada só pode ser aberta durante o período letivo desta turma.",
                )

            # 3. Fecha qualquer chamada aberta desta turma
            cur.execute("""
                UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME
                WHERE turma_id=%s AND status='Aberta'
            """, (dados.turma_id,))

            # 4. Abre nova chamada
            cur.execute("""
                INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta')
                RETURNING chamada_id
            """, (dados.turma_id, professor_id))

            nova_chamada = cur.fetchone()
            audit_logger.info("Chamada aberta turma=%s professor=%s", dados.turma_id, professor_id)

            # Iniciar reconhecimento facial automaticamente (Headless)
            global processo_camera
            if processo_camera is None or processo_camera.poll() is not None:
                script_path = os.path.join(os.path.dirname(__file__), "reconhecimento_tempo_real.py")
                processo_camera = subprocess.Popen([sys.executable, script_path])
                print(f"Processo de reconhecimento iniciado (PID: {processo_camera.pid})")

            return {"mensagem": "Chamada aberta com sucesso!", "chamada_id": nova_chamada['chamada_id']}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "abrir_chamada")


@app.post("/chamadas/fechar/{turma_id}")
def fechar_chamada(turma_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Professor"))):
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: raise Exception("Erro ao conectar no banco")

            # Busca chamada aberta e nome da turma antes de fechar
            cur.execute("""
                SELECT c.chamada_id, t.nome_disciplina
                FROM Chamadas c
                JOIN Turmas t ON t.turma_id = c.turma_id
                WHERE c.turma_id = %s AND c.status = 'Aberta'
                LIMIT 1
            """, (turma_id,))
            chamada = cur.fetchone()

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

        if chamada:
            background_tasks.add_task(
                _notificar_alunos_presentes,
                chamada["chamada_id"],
                chamada["nome_disciplina"],
            )

        return {"mensagem": "Chamada encerrada com sucesso!"}
    except Exception as e:
        raise internal_error(e, "fechar_chamada")


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
        raise internal_error(e, "status_chamada")


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
        raise internal_error(e, "listar_alunos_chamada")



@app.post("/chamadas/registrar_rosto")
@limiter.limit("10/minute")
async def registrar_rosto_aluno(
    request: Request,
    background_tasks: BackgroundTasks,
    foto: UploadFile = File(...),
    current_user: dict = Depends(require_role("Aluno")),
):
    """
    Recebe foto tirada pelo Aluno, envia pra AWS e se der match, registra presença
    e dispara notificações (push + email) em background.
    """
    image_bytes = await validate_image_upload(foto)

    try:
        from config import COLLECTION_ID
        from aws_clientes import rekognition_client

        response = rekognition_client.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            MaxFaces=1,
            FaceMatchThreshold=90,
        )

        if not response.get('FaceMatches'):
            raise HTTPException(status_code=404, detail="Rosto não reconhecido no sistema.")

        match = response['FaceMatches'][0]
        external_image_id = match['Face']['ExternalImageId']

        result = registrar_presenca_por_face(external_image_id)
        if not result:
            raise HTTPException(status_code=400, detail="Não foi possível registrar a presença. Verifique se há uma chamada aberta para sua turma.")

        audit_logger.info("Presença registrada aluno=%s ip=%s", external_image_id, request.client.host)

        background_tasks.add_task(
            _enviar_notificacoes_presenca,
            result.get("usuario_id"),
            result.get("aluno_nome", external_image_id),
            result.get("aluno_email"),
            result.get("turma_nome", "sua turma"),
        )

        return {"mensagem": "Presença confirmada com sucesso!", "aluno": external_image_id}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "registrar_rosto_aluno")
