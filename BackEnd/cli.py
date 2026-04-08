import uuid
from db_conexao import get_db_cursor
from db_repositorio import listar_funcionarios_empresa, cadastrar_funcionario_com_foto
from config import BUCKET_NAME, COLLECTION_ID
from aws_conexao import s3_client, rekognition_client
from rekognition_servico import reconhecer_funcionario_por_bytes
from captura_webcam import capture_frame_as_jpeg_bytes
from formatadores import formatar_nome_para_external_id


# --- GERENCIAR EXPEDIENTE ---

def gerenciar_expediente(opcao, empresa_id):
    with get_db_cursor(commit=True) as cur:
        if not cur:
            return

        if opcao == "abrir":
            # No contexto de ponto, "abrir" significa que os funcionários podem bater ponto
            # O expediente é definido pela tabela Horarios_Expediente
            cur.execute(
                "SELECT dia_semana, horario_inicio, horario_fim, tolerancia_minutos FROM Horarios_Expediente WHERE empresa_id = %s",
                (empresa_id,),
            )
            horarios = cur.fetchall()
            if not horarios:
                print("❌ Nenhum horário de expediente configurado.")
                return
            print("\n📋 Horários de expediente:")
            dias = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
            for h in horarios:
                print(
                    f"  {dias[h['dia_semana']]}: {h['horario_inicio']} - {h['horario_fim']} (tolerância: {h['tolerancia_minutos']}min)"
                )
            print("✅ Expediente ativo!")

        elif opcao == "fechar":
            print("ℹ️  No sistema de ponto, não há 'fechar expediente'.")
            print("    Os registros são marcados individualmente por cada funcionário.")


# --- CADASTRO FUNCIONÁRIO ---

def fluxo_cadastro_funcionario(empresa_id):
    print("\n--- 👤 CADASTRO DE FUNCIONÁRIO ---")

    # Setores disponíveis
    with get_db_cursor() as cur:
        if not cur:
            return
        cur.execute("SELECT setor_id, nome FROM Setores WHERE empresa_id = %s", (empresa_id,))
        setores = cur.fetchall()

    if not setores:
        print("❌ Nenhum setor encontrado. Cadastre setores primeiro.")
        return

    print("Selecione o setor:")
    for i, s in enumerate(setores):
        print(f"{i+1}. {s['nome']}")

    try:
        esc = int(input("Setor: ")) - 1
        setor_id = setores[esc]["setor_id"]
    except Exception:
        return

    # Dados
    nome = input("Nome Completo: ").strip()
    email = input("E-mail: ").strip()
    matricula = input("Matrícula: ").strip()
    cargo = input("Cargo: ").strip()

    external_id = formatar_nome_para_external_id(nome)
    print(f"👉 ID Facial: {external_id}")

    # Foto
    input("\nPressione ENTER para capturar foto do funcionário...")
    foto_bytes = capture_frame_as_jpeg_bytes()
    if not foto_bytes:
        print("❌ Erro ao capturar foto.")
        return

    nome_arquivo_s3 = f"funcionarios/{empresa_id}/{external_id}_{uuid.uuid4()}.jpg"
    print("☁️  Enviando para AWS S3...")

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=nome_arquivo_s3,
            Body=foto_bytes,
            ContentType="image/jpeg",
        )
    except Exception as e:
        print(f"❌ Erro S3: {e}")
        return

    print("🧠 Indexando rosto no Rekognition...")
    try:
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={"S3Object": {"Bucket": BUCKET_NAME, "Name": nome_arquivo_s3}},
            ExternalImageId=external_id,
            MaxFaces=1,
            QualityFilter="AUTO",
            DetectionAttributes=["ALL"],
        )

        if not response["FaceRecords"]:
            print("❌ NENHUM ROSTO DETECTADO!")
            return

        face_id_aws = response["FaceRecords"][0]["Face"]["FaceId"]
        print(f"✅ Rosto indexado! FaceId: {face_id_aws}")

    except Exception as e:
        print(f"❌ Erro Rekognition: {e}")
        return

    # Salvar
    sucesso = cadastrar_funcionario_com_foto(
        nome, email, matricula, empresa_id, setor_id, cargo, external_id, face_id_aws, nome_arquivo_s3
    )
    if sucesso:
        print("✨ CADASTRO CONCLUÍDO! ✨")


# --- TESTE DE RECONHECIMENTO ---

def testar_reconhecimento():
    print("\n--- 🔍 TESTE DE RECONHECIMENTO FACIAL ---")
    input("Pressione ENTER para capturar...")

    foto_bytes = capture_frame_as_jpeg_bytes()
    if not foto_bytes:
        print("❌ Erro ao capturar.")
        return

    resultado = reconhecer_funcionario_por_bytes(foto_bytes)
    if resultado:
        print(f"✅ Reconhecido: {resultado}")
    else:
        print("❌ Rosto não reconhecido.")


# --- MENU ---

def menu():
    with get_db_cursor() as cur:
        if not cur:
            return
        cur.execute("SELECT empresa_id, nome FROM Empresas LIMIT 1")
        emp = cur.fetchone()

    if not emp:
        print("❌ Nenhuma empresa cadastrada. Rode setup_db.py primeiro.")
        return

    empresa_id = emp["empresa_id"]

    while True:
        print(f"\n=== 🏢 PONTO FACIAL — {emp['nome']} ===")
        print("1. 👥 Listar Funcionários")
        print("2. ➕ Cadastrar Funcionário")
        print("3. 🔍 Testar Reconhecimento")
        print("4. 📋 Horários de Expediente")
        print("0. Sair")

        opt = input("Opção: ")

        if opt == "1":
            funcionarios = listar_funcionarios_empresa(empresa_id)
            for f in funcionarios:
                print(f"  - {f['nome']} | {f['email']} | {f.get('setor', 'N/A')}")
        elif opt == "2":
            fluxo_cadastro_funcionario(empresa_id)
        elif opt == "3":
            testar_reconhecimento()
        elif opt == "4":
            gerenciar_expediente("abrir", empresa_id)
        elif opt == "0":
            break


if __name__ == "__main__":
    menu()
