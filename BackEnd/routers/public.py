from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {"mensagem": "API SCPI está rodando!"}


@router.get("/teste_reload")
def teste_reload():
    return {"status": "reloaded"}
