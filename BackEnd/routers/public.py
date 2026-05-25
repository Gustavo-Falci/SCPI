from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {"mensagem": "API SCPI está rodando!"}
