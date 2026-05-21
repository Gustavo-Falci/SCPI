# config.py
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Configurações AWS
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
COLLECTION_ID = os.getenv("COLLECTION_ID", "sala_de_aula")
BUCKET_NAME = os.getenv("BUCKET_NAME", "faces-sala-aula-2025")

# ---------------------------------------------------------------------------
# Thresholds de reconhecimento facial (similaridade mínima 0-100).
# Centralizar evita divergência entre handlers e dificulta downgrade silencioso.
# Valores mais altos = menos false positives, mais false negatives.
# ---------------------------------------------------------------------------
# Selfie no app — câmera frontal próxima, ambiente controlado pelo aluno.
FACE_MATCH_THRESHOLD_SELFIE = int(os.getenv("FACE_MATCH_THRESHOLD_SELFIE", "90"))
# Câmera fixa na sala — distância variável, iluminação irregular, múltiplos rostos.
# Valor menor reflete maior tolerância empírica, NÃO menor exigência de segurança.
# Revisar se a taxa de false positives crescer.
FACE_MATCH_THRESHOLD_SALA = int(os.getenv("FACE_MATCH_THRESHOLD_SALA", "90"))


# Você pode adicionar validação aqui se quiser garantir que as variáveis existam
if not BUCKET_NAME or not COLLECTION_ID:
    print("⚠️  AVISO: Variáveis de ambiente da AWS não configuradas corretamente no .env")

# ---------------------------------------------------------------------------
# LGPD Export — Chave HMAC para assinar manifestos de integridade (Art. 18).
# Gere com: python -c "import secrets; print(secrets.token_hex(32))"
# ---------------------------------------------------------------------------
SCPI_EXPORT_HMAC_KEY = os.getenv("SCPI_EXPORT_HMAC_KEY")
if not SCPI_EXPORT_HMAC_KEY:
    raise RuntimeError(
        "SCPI_EXPORT_HMAC_KEY não definida. Gere com: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )