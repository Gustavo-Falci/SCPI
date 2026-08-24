import datetime
import io
import logging
import zoneinfo
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import EmailStr
from starlette.concurrency import run_in_threadpool

from core.config import (
    BUCKET_NAME,
    POLITICA_PRIVACIDADE_VERSAO,
    SCPI_PRIVACY_URL,
)
from core.errors import ErrorCode, bad_request
from core.helpers import client_ip, gerar_url_presigned, internal_error, validate_image_upload
from core.limiter import limiter
from core.regras import ANGULOS_VALIDOS
from core.security import get_current_user, require_self_or_admin
from infra.aws_clientes import s3_client
from infra.rekognition_aws import deletar_rosto, indexar_rosto_da_imagem_s3
from repositories.alunos import (
    aluno_pertence_turma,
    buscar_aluno_por_usuario_id,
    buscar_dados_titular,
    listar_frequencias_por_aluno,
    obter_dashboard_aluno,
)
from repositories.chamadas import listar_historico_chamadas_aluno
from repositories.consentimentos import obter_ultimo_evento, registrar_evento
from repositories.horarios import listar_aulas_hoje_por_aluno
from repositories.rostos import (
    listar_rostos_ativos_por_aluno,
    obter_path_biometria_por_usuario,
    obter_rosto_por_angulo,
    revogar_rosto_por_aluno,
    upsert_rosto,
)
from repositories.turmas import obter_turma_basica
from repositories.usuarios import (
    buscar_usuario_id_por_email_simples,
    buscar_usuario_id_por_id,
)
from schemas.respostas.alunos import (
    DashboardDoAluno,
    DossieLGPD,
    EstadoDoConsentimento,
    FaceCadastrada,
    FotoDeBiometria,
    FrequenciasDoAluno,
    HistoricoDeChamadas,
    StatusDosAngulos,
)
from schemas.respostas.comum import MensagemResposta

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(tags=["alunos"])


@router.get(
    "/aluno/dashboard/{usuario_id}",
    summary="Resumo do dashboard do aluno",
    responses={200: {"model": DashboardDoAluno}},
)
def get_dashboard_aluno(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Devolve nome do aluno, frequência geral (%) e as aulas de hoje
    (conforme turno e dia da semana).

    Só o próprio aluno ou um Admin pode consultar (`require_self_or_admin`
    — mismatch devolve 404, não 403, para não confirmar a existência do
    recurso a quem não é dono). Devolve 404 se o `usuario_id` não tiver
    perfil de aluno. `frequencia_geral` é 0 quando não há chamadas ainda
    (evita divisão por zero).
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_dashboard_aluno(usuario_id)
        if not row or not row.get('aluno_id'):
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        nome = row['user_nome'] or "Aluno"
        aluno_id = row['aluno_id']
        aluno_turno = row['turno']
        total_presencas = row['total_presencas'] or 0
        total_chamadas = row['total_chamadas'] or 0
        frequencia = round((total_presencas / total_chamadas) * 100) if total_chamadas > 0 else 0

        dia_hoje = datetime.datetime.now(zoneinfo.ZoneInfo("America/Sao_Paulo")).weekday()
        aulas_hoje = listar_aulas_hoje_por_aluno(aluno_id, dia_hoje, aluno_turno)

        return {"nome": nome, "frequencia_geral": frequencia, "aulas_hoje": aulas_hoje}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get(
    "/aluno/frequencias/{usuario_id}",
    summary="Frequência do aluno por turma",
    responses={200: {"model": FrequenciasDoAluno}},
)
def get_frequencias_detalhadas(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Devolve a média geral de presença do aluno e o detalhamento por turma
    (percentual, total de aulas, presenças e faltas).

    Só o próprio aluno ou um Admin pode consultar (`require_self_or_admin`,
    404 em caso de acesso negado). Devolve 404 se o `usuario_id` não tiver
    perfil de aluno. Percentuais são 0 quando a turma ainda não teve
    nenhuma aula (evita divisão por zero).
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        aluno_id = aluno['aluno_id']
        rows = listar_frequencias_por_aluno(aluno_id)

        frequencias = []
        total_presencas_global = 0
        total_chamadas_global = 0

        for row in rows:
            presencas = row['presencas']
            total = row['total_aulas']
            percentual = round((presencas / total * 100)) if total > 0 else 0

            frequencias.append({
                "turma_id": row['turma_id'],
                "codigo_turma": row['codigo_turma'],
                "nome": row['nome'],
                "presenca": percentual,
                "total": total,
                "presencas_count": presencas,
                "faltas_count": total - presencas,
            })

            total_presencas_global += presencas
            total_chamadas_global += total

        media_geral = round((total_presencas_global / total_chamadas_global * 100)) if total_chamadas_global > 0 else 0

        return {"media_geral": media_geral, "frequencias": frequencias}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get(
    "/aluno/historico-chamadas/{usuario_id}",
    summary="Histórico de chamadas do aluno numa turma",
    responses={200: {"model": HistoricoDeChamadas}},
)
def get_historico_chamadas_aluno(
    usuario_id: str,
    turma_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Devolve o histórico de chamadas do aluno numa turma específica
    (`turma_id` via query string): totais de aulas/presenças/ausências,
    contagem de chamadas parciais (presente em algumas aulas do slot, não
    em todas) e a lista de chamadas com dia da semana calculado.

    Só o próprio aluno ou um Admin pode consultar (`require_self_or_admin`,
    404 em caso de acesso negado). Devolve 404 se o aluno não existir ou se
    a turma não existir/o aluno não pertencer a ela (`aluno_pertence_turma`)
    — mesma mensagem genérica nos dois casos.
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")
        aluno_id = aluno["aluno_id"]

        if not aluno_pertence_turma(turma_id, aluno_id):
            raise HTTPException(status_code=404, detail="Turma não encontrada.")

        turma = obter_turma_basica(turma_id)
        rows = listar_historico_chamadas_aluno(aluno_id, turma_id)

        DIAS = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb", 7: "Dom"}
        chamadas = [
            {**dict(r), "dia_semana": DIAS.get(r["dia_iso"], "")}
            for r in rows
        ]

        total_slots = sum(c.get("total_aulas", 1) for c in chamadas)
        presentes_slots = sum(c.get("aulas_presentes_count", 0) for c in chamadas)
        parciais = sum(
            1 for c in chamadas
            if 0 < c.get("aulas_presentes_count", 0) < c.get("total_aulas", 1)
        )
        return {
            "turma_id": turma_id,
            "nome_disciplina": turma["nome_disciplina"],
            "codigo_turma": turma["codigo_turma"],
            "total": total_slots,
            "presentes": presentes_slots,
            "ausentes": total_slots - presentes_slots,
            "parciais": parciais,
            "percentual": round(presentes_slots / total_slots * 100) if total_slots > 0 else 0,
            "chamadas": chamadas,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "get_historico_chamadas_aluno")


def validar_consentimento(consentimento_biometrico, politica_versao):
    """Rejeita cadastro sem aceite ou com versão de política divergente.

    Versão divergente = o aluno leu um texto que não é o vigente. Aceitar aqui
    reproduziria a lacuna que este campo existe para fechar.
    """
    if not consentimento_biometrico:
        raise bad_request(ErrorCode.CONSENTIMENTO_OBRIGATORIO)
    if politica_versao != POLITICA_PRIVACIDADE_VERSAO:
        raise bad_request(ErrorCode.POLITICA_DESATUALIZADA)


def registrar_aceite_se_novo(aluno_id, politica_versao, ip, user_agent):
    """Grava 'aceite' só quando o estado atual não é já um aceite desta versão.

    Um cadastro completo manda 4 ângulos; sem esta guarda a trilha vira 4
    aceites idênticos e deixa de ser legível. Um aluno vindo do backfill tem
    aceite 'legado' — a versão diferente força o registro versionado.
    """
    ultimo = obter_ultimo_evento(aluno_id)
    ja_aceito = (
        ultimo is not None
        and ultimo.get("evento") == "aceite"
        and ultimo.get("politica_versao") == politica_versao
    )
    if ja_aceito:
        return False
    registrar_evento(aluno_id, "aceite", politica_versao,
                     ip=ip, user_agent=user_agent, origem="app")
    return True


def _persistir_biometria(
    image_bytes: bytes,
    safe_basename: str,
    user_id: Optional[str],
    email: str,
    angulo: str,
    politica_versao: str,
    current_user: dict,
    ip: Optional[str],
    user_agent: Optional[str],
) -> dict:
    """Parte bloqueante do cadastro de face: queries, S3 e Rekognition.

    Vive fora do endpoint async porque psycopg2 e boto3 são síncronos — rodando
    no corpo da corrotina, um upload de foto mais o IndexFaces (centenas de ms
    de rede) travam o event loop do worker inteiro.
    """
    if user_id:
        user = buscar_usuario_id_por_id(user_id)
    else:
        user = buscar_usuario_id_por_email_simples(email)

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não localizado para vincular face.")

    target_user_id = user['usuario_id']

    if current_user.get("role") == "Aluno" and str(target_user_id) != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Aluno só pode cadastrar a própria face.")
    if current_user.get("role") not in {"Aluno", "Admin"}:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    # aluno_id resolvido ANTES do upload: além de ser o identificador da
    # biometria, evita gastar upload no S3 e IndexFaces quando o perfil de
    # aluno nem existe.
    aluno = buscar_aluno_por_usuario_id(target_user_id)
    if not aluno:
        raise HTTPException(status_code=404, detail="Perfil de aluno não encontrado para este usuário.")

    aluno_id = aluno['aluno_id']

    # ExternalImageId = aluno_id, não o nome: dois alunos homônimos geravam
    # o mesmo id e a presença caía no aluno errado. De quebra tira o nome
    # dos metadados da collection e do caminho no S3 (minimização LGPD).
    external_id = str(aluno_id)
    filename = f"alunos/{external_id}/{safe_basename}"

    # Upload direto da memória — sem arquivo temporário em disco (evita race,
    # escrita em CWD não-gravável e leak por crash entre write e remove).
    s3_client.upload_fileobj(io.BytesIO(image_bytes), BUCKET_NAME, filename)

    resultado_rekognition = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

    if not resultado_rekognition or not resultado_rekognition.get("FaceRecords"):
        raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

    face_id = resultado_rekognition["FaceRecords"][0]["Face"]["FaceId"]

    # Captura o rosto anterior deste ângulo ANTES do upsert sobrescrever o
    # ponteiro. Sem isso o FaceId/objeto S3 antigos ficam órfãos e a
    # collection do Rekognition acumula (aluno acaba com 8 faces após
    # re-cadastrar os 4 ângulos).
    rosto_anterior = obter_rosto_por_angulo(aluno_id, angulo)

    upsert_rosto(aluno_id, external_id, face_id, filename, angulo)

    registrar_aceite_se_novo(
        aluno_id,
        politica_versao,
        ip=ip,
        user_agent=user_agent,
    )

    # Remove o rosto antigo só depois do novo estar indexado e persistido —
    # se o index acima falhasse, a biometria anterior permaneceria intacta.
    # Best-effort: falha na limpeza não invalida o cadastro bem-sucedido.
    if rosto_anterior:
        old_face_id = rosto_anterior.get("face_id_rekognition")
        old_s3_path = rosto_anterior.get("s3_path_cadastro")
        if old_face_id and old_face_id != face_id:
            try:
                deletar_rosto(old_face_id)
            except Exception as e:
                logger.warning("Falha ao deletar FaceId antigo %s (angulo=%s): %s", old_face_id, angulo, e)
        if old_s3_path and old_s3_path != filename:
            try:
                s3_client.delete_object(Bucket=BUCKET_NAME, Key=old_s3_path)
            except Exception as e:
                logger.warning("Falha ao deletar objeto S3 antigo %s (angulo=%s): %s", old_s3_path, angulo, e)

    audit_logger.info(
        "Biometria cadastrada aluno=%s angulo=%s por=%s ip=%s",
        target_user_id, angulo, current_user.get("sub"), ip,
    )
    return {"status": "sucesso", "face_id": face_id, "external_id": external_id, "angulo": angulo}


@router.post(
    "/alunos/cadastrar-face",
    summary="Cadastra um ângulo de biometria facial do aluno",
    responses={200: {"model": FaceCadastrada}},
)
@limiter.limit("10/minute")
async def cadastrar_aluno_api(
    request: Request,
    user_id: Optional[str] = Form(None),
    nome: str = Form(..., min_length=3, max_length=100),
    email: EmailStr = Form(...),
    ra: str = Form(..., pattern=r"^[A-Za-z0-9]{4,20}$"),
    foto: UploadFile = File(...),
    consentimento_biometrico: bool = Form(...),
    politica_versao: str = Form(...),
    angulo: str = Form("frontal"),
    current_user: dict = Depends(get_current_user),
):
    """Recebe uma foto (um `angulo` — padrão "frontal") e cadastra a
    biometria facial do aluno: sobe a imagem para o S3, indexa no AWS
    Rekognition e grava o vínculo no banco.

    Exige `consentimento_biometrico=true` e `politica_versao` igual à
    vigente (`POLITICA_PRIVACIDADE_VERSAO`) — devolve 400
    `CONSENTIMENTO_OBRIGATORIO`/`POLITICA_DESATUALIZADA` caso contrário.
    Aluno só pode cadastrar a própria face (403 se tentar cadastrar de
    outro usuário); Admin pode cadastrar de qualquer aluno (via
    `user_id`/`email` no form). `angulo` fora de `ANGULOS_VALIDOS` devolve
    400. Imagem é validada por magic bytes reais, não só content-type
    (`validate_image_upload`), limite de 5 MB. Devolve 400 "Nenhum rosto
    detectado na imagem." se o Rekognition não achar face.

    `ExternalImageId` no Rekognition é o `aluno_id` (UUID), nunca o nome —
    evita colisão entre alunos homônimos e tira dado pessoal da collection.
    Recadastrar o mesmo ângulo substitui o FaceId/objeto S3 anterior
    (best-effort: falha ao apagar o antigo não desfaz o cadastro novo).
    Também registra o aceite de consentimento LGPD na trilha append-only
    (só grava evento novo se o último aceite não for já desta versão — evita
    4 aceites idênticos ao cadastrar os 4 ângulos de uma vez). Roda em
    threadpool (`run_in_threadpool`): psycopg2 e boto3 são síncronos e um
    IndexFaces trava o event loop se rodar direto na corrotina.
    """
    validar_consentimento(consentimento_biometrico, politica_versao)

    if angulo not in ANGULOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Ângulo inválido. Use um de: {sorted(ANGULOS_VALIDOS)}")

    image_bytes = await validate_image_upload(foto)

    ext = ".jpg" if foto.content_type in {"image/jpeg", "image/jpg"} else ".png"
    safe_basename = f"{uuid.uuid4().hex}{ext}"

    # Request não atravessa o threadpool: ip e user-agent são lidos aqui e vão
    # como valores. Ler do Request numa thread é o tipo de acoplamento que
    # quebra silenciosamente quando o Starlette muda o ciclo de vida do escopo.
    try:
        return await run_in_threadpool(
            _persistir_biometria,
            image_bytes,
            safe_basename,
            user_id,
            email,
            angulo,
            politica_versao,
            current_user,
            client_ip(request),
            request.headers.get("user-agent") if request else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "cadastrar_aluno_api")


@router.get(
    "/aluno/biometria-foto/{usuario_id}",
    summary="URL temporária da foto de biometria cadastrada",
    responses={200: {"model": FotoDeBiometria}},
)
def obter_foto_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna URL temporária (presigned, 300s) da foto cadastrada — só dono ou Admin."""
    require_self_or_admin(usuario_id, current_user)
    try:
        row = obter_path_biometria_por_usuario(usuario_id)
        if not row or not row.get("s3_path_cadastro"):
            raise HTTPException(status_code=404, detail="Biometria não encontrada.")
        url = gerar_url_presigned(row["s3_path_cadastro"])
        if not url:
            raise HTTPException(status_code=500, detail="Falha ao gerar URL temporária.")
        return {"url": url, "expira_em_segundos": 300}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "obter_foto_biometria")


@router.get(
    "/alunos/status-angulos-face/{usuario_id}",
    summary="Ângulos de biometria já cadastrados pelo aluno",
    responses={200: {"model": StatusDosAngulos}},
)
def status_angulos_face(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna quais ângulos já foram cadastrados para o aluno (`total`,
    lista `angulos_cadastrados` e `completo` quando há 4 ou mais rostos
    ativos — o cadastro multi-ângulo padrão). Só dono ou Admin
    (`require_self_or_admin`, 404 em acesso negado); 404 se o `usuario_id`
    não tiver perfil de aluno.
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")
        rostos = listar_rostos_ativos_por_aluno(aluno["aluno_id"])
        angulos_cadastrados = [r["angulo"] for r in rostos]
        return {
            "total": len(rostos),
            "angulos_cadastrados": angulos_cadastrados,
            "completo": len(rostos) >= 4,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "status_angulos_face")


@router.get(
    "/aluno/consentimento/{usuario_id}",
    summary="Estado do consentimento LGPD do aluno",
    responses={200: {"model": EstadoDoConsentimento}},
)
def consentimento_estado(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Estado do consentimento para o card do perfil do aluno: `"nunca"`
    (nenhum evento na trilha), `"ativo"` (último evento é aceite) ou
    `"revogado"` (último evento é revogação) — derivado do último registro
    da trilha append-only (`obter_ultimo_evento`), não de uma coluna de
    estado. Também devolve a versão da política aceita, quando foi
    registrada, os ângulos de biometria ativos e a política vigente
    (`POLITICA_PRIVACIDADE_VERSAO`/`SCPI_PRIVACY_URL`) para o front comparar.
    Só dono ou Admin (`require_self_or_admin`, 404 em acesso negado); 404 se
    o `usuario_id` não tiver perfil de aluno.
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        ultimo = obter_ultimo_evento(aluno["aluno_id"])
        rostos = listar_rostos_ativos_por_aluno(aluno["aluno_id"])

        if ultimo is None:
            estado = "nunca"
        elif ultimo["evento"] == "aceite":
            estado = "ativo"
        else:
            estado = "revogado"

        registrado_em = ultimo["registrado_em"] if ultimo else None
        return {
            "estado": estado,
            "politica_versao": ultimo["politica_versao"] if ultimo else None,
            "registrado_em": registrado_em.isoformat() if registrado_em else None,
            "angulos_cadastrados": [r["angulo"] for r in rostos],
            "politica_vigente": {
                "versao": POLITICA_PRIVACIDADE_VERSAO,
                "url": SCPI_PRIVACY_URL,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "consentimento_estado")


@router.delete(
    "/aluno/biometria/{usuario_id}",
    summary="Revoga consentimento e apaga a biometria do aluno",
    responses={200: {"model": MensagemResposta}},
)
def revogar_biometria(
    usuario_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Permite ao aluno (ou Admin) revogar consentimento e apagar a
    biometria facial.

    Só dono ou Admin (`require_self_or_admin`, 404 em acesso negado). 404 se
    o aluno não existir ou não houver biometria ativa cadastrada. Apaga cada
    rosto (todos os ângulos) do Rekognition e do objeto correspondente no
    S3 — falha em qualquer uma dessas exclusões é só logada (best-effort),
    não interrompe o processo. Marca os rostos como revogados no banco
    (`revogar_rosto_por_aluno`) e grava evento `"revogacao"` na trilha
    append-only de consentimento LGPD, com `origem` `"app"` (o próprio
    aluno) ou `"admin"`. Isto apaga só a BIOMETRIA — não exclui o aluno nem
    o usuário; a exclusão de aluno é bloqueada pelo banco enquanto houver
    consentimento registrado (ver `ConsentimentosLGPD`), rota separada, fora
    deste arquivo.
    """
    require_self_or_admin(usuario_id, current_user)
    try:
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        rostos = listar_rostos_ativos_por_aluno(aluno["aluno_id"])
        if not rostos:
            raise HTTPException(status_code=404, detail="Nenhuma biometria ativa para este aluno.")

        for rosto in rostos:
            try:
                deletar_rosto(rosto["face_id_rekognition"])
            except Exception as e:
                logger.warning("Falha ao deletar face no Rekognition (angulo=%s): %s", rosto.get("angulo"), e)
            try:
                if rosto.get("s3_path_cadastro"):
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=rosto["s3_path_cadastro"])
            except Exception as e:
                logger.warning("Falha ao deletar objeto no S3 (angulo=%s): %s", rosto.get("angulo"), e)

        revogar_rosto_por_aluno(aluno["aluno_id"])

        origem = "app" if current_user.get("sub") == usuario_id else "admin"
        registrar_evento(
            aluno["aluno_id"], "revogacao", POLITICA_PRIVACIDADE_VERSAO,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
            origem=origem,
        )

        audit_logger.info("Biometria revogada usuario=%s por=%s", usuario_id, current_user.get("sub"))
        return {"mensagem": "Biometria revogada e removida com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "revogar_biometria")


# O default da rota é `formato=zip`, que devolve bytes — declarar só o JSON
# faria o /docs afirmar que ela nunca devolve pacote, e um cliente gerado do
# schema trataria o zip como JSON malformado. Mesmo padrão dos relatórios.
_CONTEUDO_ZIP = {"application/zip": {"schema": {"type": "string", "format": "binary"}}}


@router.get(
    "/aluno/meus-dados/{usuario_id}",
    summary="Exporta os dados pessoais do titular (LGPD)",
    responses={200: {"model": DossieLGPD, "content": _CONTEUDO_ZIP}},
)
def exportar_meus_dados(
    usuario_id: str,
    formato: str = "zip",
    current_user: dict = Depends(get_current_user),
):
    """Retorna dados pessoais do titular — LGPD Art. 18 §1 (direito de
    acesso/portabilidade).

    Query param ``formato``:
      - ``zip`` (default): pacote `.zip` (attachment) com PDF legível +
        JSON estruturado + foto(s) de biometria ativas + manifesto de
        integridade assinado por HMAC (`SCPI_EXPORT_HMAC_KEY`, obrigatória
        — o processo falha ao subir sem ela).
      - ``json``: retrocompatível, devolve só o JSON estruturado direto no
        corpo (sem PDF, foto nem manifesto).

    Só dono ou Admin (`require_self_or_admin`, 404 em acesso negado). 404 se
    não houver dados para o `usuario_id`. Baixar a(s) foto(s) do S3 é
    best-effort: falha ao baixar uma foto não interrompe a exportação (a
    foto simplesmente fica de fora do zip, com aviso em log). Toda
    solicitação é registrada em log de auditoria com quem pediu
    (`current_user`) e para qual titular.
    """
    from fastapi.responses import Response

    from core.config import SCPI_EXPORT_HMAC_KEY
    from infra.export_integridade import calcular_integridade
    from infra.export_pdf import gerar_pdf_dados
    from infra.export_zip import montar_zip_export

    require_self_or_admin(usuario_id, current_user)
    try:
        dados = buscar_dados_titular(usuario_id)
        if not dados:
            raise HTTPException(status_code=404, detail="Dados não encontrados para este usuário.")

        agora = datetime.datetime.now(tz=zoneinfo.ZoneInfo("America/Sao_Paulo"))
        dados["_schema_version"] = "1.0"
        dados["_gerado_em"] = agora.isoformat()

        audit_logger.info(
            "Export LGPD solicitado titular=%s por=%s formato=%s", usuario_id, current_user.get("sub"), formato
        )

        if formato == "json":
            return dados

        pdf_bytes = gerar_pdf_dados(dados)
        manifesto = calcular_integridade(dados, hmac_key=SCPI_EXPORT_HMAC_KEY)

        fotos: list[tuple[str, bytes]] = []
        aluno = buscar_aluno_por_usuario_id(usuario_id)
        if aluno:
            rostos = listar_rostos_ativos_por_aluno(aluno["aluno_id"])
            for rosto in rostos:
                s3_path = rosto.get("s3_path_cadastro")
                if not s3_path:
                    continue
                try:
                    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_path)
                    fotos.append((rosto["angulo"], obj["Body"].read()))
                except Exception as e:
                    logger.warning(
                        "Falha ao baixar foto S3 para export (path=%s): %s", s3_path, e
                    )

        zip_bytes = montar_zip_export(dados, pdf_bytes, manifesto, fotos=fotos)
        logger.info(
            "Export LGPD gerado para usuario=%s (zip=%d bytes, pdf=%d bytes, fotos=%d)",
            usuario_id, len(zip_bytes), len(pdf_bytes), len(fotos),
        )

        ra = dados.get("titular", {}).get("ra", "sem-ra")
        filename = f"meus-dados-scpi-{ra}-{agora.strftime('%Y%m%d-%H%M%S')}.zip"
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(zip_bytes)),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "exportar_meus_dados")
