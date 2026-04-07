from db_conexao import get_db_cursor, logger
import uuid

# --- BUSCA ---

def buscar_usuario_por_email(email):
    """Busca usuário pelo email para login."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("""
            SELECT u.usuario_id, u.nome, u.email, u.senha, u.tipo_usuario, u.ativo,
                   ae.empresa_id
            FROM Usuarios u
            LEFT JOIN Admin_Empresas ae ON u.usuario_id = ae.usuario_id
            WHERE u.email = %s
        """, (email,))
        return cur.fetchone()


def buscar_empresa_por_cnpj(cnpj):
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT empresa_id, nome, cnpj, plano FROM Empresas WHERE cnpj = %s",
            (cnpj,),
        )
        return cur.fetchone()


# --- CRIAÇÃO ---

def criar_empresa_db(empresa_id, nome, cnpj, plano):
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return False
            cur.execute(
                "INSERT INTO Empresas (empresa_id, nome, cnpj, plano) VALUES (%s, %s, %s, %s)",
                (empresa_id, nome, cnpj, plano),
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao criar empresa: {e}")
        return False


def criar_usuario_rh(dados):
    """Cria usuário RH/Admin e vincula a uma empresa."""
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return False

            usuario_uuid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING usuario_id
            """,
                (
                    usuario_uuid,
                    dados["nome"],
                    dados["email"],
                    dados["senha_hash"],
                    dados["tipo_usuario"],
                ),
            )
            uid = cur.fetchone()["usuario_id"]

            cur.execute(
                """
                INSERT INTO Admin_Empresas (admin_empresa_id, empresa_id, usuario_id, nivel_admin)
                VALUES (%s, %s, %s, %s)
            """,
                (str(uuid.uuid4()), dados["empresa_id"], uid, dados.get("nivel_admin", "rh")),
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao criar usuário RH/Admin: {e}")
        return False


def cadastrar_funcionario_com_foto(nome, email, matricula, empresa_id, setor_id, cargo, external_id, face_id_aws, s3_path):
    """Cria funcionário completo com vínculo AWS Rekognition."""
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return False

            from auth import get_password_hash

            senha_hash = get_password_hash("123")

            # 1. Usuário
            usuario_uuid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, %s, 'Funcionario')
                RETURNING usuario_id
            """,
                (usuario_uuid, nome, email, senha_hash),
            )
            uid = cur.fetchone()["usuario_id"]

            # 2. Funcionário
            funcionario_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO Funcionarios (funcionario_id, usuario_id, empresa_id, setor_id, matricula, cargo)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING funcionario_id
            """,
                (funcionario_id, uid, empresa_id, setor_id, matricula, cargo),
            )
            fid = cur.fetchone()["funcionario_id"]

            # 3. Rosto
            cur.execute(
                """
                INSERT INTO Colecao_Rostos (rosto_id, funcionario_id, external_image_id, face_id_rekognition, s3_path_cadastro)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (str(uuid.uuid4()), fid, external_id, face_id_aws, s3_path),
            )

            return True
    except Exception as e:
        logger.error(f"Erro no cadastro do funcionário: {e}")
        return False


# --- PONTO ---

def registrar_ponto_facial(external_image_id):
    """Registra ponto automaticamente via reconhecimento facial."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return None

        # 1. Busca funcionário pelo rosto
        cur.execute(
            """
            SELECT cr.funcionario_id, f.empresa_id
            FROM Colecao_Rostos cr
            JOIN Funcionarios f ON cr.funcionario_id = f.funcionario_id
            WHERE cr.external_image_id = %s
        """,
            (external_image_id,),
        )
        func = cur.fetchone()

        if not func:
            logger.warning(f"Funcionário não encontrado: {external_image_id}")
            return None

        fid = func["funcionario_id"]

        # 2. Determina tipo do ponto
        cur.execute(
            """
            SELECT tipo FROM Registros_Ponto
            WHERE funcionario_id = %s AND data = CURRENT_DATE
            ORDER BY hora DESC LIMIT 1
        """,
            (fid,),
        )
        ultimo = cur.fetchone()

        if not ultimo:
            tipo = "entrada"
        elif ultimo["tipo"] == "entrada":
            tipo = "intervalo_inicio"
        elif ultimo["tipo"] == "intervalo_inicio":
            tipo = "intervalo_fim"
        elif ultimo["tipo"] == "intervalo_fim":
            tipo = "saida"
        else:
            logger.warning(f"Ponto já finalizado para {external_image_id}")
            return {"mensagem": "Ponto já finalizado (entrada + saída registrada).", "tipo": None}

        # 3. Registra
        cur.execute(
            """
            INSERT INTO Registros_Ponto (registro_id, funcionario_id, tipo, data, hora, origem)
            VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_TIME, 'app')
            RETURNING registro_id, tipo, data, hora
        """,
            (str(uuid.uuid4()), fid, tipo),
        )
        return cur.fetchone()


def registrar_ponto_manual(funcionario_id, tipo, empresa_id=None):
    """Registra ponto manual com tipo explícito."""
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return None
            cur.execute(
                """
                INSERT INTO Registros_Ponto (registro_id, funcionario_id, tipo, data, hora, origem)
                VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_TIME, 'app')
                RETURNING registro_id, tipo, data, hora
            """,
                (str(uuid.uuid4()), funcionario_id, tipo),
            )
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Erro ao registrar ponto manual: {e}")
        return None


# --- LISTAGENS ---

def listar_funcionarios_empresa(empresa_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT f.funcionario_id, u.nome, u.email, f.matricula, f.cargo,
                   s.nome as setor
            FROM Funcionarios f
            JOIN Usuarios u ON f.usuario_id = u.usuario_id
            LEFT JOIN Setores s ON f.setor_id = s.setor_id
            WHERE f.empresa_id = %s AND u.ativo = TRUE
        """,
            (empresa_id,),
        )
        return cur.fetchall()


def listar_registros_funcionario(funcionario_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT rp.registro_id, rp.tipo, rp.data, rp.hora, rp.origem,
                   u.nome as funcionario
            FROM Registros_Ponto rp
            JOIN Funcionarios f ON rp.funcionario_id = f.funcionario_id
            JOIN Usuarios u ON f.usuario_id = u.usuario_id
            WHERE rp.funcionario_id = %s
            ORDER BY rp.data DESC, rp.hora DESC
            LIMIT 100
        """,
            (funcionario_id,),
        )
        return cur.fetchall()


def listar_registros_empresa_dia(empresa_id):
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            """
            SELECT rp.registro_id, u.nome as funcionario, rp.tipo,
                   rp.data, rp.hora, rp.origem, s.nome as setor
            FROM Registros_Ponto rp
            JOIN Funcionarios f ON rp.funcionario_id = f.funcionario_id
            JOIN Usuarios u ON f.usuario_id = u.usuario_id
            LEFT JOIN Setores s ON f.setor_id = s.setor_id
            WHERE f.empresa_id = %s AND rp.data = CURRENT_DATE
            ORDER BY rp.hora DESC
        """,
            (empresa_id,),
        )
        return cur.fetchall()


def criar_setor_db(setor_id, empresa_id, nome):
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return False
            cur.execute(
                "INSERT INTO Setores (setor_id, empresa_id, nome) VALUES (%s, %s, %s)",
                (setor_id, empresa_id, nome),
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao criar setor: {e}")
        return False


# --- NOVAS CONSULTAS ---

def criar_usuario_funcionario(dados):
    """Cria usuário do tipo Funcionario (sem foto/rekognition)."""
    try:
        with get_db_cursor(commit=True) as cur:
            if not cur:
                return False
            from auth import get_password_hash
            senha_hash = get_password_hash(dados.get("senha", "123"))
            usuario_uuid = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, %s, 'Funcionario')
                RETURNING usuario_id
                """,
                (usuario_uuid, dados["nome"], dados["email"], senha_hash),
            )
            return True
    except Exception as e:
        logger.error(f"Erro ao criar usuário funcionário: {e}")
        return False


def listar_setores_empresa(empresa_id):
    """Lista todos os setores de uma empresa."""
    with get_db_cursor() as cur:
        if not cur:
            return []
        cur.execute(
            "SELECT setor_id, empresa_id, nome FROM Setores WHERE empresa_id = %s ORDER BY nome",
            (empresa_id,),
        )
        return cur.fetchall()


def buscar_perfil_usuario(usuario_id):
    """Busca o perfil completo de um usuário com dados de funcionário (se houver)."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("""
            SELECT u.usuario_id, u.nome, u.email, u.tipo_usuario, u.ativo,
                   f.funcionario_id, f.matricula, f.cargo, f.empresa_id as func_empresa_id,
                   s.nome as setor,
                   ae.empresa_id as admin_empresa_id
            FROM Usuarios u
            LEFT JOIN Funcionarios f ON u.usuario_id = f.usuario_id
            LEFT JOIN Setores s ON f.setor_id = s.setor_id
            LEFT JOIN Admin_Empresas ae ON u.usuario_id = ae.usuario_id
            WHERE u.usuario_id = %s
        """, (usuario_id,))
        row = cur.fetchone()
        if not row:
            return None
        empresa_id = row.get("func_empresa_id") or row.get("admin_empresa_id") or ""
        return {
            "usuario_id": row["usuario_id"],
            "nome": row["nome"],
            "email": row["email"],
            "tipo_usuario": row["tipo_usuario"],
            "ativo": row["ativo"],
            "funcionario_id": row.get("funcionario_id"),
            "matricula": row.get("matricula"),
            "cargo": row.get("cargo"),
            "setor": row.get("setor"),
            "empresa_id": empresa_id,
        }


def buscar_empresa_por_id(empresa_id):
    """Busca empresa pelo ID."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute(
            "SELECT empresa_id, nome, cnpj, plano, data_criacao FROM Empresas WHERE empresa_id = %s",
            (empresa_id,),
        )
        return cur.fetchone()


def buscar_funcionario_por_usuario(usuario_id):
    """Busca dados do funcionário pelo usuario_id."""
    with get_db_cursor() as cur:
        if not cur:
            return None
        cur.execute("""
            SELECT f.funcionario_id, f.empresa_id, f.matricula, f.cargo,
                   s.nome as setor
            FROM Funcionarios f
            LEFT JOIN Setores s ON f.setor_id = s.setor_id
            WHERE f.usuario_id = %s
        """, (usuario_id,))
        return cur.fetchone()

