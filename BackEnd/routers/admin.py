import csv
import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from psycopg2.extras import execute_values

from core.auth_utils import get_password_hash
from core.helpers import gerar_senha_temporaria, internal_error
from core.security import require_role
from infra.database import get_db_cursor
from repositories.usuarios import buscar_usuario_por_email
from schemas.admin import (
    AtribuirProfessor,
    CriarAlunoAdmin,
    CriarProfessorAdmin,
    HorarioCreate,
    MatricularAlunos,
    TurmaCreate,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("scpi.audit")

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("Admin"))])


@router.get("/professores")
def admin_listar_professores():
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT p.professor_id, u.nome, u.email, p.departamento
                FROM Professores p
                JOIN Usuarios u ON p.usuario_id = u.usuario_id
                ORDER BY u.nome ASC
                """
            )
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)


@router.get("/turmas-completas")
def admin_listar_turmas():
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT t.turma_id, t.nome_disciplina, t.codigo_turma, t.turno, t.semestre,
                COALESCE(u.nome, 'Sem professor') as professor_nome,
                (SELECT COUNT(*) FROM Turma_Alunos ta WHERE ta.turma_id = t.turma_id) as total_alunos
                FROM Turmas t
                LEFT JOIN Professores p ON t.professor_id = p.professor_id
                LEFT JOIN Usuarios u ON p.usuario_id = u.usuario_id
                ORDER BY t.semestre ASC, t.nome_disciplina ASC
                """
            )
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas")
def admin_criar_turma(turma: TurmaCreate):
    try:
        turma_id = str(uuid.uuid4())
        professor_id = turma.professor_id if turma.professor_id else None
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina, periodo_letivo, sala_padrao, turno, semestre)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING turma_id
                """,
                (turma_id, professor_id, turma.codigo_turma, turma.nome_disciplina, turma.periodo_letivo, turma.sala_padrao, turma.turno, turma.semestre),
            )
            return {"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}
    except Exception as e:
        raise internal_error(e)


@router.patch("/turmas/{turma_id}/professor")
def admin_atribuir_professor(turma_id: str, dados: AtribuirProfessor):
    try:
        professor_id = dados.professor_id if dados.professor_id else None
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE Turmas SET professor_id = %s WHERE turma_id = %s", (professor_id, turma_id))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Turma não encontrada.")
        return {"mensagem": "Professor atribuído com sucesso."}
    except Exception as e:
        raise internal_error(e)


@router.post("/horarios")
def admin_adicionar_horario(h: HorarioCreate):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, horario_fim, sala)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (h.turma_id, h.dia_semana, h.horario_inicio, h.horario_fim, h.sala),
            )
            return {"mensagem": "Horário adicionado com sucesso!"}
    except Exception as e:
        raise internal_error(e)


@router.delete("/turmas/{turma_id}")
def admin_excluir_turma(turma_id: str):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM horarios_aulas WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turma_Alunos WHERE turma_id = %s", (turma_id,))
            cur.execute("DELETE FROM Turmas WHERE turma_id = %s", (turma_id,))
            return {"mensagem": "Turma e dependências excluídas com sucesso!"}
    except Exception as e:
        raise internal_error(e)


@router.delete("/professores/{professor_id}")
def admin_excluir_professor(professor_id: str):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT usuario_id FROM Professores WHERE professor_id = %s", (professor_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Professor não encontrado")
            usuario_id = row["usuario_id"]
            cur.execute("UPDATE Turmas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
            cur.execute("UPDATE Chamadas SET professor_id = NULL WHERE professor_id = %s", (professor_id,))
            cur.execute("DELETE FROM Professores WHERE professor_id = %s", (professor_id,))
            cur.execute("DELETE FROM Usuarios WHERE usuario_id = %s", (usuario_id,))
            return {"mensagem": "Professor excluído com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e)


@router.get("/horarios-todos")
def admin_listar_todos_horarios():
    try:
        with get_db_cursor() as cur:
            cur.execute(
                """
                SELECT h.horario_id, h.turma_id, h.dia_semana,
                       to_char(h.horario_inicio, 'HH24:MI') as inicio,
                       to_char(h.horario_fim, 'HH24:MI') as fim,
                       h.sala, t.nome_disciplina, t.turno, t.semestre
                FROM horarios_aulas h
                JOIN Turmas t ON h.turma_id = t.turma_id
                """
            )
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)


@router.delete("/horarios/{horario_id}")
def admin_excluir_horario(horario_id: str):
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM horarios_aulas WHERE horario_id = %s", (horario_id,))
            return {"mensagem": "Horário removido!"}
    except Exception as e:
        raise internal_error(e)


@router.get("/alunos")
def admin_listar_alunos(turma_id: Optional[str] = None):
    try:
        with get_db_cursor() as cur:
            if turma_id:
                cur.execute(
                    """
                    SELECT
                        a.aluno_id, a.ra, u.nome, u.email, a.turno,
                        EXISTS(
                            SELECT 1 FROM Turma_Alunos ta
                            WHERE ta.aluno_id = a.aluno_id AND ta.turma_id = %s
                        ) as ja_matriculado
                    FROM Alunos a
                    JOIN Usuarios u ON a.usuario_id = u.usuario_id
                    ORDER BY u.nome
                    """,
                    (turma_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT a.aluno_id, a.ra, u.nome, u.email, a.turno, FALSE as ja_matriculado
                    FROM Alunos a
                    JOIN Usuarios u ON a.usuario_id = u.usuario_id
                    ORDER BY u.nome
                    """
                )
            return cur.fetchall()
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas/{turma_id}/matricular-alunos")
def admin_matricular_alunos(turma_id: str, dados: MatricularAlunos):
    if not dados.aluno_ids:
        raise HTTPException(status_code=400, detail="Nenhum aluno selecionado.")
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT turno FROM Turmas WHERE turma_id = %s", (turma_id,))
            turma = cur.fetchone()
            if not turma:
                raise HTTPException(status_code=404, detail="Turma não encontrada.")
            turma_turno = turma['turno']

            cur.execute(
                "SELECT aluno_id, turno FROM Alunos WHERE aluno_id = ANY(%s)",
                (dados.aluno_ids,),
            )
            alunos_rows = cur.fetchall()

            for row in alunos_rows:
                if row['turno'] and row['turno'] != turma_turno:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Aluno não pode ser matriculado: turno do aluno ({row['turno']}) é diferente do turno da turma ({turma_turno}).",
                    )

            execute_values(
                cur,
                "INSERT INTO Turma_Alunos (turma_id, aluno_id) VALUES %s ON CONFLICT (turma_id, aluno_id) DO NOTHING",
                [(turma_id, aid) for aid in dados.aluno_ids],
            )
            matriculados = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

        return {"mensagem": f"{matriculados} aluno(s) matriculado(s) com sucesso.", "total_enviados": len(dados.aluno_ids)}
    except Exception as e:
        raise internal_error(e)


@router.post("/turmas/{turma_id}/importar-alunos")
async def admin_importar_alunos_csv(turma_id: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        decoded = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))

        importados = 0
        erros = []
        senhas_geradas = []

        with get_db_cursor(commit=True) as cur:
            for row in csv_reader:
                try:
                    nome = row.get('nome')
                    email = row.get('email')
                    ra = row.get('ra')
                    turno = row.get('turno')

                    if not nome or not email or not ra:
                        continue

                    if turno not in ('Matutino', 'Noturno'):
                        turno = None

                    user_uuid = str(uuid.uuid4())
                    senha_temporaria = gerar_senha_temporaria()
                    senha_hash = get_password_hash(senha_temporaria)
                    cur.execute(
                        """
                        INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
                        VALUES (%s, %s, %s, %s, 'Aluno', TRUE)
                        ON CONFLICT (email) DO NOTHING
                        RETURNING usuario_id
                        """,
                        (user_uuid, nome, email, senha_hash),
                    )

                    res_user = cur.fetchone()
                    usuario_id = res_user['usuario_id'] if res_user else None
                    novo_usuario = res_user is not None

                    if not usuario_id:
                        cur.execute("SELECT usuario_id FROM Usuarios WHERE email = %s", (email,))
                        usuario_id = cur.fetchone()['usuario_id']

                    if novo_usuario:
                        senhas_geradas.append({"email": email, "senha_temporaria": senha_temporaria})

                    aluno_uuid = str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO Alunos (aluno_id, usuario_id, ra, turno)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (ra) DO UPDATE SET turno = EXCLUDED.turno WHERE Alunos.turno IS NULL
                        RETURNING aluno_id
                        """,
                        (aluno_uuid, usuario_id, ra, turno),
                    )

                    res_aluno = cur.fetchone()
                    aluno_id = res_aluno['aluno_id'] if res_aluno else None

                    if not aluno_id:
                        cur.execute("SELECT aluno_id FROM Alunos WHERE ra = %s", (ra,))
                        aluno_id = cur.fetchone()['aluno_id']

                    cur.execute(
                        """
                        INSERT INTO Turma_Alunos (turma_id, aluno_id)
                        VALUES (%s, %s)
                        ON CONFLICT (turma_id, aluno_id) DO NOTHING
                        """,
                        (turma_id, aluno_id),
                    )

                    importados += 1
                except Exception as e:
                    erros.append(f"Erro na linha {row}: {str(e)}")

        return {
            "mensagem": f"Importação concluída: {importados} alunos matriculados.",
            "erros": erros,
            "senhas_geradas": senhas_geradas,
        }
    except Exception as e:
        raise internal_error(e)


@router.post("/usuarios/professor")
def admin_criar_professor(dados: CriarProfessorAdmin, current_user: dict = Depends(require_role("Admin"))):
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        professor_id = str(uuid.uuid4())

        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
                VALUES (%s, %s, %s, %s, 'Professor', TRUE)
                """,
                (usuario_id, dados.nome, email_limpo, senha_hash),
            )
            cur.execute(
                """
                INSERT INTO Professores (professor_id, usuario_id, departamento)
                VALUES (%s, %s, %s)
                """,
                (professor_id, usuario_id, dados.departamento),
            )

        audit_logger.info("Professor criado admin=%s professor_id=%s", current_user.get("sub"), professor_id)
        return {
            "mensagem": "Professor criado com sucesso!",
            "usuario_id": usuario_id,
            "senha_temporaria": senha_temporaria,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_professor")


@router.post("/usuarios/aluno")
def admin_criar_aluno(dados: CriarAlunoAdmin, current_user: dict = Depends(require_role("Admin"))):
    email_limpo = dados.email.strip()
    try:
        if buscar_usuario_por_email(email_limpo):
            raise HTTPException(status_code=400, detail="Email já cadastrado.")

        with get_db_cursor() as cur:
            cur.execute("SELECT 1 FROM Alunos WHERE ra = %s", (dados.ra,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="RA já cadastrado.")

        senha_temporaria = gerar_senha_temporaria()
        senha_hash = get_password_hash(senha_temporaria)
        usuario_id = str(uuid.uuid4())
        aluno_id = str(uuid.uuid4())

        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, primeiro_acesso)
                VALUES (%s, %s, %s, %s, 'Aluno', TRUE)
                """,
                (usuario_id, dados.nome, email_limpo, senha_hash),
            )
            cur.execute(
                """
                INSERT INTO Alunos (aluno_id, usuario_id, ra, turno)
                VALUES (%s, %s, %s, %s)
                """,
                (aluno_id, usuario_id, dados.ra, dados.turno),
            )

        audit_logger.info("Aluno criado admin=%s aluno_id=%s", current_user.get("sub"), aluno_id)
        return {
            "mensagem": "Aluno criado com sucesso!",
            "usuario_id": usuario_id,
            "aluno_id": aluno_id,
            "senha_temporaria": senha_temporaria,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(e, "admin_criar_aluno")
