import datetime
import io
import logging
import zoneinfo
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import EmailStr

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
from core.utils import formatar_nome_para_external_id
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

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(tags=["alunos"])


@router.get("/aluno/dashboard/{usuario_id}")
def get_dashboard_aluno(usuario_id: str, current_user: dict = Depends(get_current_user)):
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


@router.get("/aluno/frequencias/{usuario_id}")
def get_frequencias_detalhadas(usuario_id: str, current_user: dict = Depends(get_current_user)):
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


@router.get("/aluno/historico-chamadas/{usuario_id}")
def get_historico_chamadas_aluno(
    usuario_id: str,
    turma_id: str,
    current_user: dict = Depends(get_current_user),
):
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


@router.post("/alunos/cadastrar-face")
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
    """Recebe dados e foto do App, salva no S3, indexa no Rekognition e salva no Banco."""
    validar_consentimento(consentimento_biometrico, politica_versao)

    if angulo not in ANGULOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Ângulo inválido. Use um de: {sorted(ANGULOS_VALIDOS)}")

    image_bytes = await validate_image_upload(foto)

    ext = ".jpg" if foto.content_type in {"image/jpeg", "image/jpg"} else ".png"
    safe_basename = f"{uuid.uuid4().hex}{ext}"

    try:
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

        external_id = formatar_nome_para_external_id(nome)
        filename = f"alunos/{external_id}_{safe_basename}"

        # Upload direto da memória — sem arquivo temporário em disco (evita race,
        # escrita em CWD não-gravável e leak por crash entre write e remove).
        s3_client.upload_fileobj(io.BytesIO(image_bytes), BUCKET_NAME, filename)

        resultado_rekognition = indexar_rosto_da_imagem_s3(filename, external_id, detection_attributes="ALL")

        if not resultado_rekognition or not resultado_rekognition.get("FaceRecords"):
            raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem.")

        face_id = resultado_rekognition["FaceRecords"][0]["Face"]["FaceId"]

        aluno = buscar_aluno_por_usuario_id(target_user_id)
        if not aluno:
            raise HTTPException(status_code=404, detail="Perfil de aluno não encontrado para este usuário.")

        aluno_id = aluno['aluno_id']

        # Captura o rosto anterior deste ângulo ANTES do upsert sobrescrever o
        # ponteiro. Sem isso o FaceId/objeto S3 antigos ficam órfãos e a
        # collection do Rekognition acumula (aluno acaba com 8 faces após
        # re-cadastrar os 4 ângulos).
        rosto_anterior = obter_rosto_por_angulo(aluno_id, angulo)

        upsert_rosto(aluno_id, external_id, face_id, filename, angulo)

        registrar_aceite_se_novo(
            aluno_id,
            politica_versao,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent") if request else None,
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
            target_user_id, angulo, current_user.get("sub"), client_ip(request),
        )
        return {"status": "sucesso", "face_id": face_id, "external_id": external_id, "angulo": angulo}

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "cadastrar_aluno_api")


@router.get("/aluno/biometria-foto/{usuario_id}")
def obter_foto_biometria(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna URL temporária (presigned) da foto cadastrada — só dono ou Admin."""
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


@router.get("/alunos/status-angulos-face/{usuario_id}")
def status_angulos_face(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Retorna quais ângulos já foram cadastrados para o aluno."""
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


@router.get("/aluno/consentimento/{usuario_id}")
def consentimento_estado(usuario_id: str, current_user: dict = Depends(get_current_user)):
    """Estado do consentimento para o card do perfil do aluno."""
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


@router.delete("/aluno/biometria/{usuario_id}")
def revogar_biometria(
    usuario_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Permite ao aluno (ou Admin) revogar consentimento e apagar biometria."""
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


@router.get("/aluno/meus-dados/{usuario_id}")
def exportar_meus_dados(
    usuario_id: str,
    formato: str = "zip",
    current_user: dict = Depends(get_current_user),
):
    """Retorna dados pessoais do titular — LGPD Art. 18 §1.

    Query param ``formato``:
      - ``zip`` (default): pacote com PDF + JSON + foto + manifesto de integridade.
      - ``json``: retrocompatível, retorna apenas o JSON estruturado.
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
