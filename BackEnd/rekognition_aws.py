import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import logging
import os # Adicionado para operações de caminho de arquivo nos exemplos

# Tenta importar configurações, fornece orientação se não encontradas
try:
    from config import AWS_REGION, COLLECTION_ID
except ImportError:
    print("ERRO: Arquivo de configuração 'config.py' não encontrado ou mal configurado.")
    print("Certifique-se de que 'config.py' existe e contém AWS_REGION e COLLECTION_ID.")
    # Forneça valores padrão ou saia, dependendo do comportamento desejado
    AWS_REGION = "us-east-1" # Exemplo padrão, altere conforme necessário
    COLLECTION_ID = "sua_colecao_padrao_id" # Exemplo padrão
    print(f"Usando valores padrão: AWS_REGION='{AWS_REGION}', COLLECTION_ID='{COLLECTION_ID}'")
    # import sys # Descomente para sair se a configuração for crítica
    # sys.exit(1)

# Tenta importar BUCKET_NAME, fornece orientação
try:
    from sistema_cadastrar_aluno import BUCKET_NAME as DEFAULT_BUCKET_NAME
except ImportError:
    print("AVISO: 'BUCKET_NAME' não pôde ser importado de 'sistema_cadastrar_aluno'.")
    print("A função 'cadastrar_rosto_s3' precisará do nome do bucket via parâmetro ou defina DEFAULT_BUCKET_NAME.")
    DEFAULT_BUCKET_NAME = "seu_bucket_padrao_nome" # Exemplo padrão

# Configuração de logging
# Usando uma instância de logger para melhor controle se este módulo for importado em outro lugar
logger = logging.getLogger(__name__)
if not logger.handlers: # Evita adicionar múltiplos handlers se importado várias vezes
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Cliente Rekognition - Inicialize globalmente ou dentro de uma função/classe conforme preferir
# Inicialização global é aceitável para scripts.
try:
    rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)
except (NoCredentialsError, PartialCredentialsError):
    logger.error("❌ Credenciais AWS não encontradas ou incompletas. Verifique a configuração do seu ambiente AWS.")
    # import sys
    # sys.exit(1) # Ou trate apropriadamente
except Exception as e:
    logger.error(f"❌ Erro ao inicializar o cliente Rekognition: {e}")
    # import sys
    # sys.exit(1)


def criar_colecao_rekognition(collection_id_para_criar):
    """
    Cria uma coleção no AWS Rekognition se ela ainda não existir.

    Args:
        collection_id_para_criar (str): O ID da coleção a ser criada.

    Returns:
        bool: True se a coleção já existe ou foi criada com sucesso, False caso contrário.
    """
    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado. Não é possível criar a coleção.")
        return False
    try:
        rekognition_client.describe_collection(CollectionId=collection_id_para_criar)
        logger.info(f"ℹ️ A coleção '{collection_id_para_criar}' já existe.")
        return True
    except rekognition_client.exceptions.ResourceNotFoundException:
        logger.info(f"A coleção '{collection_id_para_criar}' não existe. Tentando criar...")
        try:
            response = rekognition_client.create_collection(CollectionId=collection_id_para_criar)
            logger.info(f"✅ Coleção '{collection_id_para_criar}' criada com sucesso!")
            logger.info(f"   ARN da Coleção: {response.get('CollectionArn')}") # Amazon Resource Name
            logger.info(f"   Código de Status: {response.get('StatusCode')}")
            return True
        except ClientError as e:
            logger.error(f"❌ Erro ao criar a coleção '{collection_id_para_criar}': {e.response['Error']['Message']}")
            return False
    except ClientError as e:
        logger.error(f"❌ Erro ao descrever a coleção '{collection_id_para_criar}': {e.response['Error']['Message']}")
        return False


def cadastrar_rosto_s3(aluno_id, s3_bucket, s3_key, collection_id_alvo):
    """
    Cadastra (indexa) o rosto de um aluno a partir de uma imagem armazenada no S3
    na coleção especificada do Rekognition.

    Args:
        aluno_id (str): O ID externo para associar ao rosto (ex: matrícula do aluno).
        s3_bucket (str): O nome do bucket S3 onde a imagem está.
        s3_key (str): O caminho (chave) para o arquivo de imagem no bucket S3.
        collection_id_alvo (str): O ID da coleção Rekognition onde o rosto será indexado.

    Returns:
        dict: O primeiro FaceRecord (registro da face) retornado pelo Rekognition se o cadastro for bem-sucedido,
              None caso contrário.
    """
    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado. Não é possível cadastrar o rosto.")
        return None
    try:
        logger.info(f"Tentando cadastrar rosto para Aluno ID: '{aluno_id}' da imagem S3: s3://{s3_bucket}/{s3_key}")
        response = rekognition_client.index_faces(
            CollectionId=collection_id_alvo,
            Image={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}},
            ExternalImageId=aluno_id,
            DetectionAttributes=['ALL'], # Pode ser 'DEFAULT' se não precisar de todos os atributos
            MaxFaces=1 # Indexa apenas o maior rosto encontrado na imagem
        )

        face_records = response.get('FaceRecords', [])

        if face_records:
            rosto_indexado = face_records[0] # MaxFaces=1 garante no máximo um registro principal aqui
            logger.info(f"✅ Rosto do aluno '{aluno_id}' cadastrado com sucesso!")
            logger.info(f"   ID da Face: {rosto_indexado.get('Face', {}).get('FaceId')}")
            logger.info(f"   ID da Imagem: {rosto_indexado.get('Face', {}).get('ImageId')}")
            if len(face_records) > 1 : # Não deve acontecer com MaxFaces=1, mas é bom estar ciente
                 logger.warning(f"⚠️ {len(face_records)} registros de face retornados, esperado 1 devido a MaxFaces=1.")
            if response.get('UnindexedFaces'): # Faces Não Indexadas
                logger.warning(f"⚠️ Alguns rostos não foram indexados: {response.get('UnindexedFaces')}")
            return rosto_indexado
        else:
            # Isso pode acontecer se UnindexedFaces (Faces Não Indexadas) tiver informações (ex: rosto muito pequeno)
            info_nao_indexado = response.get('UnindexedFaces')
            if info_nao_indexado:
                logger.error(f"❌ Nenhum rosto foi indexado para '{aluno_id}'. Motivos: {info_nao_indexado}")
            else:
                logger.error(f"❌ Nenhum rosto detectado ou indexado na imagem para o aluno '{aluno_id}'.")
            return None

    except rekognition_client.exceptions.InvalidParameterException as e:
        logger.error(f"❌ Erro de parâmetro inválido ao cadastrar rosto para '{aluno_id}': {e}")
        logger.error("   Possíveis causas: Imagem sem rostos, formato de imagem não suportado, ou ID da coleção inválido.")
        return None
    except rekognition_client.exceptions.ResourceNotFoundException as e:
        logger.error(f"❌ Coleção '{collection_id_alvo}' não encontrada ao tentar cadastrar rosto: {e}")
        return None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"❌ Erro do cliente AWS ao cadastrar rosto para '{aluno_id}': [{error_code}] {error_message}")
        return None


def reconhecer_aluno_local(caminho_imagem, collection_id_busca, limiar_similaridade=80, max_combinacoes=1):
    """
    Reconhece um aluno a partir de um arquivo de imagem local, buscando na coleção especificada.

    Args:
        caminho_imagem (str): O caminho para o arquivo de imagem local.
        collection_id_busca (str): O ID da coleção Rekognition para buscar o rosto.
        limiar_similaridade (int): O limiar de similaridade mínimo (0-100) para considerar uma correspondência.
        max_combinacoes (int): O número máximo de rostos correspondentes a retornar.

    Returns:
        list: Uma lista de dicionários, cada um contendo 'aluno_id' e 'similaridade'
              para cada rosto correspondente encontrado, ou uma lista vazia se nenhum for encontrado
              ou em caso de erro.
    """
    if not rekognition_client:
        logger.error("Cliente Rekognition não inicializado. Não é possível reconhecer o aluno.")
        return []
    try:
        with open(caminho_imagem, "rb") as image_file:
            image_bytes = image_file.read()
        
        logger.info(f"Tentando reconhecer aluno na imagem: '{caminho_imagem}' na coleção '{collection_id_busca}'")
        response = rekognition_client.search_faces_by_image(
            CollectionId=collection_id_busca,
            Image={'Bytes': image_bytes},
            MaxFaces=max_combinacoes,
            FaceMatchThreshold=float(limiar_similaridade) # API espera float
        )

        combinacoes = []
        if response.get('FaceMatches'): # Combinações de Faces
            for match in response['FaceMatches']:
                aluno_id = match['Face']['ExternalImageId']
                similarity = match['Similarity']
                logger.info(f"✅ Aluno reconhecido: {aluno_id} com similaridade: {similarity:.2f}%")
                combinacoes.append({'aluno_id': aluno_id, 'similaridade': similarity})
            return combinacoes
        else:
            # Verifica se um rosto foi detectado na imagem de entrada, mesmo que não haja correspondências
            caixa_rosto_buscado = response.get('SearchedFaceBoundingBox')
            if caixa_rosto_buscado:
                logger.warning(f"⚠️ Um rosto foi detectado na imagem '{caminho_imagem}', mas não houve correspondências na coleção '{collection_id_busca}' com o limiar de {limiar_similaridade}%.")
            else:
                logger.warning(f"ℹ️ Nenhum rosto detectado na imagem de entrada '{caminho_imagem}' ou nenhum rosto correspondente encontrado.")
            return []

    except FileNotFoundError:
        logger.error(f"❌ Arquivo de imagem '{caminho_imagem}' não encontrado.")
        return []
    except rekognition_client.exceptions.InvalidParameterException as e:
        logger.error(f"❌ Erro de parâmetro inválido ao reconhecer aluno na imagem '{caminho_imagem}': {e}")
        logger.error("   Possíveis causas: Nenhum rosto detectado na imagem de entrada, formato de imagem não suportado.")
        return []
    except rekognition_client.exceptions.ResourceNotFoundException:
        logger.error(f"❌ Coleção '{collection_id_busca}' não encontrada ao tentar reconhecer aluno.")
        return []
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"❌ Erro do cliente AWS ao reconhecer aluno: [{error_code}] {error_message}")
        return []


# Exemplo de execução protegida
if __name__ == "__main__":
    logger.info("--- Iniciando Demonstração do Módulo Rekognition ---")

    # Usa COLLECTION_ID do config.py (ou valor padrão se config.py falhar)
    TARGET_COLLECTION_ID = COLLECTION_ID 
    # Usa DEFAULT_BUCKET_NAME (do sistema_cadastrar_aluno ou valor padrão)
    TARGET_BUCKET_NAME = DEFAULT_BUCKET_NAME

    # 1. Criar a coleção (se não existir)
    logger.info("\n--- Etapa 1: Criação/Verificação da Coleção ---")
    if criar_colecao_rekognition(TARGET_COLLECTION_ID):
        logger.info(f"Pronto para usar a coleção '{TARGET_COLLECTION_ID}'.")

        # --- EXEMPLOS DE CADASTRO E RECONHECIMENTO ---
        # Os arquivos de imagem e chaves S3 abaixo são placeholders (valores de exemplo).
        # Substitua pelos seus próprios dados para testar.

        # 2. Exemplo de Cadastro de Rosto (requer imagem no S3)
        logger.info("\n--- Etapa 2: Exemplo de Cadastro de Rosto via S3 ---")
        # Crie um arquivo chamado 'rosto_exemplo_aluno1.jpg' no seu bucket S3 para este exemplo
        aluno_id_exemplo = "matricula_12345"
        s3_key_exemplo = f"fotos_alunos/{aluno_id_exemplo}.jpg" # Ex: 'fotos_alunos/matricula_12345.jpg'
        
        logger.info(f"Para testar o cadastro, certifique-se que a imagem s3://{TARGET_BUCKET_NAME}/{s3_key_exemplo} existe.")
        # Descomente a linha abaixo para tentar cadastrar (após configurar a imagem no S3):
        # face_record = cadastrar_rosto_s3(aluno_id_exemplo, TARGET_BUCKET_NAME, s3_key_exemplo, TARGET_COLLECTION_ID)
        # if face_record:
        # logger.info(f"Detalhes do cadastro: {face_record}")
        # else:
        # logger.warning("Cadastro de exemplo não realizado ou falhou. Verifique os logs e a configuração do S3.")

        # 3. Exemplo de Reconhecimento de Aluno (requer arquivo de imagem local)
        logger.info("\n--- Etapa 3: Exemplo de Reconhecimento de Aluno via Imagem Local ---")
        # Crie um arquivo de imagem local chamado 'imagem_teste_reconhecimento.jpg'
        caminho_imagem_local_exemplo = "imagem_teste_reconhecimento.jpg" 
        
        if not os.path.exists(caminho_imagem_local_exemplo):
            logger.warning(f"Arquivo de imagem local para teste '{caminho_imagem_local_exemplo}' não encontrado.")
            logger.warning("Crie este arquivo com um rosto para testar o reconhecimento.")
        else:
            logger.info(f"Tentando reconhecer aluno usando a imagem local: '{caminho_imagem_local_exemplo}'")
            alunos_reconhecidos = reconhecer_aluno_local(caminho_imagem_local_exemplo, TARGET_COLLECTION_ID, limiar_similaridade=80)
            if alunos_reconhecidos:
                for aluno in alunos_reconhecidos:
                    logger.info(f"Resultado do Reconhecimento: Aluno ID {aluno['aluno_id']}, Similaridade: {aluno['similaridade']:.2f}%")
            else:
                logger.info("Nenhum aluno reconhecido na imagem de teste ou ocorreu um erro.")
    else:
        logger.error(f"Não foi possível criar ou verificar a coleção '{TARGET_COLLECTION_ID}'. As operações subsequentes podem falhar.")

    logger.info("\n--- Demonstração Concluída ---")