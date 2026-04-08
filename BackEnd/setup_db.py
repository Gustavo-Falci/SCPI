"""
Script para criar o schema do banco de dados do Sistema de Ponto Facial Empresarial (SaaS).
Uso: python setup_db.py
"""
from db_conexao import get_db_cursor, logger

def drop_old_tables():
    """Remove tabelas antigas do schema academico."""
    tables_to_drop = [
        "Turma_Alunos",
        "Chamadas",
        "Presencas",
        "Turmas",
        "Alunos",
        "Professores",
    ]
    with get_db_cursor(commit=True) as cur:
        if not cur:
            logger.error("Falha ao conectar ao banco para drop de tabelas.")
            return False
        for table in tables_to_drop:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"Tabela antiga removida: {table}")
            except Exception as e:
                logger.warning(f"Nao foi possivel dropar {table}: {e}")
        return True

def create_tables():
    """Cria todas as tabelas do novo schema empresarial."""
    with get_db_cursor(commit=True) as cur:
        if not cur:
            logger.error("Falha ao conectar ao banco para criacao de tabelas.")
            return False

        # --- TABELA: Empresas ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Empresas (
                empresa_id UUID PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                cnpj VARCHAR(18) UNIQUE NOT NULL,
                plano VARCHAR(50) DEFAULT 'Basico',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabela Empresas criada.")

        # --- TABELA: Usuarios (adaptada) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Usuarios (
                usuario_id UUID PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha VARCHAR(512) NOT NULL,
                tipo_usuario VARCHAR(50) NOT NULL CHECK (tipo_usuario IN ('Funcionario', 'RH', 'Admin')),
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabela Usuarios criada/atualizada.")

        # --- TABELA: Setores ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Setores (
                setor_id UUID PRIMARY KEY,
                empresa_id UUID NOT NULL REFERENCES Empresas(empresa_id) ON DELETE CASCADE,
                nome VARCHAR(150) NOT NULL
            )
        """)
        logger.info("Tabela Setores criada.")

        # --- TABELA: Funcionarios ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Funcionarios (
                funcionario_id UUID PRIMARY KEY,
                usuario_id UUID NOT NULL REFERENCES Usuarios(usuario_id) ON DELETE CASCADE,
                empresa_id UUID NOT NULL REFERENCES Empresas(empresa_id) ON DELETE CASCADE,
                setor_id UUID REFERENCES Setores(setor_id) ON DELETE SET NULL,
                matricula VARCHAR(50) UNIQUE,
                cargo VARCHAR(150),
                data_admissao DATE DEFAULT CURRENT_DATE
            )
        """)
        logger.info("Tabela Funcionarios criada.")

        # --- TABELA: Colecao_Rostos (adaptada) ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Colecao_Rostos (
                rosto_id UUID PRIMARY KEY,
                funcionario_id UUID NOT NULL REFERENCES Funcionarios(funcionario_id) ON DELETE CASCADE,
                external_image_id VARCHAR(255) NOT NULL,
                face_id_rekognition VARCHAR(255) NOT NULL,
                s3_path_cadastro TEXT NOT NULL
            )
        """)
        logger.info("Tabela Colecao_Rostos criada.")

        # --- TABELA: Registros_Ponto ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Registros_Ponto (
                registro_id UUID PRIMARY KEY,
                funcionario_id UUID NOT NULL REFERENCES Funcionarios(funcionario_id) ON DELETE CASCADE,
                tipo VARCHAR(30) NOT NULL CHECK (tipo IN (
                    'entrada', 'intervalo_inicio', 'intervalo_fim', 'saida'
                )),
                data DATE NOT NULL DEFAULT CURRENT_DATE,
                hora TIME NOT NULL DEFAULT CURRENT_TIME,
                origem VARCHAR(30) NOT NULL CHECK (origem IN ('app', 'dispositivo')),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("Tabela Registros_Ponto criada.")

        # --- TABELA: Horarios_Expediente ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Horarios_Expediente (
                horario_id UUID PRIMARY KEY,
                empresa_id UUID NOT NULL REFERENCES Empresas(empresa_id) ON DELETE CASCADE,
                dia_semana INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6) CHECK (dia_semana >= 0 AND dia_semana <= 6),
                horario_inicio TIME NOT NULL,
                horario_fim TIME NOT NULL,
                tolerancia_minutos INTEGER DEFAULT 10,
                UNIQUE (empresa_id, dia_semana)
            )
        """)
        logger.info("Tabela Horarios_Expediente criada.")

        # --- TABELA: Admin_Empresas ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Admin_Empresas (
                admin_empresa_id UUID PRIMARY KEY,
                empresa_id UUID NOT NULL REFERENCES Empresas(empresa_id) ON DELETE CASCADE,
                usuario_id UUID NOT NULL REFERENCES Usuarios(usuario_id) ON DELETE CASCADE,
                nivel_admin VARCHAR(50) DEFAULT 'super_admin',
                UNIQUE (empresa_id, usuario_id)
            )
        """)
        logger.info("Tabela Admin_Empresas criada.")

        return True

def criar_empresa_teste():
    """Cria uma empresa de teste com usuario Admin/RH e 2 funcionarios de exemplo."""
    import uuid
    from auth import get_password_hash

    empresa_uuid = str(uuid.uuid4())
    default_password = get_password_hash("123")

    with get_db_cursor(commit=True) as cur:
        if not cur:
            logger.error("Falha ao conectar ao banco para dados de teste.")
            return False

        # 1. Empresa
        cur.execute("""
            INSERT INTO Empresas (empresa_id, nome, cnpj, plano)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (cnpj) DO NOTHING
        """, (empresa_uuid, "Empresa Teste LTDA", "12.345.678/0001-90", "Basico"))

        # 2. Usuario Admin + vinculo
        admin_user_uuid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (admin_user_uuid, "Carlos Administrador", "admin@teste.com", default_password, "Admin"))

        cur.execute("""
            INSERT INTO Admin_Empresas (admin_empresa_id, empresa_id, usuario_id, nivel_admin)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usuario_id, empresa_id) DO NOTHING
        """, (str(uuid.uuid4()), empresa_uuid, admin_user_uuid, "super_admin"))

        # 3. Usuario RH + vinculo
        rh_user_uuid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (rh_user_uuid, "Maria RH", "rh@teste.com", default_password, "RH"))

        cur.execute("""
            INSERT INTO Admin_Empresas (admin_empresa_id, empresa_id, usuario_id, nivel_admin)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usuario_id, empresa_id) DO NOTHING
        """, (str(uuid.uuid4()), empresa_uuid, rh_user_uuid, "rh"))

        # 4. Setores
        setor_ti = str(uuid.uuid4())
        setor_rh_setor = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Setores (setor_id, empresa_id, nome)
            VALUES (%s, %s, %s), (%s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (setor_ti, empresa_uuid, "TI", setor_rh_setor, empresa_uuid, "Recursos Humanos"))

        # 5. Funcionario teste 1
        func_user_uuid1 = str(uuid.uuid4())
        funcionario_id1 = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (func_user_uuid1, "Joao da Silva", "joao@teste.com", default_password, "Funcionario"))

        cur.execute("""
            INSERT INTO Funcionarios (funcionario_id, usuario_id, empresa_id, setor_id, matricula, cargo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (funcionario_id1, func_user_uuid1, empresa_uuid, setor_ti, "MAT-001", "Desenvolvedor"))

        # 6. Funcionario teste 2
        func_user_uuid2 = str(uuid.uuid4())
        funcionario_id2 = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (func_user_uuid2, "Ana Souza", "ana@teste.com", default_password, "Funcionario"))

        cur.execute("""
            INSERT INTO Funcionarios (funcionario_id, usuario_id, empresa_id, setor_id, matricula, cargo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (funcionario_id2, func_user_uuid2, empresa_uuid, setor_rh_setor, "MAT-002", "Analista de RH"))

        # 6. Horarios de expediente padrao (seg a sex, 08:00-17:00)
        for dia in [1, 2, 3, 4, 5]:  # segunda a sexta
            horario_uuid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Horarios_Expediente (horario_id, empresa_id, dia_semana, horario_inicio, horario_fim, tolerancia_minutos)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (empresa_id, dia_semana) DO NOTHING
            """, (horario_uuid, empresa_uuid, dia, "08:00", "17:00", 10))

        logger.info("Dados de teste criados com sucesso!")
        logger.info(f"Empresa: Empresa Teste LTDA")
        logger.info(f"Admin: admin@teste.com / 123")
        logger.info(f"RH: rh@teste.com / 123")
        logger.info(f"Funcionario 1: joao@teste.com / 123")
        logger.info(f"Funcionario 2: ana@teste.com / 123")
        return True

def main():
    logger.info("=== Setup do Banco de Dados - Ponto Facial Empresarial ===")
    logger.info("Removendo tabelas antigas...")
    drop_old_tables()

    logger.info("Criando novas tabelas...")
    create_tables()

    logger.info("Inserindo dados de teste...")
    criar_empresa_teste()

    logger.info("=== Setup concluido! ===")

if __name__ == "__main__":
    main()
