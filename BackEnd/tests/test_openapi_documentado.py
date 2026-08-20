"""Guarda: toda rota do app precisa aparecer documentada no /docs.

Motivo: o Swagger é a documentação viva da API — a única que não envelhece
sozinha, porque mora junto do código. Rota sem `summary` aparece no /docs com o
nome da função em inglês macarrônico; rota sem descrição não diz quem pode
chamar nem o que volta. Este teste falha quando alguém acrescenta rota sem
documentar, que é o momento barato de corrigir.

Não valida `response_model`: isso filtra o payload e é mudança de
comportamento, decidida rota a rota (ver o manual da API quando existir).
"""
import re

import pytest
from fastapi.routing import APIRoute

# Rotas que o próprio FastAPI cria e não temos como anotar.
_ROTAS_INTERNAS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def _app():
    """Importa o app real. Falha explícita se o import quebrar."""
    from api import app

    return app


def _rotas_documentaveis():
    """Rotas que aparecem no /docs — as únicas em que documentação é visível.

    `include_in_schema=False` fica de fora: a rota não tem página no Swagger,
    então não há o que documentar ali. Hoje é só o HEAD /health, que duplica o
    GET logo acima dele. Marcar uma rota assim para escapar deste guarda seria
    abuso: a rota some do /docs junto.
    """
    return [
        rota
        for rota in _app().routes
        if isinstance(rota, APIRoute)
        and rota.path not in _ROTAS_INTERNAS
        and rota.include_in_schema
    ]


def test_existem_rotas_para_documentar():
    """Sanidade: se a coleta vier vazia, os testes abaixo passariam à toa."""
    assert len(_rotas_documentaveis()) >= 60


def test_toda_rota_tem_summary():
    sem_summary = [
        f"{sorted(r.methods)[0]} {r.path}"
        for r in _rotas_documentaveis()
        if not (r.summary or "").strip()
    ]
    assert not sem_summary, (
        "%d rota(s) sem summary — aparecem no /docs com o nome da função:\n  %s"
        % (len(sem_summary), "\n  ".join(sem_summary))
    )


def test_toda_rota_tem_descricao():
    """A descrição vem da docstring da função (ou do kwarg `description`)."""
    sem_descricao = [
        f"{sorted(r.methods)[0]} {r.path}"
        for r in _rotas_documentaveis()
        if not (r.description or "").strip()
    ]
    assert not sem_descricao, (
        "%d rota(s) sem descrição — o leitor não sabe quem pode chamar nem o que volta:\n  %s"
        % (len(sem_descricao), "\n  ".join(sem_descricao))
    )


def test_toda_rota_tem_tag():
    """Sem tag, a rota cai no grupo 'default' do Swagger, fora do seu domínio."""
    sem_tag = [
        f"{sorted(r.methods)[0]} {r.path}" for r in _rotas_documentaveis() if not r.tags
    ]
    assert not sem_tag, "%d rota(s) sem tag:\n  %s" % (
        len(sem_tag),
        "\n  ".join(sem_tag),
    )


def test_app_tem_metadados():
    app = _app()
    assert app.title, "app sem title"
    assert (app.version or "").strip(), "app sem version"
    assert (app.description or "").strip(), "app sem description"


def test_toda_tag_usada_esta_descrita_em_openapi_tags():
    """Tag sem descrição vira só um cabeçalho solto no /docs."""
    app = _app()
    descritas = {t["name"] for t in (app.openapi_tags or [])}
    usadas = {tag for rota in _rotas_documentaveis() for tag in rota.tags}
    faltando = sorted(usadas - descritas)
    assert not faltando, "tag(s) usada(s) sem descrição em openapi_tags: %s" % ", ".join(
        faltando
    )


def test_schema_openapi_gera_sem_erro():
    """Anotação malformada só aparece na hora de montar o schema."""
    schema = _app().openapi()
    assert schema["info"]["title"]
    assert schema["paths"]


@pytest.mark.parametrize("campo", ["summary", "description"])
def test_documentacao_nao_e_placeholder(campo):
    """Pega TODO/TBD/lorem esquecido na documentação de rota."""
    # Marcador de pendência é MAIÚSCULO por convenção (TODO:, FIXME). Em
    # português "todo" significa "inteiro" e "xxx" aparece em máscara de dado,
    # então busca minúscula dá falso positivo e obriga a reescrever frase
    # correta — foi o que aconteceu enquanto este teste era case-insensitive.
    marcador = re.compile(r"\b(TODO|TBD|FIXME|HACK|LOREM)\b")
    rascunho = re.compile(
        r"(descrição da rota|preencher aqui|lorem ipsum|documentar depois)",
        re.IGNORECASE,
    )
    suspeitas = []
    for rota in _rotas_documentaveis():
        texto = (getattr(rota, campo) or "").strip()
        if marcador.search(texto) or rascunho.search(texto):
            suspeitas.append(f"{sorted(rota.methods)[0]} {rota.path}: {texto[:60]}")
    assert not suspeitas, "placeholder em %s:\n  %s" % (campo, "\n  ".join(suspeitas))
