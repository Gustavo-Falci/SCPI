import logging
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from core.auth_utils import get_password_hash
from core.config import BUCKET_NAME, COLLECTION_ID
from core.csv_utils import EMAIL_REGEX, MAX_CSV_BYTES, criar_leitor_csv, validar_celula_csv
from core.helpers import audit, client_ip, gerar_senha_temporaria, internal_error
from core.security import require_role
from infra.aws_clientes import rekognition_client, s3_client
from infra.rekognition_aws import deletar_rosto, listar_todas_faces
from infra.s3_aws import listar_todos_objetos_s3
from infra.notificacoes import send_email_senha_temporaria
from services.inventario_biometrico import reconciliar_inventario
from repositories.alunos import (
    LIMITE_PAGINA,
    atualizar_aluno,
    contar_alunos_pendentes,
    criar_aluno_com_usuario,
    excluir_aluno_em_cascata,
    existe_aluno_por_ra,
    listar_alunos_para_admin,
    listar_alunos_por_ids,
)
from repositories.rostos import listar_inventario_biometrico, listar_rostos_ativos_por_aluno
from repositories.horarios import (
    detectar_conflito_horario,
    excluir_horario,
    inserir_horario,
    listar_horarios_completos,
)
from repositories.professores import (
    atualizar_professor,
    buscar_usuario_id_por_professor_id,
    criar_professor_com_usuario,
    excluir_professor_em_cascata,
    importar_professor_csv,
    listar_professores_para_admin,
)
from repositories.turmas import (
    atribuir_professor_turma,
    criar_turma,
    desmatricular_alunos_da_turma,
    excluir_turma_em_cascata,
    listar_alunos_da_turma,
    listar_turmas_completas,
    matricular_alunos_em_turma,
    obter_turno_turma,
)
from repositories.usuarios import buscar_usuario_por_email
from services.import_alunos import processar_csv_alunos
from schemas.admin import (
    AtribuirProfessor,
    AtualizarAlunoAdmin,
    AtualizarProfessorAdmin,
    CriarAlunoAdmin,
    CriarProfessorAdmin,
    HorarioCreate,
    MatricularAlunos,
    TurmaCreate,
)
from schemas.respostas.admin import (
    AlunoCriado,
    AlunosPaginados,
    InventarioBiometrico,
    MatriculaAplicada,
    ProfessorCriado,
    TurmaCriada,
)
from schemas.respostas.comum import MensagemResposta

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("Admin"))])


@router.get("/professores", summary="Listar professores")
def admin_listar_professores():
    """Lista todos os professores cadastrados, ordenados por nome.

    Devolve uma lista de objetos com `professor_id`, `nome` e `email`.
    """
    try:
        return listar_professores_para_admin()
    except Exception as e:
        raise internal_error(e)


@router.get("/turmas-completas", summary="Listar turmas com professor e total de alunos")
def admin_listar_turmas():
    """Lista todas as turmas cadastradas, ordenadas por semestre e disciplina.

    Devolve `turma_id`, `nome_disciplina`, `codigo_turma`, `turno`, `semestre`,
    `periodo_letivo`, `professor_nome` (texto "Sem professor" quando a turma
    não tem professor atribuído) e `total_alunos` (contagem de matrículas).
    """
    try:
        return listar_turmas_completas()
    except Exception as e:
        raise internal_error(e)


@router.get("/turmas/{turma_id}/alunos", summary="Listar alunos matriculados na turma")
def admin_listar_alunos_turma(turma_id: str):
    """Lista os alunos matriculados na turma, ordenados por nome.

    Devolve uma lista de objetos com `aluno_id`, `nome`, `email` e `ra`.
    Turma inexistente não gera 404: devolve lista vazia, pois a consulta
    simplesmente não encontra matrículas para o id informado.
    """
    try:
        alunos = listar_alunos_da_turma(turma_id)
        return [
            {
                "aluno_id": a["id"],
                "nome": a["nome"],
                "email": a["email"],
                "ra": a["ra"],
            }
            for a in alunos
        ]
    except Exception as e:
        raise internal_error(e)


@router.post(
    "/turmas",
    summary="Criar turma",
    responses={200: {"model": TurmaCriada}},
)
def admin_criar_turma(turma: TurmaCreate, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Cria uma turma nova, com `professor_id` opcional (turma pode nascer sem professor).

    Gera o `turma_id` (UUID) no próprio backend. Devolve `mensagem` e o
    `turma_id` criado. `codigo_turma` duplicado vira 409 (constraint
    `turmas_codigo_turma_key`, tratada em `core/helpers.py`).
    """
    try:
        turma_id = str(uuid.uuid4())
        professor_id = turma.professor_id if turma.professor_id else None
        criar_turma(
            turma_id,
            professor_id,
            turma.codigo_turma,
            turma.nome_disciplina,
            turma.periodo_letivo,
            turma.sala_padrao,
            turma.turno,
            turma.semestre,
        )
        audit("Turma criada", admin=current_user.get("sub"), turma_id=turma_id,
              codigo=turma.codigo_turma, ip=client_ip(request))
        return {"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}
    except Exception as e:
        raise internal_error(e, "admin_criar_turma")


@router.patch(
    "/turmas/{turma_id}/professor",
    summary="Atribuir ou remover professor da turma",
    responses={200: {"model": MensagemResposta}},
)
def admin_atribuir_professor(turma_id: str, dados: AtribuirProfessor, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Define o professor responsável pela turma.

    `professor_id` nulo ou ausente desassocia a turma de qualquer professor
    (fica "Sem professor"). Devolve `mensagem`; 404 se a turma não existir.
    """
    try:
        professor_id = dados.professor_id if dados.professor_id else None
        rowcount = atribuir_professor_turma(turma_id, professor_id)
        if rowcount == 0:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        audit("Professor atribuído à turma", admin=current_user.get("sub"),
              turma_id=turma_id, professor_id=professor_id, ip=client_ip(request))
        return {"mensagem": "Professor atribuído com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_atribuir_professor")


@router.post(
    "/horarios",
    summary="Adicionar horário de aula",
    responses={200: {"model": MensagemResposta}},
)
def admin_adicionar_horario(h: HorarioCreate, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Cria um horário (dia da semana + faixa de hora + sala) para uma turma.

    Rejeita `horario_fim <= horario_inicio` com 400. Antes de inserir, verifica
    conflito de agenda contra horários existentes que se sobrepõem no mesmo dia:
    mesma turma, mesma sala, ou mesmo professor (via `professor_id` da turma).
    Conflito devolve 409 com o motivo (`turma`, `sala` ou `professor`) e os
    dados da aula conflitante na mensagem. Sem corpo de retorno estruturado
    além de `mensagem`.
    """
    try:
        if h.horario_fim <= h.horario_inicio:
            raise HTTPException(status_code=400, detail="Horário de fim deve ser maior que o de início.")
        conflito = detectar_conflito_horario(
            h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala
        )
        if conflito:
            dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            dia_nome = dias[h.dia_semana] if 0 <= h.dia_semana < 7 else f"dia {h.dia_semana}"
            motivo_msg = {
                "turma": "esta turma já tem aula",
                "sala": f"a sala {conflito['sala']} já está ocupada",
                "professor": "o professor já tem aula",
            }.get(conflito["motivo"], "já existe aula")
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Conflito de horário: {motivo_msg} na {dia_nome} "
                    f"das {conflito['inicio']} às {conflito['fim']} "
                    f"({conflito['nome_disciplina']} — {conflito['codigo_turma']})."
                ),
            )
        inserir_horario(h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala)
        audit("Horário adicionado", admin=current_user.get("sub"), turma_id=h.turma_id,
              dia=h.dia_semana, inicio=h.horario_inicio, fim=h.horario_fim, ip=client_ip(request))
        return {"mensagem": "Horário adicionado com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_adicionar_horario")


@router.delete(
    "/turmas/{turma_id}",
    summary="Excluir turma",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_turma(turma_id: str, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Exclui a turma e tudo que depende dela.

    Apaga manualmente `horarios_aulas` e as matrículas (`Turma_Alunos`); a
    exclusão da própria turma então dispara `ON DELETE CASCADE` no banco sobre
    `Chamadas` e, em cadeia, sobre `Presencas` da turma — ou seja, o
    histórico inteiro de chamadas e presenças da turma é apagado junto, sem
    aviso separado. Não valida se a turma existe: `turma_id` inexistente também
    devolve `mensagem` de sucesso (nenhuma linha é afetada, mas não há erro).
    """
    try:
        excluir_turma_em_cascata(turma_id)
        audit("Turma excluída", admin=current_user.get("sub"), turma_id=turma_id, ip=client_ip(request))
        return {"mensagem": "Turma e dependências excluídas com sucesso!"}
    except Exception as e:
        raise internal_error(e, "admin_excluir_turma")


@router.patch(
    "/alunos/{aluno_id}",
    summary="Atualizar dados do aluno",
    responses={200: {"model": MensagemResposta}},
)
def admin_atualizar_aluno(aluno_id: str, dados: AtualizarAlunoAdmin, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Atualiza nome, email, RA e/ou turno do aluno — todos os campos opcionais, só
    os enviados são alterados.

    Antes de gravar, confere se o novo email ou RA já pertence a *outro*
    usuário/aluno (400 "Email já cadastrado."/"RA já cadastrado." se sim; o
    próprio dono pode reenviar seu email/RA atual sem erro). 404 se o aluno
    não existir. Devolve só `mensagem`.
    """
    try:
        if dados.email is not None:
            from repositories.usuarios import buscar_usuario_por_email
            existente = buscar_usuario_por_email(dados.email.strip())
            if existente and existente.get("usuario_id"):
                from repositories.alunos import buscar_usuario_id_por_aluno_id
                row = buscar_usuario_id_por_aluno_id(aluno_id)
                if not row or row["usuario_id"] != existente["usuario_id"]:
                    raise HTTPException(status_code=400, detail="Email já cadastrado.")
        if dados.ra is not None:
            if existe_aluno_por_ra(dados.ra):
                from repositories.alunos import buscar_aluno_id_por_ra
                ra_aluno_id = buscar_aluno_id_por_ra(dados.ra)
                if ra_aluno_id != aluno_id:
                    raise HTTPException(status_code=400, detail="RA já cadastrado.")
        resultado = atualizar_aluno(
            aluno_id,
            nome=dados.nome,
            email=dados.email.strip() if dados.email else None,
            ra=dados.ra,
            turno=dados.turno,
        )
        if not resultado:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")
        audit("Aluno atualizado", admin=current_user.get("sub"), aluno_id=aluno_id, ip=client_ip(request))
        return {"mensagem": "Aluno atualizado com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_atualizar_aluno")


@router.delete(
    "/alunos/{aluno_id}",
    summary="Excluir aluno e biometria associada",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_aluno(aluno_id: str, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Exclui o aluno e sua biometria, nesta ordem: primeiro tenta remover cada
    rosto ativo do Rekognition e o objeto correspondente no S3 (best-effort —
    falha em qualquer um dos dois só gera log de warning, não interrompe a
    exclusão); depois apaga em cascata no banco `Colecao_Rostos`,
    `Turma_Alunos`, `Presencas`, `Alunos` e `Usuarios`. 404 se o aluno não
    existir. Devolve só `mensagem`.

    Armadilha conhecida: a exclusão **não** apaga `ConsentimentosLGPD` (a
    trilha de consentimento é append-only por design, e a FK não declara
    `ON DELETE`). Qualquer aluno com biometria ativa tem uma linha nessa tabela
    (veio do backfill da migration), então o `DELETE` costuma falhar com
    400 `FOREIGN_KEY_VIOLATION` e a mensagem genérica "Referência inválida:
    um dos registros vinculados não existe." — sem mencionar consentimento.
    Ou seja, hoje o caminho comum do direito ao esquecimento (LGPD) está
    bloqueado por este endpoint.
    """
    try:
        rostos = listar_rostos_ativos_por_aluno(aluno_id)
        for rosto in rostos:
            try:
                deletar_rosto(rosto["face_id_rekognition"])
            except Exception as e:
                logger.warning("Falha Rekognition ao excluir aluno %s: %s", aluno_id, e)
            try:
                if rosto.get("s3_path_cadastro"):
                    s3_client.delete_object(Bucket=BUCKET_NAME, Key=rosto["s3_path_cadastro"])
            except Exception as e:
                logger.warning("Falha S3 ao excluir aluno %s: %s", aluno_id, e)

        usuario_id = excluir_aluno_em_cascata(aluno_id)
        if not usuario_id:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")

        audit("Aluno excluído", admin=current_user.get("sub"), aluno_id=aluno_id, ip=client_ip(request))
        return {"mensagem": "Aluno excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.patch(
    "/professores/{professor_id}",
    summary="Atualizar dados do professor",
    responses={200: {"model": MensagemResposta}},
)
def admin_atualizar_professor(
    professor_id: str,
    dados: AtualizarProfessorAdmin,
    request: Request,
    current_user: dict = Depends(require_role("Admin")),
):
    """Atualiza nome e/ou email do professor — ambos opcionais, só os
    enviados são alterados.

    Confere se o novo email já pertence a *outro* usuário antes de gravar
    (400 "Email já cadastrado." se sim). 404 se o professor não existir.
    Devolve só `mensagem`.
    """
    try:
        if dados.email is not None:
            existente = buscar_usuario_por_email(dados.email.strip())
            if existente and existente.get("usuario_id"):
                row = buscar_usuario_id_por_professor_id(professor_id)
                if not row or row["usuario_id"] != existente["usuario_id"]:
                    raise HTTPException(status_code=400, detail="Email já cadastrado.")
        resultado = atualizar_professor(
            professor_id,
            nome=dados.nome,
            email=dados.email.strip() if dados.email else None,
        )
        if not resultado:
            raise HTTPException(status_code=404, detail="Professor não encontrado.")
        audit("Professor atualizado", admin=current_user.get("sub"), professor_id=professor_id, ip=client_ip(request))
        return {"mensagem": "Professor atualizado com sucesso."}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_atualizar_professor")


@router.delete(
    "/professores/{professor_id}",
    summary="Excluir professor",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_professor(professor_id: str, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Exclui o professor, órfão de propósito: antes de apagar `Professores` e
    `Usuarios`, zera `professor_id` em `Turmas` e `Chamadas` (a turma fica
    "Sem professor", chamadas antigas ficam sem professor associado). O
    histórico de presença é preservado — a exclusão só chega em `Presencas`
    se cascatear a partir de `Chamadas`, e aqui `Chamadas` nunca é apagada.
    404 se o professor não existir. Devolve só `mensagem`.
    """
    try:
        usuario_id = excluir_professor_em_cascata(professor_id)
        if not usuario_id:
            raise HTTPException(status_code=404, detail="Professor não encontrado")
        audit("Professor excluído", admin=current_user.get("sub"), professor_id=professor_id, ip=client_ip(request))
        return {"mensagem": "Professor excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_excluir_professor")


@router.get("/horarios-todos", summary="Listar todos os horários de aula")
def admin_listar_todos_horarios():
    """Lista todos os horários de aula cadastrados, de todas as turmas.

    Devolve `horario_id`, `turma_id`, `dia_semana` (0-6), `inicio`/`fim`
    (strings "HH:MM"), `sala`, `nome_disciplina`, `turno` e `semestre`.
    """
    try:
        return listar_horarios_completos()
    except Exception as e:
        raise internal_error(e)


@router.delete(
    "/horarios/{horario_id}",
    summary="Excluir horário de aula",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_horario(horario_id: str, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Exclui um horário de aula pelo id.

    Não confere se o horário existia: `horario_id` inexistente também
    devolve `mensagem` de sucesso (nenhuma linha é afetada, mas não há 404).
    """
    try:
        excluir_horario(horario_id)
        audit("Horário removido", admin=current_user.get("sub"), horario_id=horario_id, ip=client_ip(request))
        return {"mensagem": "Horário removido!"}
    except Exception as e:
        raise internal_error(e, "admin_excluir_horario")


@router.get(
    "/alunos",
    summary="Listar alunos com filtros e paginação",
    responses={200: {"model": AlunosPaginados}},
)
def admin_listar_alunos(
    q: Optional[str] = None,
    turno: Optional[Literal["Matutino", "Noturno"]] = None,
    semestre: Optional[str] = None,
    periodo_letivo: Optional[str] = None,
    turma_id: Optional[str] = None,
    situacao: Optional[Literal["sem_turma", "sem_biometria", "pendentes"]] = None,
    contexto_turma_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    # Sem `le=100` de propósito: pedir demais é reduzido ao teto, não rejeitado.
    # Um cliente que mandou limit=500 deve receber 100 alunos, não um 422.
    limit: int = Query(10, ge=1),
):
    """Lista alunos paginados no banco, com busca e filtros combináveis.

    `q` busca por nome/email/RA (ILIKE). `turno`, `semestre`, `periodo_letivo`
    e `turma_id` filtram por matrícula. `situacao` restringe a um subconjunto:
    `sem_turma` (nenhuma matrícula), `sem_biometria` (sem rosto ativo) ou
    `pendentes` (turno indefinido, ou sem matrícula dentro do escopo pedido).
    `contexto_turma_id` marca cada aluno com `ja_matriculado` naquela turma
    (usado pelo modal de matrícula). Devolve `{"items": [...], "total": n,
    "ocultos_pendentes": m}` — `total` é o total já filtrado (paginação),
    `ocultos_pendentes` é quantos alunos ficaram de fora só pelo critério de
    pendência (sempre 0 quando `situacao=pendentes`, para não contar a
    própria lista como "oculta").

    Armadilha: `limit` não tem teto de validação (sem `le=100`) — pedir mais
    de 100 não vira 422, é silenciosamente reduzido a `LIMITE_PAGINA` (100).
    """
    try:
        limit = min(limit, LIMITE_PAGINA)
        resultado = listar_alunos_para_admin(
            q=q, turno=turno, semestre=semestre, periodo_letivo=periodo_letivo,
            turma_id=turma_id, situacao=situacao, contexto_turma_id=contexto_turma_id,
            page=page, limit=limit,
        )
        # Com situacao=pendentes a lista já É a dos ocultos: contar de novo confundiria.
        ocultos = 0 if situacao == "pendentes" else contar_alunos_pendentes(
            q=q, turno=turno, semestre=semestre,
            periodo_letivo=periodo_letivo, turma_id=turma_id,
        )
        return {**resultado, "ocultos_pendentes": ocultos}
    except Exception as e:
        raise internal_error(e, "admin_listar_alunos")


@router.post(
    "/turmas/{turma_id}/matricular-alunos",
    summary="Matricular alunos na turma",
    responses={200: {"model": MatriculaAplicada}},
)
def admin_matricular_alunos(turma_id: str, dados: MatricularAlunos, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Matricula um lote de alunos na turma.

    Rejeita com 400 se algum aluno da lista tiver turno definido diferente do
    turno da turma. Matrículas duplicadas são ignoradas silenciosamente
    (`ON CONFLICT DO NOTHING`) — por isso `matriculados` pode ser menor que
    `total_enviados`. Devolve `mensagem` e `total_enviados`; 404 se a turma
    não existir; 400 se a lista de `aluno_ids` vier vazia.
    """
    if not dados.aluno_ids:
        raise HTTPException(status_code=400, detail="Nenhum aluno selecionado.")
    try:
        turma = obter_turno_turma(turma_id)
        if not turma:
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        turma_turno = turma['turno']

        alunos_rows = listar_alunos_por_ids(dados.aluno_ids)
        for row in alunos_rows:
            if row['turno'] and row['turno'] != turma_turno:
                raise HTTPException(
                    status_code=400,
                    detail=f"Aluno não pode ser matriculado: turno do aluno ({row['turno']}) é diferente do turno da turma ({turma_turno}).",
                )

        matriculados = matricular_alunos_em_turma(turma_id, dados.aluno_ids)
        audit("Matrícula", admin=current_user.get("sub"), turma_id=turma_id,
              matriculados=matriculados, enviados=len(dados.aluno_ids), ip=client_ip(request))
        return {"mensagem": f"{matriculados} aluno(s) matriculado(s) com sucesso.", "total_enviados": len(dados.aluno_ids)}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_matricular_alunos")


@router.post(
    "/turmas/{turma_id}/desmatricular-alunos",
    summary="Desmatricular alunos da turma",
    responses={200: {"model": MatriculaAplicada}},
)
def admin_desmatricular_alunos(
    turma_id: str,
    dados: MatricularAlunos,
    request: Request,
    current_user: dict = Depends(require_role("Admin")),
):
    """Remove um lote de alunos da turma (apaga a linha em `Turma_Alunos`).

    Não apaga `Presencas` — o histórico de presença do aluno naquela turma
    permanece, mesmo desmatriculado. Devolve `mensagem` e `total_enviados`;
    404 se a turma não existir; 400 se `aluno_ids` vier vazio.
    """
    if not dados.aluno_ids:
        raise HTTPException(status_code=400, detail="Nenhum aluno selecionado.")
    try:
        if not obter_turno_turma(turma_id):
            raise HTTPException(status_code=404, detail="Turma não encontrada.")
        removidos = desmatricular_alunos_da_turma(turma_id, dados.aluno_ids)
        audit("Desmatrícula", admin=current_user.get("sub"), turma_id=turma_id,
              removidos=removidos, enviados=len(dados.aluno_ids), ip=client_ip(request))
        return {
            "mensagem": f"{removidos} aluno(s) desmatriculado(s) com sucesso.",
            "total_enviados": len(dados.aluno_ids),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


def _validar_extensao_csv(filename):
    if not (filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .csv são aceitos.")


def _processar_professores_csv(csv_reader, background_tasks: BackgroundTasks):
    """Loop síncrono da importação de professores — roda em threadpool porque
    get_password_hash (pbkdf2 600k iterações, ~300ms) é chamado por linha e
    bloquearia o event loop se rodasse direto no handler async."""
    importados = 0
    duplicados = 0
    emails_enviados = 0
    erros = []

    for linha_num, row in enumerate(csv_reader, start=2):  # 1 = header
        try:
            nome = validar_celula_csv(row.get("nome", ""), "nome")
            email = validar_celula_csv(row.get("email", ""), "email")

            if not nome or not email:
                continue

            if len(nome) < 3:
                raise ValueError("Nome deve ter ao menos 3 caracteres.")
            if not EMAIL_REGEX.match(email):
                raise ValueError("E-mail em formato inválido.")

            senha_temporaria = gerar_senha_temporaria()
            senha_hash = get_password_hash(senha_temporaria)

            novo_usuario, _ = importar_professor_csv(
                nome, email, senha_hash
            )

            if novo_usuario:
                background_tasks.add_task(
                    send_email_senha_temporaria, email, nome, senha_temporaria, "Professor"
                )
                emails_enviados += 1
                importados += 1
            else:
                duplicados += 1
        except ValueError as ve:
            erros.append(f"Linha {linha_num}: {ve}")
        except Exception as e:
            erros.append(f"Linha {linha_num}: erro inesperado ({type(e).__name__}).")
            logger.warning("Erro na importação CSV professor linha %s: %s", linha_num, e)

    return importados, duplicados, emails_enviados, erros


@router.post("/turmas/{turma_id}/importar-alunos", summary="Importar alunos via CSV para a turma")
async def admin_importar_alunos_csv(
    turma_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("Admin")),
):
    """Importa alunos de um CSV (colunas `nome`, `email`, `ra`; `turno`
    opcional) e matricula todos direto nesta turma — a coluna `turma`, se
    vier no CSV, é ignorada, pois a turma já está fixada pela URL.

    Aceita BOM do Excel (`utf-8-sig`) e ponto-e-vírgula como separador (ver
    `criar_leitor_csv`/`processar_csv_alunos`). Roda em threadpool porque o
    hash de senha (pbkdf2, ~300ms) por linha bloquearia o event loop.
    Aluno novo recebe senha temporária por email em background. Devolve
    `mensagem`, `emails_enviados` e `erros` (lista de erros por linha — uma
    linha com erro não aborta o import, só é pulada).
    """
    _validar_extensao_csv(file.filename)
    conteudo = await file.read()

    def agendar_email(email, nome, senha):
        background_tasks.add_task(send_email_senha_temporaria, email, nome, senha, "Aluno")

    try:
        # pbkdf2 a 600k iterações (~300ms/hash) roda por linha do CSV — em thread
        # separada para não travar o event loop (que o gunicorn mataria após 30s
        # sem heartbeat, deixando o import parcialmente commitado).
        res = await run_in_threadpool(
            processar_csv_alunos, conteudo, turma_id_fixo=turma_id, on_novo_usuario=agendar_email
        )
        total = res.importados + res.duplicados
        audit("Importação CSV alunos", admin=current_user.get("sub"), turma_id=turma_id,
              importados=total, emails=res.emails_enviados, erros=len(res.erros),
              ip=client_ip(request))
        return {
            "mensagem": f"Importação concluída: {total} alunos matriculados.",
            "emails_enviados": res.emails_enviados,
            "erros": res.erros,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_importar_alunos_csv")


@router.post("/importar-alunos", summary="Importar alunos via CSV (sem turma fixa)")
async def admin_importar_alunos_csv_global(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("Admin")),
):
    """Importa alunos de um CSV (colunas `nome`, `email`, `ra`; `turno` e
    `turma` opcionais), sem turma fixada pela URL: se a linha trouxer coluna
    `turma`, o código é resolvido para `turma_id` e o aluno é matriculado; um
    código que não existe vira erro só naquela linha (não aborta o import).

    Mesmas regras de CSV do endpoint por turma (BOM do Excel, `;` como
    separador) e mesmo motivo para rodar em threadpool (hash de senha por
    linha). Devolve `mensagem`, `importados`, `duplicados`, `matriculados`,
    `emails_enviados` e `erros` — mais granular que a versão por turma porque
    aqui "importado" e "matriculado" podem divergir (aluno já existente sem
    matrícula anterior, por exemplo).
    """
    _validar_extensao_csv(file.filename)
    conteudo = await file.read()

    def agendar_email(email, nome, senha):
        background_tasks.add_task(send_email_senha_temporaria, email, nome, senha, "Aluno")

    try:
        # Mesmo motivo do endpoint por turma: pbkdf2 por linha sai do event loop.
        res = await run_in_threadpool(processar_csv_alunos, conteudo, on_novo_usuario=agendar_email)
        audit("Importação CSV alunos (global)", admin=current_user.get("sub"),
              importados=res.importados, duplicados=res.duplicados,
              matriculados=res.matriculados, emails=res.emails_enviados,
              erros=len(res.erros), ip=client_ip(request))
        return {
            "mensagem": f"Importação concluída: {res.importados} aluno(s) cadastrado(s).",
            "importados": res.importados,
            "duplicados": res.duplicados,
            "matriculados": res.matriculados,
            "emails_enviados": res.emails_enviados,
            "erros": res.erros,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_importar_alunos_csv_global")


@router.post("/importar-professores", summary="Importar professores via CSV")
async def admin_importar_professores_csv(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("Admin")),
):
    """Importa professores de um CSV (colunas `nome`, `email`).

    Aceita BOM do Excel (`utf-8-sig`) e `;` como separador. Rejeita arquivo
    vazio (400) ou maior que 2 MB (413). O loop de linhas roda em threadpool
    pelo mesmo motivo dos imports de aluno: hash de senha por linha
    bloquearia o event loop. Email já cadastrado conta como `duplicados`, não
    como erro. Professor novo recebe senha temporária por email em
    background. Devolve `mensagem`, `duplicados`, `emails_enviados` e
    `erros` (por linha, não interrompe o import).
    """
    _validar_extensao_csv(file.filename)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV muito grande (limite: 2 MB).")

    try:
        # utf-8-sig descarta o BOM gravado pelo Excel.
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV deve estar em UTF-8.")

    try:
        csv_reader = criar_leitor_csv(decoded, ["nome", "email"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    try:
        importados, duplicados, emails_enviados, erros = await run_in_threadpool(
            _processar_professores_csv, csv_reader, background_tasks
        )

        audit("Importação CSV professores", admin=current_user.get("sub"), importados=importados,
              duplicados=duplicados, emails=emails_enviados, erros=len(erros), ip=client_ip(request))
        return {
            "mensagem": f"Importação concluída: {importados} professor(es) cadastrado(s).",
            "duplicados": duplicados,
            "emails_enviados": emails_enviados,
            "erros": erros,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_importar_professores_csv")


@router.post(
    "/usuarios/professor",
    summary="Criar professor com usuário de acesso",
    responses={200: {"model": ProfessorCriado}},
)
def admin_criar_professor(dados: CriarProfessorAdmin, request: Request, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Admin"))):
    """Cria um professor: usuário de login (`tipo_usuario='Professor'`) mais o
    registro em `Professores`, numa transação.

    Gera senha temporária e envia por email em background (`primeiro_acesso`
    fica `TRUE`, forçando troca no primeiro login). 400 se o email já
    existir. Devolve `mensagem`, `usuario_id` e `email`.
    """
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        professor_id = str(uuid.uuid4())

        criar_professor_com_usuario(usuario_id, professor_id, dados.nome, email_limpo, senha_hash)

        background_tasks.add_task(send_email_senha_temporaria, email_limpo, dados.nome, senha_temporaria, "Professor")

        audit("Professor criado", admin=current_user.get("sub"), professor_id=professor_id, ip=client_ip(request))
        return {
            "mensagem": "Professor criado com sucesso!",
            "usuario_id": usuario_id,
            "email": email_limpo,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_professor")


@router.post(
    "/usuarios/aluno",
    summary="Criar aluno com usuário de acesso",
    responses={200: {"model": AlunoCriado}},
)
def admin_criar_aluno(dados: CriarAlunoAdmin, request: Request, background_tasks: BackgroundTasks, current_user: dict = Depends(require_role("Admin"))):
    """Cria um aluno: usuário de login (`tipo_usuario='Aluno'`) mais o
    registro em `Alunos` (RA, turno), numa transação. Não matricula em
    nenhuma turma — isso é feito à parte, por `/turmas/{turma_id}/matricular-alunos`.

    Gera senha temporária e envia por email em background (`primeiro_acesso`
    fica `TRUE`). 400 se o email ou o RA já existirem. Devolve `mensagem`,
    `usuario_id`, `aluno_id` e `email`.
    """
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        if existe_aluno_por_ra(dados.ra):
            raise HTTPException(status_code=400, detail="RA já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        aluno_id = str(uuid.uuid4())

        criar_aluno_com_usuario(usuario_id, aluno_id, dados.nome, email_limpo, senha_hash, dados.ra, dados.turno)

        background_tasks.add_task(send_email_senha_temporaria, email_limpo, dados.nome, senha_temporaria, "Aluno")

        audit("Aluno criado", admin=current_user.get("sub"), aluno_id=aluno_id, ip=client_ip(request))
        return {
            "mensagem": "Aluno criado com sucesso!",
            "usuario_id": usuario_id,
            "aluno_id": aluno_id,
            "email": email_limpo,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_aluno")


class BulkFaceIds(BaseModel):
    face_ids: List[str]


class S3KeyPayload(BaseModel):
    key: str


@router.get(
    "/rostos/inventario",
    summary="Auditoria cruzada da biometria (Rekognition/S3/banco)",
    responses={200: {"model": InventarioBiometrico}},
)
def admin_inventario_biometrico():
    """Collection, bucket e banco cruzados para auditoria da aba Biometria.

    Degrada por lado em vez de derrubar a tela: se uma das listagens da AWS
    falhar, o outro lado ainda chega e `indisponivel` diz o que faltou.

    Devolve `{"rekognition": [...], "s3": [...], "alunos": [...], "resumo":
    {...}, "indisponivel": [...]}`. Cada item de `rekognition`/`s3` tem
    `status` (`ok`/`revogado`/`orfao`) e `divergente` (True quando o par no
    outro lado não existe — só calculado se os dois lados da AWS
    responderam). `alunos` lista quem tem biometria ativa com os ângulos
    presentes/faltantes. `resumo` traz as contagens de cada bloco.
    `indisponivel` lista `"rekognition"` e/ou `"s3"` quando a AWS falhou.
    """
    try:
        faces, faces_ok = listar_todas_faces()
        objetos, objetos_ok = listar_todos_objetos_s3()
        registros = listar_inventario_biometrico()

        indisponivel = []
        if not faces_ok:
            indisponivel.append("rekognition")
        if not objetos_ok:
            indisponivel.append("s3")

        return reconciliar_inventario(faces, objetos, registros, indisponivel)
    except Exception as e:
        raise internal_error(e, "admin_inventario_biometrico")


@router.delete(
    "/rostos/rekognition/bulk",
    summary="Excluir rostos do Rekognition em lote",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_rostos_rekognition_bulk(payload: BulkFaceIds, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Remove uma lista de `face_ids` da collection do Rekognition, direto —
    usado pela tela de auditoria para limpar rostos órfãos (sem registro
    correspondente no banco).

    Não toca no banco (`Colecao_Rostos`) nem no S3: é limpeza só do lado
    Rekognition. Lista é truncada em 4096 itens (limite da própria API AWS).
    503 se o cliente Rekognition não estiver configurado; 400 se a lista
    vier vazia. Devolve `mensagem` com a contagem removida.
    """
    if rekognition_client is None:
        raise HTTPException(status_code=503, detail="Rekognition não disponível")
    if not payload.face_ids:
        raise HTTPException(status_code=400, detail="Nenhum face_id informado.")
    try:
        face_ids = payload.face_ids[:4096]
        rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=face_ids)
        audit("Rostos Rekognition removidos (bulk)", admin=current_user.get("sub"),
              total=len(face_ids), ip=client_ip(request))
        return {"mensagem": f"{len(face_ids)} rosto(s) removido(s) com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rostos_rekognition_bulk")


@router.delete(
    "/rostos/rekognition/{face_id}",
    summary="Excluir rosto do Rekognition",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_rosto_rekognition(face_id: str, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Remove um único rosto (`face_id`) da collection do Rekognition, direto.

    Não toca no banco nem no S3 — é a versão de um item só do endpoint em
    lote, para a tela de auditoria. 503 se o cliente Rekognition não estiver
    configurado. Devolve `mensagem` de sucesso.
    """
    if rekognition_client is None:
        raise HTTPException(status_code=503, detail="Rekognition não disponível")
    try:
        rekognition_client.delete_faces(CollectionId=COLLECTION_ID, FaceIds=[face_id])
        audit("Rosto Rekognition removido", admin=current_user.get("sub"),
              face_id=face_id, ip=client_ip(request))
        return {"mensagem": "Rosto removido com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rosto_rekognition")


@router.delete(
    "/rostos/s3",
    summary="Excluir objeto de rosto no S3",
    responses={200: {"model": MensagemResposta}},
)
def admin_excluir_rosto_s3(payload: S3KeyPayload, request: Request, current_user: dict = Depends(require_role("Admin"))):
    """Remove um objeto do bucket S3 pela `key`, direto — usado pela tela de
    auditoria para limpar arquivos órfãos (sem registro correspondente no
    banco ou no Rekognition).

    Não toca no banco nem no Rekognition. `key` precisa começar com
    `alunos/` e não pode conter `..` — restrição de escopo contra apagar
    outro objeto qualquer do bucket via key arbitrária (defesa em
    profundidade, mesmo sendo endpoint só de Admin). 503 se o cliente S3 não
    estiver configurado; 400 se a key vier vazia ou fora do escopo. Devolve
    `mensagem` de sucesso.
    """
    if s3_client is None:
        raise HTTPException(status_code=503, detail="S3 não disponível")
    if not payload.key:
        raise HTTPException(status_code=400, detail="Key não informada.")
    # Restringe ao prefixo de biometria — impede deleção de outros objetos do
    # bucket via key arbitrária (defense-in-depth, mesmo sendo endpoint Admin).
    if not payload.key.startswith("alunos/") or ".." in payload.key:
        raise HTTPException(status_code=400, detail="Key fora do escopo permitido.")
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=payload.key)
        audit("Objeto S3 de rosto removido", admin=current_user.get("sub"),
              key=payload.key, ip=client_ip(request))
        return {"mensagem": "Arquivo S3 removido com sucesso."}
    except Exception as e:
        raise internal_error(e, "admin_excluir_rosto_s3")
