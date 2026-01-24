# db_operacoes.py
from database import get_db_cursor, logger
import uuid


# --- OPERAÇÕES DE AUTENTICAÇÃO ---

def buscar_usuario_por_email(email):
    """Busca usuário pelo email para login."""
    with get_db_cursor() as cur:
        if not cur: return None
        # Seleciona senha também para verificação
        cur.execute("SELECT usuario_id, nome, email, senha, tipo_usuario FROM Usuarios WHERE email = %s", (email,))
        return cur.fetchone()

def criar_usuario_completo(dados_usuario, dados_perfil):
    """
    Cria usuário + perfil (Professor ou Aluno) em uma transação.
    dados_usuario: dict(nome, email, senha_hash, tipo_usuario)
    dados_perfil: dict(ra, departamento, etc dependendo do tipo)
    """
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: return False

            # 1. Cria Usuário
            usuario_uuid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, %s, %s) 
                RETURNING usuario_id
            """, (usuario_uuid, dados_usuario['nome'], dados_usuario['email'], dados_usuario['senha_hash'], dados_usuario['tipo_usuario']))
            
            usuario_id = cur.fetchone()['usuario_id']

            # 2. Cria Perfil Específico
            if dados_usuario['tipo_usuario'] == 'Aluno':
                aluno_uuid = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO Alunos (aluno_id, usuario_id, ra)
                    VALUES (%s, %s, %s)
                """, (aluno_uuid, usuario_id, dados_perfil.get('ra')))
                
            elif dados_usuario['tipo_usuario'] == 'Professor':
                prof_uuid = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO Professores (professor_id, usuario_id, departamento, data_admissao)
                    VALUES (%s, %s, %s, CURRENT_DATE)
                """, (prof_uuid, usuario_id, dados_perfil.get('departamento', 'Geral')))
            
            return True
    except Exception as e:
        logger.error(f"Erro ao criar usuário completo: {e}")
        return False

# --- OPERAÇÕES DE RECONHECIMENTO ---

def registrar_presenca_por_face(external_image_id):
    """Registra presença se houver chamada aberta."""
    # commit=True pois vamos fazer INSERT
    with get_db_cursor(commit=True) as cur:
        if not cur: return False


        # 1. Busca Aluno
        cur.execute("SELECT aluno_id FROM Colecao_Rostos WHERE external_image_id = %s", (external_image_id,))
        aluno = cur.fetchone()
        
        if not aluno:
            logger.warning(f"Aluno não encontrado para ID: {external_image_id}")
            return False
        
        aluno_uuid = aluno['aluno_id']

        # 2. Busca Chamada Aberta
        cur.execute("""
            SELECT chamada_id, turma_id FROM Chamadas 
            WHERE status = 'Aberta' ORDER BY data_criacao DESC LIMIT 1
        """)
        chamada = cur.fetchone()

        if not chamada:
            logger.warning("Nenhuma chamada aberta no momento.")
            return False

        # 3. Verifica Matrícula
        cur.execute("""
            SELECT 1 FROM Turma_Alunos WHERE turma_id = %s AND aluno_id = %s
        """, (chamada['turma_id'], aluno_uuid))
        
        if not cur.fetchone():
            logger.warning(f"Aluno {external_image_id} não pertence a esta turma.")
            return False

        # 4. Registra Presença
        cur.execute("""
            INSERT INTO Presencas (chamada_id, aluno_id, tipo_registro)
            VALUES (%s, %s, 'Reconhecimento')
            ON CONFLICT (chamada_id, aluno_id) DO NOTHING
        """, (chamada['chamada_id'], aluno_uuid))
        
        if cur.rowcount > 0:
            logger.info(f"✅ Presença confirmada: {external_image_id}")
            return True
        return False

# --- OPERAÇÕES ADMINISTRATIVAS ---

def listar_turmas_professor(usuario_id_professor):
    # commit=False (padrão) pois é apenas LEITURA
    with get_db_cursor() as cur:
        if not cur: return []
        cur.execute("""
            SELECT t.turma_id, t.nome_disciplina, t.codigo_turma 
            FROM Turmas t
            JOIN Professores p ON t.professor_id = p.professor_id
            WHERE p.usuario_id = %s
        """, (usuario_id_professor,))
        return cur.fetchall()

def cadastrar_novo_aluno(nome, email, ra, turma_id, external_id, face_id_aws, s3_path):
    """Cadastra toda a cadeia de dados do aluno."""
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur: return False
            
            # 1. Usuário
            usuario_uuid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, '123', 'Aluno') RETURNING usuario_id
            """, (usuario_uuid, nome, email))
            usuario_id = cur.fetchone()['usuario_id']

            # 2. Aluno
            aluno_uuid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Alunos (aluno_id, usuario_id, ra)
                VALUES (%s, %s, %s) RETURNING aluno_id
            """, (aluno_uuid, usuario_id, ra))
            aluno_id = cur.fetchone()['aluno_id']

            # 3. Matrícula
            cur.execute("INSERT INTO Turma_Alunos (turma_id, aluno_id) VALUES (%s, %s)", (turma_id, aluno_id))

            # 4. AWS Link
            cur.execute("""
                INSERT INTO Colecao_Rostos (aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro)
                VALUES (%s, %s, %s, %s)
            """, (aluno_id, external_id, face_id_aws, s3_path))
            
            return True
    except Exception as e:
        logger.error(f"Erro no cadastro completo: {e}")
        return False