import { apiClient } from './apiClient';

export async function listarTurmasCompletas() {
  const res = await apiClient.get('/admin/turmas-completas');
  return res.data;
}

export async function criarTurma(payload) {
  const res = await apiClient.post('/admin/turmas', payload);
  return res.data;
}

export async function deletarTurma(turma_id) {
  await apiClient.delete(`/admin/turmas/${turma_id}`);
}

export async function atribuirProfessor(turma_id, professor_id) {
  await apiClient.patch(`/admin/turmas/${turma_id}/professor`, {
    professor_id: professor_id || null,
  });
}

export async function importarAlunosCSV(turma_id, file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiClient.post(`/admin/turmas/${turma_id}/importar-alunos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function matricularAlunos(turma_id, aluno_ids) {
  const res = await apiClient.post(`/admin/turmas/${turma_id}/matricular-alunos`, {
    aluno_ids,
  });
  return res.data;
}
