from database import get_db_cursor
from auth_utils import get_password_hash
import uuid

def reset():
    h = get_password_hash('admin123')
    try:
        with get_db_cursor(commit=True) as cur:
            # Limpa qualquer admin antigo
            cur.execute("DELETE FROM Usuarios WHERE LOWER(email) = 'admin@scpi.com'")
            
            # Cria novo admin oficial
            uid = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario) 
                VALUES (%s, 'Administrador', 'admin@scpi.com', %s, 'Admin')
            """, (uid, h))
            print("✅ Usuário admin@scpi.com criado com senha: admin123")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    reset()
