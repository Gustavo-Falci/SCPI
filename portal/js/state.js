const state = {
  turno: 'Matutino',
  semestre: 'Todos',
  activeTab: 'turmas',
  user: null,
  cache: {
    turmas: null,
    professores: null,
    alunos: null,
    grade: null,
    relatorios: null,
    rostos_rek: null,
    rostos_s3: null,
  },
};

const listeners = {};

export const getState = () => state;

export function setState(updates) {
  Object.assign(state, updates);
  Object.keys(updates).forEach(k => listeners[k]?.forEach(fn => fn(state[k])));
}

export function invalidate(...keys) {
  keys.forEach(k => { if (k in state.cache) state.cache[k] = null; });
}

export function on(key, fn) {
  if (!listeners[key]) listeners[key] = [];
  listeners[key].push(fn);
  return () => { listeners[key] = listeners[key].filter(f => f !== fn); };
}
