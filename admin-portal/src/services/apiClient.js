import axios from 'axios';
import { API_URL } from '../config/api';

const STORAGE_KEYS = {
  token: 'admin_token',
  refresh: 'admin_refresh_token',
  user: 'admin_user',
};

export function clearAdminSession() {
  localStorage.removeItem(STORAGE_KEYS.token);
  localStorage.removeItem(STORAGE_KEYS.refresh);
  localStorage.removeItem(STORAGE_KEYS.user);
}

export function saveAdminSession(data) {
  localStorage.setItem(STORAGE_KEYS.token, data.access_token);
  localStorage.setItem(STORAGE_KEYS.refresh, data.refresh_token);
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(data));
}

export function readAdminSession() {
  const token = localStorage.getItem(STORAGE_KEYS.token);
  const refresh = localStorage.getItem(STORAGE_KEYS.refresh);
  const userRaw = localStorage.getItem(STORAGE_KEYS.user);
  if (!token || !refresh || !userRaw) {
    return { ok: false, partial: !!(token || refresh || userRaw) };
  }
  try {
    return { ok: true, user: JSON.parse(userRaw), token, refresh };
  } catch {
    return { ok: false, partial: true };
  }
}

export const apiClient = axios.create({ baseURL: API_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(STORAGE_KEYS.token);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

async function tryRefreshAdminToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = localStorage.getItem(STORAGE_KEYS.refresh);
    if (!refresh) return null;
    try {
      const response = await axios.post(
        `${API_URL}/auth/refresh`,
        { refresh_token: refresh },
        { headers: { 'Content-Type': 'application/json' } }
      );
      const data = response.data;
      if (data?.access_token && data?.refresh_token) {
        localStorage.setItem(STORAGE_KEYS.token, data.access_token);
        localStorage.setItem(STORAGE_KEYS.refresh, data.refresh_token);
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

export function installAuthInterceptor(onSessionExpired) {
  const id = apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      const status = error.response?.status;

      if (
        status !== 401 ||
        !originalRequest ||
        originalRequest._retry ||
        originalRequest.url?.includes('/auth/refresh') ||
        originalRequest.url?.includes('/auth/login')
      ) {
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      const newToken = await tryRefreshAdminToken();
      if (!newToken) {
        onSessionExpired?.();
        return Promise.reject(error);
      }

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return apiClient(originalRequest);
    }
  );

  return () => apiClient.interceptors.response.eject(id);
}

export function extractErrorMessage(err, fallback = 'Falha no servidor') {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail) return JSON.stringify(detail);
  return fallback;
}
