import { API_URL } from './config.js';
import { getToken, getRefreshToken, updateTokens, clearSession } from './auth.js';

const HTTP_MSGS = {
  400: 'Requisição inválida. Confira os dados informados.',
  401: 'Sessão expirada. Faça login novamente.',
  403: 'Sem permissão para este recurso.',
  404: 'Recurso não encontrado.',
  409: 'Conflito ao processar a solicitação.',
  422: 'Dados inválidos. Confira o formulário.',
  429: 'Muitas requisições. Aguarde alguns segundos.',
  500: 'Erro interno do servidor.',
  502: 'Servidor indisponível.',
  503: 'Serviço temporariamente indisponível.',
  504: 'Servidor demorou para responder.',
};

export function extractError(err) {
  if (typeof err === 'string') return err;
  const detail = err?.detail;
  if (detail) {
    if (typeof detail === 'object' && !Array.isArray(detail) && typeof detail.detail === 'string') return detail.detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map(e => { const loc = (e.loc || []).filter(p => p !== 'body').join('.'); return loc ? `${loc}: ${e.msg}` : e.msg; }).join(' | ');
    }
    if (typeof detail === 'string') return detail;
  }
  if (err?.message) return err.message;
  return 'Erro desconhecido';
}

let _onExpired = null;
export const setOnExpired = fn => { _onExpired = fn; };

let refreshPromise = null;

async function refreshTokens() {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return null;
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (data.access_token && data.refresh_token) {
        updateTokens(data.access_token, data.refresh_token);
        return data.access_token;
      }
      return null;
    } catch { return null; }
  })();
  try { return await refreshPromise; } finally { refreshPromise = null; }
}

async function request(path, opts = {}, retry = true) {
  const token = getToken();
  const isFormData = opts.body instanceof FormData;
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(opts.headers || {}),
  };

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  } catch {
    throw { detail: 'Sem conexão com o servidor.' };
  }

  if (res.status === 401 && retry) {
    const newToken = await refreshTokens();
    if (!newToken) { clearSession(); _onExpired?.(); throw { detail: HTTP_MSGS[401] }; }
    return request(path, opts, false);
  }

  if (res.status === 204) return null;

  let data;
  try { data = await res.json(); } catch { data = null; }

  if (!res.ok) {
    throw data || { detail: HTTP_MSGS[res.status] || `Erro ${res.status}` };
  }

  return data;
}

export const api = {
  get: (path) => request(path, { method: 'GET' }),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  postForm: (path, params) => request(path, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(params) }),
  postMultipart: (path, formData) => request(path, { method: 'POST', body: formData }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
  del: (path, body = null) => request(path, { method: 'DELETE', ...(body ? { body: JSON.stringify(body) } : {}) }),
};
