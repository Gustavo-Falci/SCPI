import * as SecureStore from "expo-secure-store";

const API_URL = "http://192.168.15.149:8000";

export { API_URL };

async function getAuthHeaders() {
  const token = await SecureStore.getItemAsync("access_token");
  return {
    Authorization: `Bearer ${token}`,
  };
}

// --- AUTH ---

export async function loginRequest(email, senha) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", senha);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao fazer login");
  return data;
}

// --- USUARIOS ---

export async function buscarPerfilUsuario() {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/usuarios/me`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar perfil");
  return data;
}

export async function buscarFuncionarioLogado(token) {
  const response = await fetch(`${API_URL}/usuarios/me/funcionario`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar funcionário");
  return data;
}

// --- EMPRESAS ---

export async function buscarEmpresa(empresaId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/empresas/${empresaId}`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar empresa");
  return data;
}

// --- SETORES ---

export async function buscarSetores(empresaId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/setores/${empresaId}`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar setores");
  return data.setores;
}

export async function criarSetor(empresaId, nome) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/empresas/${empresaId}/setores`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ nome }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao criar setor");
  return data;
}

// --- FUNCIONARIOS ---

export async function buscarFuncionarios(empresaId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/funcionarios/${empresaId}`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar funcionários");
  return data.funcionarios;
}

export async function criarFuncionario(dados, fotoUri) {
  const headers = await getAuthHeaders();
  const formData = new FormData();
  formData.append("nome", dados.nome);
  formData.append("email", dados.email);
  formData.append("matricula", dados.matricula);
  formData.append("empresa_id", dados.empresa_id);
  formData.append("setor_id", dados.setor_id);
  if (dados.cargo) formData.append("cargo", dados.cargo);
  formData.append("foto", {
    uri: fotoUri,
    name: "funcionario.jpg",
    type: "image/jpeg",
  });

  const response = await fetch(`${API_URL}/funcionarios`, {
    method: "POST",
    body: formData,
    headers: { ...headers, "Content-Type": "multipart/form-data" },
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao criar funcionário");
  return data;
}

// --- PONTO ---

export async function registrarPonto(fotoUri) {
  const formData = new FormData();
  formData.append("foto", {
    uri: fotoUri,
    name: "ponto.jpg",
    type: "image/jpeg",
  });

  const response = await fetch(`${API_URL}/ponto/registrar`, {
    method: "POST",
    body: formData,
    headers: { "Content-Type": "multipart/form-data" },
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao registrar ponto");
  return data;
}

export async function buscarHistorico(funcionarioId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/ponto/historico/${funcionarioId}`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar histórico");
  return data.registros;
}

export async function buscarRegistrosDia(empresaId) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_URL}/ponto/hoje/${empresaId}`, { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao buscar registros do dia");
  return data.registros;
}
