import { loadGlobal, saveGlobal } from './persist.js';

const GLOBAL_DEFAULTS = { activeTab: 'turmas', turno: 'Matutino', semestre: 'Todos' };
const hydrated = loadGlobal(GLOBAL_DEFAULTS);

const state = {
  turno: hydrated.turno,
  semestre: hydrated.semestre,
  activeTab: hydrated.activeTab,
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

const GLOBAL_KEYS = ['activeTab', 'turno', 'semestre'];

export function setState(updates) {
  Object.assign(state, updates);
  const globalPatch = {};
  for (const k of GLOBAL_KEYS) {
    if (k in updates) globalPatch[k] = state[k];
  }
  if (Object.keys(globalPatch).length) saveGlobal(globalPatch);
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
