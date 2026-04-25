import { apiClient } from './apiClient';

export async function listarAlunos(params = {}) {
  const res = await apiClient.get('/admin/alunos', { params });
  return res.data;
}

export async function criarAluno(payload) {
  const res = await apiClient.post('/admin/usuarios/aluno', payload);
  return res.data;
}
