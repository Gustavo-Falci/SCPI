# config.py
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configurações AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COLLECTION_ID = os.getenv("COLLECTION_ID", "sala_de_aula")
BUCKET_NAME = os.getenv("BUCKET_NAME", "faces-sala-aula-2025")


# Você pode adicionar validação aqui se quiser garantir que as variáveis existam
if not BUCKET_NAME or not COLLECTION_ID:
    print("⚠️  AVISO: Variáveis de ambiente da AWS não configuradas corretamente no .env")