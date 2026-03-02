from database import get_db_cursor
import uuid

def test():
    with get_db_cursor(commit=False) as cur:
        usuario_uuid = str(uuid.uuid4())
        print("Executando insert...")
        cur.execute("""
            INSERT INTO Usuarios (usuario_id, nome, email, senha, tipo_usuario)
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING usuario_id
        """, (usuario_uuid, 'Teste Debug', f'debug_{usuario_uuid}@teste.com', '123', 'Aluno'))
        
        row = cur.fetchone()
        print(f"Resultado do fetchone(): {row}")
        print(f"Tipo do resultado: {type(row)}")

if __name__ == "__main__":
    test()
