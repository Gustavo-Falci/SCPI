import { apiClient } from './apiClient';

export async function listarAlunos(params = {}) {
  const res = await apiClient.get('/admin/alunos', { params });
  return res.data;
}

export async function criarAluno(payload) {
  const res = await apiClient.post('/admin/usuarios/aluno', payload);
  return res.data;
}

export async function atualizarAluno(aluno_id, payload) {
  const res = await apiClient.patch(`/admin/alunos/${aluno_id}`, payload);
  return res.data;
}

export async function deletarAluno(aluno_id) {
  await apiClient.delete(`/admin/alunos/${aluno_id}`);
}
