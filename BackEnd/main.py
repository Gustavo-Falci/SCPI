# main.py
import uuid
from database import get_db_cursor
from db_operacoes import listar_turmas_professor, cadastrar_novo_aluno
from config import BUCKET_NAME, COLLECTION_ID
from aws_clientes import s3_client, rekognition_client
from capture_camera import capture_frame_as_jpeg_bytes
from utils import formatar_nome_para_external_id

# --- FUNÇÕES DE CONTROLE DE CHAMADA ---

def gerenciar_chamada(opcao, usuario_id_prof):
    with get_db_cursor(commit=True) as cur:
        if not cur: return

        if opcao == "abrir":
            turmas = listar_turmas_professor(usuario_id_prof)
            if not turmas:
                print("❌ Você não tem turmas.")
                return
            
            print("\nSelecione a turma para iniciar a chamada:")
            for i, t in enumerate(turmas):
                print(f"{i+1}. {t['nome_disciplina']}")
            
            try:
                escolha = int(input("Opção: ")) - 1
                turma_id = turmas[escolha]['turma_id']
                prof_id = obter_professor_id(usuario_id_prof)
                
                # Fecha anteriores
                cur.execute("UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME WHERE status='Aberta'")
                # Abre nova
                cur.execute("""
                    INSERT INTO Chamadas (turma_id, professor_id, data_chamada, horario_inicio, status)
                    VALUES (%s, %s, CURRENT_DATE, CURRENT_TIME, 'Aberta')
                """, (turma_id, prof_id))
                print("✅ Chamada ABERTA com sucesso!")
            except Exception as e:
                print(f"Erro ao abrir chamada: {e}")

        elif opcao == "fechar":
            cur.execute("UPDATE Chamadas SET status='Fechada', horario_fim=CURRENT_TIME WHERE status='Aberta'")
            print(f"✅ {cur.rowcount} chamada(s) encerrada(s).")

# --- FUNÇÃO CENTRALIZADA: CADASTRO BIOMÉTRICO ---
def fluxo_cadastro_completo(professor_user_id):
    print("\n--- 📸 CADASTRO BIOMÉTRICO DE ALUNO ---")
    
    # 1. Selecionar Turma
    turmas = listar_turmas_professor(professor_user_id)
    if not turmas:
        print("❌ Sem turmas disponíveis.")
        return

    print("Selecione a turma para matricular o aluno:")
    for i, t in enumerate(turmas):
        print(f"{i+1}. {t['nome_disciplina']}")
    
    try:
        esc = int(input("Turma: ")) - 1
        turma_id = turmas[esc]['turma_id']
    except: return

    # 2. Dados Textuais
    nome = input("Nome Completo: ").strip()
    email = input("E-mail: ").strip()
    ra = input("RA: ").strip()
    
    # Usa a função do utils.py
    external_id = formatar_nome_para_external_id(nome)
    print(f"👉 ID Facial gerado: {external_id}")

    # 3. Captura da Câmera
    print("\n📸 POSICIONE O ALUNO NA FRENTE DA CÂMERA...")
    input("Pressione ENTER para capturar a foto...")
    
    foto_bytes = capture_frame_as_jpeg_bytes()
    if not foto_bytes:
        print("❌ Erro ao capturar foto.")
        return

    # 4. Upload para S3
    nome_arquivo_s3 = f"alunos/{external_id}_{uuid.uuid4()}.jpg"
    print("☁️  Enviando para AWS S3...")
    
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME, Key=nome_arquivo_s3, 
            Body=foto_bytes, ContentType='image/jpeg'
        )
    except Exception as e:
        print(f"❌ Erro S3: {e}")
        return

    # 5. Indexar no Rekognition
    print("🧠 Indexando rosto no Rekognition...")
    try:
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': nome_arquivo_s3}},
            ExternalImageId=external_id,
            MaxFaces=1, QualityFilter="AUTO", DetectionAttributes=['ALL']
        )
        
        if not response['FaceRecords']:
            print("❌ NENHUM ROSTO DETECTADO! Tente novamente.")
            return
        
        face_id_aws = response['FaceRecords'][0]['Face']['FaceId']
        print(f"✅ Rosto indexado! FaceId AWS: {face_id_aws}")

    except Exception as e:
        print(f"❌ Erro Rekognition: {e}")
        return

    # 6. Salvar no Banco
    sucesso = cadastrar_novo_aluno(nome, email, ra, turma_id, external_id, face_id_aws, nome_arquivo_s3)
    if sucesso:
        print("\n✨ CADASTRO CONCLUÍDO COM SUCESSO! ✨")

# --- AUXILIARES ---
def obter_professor_id(usuario_id):
    with get_db_cursor() as cur:
        cur.execute("SELECT professor_id FROM Professores WHERE usuario_id = %s", (usuario_id,))
        res = cur.fetchone()
        return res['professor_id'] if res else None

def menu():
    # Pega o primeiro professor do banco para simular login
    with get_db_cursor() as cur:
        if not cur: return
        cur.execute("SELECT usuario_id, nome FROM Usuarios WHERE tipo_usuario='Professor' LIMIT 1")
        prof = cur.fetchone()

    if not prof:
        print("❌ Nenhum professor cadastrado. Rode o setup_teste.py primeiro.")
        return

    while True:
        print(f"\n=== 🎓 SCPI LOCAL (Prof: {prof['nome']}) ===")
        print("1. 📂 Listar Turmas")
        print("2. 🔔 ABRIR Chamada")
        print("3. 🔕 FECHAR Chamada")
        print("4. ➕ CADASTRAR ALUNO (Foto + AWS)")
        print("0. Sair")
        
        opt = input("Opção: ")
        
        if opt == "1":
            turmas = listar_turmas_professor(prof['usuario_id'])
            for t in turmas: print(f"- {t['nome_disciplina']}")
        elif opt == "2":
            gerenciar_chamada("abrir", prof['usuario_id'])
        elif opt == "3":
            gerenciar_chamada("fechar", prof['usuario_id'])
        elif opt == "4":
            fluxo_cadastro_completo(prof['usuario_id'])
        elif opt == "0":
            break

if __name__ == "__main__":
    menu()