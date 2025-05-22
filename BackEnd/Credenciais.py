import boto3
from botocore.exceptions import ClientError
import config # Importe o seu arquivo de configuração

# Use as configurações do seu arquivo config.py
AWS_REGION = config.AWS_REGION
COLLECTION_ID = config.COLLECTION_ID

print(f"Configurações carregadas: Região AWS = {AWS_REGION}, ID da Coleção = {COLLECTION_ID}")

try:
    # O boto3 vai automaticamente usar as credenciais do seu arquivo ~/.aws/credentials
    # e a região que você definiu explicitamente aqui no construtor do cliente.
    # Se você já definiu a região em ~/.aws/config, esta linha sobrescreve.
    rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)

    # --- Exemplo de Teste de Conexão: Listar Coleções ---
    print("\nTentando listar coleções para testar a conexão...")
    response_list_collections = rekognition_client.list_collections()
    print("Conexão bem-sucedida! Coleções Rekognition existentes:", response_list_collections.get('CollectionIds', []))

except ClientError as e:
    # Captura erros específicos do cliente AWS
    error_code = e.response['Error']['Code']
    error_message = e.response['Error']['Message']
    print(f"\nERRO: {error_code} - {error_message}")

    if error_code == 'UnrecognizedClientException':
        print("Causa provável: As credenciais da AWS estão inválidas ou ausentes.")
        print("Por favor, verifique se seu ~/.aws/credentials está configurado corretamente com as chaves de acesso do usuário IAM.")
    elif error_code == 'AccessDeniedException':
        print("Causa provável: O usuário IAM não tem as permissões necessárias para esta operação.")
        print(f"Certifique-se de que o usuário tem permissões para 'rekognition:ListCollections' e outras operações que você está tentando usar.")
    elif error_code == 'ResourceNotFoundException':
        print(f"Causa provável: A coleção Rekognition '{COLLECTION_ID}' não existe na região '{AWS_REGION}'.")
        print("Verifique se o nome da coleção e a região estão corretos.")
    else:
        print(f"Um erro inesperado do cliente AWS ocorreu.")
except Exception as e:
    # Captura outros erros gerais
    print(f"\nERRO GERAL: {e}")