// Portal não armazena tokens no localStorage. A sessão flui via cookies
// HttpOnly (scpi_access / scpi_refresh) emitidos pelo backend. localStorage
// guarda apenas o perfil público do usuário para renderização imediata da UI.
const K = { user: 'admin_user' };

// Chaves legadas — limpas em qualquer clearSession para não deixar tokens
// antigos parados em localStorage de usuários que já passaram por versões
// anteriores do portal.
const LEGACY_KEYS = ['admin_token', 'admin_refresh_token'];

const USER_PROFILE_FIELDS = [
  'user_role',
  'user_id',
  'user_name',
  'user_email',
  'user_ra',
  'primeiro_acesso',
  'face_cadastrada',
];

function pickUserProfile(data) {
  if (!data || typeof data !== 'object') return null;
  const profile = {};
  for (const key of USER_PROFILE_FIELDS) {
    if (key in data) profile[key] = data[key];
  }
  return profile;
}

export const getUser = () => {
  try { return JSON.parse(localStorage.getItem(K.user)); } catch { return null; }
};

export function saveSession(data) {
  const profile = pickUserProfile(data);
  if (profile) localStorage.setItem(K.user, JSON.stringify(profile));
}

export function clearSession() {
  localStorage.removeItem(K.user);
  for (const legacy of LEGACY_KEYS) localStorage.removeItem(legacy);
}

export function readSession() {
  const user = getUser();
  if (!user) {
    if (LEGACY_KEYS.some(k => localStorage.getItem(k))) clearSession();
    return { ok: false };
  }
  return { ok: true, user };
}
