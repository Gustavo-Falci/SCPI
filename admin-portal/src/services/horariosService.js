import { apiClient } from './apiClient';

export async function listarHorariosTodos() {
  const res = await apiClient.get('/admin/horarios-todos');
  return res.data;
}

export async function criarHorario(payload) {
  const res = await apiClient.post('/admin/horarios', payload);
  return res.data;
}

export async function deletarHorario(horario_id) {
  await apiClient.delete(`/admin/horarios/${horario_id}`);
}

export function detectarConflitoHorario(grade, { turma_id, dia_semana, inicio, fim }) {
  return grade.find(
    (g) =>
      g.turma_id === turma_id &&
      g.dia_semana === dia_semana &&
      inicio < g.fim &&
      fim > g.inicio
  );
}
