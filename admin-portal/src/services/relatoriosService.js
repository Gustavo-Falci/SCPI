import { apiClient } from './apiClient';

export async function listarRelatorios() {
  const res = await apiClient.get('/admin/relatorios/chamadas');
  return res.data;
}

export async function detalheRelatorio(chamada_id) {
  const res = await apiClient.get(`/admin/relatorios/chamadas/${chamada_id}`);
  return res.data;
}
