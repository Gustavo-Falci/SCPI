"""Prova de que o modelo declarado no /docs é o que a rota devolve de verdade.

Documentação de resposta só vale se alguém a confronta com o retorno real —
senão envelhece igual a um comentário. Este apoio pega o modelo declarado no
app (`responses={200: {"model": X}}` ou `response_model=`) e valida contra ele
o payload que o teste acabou de obter da rota.

Os modelos herdam `RespostaBase`, que é `extra="forbid"`. Isso faz a validação
pegar os DOIS lados do desalinhamento:

- campo documentado que a rota não devolve → erro de campo obrigatório ausente;
- campo devolvido que ninguém documentou → erro de campo extra.

O payload passa por `jsonable_encoder` antes: o cliente lê JSON, não objetos
Python. Sem isso, um `uuid.UUID` vindo do psycopg2 falharia contra `str` e o
teste acusaria divergência que o cliente nunca vê.
"""
import json

from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from pydantic import TypeAdapter


def _rota(metodo: str, caminho: str) -> APIRoute:
    from api import app

    metodo = metodo.upper()
    for rota in app.routes:
        if (
            isinstance(rota, APIRoute)
            and rota.path == caminho
            and metodo in (rota.methods or set())
        ):
            return rota
    raise AssertionError(f"rota {metodo} {caminho} não existe no app")


def modelo_declarado(metodo: str, caminho: str):
    """Modelo de saída que a rota declara para 200, lido do app real.

    Lê do app e não de um import direto de propósito: o que documenta a rota é
    o que está pendurado nela, não o modelo que existe no arquivo. Modelo
    escrito e esquecido sem pendurar reprova aqui.
    """
    rota = _rota(metodo, caminho)
    modelo = (rota.responses.get(200) or {}).get("model") or rota.response_model
    assert modelo is not None, (
        f"{metodo.upper()} {caminho} não declara modelo de saída para 200 — "
        "acrescente `responses={200: {\"model\": X}}` na rota"
    )
    return modelo


def corpo_json(resposta):
    """Reduz ao dict/lista que o cliente recebe, venha de onde vier.

    Aceita as três formas que os testes daqui produzem: retorno direto do
    handler (dict), `Response` do Starlette (o caminho do 503 do /health, que
    não passa pelo serializador da rota) e resposta do TestClient.
    """
    if hasattr(resposta, "json") and callable(resposta.json):
        return resposta.json()
    if hasattr(resposta, "body"):
        return json.loads(resposta.body)
    return jsonable_encoder(resposta)


def assert_resposta_conforme(resposta, metodo: str, caminho: str):
    """Valida o payload contra o modelo que a rota declara. Devolve o modelo.

    Valida por `TypeAdapter` e não por `Modelo.model_validate` porque nem todo
    200 é um modelo único: rota que devolve lista declara `list[X]`, e rota com
    envelope opt-in declara a união dos dois formatos. `TypeAdapter` aceita as
    três formas com a mesma chamada.
    """
    modelo = modelo_declarado(metodo, caminho)
    TypeAdapter(modelo).validate_python(jsonable_encoder(corpo_json(resposta)))
    return modelo
