from database import get_db_connection
from auth_utils import get_password_hash
import uuid

def criar_usuario_admin():
    conn = get_db_connection()
    if not conn: 
        print("❌ Falha ao conectar no banco.")
        return

    # CONFIGURAÇÕES DO ADMIN
    NOME_ADMIN = "Administrador Sistema"
    EMAIL_ADMIN = "admin@scpi.com"
    SENHA_ADMIN = "admin123" # Recomendo alterar após o primeiro acesso

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
        print(f"👉 Senha: {SENHA_ADMIN}")
        print("\nUse estas credenciais para acessar o portal web em http://localhost:3000")

    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao criar admin: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    criar_usuario_admin()
