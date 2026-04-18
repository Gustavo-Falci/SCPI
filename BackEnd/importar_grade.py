"""
Importador da grade horaria ADS Fatec (versao consolidada pelo usuario).

Fonte: lista GRADE abaixo (blocos ja fundidos).
Tupla: (semestre, turno, dia_idx, inicio, fim, disciplina, professor)
  dia_idx: 0=Seg, 1=Ter, 2=Qua, 3=Qui, 4=Sex

Idempotente: reusa Usuarios/Professores/Turmas existentes e sempre reescreve
os horarios_aulas das turmas tocadas.

Uso:
    cd BackEnd
    python importar_grade.py
"""
import os
import re
import sys
import uuid
import hashlib

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db_cursor
from auth_utils import get_password_hash

PERIODO_LETIVO = "2026-1"

GRADE = [
    # --- ADS 1 Matutino ---
    ("1", "Matutino", 0, "07:40", "11:10", "ARQ. E ORG.", "Rodrigo"),
    ("1", "Matutino", 0, "11:20", "13:00", "SO", "Celso"),
    ("1", "Matutino", 1, "07:40", "09:20", "SO", "Celso"),
    ("1", "Matutino", 1, "09:30", "11:10", "ALGORITMOS", "Sandra Cielavin"),
    ("1", "Matutino", 2, "07:40", "09:20", "PROJ. INTEGI", "Silvia Garcia"),
    ("1", "Matutino", 2, "09:30", "13:00", "ENG. SOFT. I", "Marcelo Moreira"),

    # --- ADS 2 Matutino ---
    ("2", "Matutino", 0, "07:40", "09:20", "ENG. SOFT. I", "Adriano"),
    ("2", "Matutino", 0, "09:30", "13:00", "SIST. INFO.", "Marcus"),
    ("2", "Matutino", 1, "09:30", "12:10", "COM. EXPRESSÃO", "Eva"),
    ("2", "Matutino", 1, "10:20", "13:00", "LING. PROGR.", "Andréia Casare"),
    ("2", "Matutino", 2, "07:40", "09:20", "CÁLCULO", "Marcelo Silvério"),
    ("2", "Matutino", 2, "10:20", "13:00", "ENG. SOFT. I", "Adriano"),
    ("2", "Matutino", 3, "07:40", "09:20", "COM. EXPRESSÃO", "Eva"),
    ("2", "Matutino", 3, "09:30", "12:10", "INGLÊS II", "Ademar"),
    ("2", "Matutino", 3, "10:20", "13:00", "LING. PROGR.", "Andréia Casare"),
    ("2", "Matutino", 4, "09:30", "12:10", "CÁLCULO", "Marcelo Silvério"),
    ("2", "Matutino", 4, "10:20", "13:00", "CONTABILIDADE", "Altimar"),

    # --- ADS 3 Matutino ---
    ("3", "Matutino", 0, "07:40", "11:10", "SO I", "Deivison"),
    ("3", "Matutino", 0, "11:20", "13:00", "SOCIEDADE E TEC", "Paula Granato"),
    ("3", "Matutino", 1, "07:40", "13:00", "ESTATÍSTICA", "ATRIBUIÇÃO"),
    ("3", "Matutino", 2, "07:40", "11:10", "ESTR. DE DADOS", "Adriano"),
    ("3", "Matutino", 3, "07:40", "09:20", "ALGORITMOS", "Sandra Cielavin"),
    ("3", "Matutino", 3, "09:30", "11:10", "IHC", "Marcelo Camargo"),
    ("3", "Matutino", 3, "11:20", "13:00", "ENG. SOFT II", "José Antonio"),
    ("3", "Matutino", 4, "07:40", "09:20", "INGLÊS I", "Ademar"),
    ("3", "Matutino", 4, "09:30", "13:00", "COM. EXP (Online)", "Eva"),

    # --- ADS 4 Matutino ---
    ("4", "Matutino", 0, "07:40", "09:20", "ENG. SOFT. III", "Silvia Garcia"),
    ("4", "Matutino", 0, "09:30", "11:10", "Banco de Dados", "Andréia Casare"),
    ("4", "Matutino", 0, "11:20", "13:00", "POO", "Sandra Cielavin"),
    ("4", "Matutino", 1, "07:40", "08:30", "Banco de Dados", "Andréia Casare"),
    ("4", "Matutino", 1, "08:30", "12:10", "PROG. VIII", "José Antonio"),
    ("4", "Matutino", 1, "12:10", "13:00", "METODOLOGIA", "Silvia Garcia"),
    ("4", "Matutino", 2, "07:40", "08:30", "Banco de Dados", "Andréia Casare"),
    ("4", "Matutino", 2, "08:30", "12:10", "SO II", "Celso"),
    ("4", "Matutino", 4, "07:40", "08:30", "ENG. SOFT. III", "Silvia Garcia"),
    ("4", "Matutino", 4, "08:30", "10:20", "INGLÊS IV", "Ademar"),
    ("4", "Matutino", 4, "10:20", "12:10", "POO", "Sandra Cielavin"),

    # --- ADS 5 Matutino ---
    ("5", "Matutino", 0, "07:40", "11:10", "PROG. LINEAR", "Jefferson"),
    ("5", "Matutino", 0, "11:20", "13:00", "LAB.BD", "Andréia Casare"),
    ("5", "Matutino", 1, "07:40", "09:20", "SEG INFO.", "Celso"),
    ("5", "Matutino", 2, "07:40", "11:10", "LAB. ENG SOFT", "Danilo"),
    ("5", "Matutino", 2, "11:20", "13:00", "LAB.BD", "Andréia Casare"),

    # --- ADS 6 Matutino ---
    ("6", "Matutino", 3, "07:40", "09:20", "PROG. WEB", "Deivison"),
    ("6", "Matutino", 3, "09:30", "11:10", "INGLÊS V", "Luciana Almeida"),
    ("6", "Matutino", 3, "11:20", "13:00", "PROG. WEB", "Deivison"),
    ("6", "Matutino", 4, "07:40", "11:10", "REDES DE COMP", "Rodrigo"),

    # --- ADS 1 Noturno ---
    ("1", "Noturno", 0, "18:45", "19:35", "SO", "Celso"),
    ("1", "Noturno", 0, "19:35", "23:05", "ALGORITMOS", "Sandra Cielavin"),
    ("1", "Noturno", 1, "18:45", "19:35", "PROJ. INTEGI", "Silvia Garcia"),
    ("1", "Noturno", 1, "19:35", "23:05", "ARQ. E ORG.", "Rodrigo"),
    ("1", "Noturno", 2, "18:45", "19:35", "PROJ. INTEGI", "Silvia Garcia"),
    ("1", "Noturno", 2, "19:35", "23:05", "ENG. SOFT I", "Marcelo Moreira"),
    ("1", "Noturno", 3, "18:45", "20:25", "INGLÊS I", "Ademar"),
    ("1", "Noturno", 3, "20:25", "23:05", "SO", "Celso"),
    ("1", "Noturno", 4, "18:45", "22:15", "COM. EXP (Online)", "Eva"),

    # --- ADS 2 Noturno ---
    ("2", "Noturno", 0, "18:45", "22:15", "SIST. INFO.", "Marcus"),
    ("2", "Noturno", 0, "22:15", "23:05", "LING. PROGR", "Andréia Casare"),
    ("2", "Noturno", 1, "18:45", "20:25", "COM. EXPRESSÃO", "Eva"),
    ("2", "Noturno", 1, "20:25", "23:05", "LING. PROGR.", "Andréia Casare"),
    ("2", "Noturno", 2, "18:45", "22:15", "CÁLCULO", "Marcelo Silvério"),
    ("2", "Noturno", 2, "22:15", "23:05", "ENG. SOFT. I", "Carlos"),
    ("2", "Noturno", 3, "18:45", "20:25", "COM. EXPRESSÃO", "Eva"),
    ("2", "Noturno", 3, "20:25", "22:15", "INGLÊS II", "Ademar"),
    ("2", "Noturno", 4, "18:45", "20:25", "CONTABILIDADE", "Altimar"),
    ("2", "Noturno", 4, "20:25", "23:05", "ENG. SOFT. I", "Carlos"),

    # --- ADS 3 Noturno ---
    ("3", "Noturno", 0, "18:45", "22:15", "ESTR. DE DADOS", "Danilo"),
    ("3", "Noturno", 0, "22:15", "23:05", "SO I", "ATRIBUIÇÃO"),
    ("3", "Noturno", 1, "18:45", "22:15", "ESTATÍSTICA", "Antônio Carlos Camilo"),
    ("3", "Noturno", 1, "22:15", "23:05", "ENG. SOFT II", "Carlos"),
    ("3", "Noturno", 2, "18:45", "20:25", "SOCIEDADE E TEC", "Paula Granato"),
    ("3", "Noturno", 2, "20:25", "23:05", "SO I", "ATRIBUIÇÃO"),
    ("3", "Noturno", 3, "18:45", "20:25", "IHC", "Marcelo Camargo"),
    ("3", "Noturno", 3, "20:25", "23:05", "ENG. SOFT II", "Carlos"),
    ("3", "Noturno", 4, "18:45", "20:25", "INGLÊS I/II", "ATRIBUIÇÃO"),
    ("3", "Noturno", 4, "20:25", "22:15", "ECON E FINANÇAS", "Henrique"),

    # --- ADS 4 Noturno ---
    ("4", "Noturno", 0, "18:45", "20:25", "PROG. VIII", "José Antonio"),
    ("4", "Noturno", 0, "20:25", "22:15", "Banco de Dados", "Andréia Casare"),
    ("4", "Noturno", 0, "22:15", "23:05", "METODOLOGIA", "ATRIBUIÇÃO"),
    ("4", "Noturno", 1, "18:45", "20:25", "SO II", "Celso"),
    ("4", "Noturno", 1, "20:25", "22:15", "SO I", "Celso"),
    ("4", "Noturno", 1, "22:15", "23:05", "METODOLOGIA", "ATRIBUIÇÃO"),
    ("4", "Noturno", 2, "18:45", "20:25", "Banco de Dados", "Andréia Casare"),
    ("4", "Noturno", 2, "20:25", "22:15", "ENG. SOFT. III", "Silvia Garcia"),
    ("4", "Noturno", 3, "18:45", "20:25", "PROG. VIII", "José Antonio"),
    ("4", "Noturno", 3, "20:25", "23:05", "POO", "Sandra Cielavin"),
    ("4", "Noturno", 4, "18:45", "20:25", "ENG. SOFT. III", "Silvia Garcia"),
    ("4", "Noturno", 4, "20:25", "22:15", "POO", "Sandra Cielavin"),
    ("4", "Noturno", 4, "22:15", "23:05", "INGLÊS IV", "ATRIBUIÇÃO"),

    # --- ADS 5 Noturno ---
    ("5", "Noturno", 0, "18:45", "20:25", "LAB.BD", "Andréia Casare"),
    ("5", "Noturno", 0, "20:25", "22:15", "SEG. INFO", "Celso"),
    ("5", "Noturno", 1, "18:45", "20:25", "LAB.BD", "Andréia Casare"),
    ("5", "Noturno", 1, "20:25", "23:05", "PROG. LINEAR", "Jefferson"),
    ("5", "Noturno", 2, "18:45", "19:35", "PROG. WEB", "Leandro Medeiros"),
    ("5", "Noturno", 2, "19:35", "23:05", "LAB. ENG. SOFT.", "ATRIBUIÇÃO"),
    ("5", "Noturno", 3, "18:45", "20:25", "INGLÊS V", "Luciana Almeida"),
    ("5", "Noturno", 3, "20:25", "23:05", "PROG. WEB", "Leandro Medeiros"),
    ("5", "Noturno", 4, "18:45", "19:35", "PROG. LINEAR", "Jefferson"),
    ("5", "Noturno", 4, "19:35", "23:05", "REDES DE COMP.", "Rodrigo"),

    # --- ADS 6 Noturno ---
    ("6", "Noturno", 1, "18:45", "20:25", "EMPREENDEDORISM", "José Carlos Belo"),
    ("6", "Noturno", 1, "20:25", "23:05", "TÓPICOS ESPECIAIS", "José Antonio"),
    # Quarta: corrigido de 08:30-13:00 (horario matutino) para slots noturnos
    ("6", "Noturno", 2, "18:45", "20:25", "GESTÃO DE PROJETO", "Marcelo Moreira"),
    ("6", "Noturno", 2, "20:25", "23:05", "GESTÃO DE PROJETO", "Marcelo Moreira"),
]


def slugify_email(nome: str) -> str:
    s = nome.lower().strip()
    mapa = {"ç": "c", "ã": "a", "á": "a", "à": "a", "â": "a",
            "é": "e", "ê": "e", "í": "i", "ó": "o", "ô": "o",
            "õ": "o", "ú": "u"}
    for k, v in mapa.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", ".", s)
    s = re.sub(r"[^a-z0-9.]", "", s)
    return s or "atribuir"


def short_hash(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:5].upper()


def upsert_professores(cur, nomes):
    mapa = {}
    senha_hash = get_password_hash("123")
    for nome in nomes:
        email = f"{slugify_email(nome)}@fatec.sp.gov.br"
        cur.execute("SELECT usuario_id FROM Usuarios WHERE email = %s", (email,))
        r = cur.fetchone()
        if r:
            usuario_id = r["usuario_id"]
        else:
            usuario_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
                VALUES (%s, %s, %s, %s, 'Professor')
            """, (usuario_id, nome, email, senha_hash))

        cur.execute("SELECT professor_id FROM Professores WHERE usuario_id = %s", (usuario_id,))
        r = cur.fetchone()
        if r:
            mapa[nome] = r["professor_id"]
        else:
            prof_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Professores (professor_id, usuario_id, departamento)
                VALUES (%s, %s, 'ADS')
            """, (prof_id, usuario_id))
            mapa[nome] = prof_id
    return mapa


def upsert_turmas(cur, chaves, prof_map):
    mapa = {}
    for key in chaves:
        semestre, disciplina, turno, professor = key
        cur.execute("""
            SELECT turma_id FROM Turmas
            WHERE semestre = %s AND nome_disciplina = %s AND turno = %s AND professor_id = %s
        """, (semestre, disciplina, turno, prof_map[professor]))
        r = cur.fetchone()
        if r:
            mapa[key] = r["turma_id"]
            continue

        codigo = f"ADS{semestre}{turno[0].upper()}-{short_hash(disciplina + professor)}"
        turma_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO Turmas (turma_id, professor_id, codigo_turma, nome_disciplina,
                                periodo_letivo, sala_padrao, turno, semestre)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (turma_id, prof_map[professor], codigo, disciplina,
              PERIODO_LETIVO, "—", turno, semestre))
        mapa[key] = turma_id
    return mapa


def main():
    professores_nomes = sorted({row[6] for row in GRADE})
    turma_keys = sorted({(row[0], row[5], row[1], row[6]) for row in GRADE})

    print(f"[1/3] Upsert de {len(professores_nomes)} professores...")
    with get_db_cursor(commit=True) as cur:
        prof_map = upsert_professores(cur, professores_nomes)

    print(f"[2/3] Upsert de {len(turma_keys)} turmas...")
    with get_db_cursor(commit=True) as cur:
        turma_map = upsert_turmas(cur, turma_keys, prof_map)

    print(f"[3/3] Reescrevendo {len(GRADE)} horarios...")
    with get_db_cursor(commit=True) as cur:
        turma_ids = tuple(set(turma_map.values()))
        if turma_ids:
            placeholders = ",".join(["%s"] * len(turma_ids))
            cur.execute(f"DELETE FROM horarios_aulas WHERE turma_id IN ({placeholders})", turma_ids)
        for semestre, turno, dia, inicio, fim, disciplina, professor in GRADE:
            key = (semestre, disciplina, turno, professor)
            turma_id = turma_map[key]
            cur.execute("""
                INSERT INTO horarios_aulas (turma_id, dia_semana, horario_inicio, horario_fim, sala)
                VALUES (%s, %s, %s, %s, %s)
            """, (turma_id, dia, inicio, fim, "—"))

    print("\n[OK] Importacao concluida.")
    print(f"      Professores: {len(professores_nomes)}")
    print(f"      Turmas:      {len(turma_keys)}")
    print(f"      Horarios:    {len(GRADE)}")
    print("\nSenha padrao dos professores importados: 123")


if __name__ == "__main__":
    main()
