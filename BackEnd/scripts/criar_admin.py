import os
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from infra.database import get_db_connection, release_connection, close_pool
from core.auth_utils import get_password_hash
import uuid

load_dotenv(override=True)


def criar_usuario_admin():
    conn = get_db_connection()
    if not conn:
        print("❌ Falha ao conectar no banco.")
        return

    NOME_ADMIN = os.getenv("ADMIN_NOME", "Administrador Sistema")
    EMAIL_ADMIN = os.getenv("ADMIN_EMAIL")
    SENHA_ADMIN = os.getenv("ADMIN_SENHA")

    if not EMAIL_ADMIN or not SENHA_ADMIN:
        print("❌ Defina ADMIN_EMAIL e ADMIN_SENHA no .env antes de rodar.")
        release_connection(conn)
        sys.exit(1)

    if len(SENHA_ADMIN) < 8:
        print("❌ ADMIN_SENHA deve ter pelo menos 8 caracteres.")
        release_connection(conn)
        sys.exit(1)

    try:
        cur = conn.cursor()
        print(f"🚀 Criando usuário Admin: {EMAIL_ADMIN}...")

        # 1. Gerar Hash da Senha
        senha_hash = get_password_hash(SENHA_ADMIN)
        usuario_uuid = str(uuid.uuid4())

        # 2. Inserir na tabela Usuarios
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario, data_cadastro) 
            VALUES (%s, %s, %s, %s, 'Admin', CURRENT_TIMESTAMP) 
            ON CONFLICT (email) DO UPDATE 
            SET senha = EXCLUDED.senha, tipo_usuario = 'Admin'
            RETURNING usuario_id
        """, (usuario_uuid, NOME_ADMIN, EMAIL_ADMIN, senha_hash))
        
        res = cur.fetchone()
        conn.commit()

        print("\n✅ SUCESSO! Usuário Administrador criado/atualizado.")
        print(f"👉 Login: {EMAIL_ADMIN}")
        print("👉 Senha: (definida via ADMIN_SENHA no .env — não impressa)")
        print("\nUse estas credenciais para acessar o portal web em http://localhost:3000")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao criar admin: {e}")
    finally:
        release_connection(conn)

if __name__ == "__main__":
    try:
        criar_usuario_admin()
    finally:
        close_pool()
