"""Guarda da etapa B do Swagger: modelo de saída declarado e honesto.

A etapa A garantiu que toda rota TEM documentação; esta garante que a
documentação diz o que a rota DEVOLVE. O avanço era medido por uma lista que só
encolhe, `SEM_MODELO_DE_SAIDA` — e ela chegou a **vazia** no lote 5: toda rota
que devolve 200 declara o corpo. A lista fica no lugar como guarda: rota nova
sem modelo reprova aqui, e quem quiser adiar tem que escrever a linha, que é o
momento de perguntar se não dá para documentar logo.

Nada é declarado sem prova: a fidelidade de cada modelo está em
`tests/test_respostas_documentadas.py`, `test_respostas_mutacoes.py`,
`test_respostas_leituras.py` e `test_respostas_auth_e_imports.py`, que validam o
payload real da rota contra o modelo com `extra="forbid"`.
"""
import typing

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from tests.conformidade_respostas import modelo_declarado

_ROTAS_INTERNAS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}

# Rotas que ainda não declaram modelo de saída. ESTA LISTA SÓ ENCOLHE:
# documentar uma rota significa apagar a linha dela daqui. Acrescentar linha só
# faz sentido para rota realmente nova — e mesmo aí, prefira documentar.
SEM_MODELO_DE_SAIDA = set()

# Rotas que NUNCA devolvem 200 — não é dívida, é ausência de corpo. As duas
# estão desativadas e levantam 403 incondicionalmente; declarar modelo de saída
# nelas documentaria uma resposta que não existe. A isenção só se sustenta
# porque `tests/test_respostas_auth_e_imports.py` prova o 403 chamando os dois
# handlers: se um deles voltar a responder 200, aquele teste reprova.
ROTAS_SEM_200 = {
    "POST /auth/register",
    "POST /auth/register-aluno-com-face",
}

# `Token` é a única saída declarada por `response_model=`, de antes desta etapa.
# Fica fora do `extra="forbid"` de propósito: `response_model` VALIDA em
# runtime, e proibir campo extra ali transformaria documentação em erro no
# login. Modelo novo usa `responses={200: ...}`, que não valida nada em runtime.
_FORA_DO_EXTRA_FORBID = {"Token"}

# Fim do lote 5: a dívida zerou. Continua sendo fotografia, não meta — só que
# agora qualquer valor acima de zero significa rota nova sem modelo.
_DIVIDA_NO_FIM_DO_LOTE_5 = 0

LOTE_1 = [
    ("GET", "/"),
    ("GET", "/politica-privacidade"),
    ("GET", "/health"),
    ("GET", "/professor/dashboard/{usuario_id}"),
    ("GET", "/turmas/{usuario_id}"),
    ("GET", "/aluno/consentimento/{usuario_id}"),
    ("DELETE", "/aluno/biometria/{usuario_id}"),
    ("GET", "/chamadas/aberta/sala"),
    ("POST", "/chamadas/registrar_presenca_camera"),
    ("GET", "/professor/relatorios/filtros"),
    ("GET", "/admin/relatorios/filtros"),
    ("GET", "/admin/alunos"),
    ("GET", "/admin/rostos/inventario"),
]

LOTE_2 = [
    ("GET", "/professor/relatorios/chamadas"),
    ("GET", "/professor/relatorios/chamadas/{chamada_id}"),
    ("GET", "/professor/relatorios/turmas/{turma_id}/frequencia"),
    ("GET", "/admin/relatorios/chamadas"),
    ("GET", "/admin/relatorios/chamadas/{chamada_id}"),
    ("GET", "/admin/relatorios/turmas/{turma_id}/frequencia"),
]

# A família de mutações. Quinze delas devolvem só `MensagemResposta`; as seis
# restantes acrescentam o id que o backend gerou ou a contagem do lote.
LOTE_3 = [
    ("DELETE", "/admin/turmas/{turma_id}"),
    ("DELETE", "/admin/alunos/{aluno_id}"),
    ("DELETE", "/admin/professores/{professor_id}"),
    ("DELETE", "/admin/horarios/{horario_id}"),
    ("DELETE", "/admin/rostos/rekognition/bulk"),
    ("DELETE", "/admin/rostos/rekognition/{face_id}"),
    ("DELETE", "/admin/rostos/s3"),
    ("PATCH", "/admin/alunos/{aluno_id}"),
    ("PATCH", "/admin/professores/{professor_id}"),
    ("PATCH", "/admin/turmas/{turma_id}/professor"),
    ("POST", "/admin/horarios"),
    ("POST", "/admin/turmas"),
    ("POST", "/admin/turmas/{turma_id}/matricular-alunos"),
    ("POST", "/admin/turmas/{turma_id}/desmatricular-alunos"),
    ("POST", "/admin/usuarios/professor"),
    ("POST", "/admin/usuarios/aluno"),
    ("POST", "/chamadas/abrir"),
    ("POST", "/chamadas/fechar/{turma_id}"),
    ("POST", "/chamadas/{chamada_id}/ajustar"),
    ("POST", "/chamadas/{chamada_id}/finalizar"),
    ("POST", "/notificacoes/registrar-token"),
]

# As leituras que sobraram: listagens do portal Admin, telas do aluno, turma do
# professor, estado da chamada e sessão. A forma da resposta é a forma do
# SELECT — o que se documenta aqui é o contrato da consulta.
LOTE_4 = [
    ("GET", "/admin/professores"),
    ("GET", "/admin/turmas-completas"),
    ("GET", "/admin/horarios-todos"),
    ("GET", "/admin/turmas/{turma_id}/alunos"),
    ("GET", "/aluno/dashboard/{usuario_id}"),
    ("GET", "/aluno/frequencias/{usuario_id}"),
    ("GET", "/aluno/historico-chamadas/{usuario_id}"),
    ("GET", "/aluno/biometria-foto/{usuario_id}"),
    ("GET", "/alunos/status-angulos-face/{usuario_id}"),
    ("GET", "/turmas/{turma_id}/alunos"),
    ("GET", "/chamadas/status/{turma_id}"),
    ("GET", "/chamadas/{chamada_id}/alunos"),
    ("GET", "/auth/session"),
]

# O fecho da etapa B: auth, os três imports CSV, o cadastro de face e o dossiê
# LGPD. `/auth/register` e `/auth/register-aluno-com-face` não aparecem aqui —
# estão em `ROTAS_SEM_200`.
LOTE_5 = [
    ("POST", "/auth/refresh"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/alterar-senha"),
    ("POST", "/auth/alterar-senha-primeiro-acesso"),
    ("POST", "/auth/esqueci-senha"),
    ("POST", "/auth/verificar-codigo"),
    ("POST", "/auth/redefinir-senha"),
    ("POST", "/admin/importar-alunos"),
    ("POST", "/admin/importar-professores"),
    ("POST", "/admin/turmas/{turma_id}/importar-alunos"),
    ("POST", "/alunos/cadastrar-face"),
    ("GET", "/aluno/meus-dados/{usuario_id}"),
]


def _rotas_documentaveis():
    from api import app

    return [
        rota
        for rota in app.routes
        if isinstance(rota, APIRoute)
        and rota.path not in _ROTAS_INTERNAS
        and rota.include_in_schema
    ]


def _etiqueta(rota: APIRoute) -> str:
    return f"{sorted(rota.methods)[0]} {rota.path}"


def _modelo_de(rota: APIRoute):
    return (rota.responses.get(200) or {}).get("model") or rota.response_model


def _com_modelo():
    return {_etiqueta(r): _modelo_de(r) for r in _rotas_documentaveis() if _modelo_de(r)}


def _modelos_pydantic(anotacao):
    """Todo BaseModel alcançável a partir da anotação declarada.

    Nem todo 200 é um modelo solto: rota que devolve lista declara `list[X]`, e
    a listagem do professor declara a união do formato simples com o envelope
    do `paginado=1`. Sem desembrulhar, os guardas abaixo olhariam para
    `list`/`Union` — que não são BaseModel — e deixariam passar modelo sem
    `extra="forbid"` escondido lá dentro.
    """
    if isinstance(anotacao, type) and issubclass(anotacao, BaseModel):
        return {anotacao}
    achados = set()
    for parte in typing.get_args(anotacao):
        achados |= _modelos_pydantic(parte)
    return achados


def test_rota_sem_modelo_esta_declarada_na_lista():
    """Rota nova entra documentada ou entra na lista — nunca em silêncio."""
    sem_modelo = {_etiqueta(r) for r in _rotas_documentaveis() if not _modelo_de(r)}
    novas = sorted(sem_modelo - SEM_MODELO_DE_SAIDA - ROTAS_SEM_200)
    assert not novas, (
        "%d rota(s) sem modelo de saída e fora de SEM_MODELO_DE_SAIDA:\n  %s"
        % (len(novas), "\n  ".join(novas))
    )


def test_rota_sem_200_continua_sem_modelo():
    """A isenção vale nos dois sentidos.

    Declarar modelo numa rota que só levanta 403 documentaria corpo que nunca
    sai; e uma rota que voltasse a responder 200 precisa sair de `ROTAS_SEM_200`
    e ganhar modelo, não ficar isenta para sempre.
    """
    indevidas = sorted(ROTAS_SEM_200 & set(_com_modelo()))
    assert not indevidas, (
        "%d rota(s) de ROTAS_SEM_200 declaram modelo de 200:\n  %s"
        % (len(indevidas), "\n  ".join(indevidas))
    )


def test_rota_sem_200_ainda_existe():
    """Entrada órfã em ROTAS_SEM_200 isentaria uma rota que não existe mais."""
    todas = {_etiqueta(r) for r in _rotas_documentaveis()}
    orfas = sorted(ROTAS_SEM_200 - todas)
    assert not orfas, (
        "%d entrada(s) de ROTAS_SEM_200 sem rota correspondente:\n  %s"
        % (len(orfas), "\n  ".join(orfas))
    )


def test_a_lista_nao_tem_rota_ja_documentada():
    """A lista só encolhe: documentou, apaga a linha.

    Deixar a rota na lista depois de documentá-la faria o contador de dívida
    mentir para cima, e o próximo lote começaria pelo trabalho já feito.
    """
    resolvidas = sorted(SEM_MODELO_DE_SAIDA & set(_com_modelo()))
    assert not resolvidas, (
        "%d rota(s) já declaram modelo — apague de SEM_MODELO_DE_SAIDA:\n  %s"
        % (len(resolvidas), "\n  ".join(resolvidas))
    )


def test_a_lista_nao_tem_rota_que_sumiu():
    """Entrada órfã esconde dívida que não existe mais e falseia a contagem."""
    todas = {_etiqueta(r) for r in _rotas_documentaveis()}
    orfas = sorted(SEM_MODELO_DE_SAIDA - todas)
    assert not orfas, (
        "%d entrada(s) de SEM_MODELO_DE_SAIDA sem rota correspondente:\n  %s"
        % (len(orfas), "\n  ".join(orfas))
    )


def test_todo_modelo_declarado_alcanca_um_pydantic():
    """Anotação que não chega a nenhum BaseModel não descreve corpo nenhum."""
    errados = [
        f"{etiqueta}: {modelo!r}"
        for etiqueta, modelo in _com_modelo().items()
        if not _modelos_pydantic(modelo)
    ]
    assert not errados, "modelo de saída que não é BaseModel:\n  %s" % "\n  ".join(
        errados
    )


def test_modelo_novo_proibe_campo_extra():
    """`extra="forbid"` é o que faz o guarda de fidelidade pegar campo não documentado."""
    frouxos = [
        f"{etiqueta}: {modelo.__name__}"
        for etiqueta, anotacao in _com_modelo().items()
        for modelo in sorted(_modelos_pydantic(anotacao), key=lambda m: m.__name__)
        if modelo.__name__ not in _FORA_DO_EXTRA_FORBID
        and modelo.model_config.get("extra") != "forbid"
    ]
    assert not frouxos, (
        "modelo de saída sem extra='forbid' (herde RespostaBase):\n  %s"
        % "\n  ".join(frouxos)
    )


def test_schema_openapi_descreve_o_corpo_das_rotas_documentadas():
    """O modelo tem que chegar ao /docs, não só ao decorador.

    `responses={200: {"model": X}}` que não vira `content` no schema
    significaria Swagger mostrando "Successful Response" vazio — documentação
    que não documenta.
    """
    from api import app

    schema = app.openapi()
    mudos = []
    for etiqueta in _com_modelo():
        metodo, caminho = etiqueta.split(" ", 1)
        resposta = schema["paths"][caminho][metodo.lower()]["responses"]["200"]
        if not resposta.get("content", {}).get("application/json", {}).get("schema"):
            mudos.append(etiqueta)
    assert not mudos, "200 sem schema no OpenAPI:\n  %s" % "\n  ".join(mudos)


def test_divida_restante_e_a_esperada():
    assert len(SEM_MODELO_DE_SAIDA) == _DIVIDA_NO_FIM_DO_LOTE_5


@pytest.mark.parametrize("metodo,caminho", LOTE_1 + LOTE_2 + LOTE_3 + LOTE_4 + LOTE_5)
def test_lote_ja_fechado_continua_declarado(metodo, caminho):
    """Trava os lotes fechados: remover o modelo de uma destas rotas reprova aqui."""
    assert modelo_declarado(metodo, caminho) is not None
