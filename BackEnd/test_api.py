import requests

def test_register():
    url = "http://localhost:8000/auth/register"
    dados = {
        "nome": "Aluno API",
        "email": "teste2@api.com",
        "senha": "senha",
        "tipo_usuario": "Aluno",
        "ra": "API123"
    }
    
    try:
        response = requests.post(url, json=dados)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro ao conectar com a API: {e}")

if __name__ == "__main__":
    test_register()
