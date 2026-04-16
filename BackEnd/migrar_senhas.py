from database import get_db_cursor
from auth_utils import get_password_hash
import time

def migrar_senhas_para_hash():
    try:
        # Usando o context manager que já retorna dicionários
        with get_db_cursor(commit=True) as cur:
            print("🚀 Iniciando migração de senhas para Bcrypt...")

            # 1. Busca usuários
            cur.execute("SELECT usuario_id, email, senha FROM Usuarios")
            usuarios = cur.fetchall()
            
            count = 0
            for user in usuarios:
                user_id = user['usuario_id']
                senha_atual = user['senha']
                
                # Verifica se já é um hash (Bcrypt começa com $2b$ ou $2a$)
                if not str(senha_atual).startswith('$2b$'):
                    print(f"🔐 Criptografando senha de: {user['email']}")
                    novo_hash = get_password_hash(senha_atual)
                    
                    cur.execute("UPDATE Usuarios SET senha = %s WHERE usuario_id = %s", (novo_hash, user_id))
                    count += 1

            print(f"\n✅ SUCESSO! {count} senhas foram migradas para hashes seguros.")

    except Exception as e:
        print(f"❌ Erro na migração: {e}")

if __name__ == "__main__":
    migrar_senhas_para_hash()
