from database import get_db_cursor
from auth_utils import get_password_hash

def force_update():
    # 1. Gerar o hash Bcrypt oficial para 'admin123'
    nova_senha_hash = get_password_hash('admin123')
    
    try:
        with get_db_cursor(commit=True) as cur:
            print(f"🔐 Gerando novo hash Bcrypt para admin...")
            
            # 2. Atualiza diretamente o registro existente
            cur.execute("""
                UPDATE Usuarios 
                SET senha = %s, 
                    tipo_usuario = 'Admin',
                    nome = 'Administrador Sistema'
                WHERE LOWER(email) = 'admin@scpi.com'
            """, (nova_senha_hash,))
            
            if cur.rowcount > 0:
                print("✅ SUCESSO! Senha do admin@scpi.com atualizada para 'admin123'.")
                print(f"DEBUG: Novo Hash aplicado: {nova_senha_hash[:20]}...")
            else:
                print("❌ ERRO: Usuário admin@scpi.com não foi localizado no banco.")
                
    except Exception as e:
        print(f"❌ Erro crítico: {e}")

if __name__ == "__main__":
    force_update()
