from rekognition_aws import criar_colecao, cadastrar_rosto, reconhecer_aluno
from sistema_cadastrar_aluno import s3_client, BUCKET_NAME
import botocore.exceptions
import capture_camera
import os
import uuid
import re


# Função para formatar o nome/ID do aluno conforme exigido pelo Amazon Rekognition
# Ela substitui espaços por "_" e remove caracteres não permitidos
def formatar_nome_para_external_id(nome):
    nome_formatado = re.sub(r'\s+', '_', nome)  # Substitui espaços por underline
    nome_formatado = re.sub(r'[^a-zA-Z0-9_.\-:]', '', nome_formatado)  # Remove caracteres inválidos
    return nome_formatado

# Função que realiza a criação da coleção de rostos no Amazon Rekognition
def acao_criar_colecao():
    print("\nℹ️ Essa ação só precisa ser feita uma vez. Se a coleção já existe, será ignorada.")
    try:
        criar_colecao()
        print("✅ Coleção criada com sucesso (ou já existente).")
    except botocore.exceptions.ClientError as e:
        print(f"❌ Erro ao criar coleção ({type(e).__name__}): {e}")

# Função que cadastra um novo aluno:
# Captura a imagem, envia ao S3, cadastra no Rekognition e remove a imagem local
def acao_cadastrar_aluno():
    nome = input("🧑 Digite o nome ou ID do aluno: ").strip()
    if not nome:
        print("⚠️ Nome inválido. Tente novamente.")
        return

    # Captura imagem do aluno
    imagem_path = capture_camera.capture_image()
    if not imagem_path:
        print("❌ Erro ao capturar imagem.")
        return

    # Gera um caminho único para o arquivo usando UUID
    imagem_uuid = uuid.uuid4()
    s3_path = f"alunos/{nome}_{imagem_uuid}.jpg"

    # Formata o nome para ser compatível com Rekognition
    nome_formatado = formatar_nome_para_external_id(nome)

    try:
        # Envia a imagem capturada para o bucket do S3
        s3_client.upload_file(imagem_path, BUCKET_NAME, s3_path)
        print(f"✅ Imagem enviada: s3://{BUCKET_NAME}/{s3_path}")

        # Cadastra o rosto da imagem no Rekognition usando o nome formatado
        cadastrar_rosto(s3_path, nome_formatado)
        print(f"📌 Rosto cadastrado no Rekognition para o aluno '{nome}'.")
    except botocore.exceptions.ClientError as e:
        print(f"❌ Erro durante o cadastro ({type(e).__name__}): {e}")
    finally:
        # Remove a imagem local da máquina, mesmo se houver erro
        if os.path.exists(imagem_path):
            os.remove(imagem_path)
            print(f"🗑️ Imagem local '{imagem_path}' excluída.")

# Função que realiza o reconhecimento facial de um aluno
def acao_reconhecer_aluno():
    # Captura imagem da câmera
    imagem_path = capture_camera.capture_image()
    if not imagem_path:
        print("❌ Erro ao capturar imagem.")
        return

    try:
        # Envia a imagem para reconhecimento no Rekognition
        reconhecer_aluno(imagem_path)
    except botocore.exceptionsClientError as e:
        print(f"❌ Erro no reconhecimento ({type(e).__name__}): {e}")
    finally:
        # Remove a imagem local após o reconhecimento
        if os.path.exists(imagem_path):
            os.remove(imagem_path)
            print(f"🗑️ Imagem local '{imagem_path}' excluída após o reconhecimento.")

# Função principal que exibe o menu e chama as funcionalidades conforme a escolha do usuário
def main():
    print("\n🎬 Bem-vindo ao Sistema de Reconhecimento Facial para Chamada!\n")

    while True:
        # Menu de opções
        print("\nEscolha uma opção:")
        print("1️⃣  Criar Coleção (apenas uma vez)")
        print("2️⃣  Cadastrar um Aluno")
        print("3️⃣  Reconhecer um Aluno")
        print("4️⃣  Sair")

        escolha = input("👉 Digite a opção (1-4): ").strip()

        if escolha == "1":
            acao_criar_colecao()
        elif escolha == "2":
            acao_cadastrar_aluno()
        elif escolha == "3":
            acao_reconhecer_aluno()
        elif escolha == "4":
            print("🚪 Saindo do sistema... Até logo!")
            break
        else:
            print("❌ Opção inválida! Digite um número entre 1 e 4.")

# Ponto de entrada do programa
if __name__ == "__main__":
    main()