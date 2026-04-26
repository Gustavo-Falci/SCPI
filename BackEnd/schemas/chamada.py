from pydantic import BaseModel


class ChamadaAbrir(BaseModel):
    turma_id: str
