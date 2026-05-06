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

/**
 * Mensagens amigáveis (PT-BR) por status HTTP.
 * Usadas como fallback quando o backend não envia `detail` legível.
 */
const HTTP_STATUS_MESSAGES = {
  400: 'Requisição inválida. Confira os dados informados.',
  401: 'Sua sessão expirou. Faça login novamente.',
  403: 'Você não tem permissão para acessar este recurso.',
  404: 'Recurso não encontrado.',
  408: 'A requisição demorou demais. Tente novamente.',
  409: 'Conflito ao processar a solicitação.',
  413: 'Arquivo grande demais para envio.',
  415: 'Tipo de arquivo não suportado.',
  422: 'Dados inválidos. Confira o formulário.',
  429: 'Muitas requisições em pouco tempo. Aguarde alguns segundos.',
  500: 'Erro interno do servidor. Tente novamente em instantes.',
  502: 'Servidor indisponível no momento.',
  503: 'Serviço temporariamente indisponível.',
  504: 'O servidor demorou para responder. Tente novamente.',
};

/**
 * Formata um erro de validação Pydantic v2.
 * Aceita itens como: { loc: ["body","email"], msg: "field required", type: "..." }
 */
function formatPydanticErrors(arr) {
  return arr
    .map((item) => {
      const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== 'body').join('.') : '';
      const msg = item.msg || item.message || 'inválido';
      return loc ? `${loc}: ${msg}` : msg;
    })
    .join(' | ');
}

/**
 * Extrai mensagem amigável de um erro do axios/fetch.
 *
 * Trata:
 *  - Sem resposta (rede offline)
 *  - detail string (formato simples)
 *  - detail dict { detail, error_code } (formato novo do backend)
 *  - detail array (Pydantic validation errors)
 *  - Status HTTP comuns (404, 403, 401, 429, 5xx)
 */
export function extractErrorMessage(err, fallback = 'Falha no servidor') {
  // Sem resposta: provável erro de rede / CORS / timeout
  if (!err?.response) {
    if (err?.code === 'ECONNABORTED') return 'Tempo de resposta esgotado. Tente novamente.';
    if (err?.message?.toLowerCase().includes('network')) {
      return 'Sem conexão com o servidor. Verifique sua internet.';
    }
    return err?.message || fallback;
  }

  const status = err.response.status;
  const data = err.response.data;
  const detail = data?.detail;

  // Backend padronizado: detail é objeto { detail, error_code }
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && typeof detail.detail === 'string') {
    return detail.detail;
  }

  // Pydantic v2: detail é array de erros
  if (Array.isArray(detail) && detail.length > 0) {
    return formatPydanticErrors(detail);
  }

  // String simples
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  // Mensagem direta no body (alguns endpoints)
  if (typeof data?.message === 'string') return data.message;

  // Fallback por status HTTP
  if (HTTP_STATUS_MESSAGES[status]) return HTTP_STATUS_MESSAGES[status];

  return fallback;
}

/**
 * Retorna o `error_code` (string) embutido pelo backend, se disponível.
 * Útil para fluxos que precisam reagir a um código específico.
 */
export function extractErrorCode(err) {
  const detail = err?.response?.data?.detail;
  if (detail && typeof detail === 'object' && typeof detail.error_code === 'string') {
    return detail.error_code;
  }
  return null;
}
