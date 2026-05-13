const K = { token: 'admin_token', refresh: 'admin_refresh_token', user: 'admin_user' };

export const getToken = () => localStorage.getItem(K.token);
export const getRefreshToken = () => localStorage.getItem(K.refresh);
export const getUser = () => { try { return JSON.parse(localStorage.getItem(K.user)); } catch { return null; } };

export function saveSession(data) {
  localStorage.setItem(K.token, data.access_token);
  localStorage.setItem(K.refresh, data.refresh_token);
  localStorage.setItem(K.user, JSON.stringify(data));
}

export function updateTokens(access_token, refresh_token) {
  localStorage.setItem(K.token, access_token);
  localStorage.setItem(K.refresh, refresh_token);
}

export function clearSession() {
  localStorage.removeItem(K.token);
  localStorage.removeItem(K.refresh);
  localStorage.removeItem(K.user);
}

export function readSession() {
  const token = getToken();
  const refresh = getRefreshToken();
  const user = getUser();
  if (!token || !refresh || !user) {
    if (token || refresh || user) clearSession();
    return { ok: false };
  }
  return { ok: true, user, token, refresh };
}
