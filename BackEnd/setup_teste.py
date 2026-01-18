from database import get_db_connection
import uuid

def criar_dados_teste():
    conn = get_db_connection()
    if not conn: 
        print("❌ Falha ao conectar no banco.")
        return

    # --- CONFIGURACAO OBRIGATORIA ---
    # Coloque aqui EXATAMENTE o ID que o Rekognition retorna quando ve seu rosto
    EXTERNAL_IMAGE_ID_TESTE = "Gustavo_Falci"  
    # --------------------------------

    try:
        cur = conn.cursor()
        print("🚀 Iniciando criacao de dados de teste (Schema Validado)...")

        # 1. Criar Usuario ALUNO
        # Campo corrigido: 'senha' (antes era senha_hash)
        aluno_user_uuid = str(uuid.uuid4())
        print("1. Criando Usuario Aluno...")
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, data_cadastro) 
            VALUES (%s, 'Aluno Teste', 'aluno@teste.com', '123', 'Aluno', CURRENT_TIMESTAMP) 
            ON CONFLICT (email) DO UPDATE SET email=EXCLUDED.email 
            RETURNING usuario_id
        """, (aluno_user_uuid,))
        
        res = cur.fetchone()
        if res: 
            aluno_user_uuid = res[0]
        else:
            cur.execute("SELECT usuario_id FROM Usuarios WHERE email='aluno@teste.com'")
            aluno_user_uuid = cur.fetchone()[0]

        # 2. Criar Perfil ALUNO
        # Colunas validadas: aluno_id, usuario_id, ra (sem data_nascimento)
        aluno_uuid = str(uuid.uuid4())
        print("2. Criando Perfil Aluno...")
        cur.execute("""
            INSERT INTO Alunos (aluno_id, usuario_id, ra) 
            VALUES (%s, %s, 'RA12345') 
            ON CONFLICT (ra) DO UPDATE SET ra=EXCLUDED.ra
            RETURNING aluno_id
        """, (aluno_uuid, aluno_user_uuid))
        
        res = cur.fetchone()
        if res: 
            aluno_uuid = res[0]
        else:
            cur.execute("SELECT aluno_id FROM Alunos WHERE usuario_id=%s", (aluno_user_uuid,))
            aluno_uuid = cur.fetchone()[0]

        # 3. VINCULAR AWS REKOGNITION (Tabela colecao_rostos)
        # Colunas: colecao_rosto_id (auto), aluno_id, external_image_id, face_id_rekognition, s3_path_cadastro, data_indexacao
        print(f"3. Vinculando ID AWS '{EXTERNAL_IMAGE_ID_TESTE}' ao aluno...")
        cur.execute("""
            INSERT INTO Colecao_Rostos (aluno_id, external_image_id, s3_path_cadastro, data_indexacao) 
            VALUES (%s, %s, 'teste/caminho.jpg', CURRENT_TIMESTAMP)
            ON CONFLICT (external_image_id) DO UPDATE SET aluno_id = EXCLUDED.aluno_id
        """, (aluno_uuid, EXTERNAL_IMAGE_ID_TESTE))

        # 4. Criar Usuario PROFESSOR
        # Campo corrigido: 'senha'
        prof_user_uuid = str(uuid.uuid4())
        print("4. Criando Usuario Professor...")
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, data_cadastro) 
            VALUES (%s, 'Prof Teste', 'prof@teste.com', '123', 'Professor', CURRENT_TIMESTAMP) 
            ON CONFLICT (email) DO UPDATE SET email=EXCLUDED.email
            RETURNING usuario_id
        """, (prof_user_uuid,))
        
        res = cur.fetchone()
        if res:
            prof_user_uuid = res[0]
        else:
            cur.execute("SELECT usuario_id FROM Usuarios WHERE email='prof@teste.com'")
            prof_user_uuid = cur.fetchone()[0]
        
        # 5. Criar Perfil PROFESSOR
        # Colunas: professor_id, usuario_id, departamento, data_admissao
        prof_uuid = str(uuid.uuid4())
        print("5. Criando Perfil Professor...")
        cur.execute("""
            INSERT INTO Professores (professor_id, usuario_id, departamento, data_admissao) 
            VALUES (%s, %s, 'Computacao', CURRENT_DATE) 
            ON CONFLICT (usuario_id) DO UPDATE SET departamento=EXCLUDED.departamento
            RETURNING professor_id
        """, (prof_uuid, prof_user_uuid))
        
        res = cur.fetchone()
        if res:
            prof_uuid = res[0]
        else:
            cur.execute("SELECT professor_id FROM Professores WHERE usuario_id=%s", (prof_user_uuid,))
            prof_uuid = cur.fetchone()[0]

        # 6. Criar TURMA
        # Colunas: turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao
        turma_uuid = str(uuid.uuid4())
        print("6. Criando Turma de Teste...")
        cur.execute("""
            INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao) 
            VALUES (%s, %s, 'TURMA-TESTE', 'Engenharia Sw', '2025-1', 'B202') 
            ON CONFLICT (codigo_turma) DO UPDATE SET nome_disciplina=EXCLUDED.nome_disciplina
            RETURNING turma_id
        """, (turma_uuid, prof_uuid))
        
        res = cur.fetchone()
        if res:
            turma_uuid = res[0]
        else:
            cur.execute("SELECT turma_id FROM Turmas WHERE codigo_turma='TURMA-TESTE'")
            turma_uuid = cur.fetchone()[0]

        # 7. MATRICULAR ALUNO NA TURMA (Tabela turma_alunos)
        # Colunas: turma_aluno_id (auto), turma_id, aluno_id, data_associacao
        print("7. Matriculando aluno na turma...")
        cur.execute("""
            INSERT INTO Turma_Alunos (turma_id, aluno_id, data_associacao)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (turma_id, aluno_id) DO NOTHING
        """, (turma_uuid, aluno_uuid))

        # 8. Criar Chamada ABERTA (Tabela chamadas)
        # Colunas: chamada_id (auto), turma_id, professor_id, data_chamada, horario_inicio, horario_fim, status, data_criacao
        cur.execute("UPDATE Chamadas SET status='Fechada' WHERE status='Aberta'")
        
        print("8. Abrindo uma chamada para teste imediato...")
        cur.execute("""
            INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status, data_criacao)
            VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta', CURRENT_TIMESTAMP)
        """, (turma_uuid, prof_uuid))

        conn.commit()
        print("\n✅ SUCESSO! Banco populado com o schema CORRETO.")
        print(f"👉 Aluno vinculado: {EXTERNAL_IMAGE_ID_TESTE} (RA: RA12345)")
        print("👉 Turma criada: Engenharia Sw (Cod: TURMA-TESTE)")
        print("👉 Chamada: Aberta. Pode rodar o reconhecimento!")

    except Exception as e:
        conn.rollback()
        # repr(e) ajuda a ver erros com acentuação se o terminal Windows reclamar
        print(f"❌ Erro ao criar dados: {repr(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    criar_dados_teste()