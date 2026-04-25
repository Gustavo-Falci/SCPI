import { apiClient } from './apiClient';

export async function listarProfessores() {
  const res = await apiClient.get('/admin/professores');
  return res.data;
}

export async function criarProfessor(payload) {
  const res = await apiClient.post('/admin/usuarios/professor', payload);
  return res.data;
}

export async function deletarProfessor(professor_id) {
  await apiClient.delete(`/admin/professores/${professor_id}`);
}
