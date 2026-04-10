import requests
import pytest

BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="module")
def admin_token():
    """Faz login como Admin e retorna o token."""
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin@teste.com",
        "password": "123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]

def test_health_check():
    """Testa o endpoint raiz."""
    response = requests.get(BASE_URL)
    assert response.status_code == 200
    assert response.json() == {"mensagem": "API Ponto Facial Empresarial está rodando!"}

def test_login_admin():
    """Testa o login do admin."""
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin@teste.com",
        "password": "123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user_role"] == "Admin"

def test_rota_protegida_sem_token():
    """Testa o acesso a uma rota protegida sem token."""
    response = requests.get(f"{BASE_URL}/usuarios/me")
    assert response.status_code == 401  # Deve ser Unauthorized

def test_rota_protegida_com_token(admin_token):
    """Testa o acesso a uma rota protegida com token de admin."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/usuarios/me", headers=headers)
    assert response.status_code == 200
    # O email do usuário logado deve ser o do payload do token.
    # A rota /usuarios/me busca pelo usuario_id do token.
    # O usuário admin criado em setup_db tem o email "admin@teste.com"
    assert response.json()["email"] == "admin@teste.com"

def test_listar_funcionarios(admin_token):
    """Testa o endpoint de listar funcionários."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # O endpoint de perfil do usuário não retorna o empresa_id diretamente.
    # O vínculo está na tabela Admin_Empresas.
    # Para o teste, vamos pegar o empresa_id de um dos funcionários,
    # já que todos são da mesma empresa de teste.

    # Primeiro, buscar o perfil do admin para garantir que está logado
    perfil_response = requests.get(f"{BASE_URL}/usuarios/me", headers=headers)
    assert perfil_response.status_code == 200
    admin_data = perfil_response.json()
    assert admin_data['email'] == "admin@teste.com"

    # Como o admin não está diretamente ligado a uma empresa no seu perfil de usuário
    # (o vínculo é feito pela tabela Admin_Empresas), vamos usar uma abordagem diferente.
    # O ideal seria um endpoint que retornasse as empresas do admin, mas para o teste,
    # vamos buscar a empresa pelo CNPJ de teste.

    # A API não tem um endpoint para buscar empresa por CNPJ (só internamente).
    # O teste mais simples é logar como funcionário e pegar a empresa_id.

    # Login como funcionário para obter o empresa_id
    func_response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "joao@teste.com",
        "password": "123"
    })
    assert func_response.status_code == 200
    empresa_id = func_response.json()["empresa_id"]

    # Agora, listar os funcionários da empresa com o token de admin
    response = requests.get(f"{BASE_URL}/funcionarios/{empresa_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "funcionarios" in data
    assert len(data["funcionarios"]) >= 2 # Deve ter os 2 funcionários de teste
