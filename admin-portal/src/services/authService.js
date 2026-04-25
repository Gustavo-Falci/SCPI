import axios from 'axios';
import { API_URL } from '../config/api';
import { apiClient, clearAdminSession, saveAdminSession } from './apiClient';

export async function login(email, password) {
  const params = new URLSearchParams();
  params.append('username', email.trim());
  params.append('password', password);

  const res = await axios.post(`${API_URL}/auth/login`, params.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  saveAdminSession(res.data);
  return res.data;
}

export async function logout() {
  const refresh = localStorage.getItem('admin_refresh_token');
  if (refresh) {
    try {
      await apiClient.post('/auth/logout', { refresh_token: refresh });
    } catch {
      // limpeza local é autoritativa
    }
  }
  clearAdminSession();
}

export { clearAdminSession, saveAdminSession, readAdminSession } from './apiClient';
