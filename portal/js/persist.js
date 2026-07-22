// Persistência de UI do portal em sessionStorage: sobrevive ao F5, some ao
// fechar a aba, e é independente entre abas do navegador. Falha silenciosa se
// o storage estiver bloqueado (mesma filosofia de scpi.sidebar.collapsed).
const KEY = 'scpi.portal.ui';

function readAll() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

function writeAll(obj) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(obj));
  } catch {
    /* storage bloqueado: degrada para sessão só-em-memória */
  }
}

export function loadGlobal(defaults) {
  const all = readAll();
  return { ...defaults, ...all.global };
}

export function saveGlobal(patch) {
  const all = readAll();
  all.global = { ...all.global, ...patch };
  writeAll(all);
}

export function loadTab(tabId, defaults) {
  const all = readAll();
  return { ...defaults, ...(all.tabs && all.tabs[tabId]) };
}

export function saveTab(tabId, patch) {
  const all = readAll();
  all.tabs = all.tabs || {};
  all.tabs[tabId] = { ...all.tabs[tabId], ...patch };
  writeAll(all);
}

export function clearUI() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* nada a fazer */
  }
}
