# Imports corrigidos e organizados
import logging
import re
import uuid  # Para gerar IDs únicos para imagens

import botocore.exceptions
from aws_clientes import s3_client
from capture_camera import capture_frame_as_jpeg_bytes
from config import BUCKET_NAME
from rekognition_aws import cadastrar_rosto as rekognition_cadastrar_rosto
from rekognition_aws import criar_colecao as rekognition_criar_colecao
from rekognition_aws import reconhecer_aluno_por_bytes as rekognition_reconhecer_aluno_por_bytes

# Configuração do logger para este módulo
logger = logging.getLogger(__name__)
# A configuração básica do logging (basicConfig) deve ser feita idealmente uma vez,
# no ponto de entrada principal da aplicação. Se este script é um ponto de entrada, está OK.
# Se for importado, a configuração do logger do módulo que o importa prevalecerá.
if not logger.hasHandlers():  # Evita adicionar handlers múltiplos se já configurado
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
    )


def formatar_nome_para_external_id(nome: str) -> str:
    """Formata o nome/ID do aluno para ser compatível com Amazon Rekognition."""
    nome_formatado = re.sub(r"\s+", "_", nome)  # Substitui espaços por underline
    nome_formatado = re.sub(r"[^a-zA-Z0-9_.\-:]", "", nome_formatado)  # Remove caracteres inválidos
    return nome_formatado


def acao_criar_colecao():
    """Realiza a criação da coleção de rostos no Amazon Rekognition."""
    print("\nℹ️  Esta ação só precisa ser feita uma vez. Se a coleção já existe, será informado.")
    try:
        # A função rekognition_criar_colecao já verifica se o rekognition_client está disponível
        # e também trata os erros de ClientError internamente, logando-os.
        resultado = rekognition_criar_colecao()
        if resultado is not None:  # A função retorna a resposta da API ou None em caso de erro/já existir sem erro
            # A mensagem de sucesso ou "já existe" é logada dentro de rekognition_criar_colecao
            print("✅ Verificação/Criação da coleção concluída. Veja os logs para detalhes.")
        else:
            # Se resultado for None, um erro já foi logado dentro de rekognition_criar_colecao
            print("❌ Falha ao verificar/criar coleção. Verifique os logs.")

    except Exception as e:  # Captura qualquer outra exceção inesperada
        print(f"❌ Erro inesperado ao tentar criar coleção: {e}")
        logger.error(f"Erro inesperado na acao_criar_colecao: {e}", exc_info=True)


def acao_cadastrar_aluno():
    """Cadastra um novo aluno: captura imagem, envia bytes ao S3, cadastra no Rekognition."""
    nome = input("🧑 Digite o nome ou ID do aluno: ").strip()

    if not nome:
        print("⚠️ Nome inválido. Tente novamente.")
        logger.warning("Nome de aluno inválido fornecido para cadastro.")
        return

    print("📸 Posicione-se para a foto...")
    image_bytes = capture_frame_as_jpeg_bytes()  # Captura como bytes

    if not image_bytes:
        print("❌ Erro ao capturar imagem. Verifique a câmera e tente novamente.")
        # O logger dentro de capture_frame_as_jpeg_bytes já deve ter logado o erro específico.
        return

    nome_formatado = formatar_nome_para_external_id(nome)
    imagem_uuid = uuid.uuid4()
    s3_path = f"alunos/{nome_formatado}_{imagem_uuid}.jpg"  # Usa nome_formatado para o path S3
    logger.info(f"Nome do arquivo S3 para cadastro: {s3_path}")

    if not s3_client:
        print("❌ Cliente S3 não está disponível. Cadastro cancelado.")
        logger.error("Cliente S3 não disponível para cadastro em acao_cadastrar_aluno.")
        return

    try:
        # Envia os bytes da imagem para o bucket do S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_path, Body=image_bytes, ContentType="image/jpeg")
        print(f"✅ Imagem enviada para: s3://{BUCKET_NAME}/{s3_path}")
        logger.info(f"Bytes da imagem enviados para s3://{BUCKET_NAME}/{s3_path}")

        # Cadastra o rosto da imagem (que está no S3) no Rekognition
        # rekognition_cadastrar_rosto é um wrapper que chama indexar_rosto_da_imagem_s3
        resultado_cadastro_rekognition = rekognition_cadastrar_rosto(s3_path, nome_formatado)

        # A função rekognition_cadastrar_rosto (e indexar_rosto_da_imagem_s3) já loga detalhes.
        # Podemos adicionar uma mensagem aqui baseada no resultado.
        if resultado_cadastro_rekognition and resultado_cadastro_rekognition.get("FaceRecords"):
            print(f"✅ Rosto do aluno '{nome}' (ID: {nome_formatado}) registrado no Rekognition com sucesso!")

        elif resultado_cadastro_rekognition and resultado_cadastro_rekognition.get("UnindexedFaces"):
            print(
                f"⚠️ Rosto do aluno '{nome}' (ID: {nome_formatado}) NÃO foi indexado. Razão: {resultado_cadastro_rekognition.get('UnindexedFaces')[0].get('Reasons')}"
            )

        elif resultado_cadastro_rekognition is None:  # Erro na chamada da API
            print(
                f"❌ Falha ao tentar registrar o rosto do aluno '{nome}' (ID: {nome_formatado}) no Rekognition. Verifique os logs."
            )

        else:  # Resposta sem FaceRecords e sem UnindexedFaces (pouco comum se não houver erro)
            print(
                f"❓ Resposta inesperada do Rekognition para o cadastro do aluno '{nome}' (ID: {nome_formatado}). Verifique os logs."
            )

    except botocore.exceptions.ClientError as e_s3:
        print(f"❌ Erro ao enviar imagem para o S3: {e_s3.response['Error']['Message']}")
        logger.error(
            f"Erro S3 durante o cadastro do aluno '{nome}': {e_s3.response['Error']['Message']}",
            exc_info=True,
        )

    except Exception as e:
        print(f"❌ Erro inesperado durante o cadastro: {e}")
        logger.error(f"Erro inesperado durante o cadastro do aluno '{nome}': {e}", exc_info=True)
    # Não há 'finally' para remover arquivo local, pois não foi salvo.


def acao_reconhecer_aluno():
    """Realiza o reconhecimento facial de um aluno usando imagem em memória."""
    print("📸 Posicione-se para a foto de reconhecimento...")
    image_bytes = capture_frame_as_jpeg_bytes()  # Captura como bytes

    if not image_bytes:
        print("❌ Erro ao capturar imagem. Verifique a câmera e tente novamente.")
        return

    try:
        # Envia os bytes da imagem para reconhecimento no Rekognition
        # A função rekognition_reconhecer_aluno_por_bytes já loga o resultado
        aluno_id_reconhecido = rekognition_reconhecer_aluno_por_bytes(image_bytes)

        if aluno_id_reconhecido:
            print(f"🙂 Aluno reconhecido: {aluno_id_reconhecido}")

        else:
            # A função interna já logou "Rosto não reconhecido" ou "Nenhum rosto detectado"
            print("🚫 Aluno não reconhecido.")

        # Bloco opcional para salvar imagem de tentativa no S3 (se decidir implementar)
        # import datetime
        # agora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # status_rec = f"reconhecido_{aluno_id_reconhecido}" if aluno_id_reconhecido else "nao_reconhecido"
        # s3_path_tentativa = f"tentativas_reconhecimento/{agora}_{status_rec}.jpg"
        # try:
        #     if s3_client:
        #         s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_path_tentativa, Body=image_bytes, ContentType='image/jpeg')
        #         logger.info(f"Imagem da tentativa de reconhecimento salva em S3: {s3_path_tentativa}")
        # except Exception as e_s3_rec:
        #     logger.error(f"Falha ao salvar imagem de tentativa de reconhecimento no S3: {e_s3_rec}")

    except botocore.exceptions.ClientError as e_rek:  # Erro específico do Rekognition
        print(f"❌ Erro na chamada ao Rekognition: {e_rek.response['Error']['Message']}")
        # O logger dentro de rekognition_reconhecer_aluno_por_bytes já deve ter logado

    except Exception as e:
        print(f"❌ Erro inesperado durante o reconhecimento: {e}")
        logger.error(f"Erro inesperado na acao_reconhecer_aluno: {e}", exc_info=True)
    # Não há 'finally' para remover arquivo local.


def main():
    print("\n🎬 Bem-vindo ao Sistema de Reconhecimento Facial para Chamada!\n")

    while True:
        print("\nEscolha uma opção:")
        print("1️⃣  Criar Coleção (verificar/criar se necessário)")
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


if __name__ == "__main__":
    main()
