import os
from dotenv import load_dotenv

load_dotenv()

# AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COLLECTION_ID = os.getenv("COLLECTION_ID", "ponto-facial-empresas")
BUCKET_NAME = os.getenv("BUCKET_NAME", "ponto-facial-imagens")

# Security
if not os.getenv("SECRET_KEY"):
    raise ValueError("SECRET_KEY deve ser definida no arquivo .env")
