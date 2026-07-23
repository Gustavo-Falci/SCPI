import { toast } from './toast.js';
import { confirm } from './confirm.js';
import { getState, setState } from './state.js';
import { clearUI } from './persist.js';
import { readSession, saveSession, clearSession } from './auth.js';
import { api, setOnExpired, extractError, validateSession } from './api.js';
import { icon } from './icons.js';
import { escapeHtml } from './utils.js';
import { closeModal } from './modal.js';
import { skeletons } from './skeleton.js';
import { runCreate, clearCreate } from './registry.js';
import { mount as mountTurmas } from './tabs/turmas.js';
import { mount as mountHorarios } from './tabs/horarios.js';
import { mount as mountProfessores } from './tabs/professores.js';
import { mount as mountAlunos } from './tabs/alunos.js';
import { mount as mountRelatorios } from './tabs/relatorios.js';
import { mount as mountRostos } from './tabs/rostos.js';

const TABS = [
  { id: 'turmas',      label: 'Turmas',    bLabel: 'Turmas',    iconName: 'graduation-cap', title: 'Turmas',          subtitle: 'Gestão de disciplinas e matrículas',   mount: mountTurmas,      skeleton: () => skeletons.twoCol(6) },
  { id: 'horarios',    label: 'Horários',  bLabel: 'Grade',     iconName: 'calendar',       title: 'Grade Horária',   subtitle: 'Configuração da grade semanal',         mount: mountHorarios,    skeleton: () => skeletons.grid() },
  { id: 'professores', label: 'Professores',bLabel: 'Profs',    iconName: 'users',          title: 'Professores',     subtitle: 'Cadastro e gestão de professores',      mount: mountProfessores, skeleton: () => skeletons.twoCol(5) },
  { id: 'alunos',      label: 'Alunos',    bLabel: 'Alunos',    iconName: 'user',           title: 'Alunos',          subtitle: 'Cadastro e gestão de alunos',           mount: mountAlunos,      skeleton: () => skeletons.twoCol(5) },
  { id: 'relatorios',  label: 'Relatórios',bLabel: 'Relat.',    iconName: 'file-text',      title: 'Relatórios',      subtitle: 'Histórico de chamadas e presenças',     mount: mountRelatorios,  skeleton: () => skeletons.list(8) },
  { id: 'rostos',      label: 'Biometria', bLabel: 'Rostos',    iconName: 'scan-face',      title: 'Banco de Rostos', subtitle: 'Gestão do banco biométrico AWS',        mount: mountRostos,      skeleton: () => skeletons.panels() },
];

const TABS_WITH_CREATE = new Set(['turmas', 'professores', 'alunos']);

// Bottom nav: máx 5 itens (UX guideline bottom-nav-limit)
// 4 tabs principais + botão "Mais" que abre sidebar
const BOTTOM_NAV_TABS = ['turmas', 'alunos', 'professores', 'relatorios'];

function buildSidebar() {
  const nav = document.getElementById('sidebar-nav');
  nav.innerHTML = TABS.map(t => `
    <button data-tab="${t.id}" data-label="${t.label}" class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-black text-sm transition-all text-left text-gray-500 hover:text-white hover:bg-white/5">
      ${icon(t.iconName, 18)}<span>${t.label}</span>
    </button>
  `).join('');
  nav.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
}

function buildBottomNav() {
  const nav = document.getElementById('bottom-nav');
  if (!nav) return;
  const mainTabs = TABS.filter(t => BOTTOM_NAV_TABS.includes(t.id));
  nav.innerHTML = mainTabs.map(t => `
    <button data-tab="${t.id}" class="bnav-item" aria-label="${t.label}">
      ${icon(t.iconName, 20)}
      <span>${t.bLabel}</span>
      <div class="bnav-dot"></div>
    </button>
  `).join('') + `
    <button id="bnav-more" class="bnav-item" aria-label="Mais opções">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
      <span>Mais</span>
      <div class="bnav-dot"></div>
    </button>
  `;
  nav.querySelectorAll('.bnav-item[data-tab]').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
  document.getElementById('bnav-more').addEventListener('click', openSidebar);
}

function setActiveNav(tabId) {
  document.querySelectorAll('.nav-item').forEach(btn => {
    const a = btn.dataset.tab === tabId;
    btn.className = `nav-item w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-black text-sm transition-all text-left ${a ? 'bg-accent/10 text-accent border border-accent/20' : 'text-gray-500 hover:text-white hover:bg-white/5'}`;
  });
  document.querySelectorAll('.bnav-item[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  // "Mais" fica ativo se tab atual não está no bottom nav principal
  document.getElementById('bnav-more')?.classList.toggle('active', !BOTTOM_NAV_TABS.includes(tabId));
  // FAB: show only for tabs with create form
  const fab = document.getElementById('fab');
  if (fab) fab.classList.toggle('hidden', !TABS_WITH_CREATE.has(tabId));
}

function updateHeader(tab) {
  document.getElementById('header-title').textContent = tab.title;
  document.getElementById('header-subtitle').textContent = tab.subtitle;
}

// Aba salva pode apontar para um id removido em versão futura: valida e cai em turmas.
function tabValida(id) {
  return TABS.some(t => t.id === id) ? id : 'turmas';
}

function switchTab(tabId) {
  const tab = TABS.find(t => t.id === tabId);
  if (!tab) return;
  clearCreate();
  setState({ activeTab: tabId });
  setActiveNav(tabId);
  updateHeader(tab);
  updateFiltersVisibility(tabId);
  closeSidebar();

  const content = document.getElementById('tab-content');
  content.innerHTML = tab.skeleton ? tab.skeleton() : `<div class="flex-1 flex items-center justify-center"><div class="spin opacity-50">${icon('loader', 28)}</div></div>`;
  tab.mount(content).catch(err => {
    content.innerHTML = `<div class="tab-anim flex-1 flex items-center justify-center text-red-400 font-black text-sm">${escapeHtml(extractError(err))}</div>`;
  });
}

function openSidebar() {
  document.getElementById('sidebar').classList.remove('-translate-x-full');
  document.getElementById('sidebar-overlay').classList.remove('hidden');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.add('-translate-x-full');
  document.getElementById('sidebar-overlay').classList.add('hidden');
}

// Colapso desktop. A classe mora no <html>, não no <aside>: o script anti-flash
// do index.html roda no <head>, quando o <aside> ainda não existe no DOM.
function isSidebarCollapsed() {
  return document.documentElement.classList.contains('sidebar-collapsed');
}

function applyCollapsed(collapsed) {
  document.documentElement.classList.toggle('sidebar-collapsed', collapsed);
  const btn = document.getElementById('sidebar-toggle');
  if (!btn) return;
  btn.setAttribute('aria-expanded', String(!collapsed));
  btn.setAttribute('aria-label', collapsed ? 'Expandir menu' : 'Recolher menu');
}

const SIDEBAR_KEY = 'scpi.sidebar.collapsed';

function saveCollapsed(collapsed) {
  try {
    if (collapsed) localStorage.setItem(SIDEBAR_KEY, '1');
    else localStorage.removeItem(SIDEBAR_KEY);
  } catch (e) { /* cookies bloqueados: o estado vale só para esta página */ }
}

function initSidebarToggle() {
  const btn = document.getElementById('sidebar-toggle');
  btn.innerHTML = icon('chevron-left', 18);
  // A classe já veio do script do <head>; aqui só sincronizamos o ARIA.
  applyCollapsed(isSidebarCollapsed());
  btn.addEventListener('click', () => {
    const next = !isSidebarCollapsed();
    applyCollapsed(next);
    saveCollapsed(next);
  });
}

function initKeyboard() {
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    const confirmOverlay = document.getElementById('confirm-overlay');
    const modalOverlay = document.getElementById('modal-overlay');
    if (!confirmOverlay.classList.contains('hidden')) {
      confirmOverlay.classList.add('hidden');
    } else if (!modalOverlay.classList.contains('hidden')) {
      closeModal();
    } else if (!document.getElementById('sidebar').classList.contains('-translate-x-full')) {
      closeSidebar();
    }
  });
}

// style inline em vez de classe: vence qualquer utilitário de display e não
// depende da ordem em que o Tailwind CDN gerou .hidden/.flex.
function hideBoot() {
  const boot = document.getElementById('view-boot');
  if (boot) boot.style.display = 'none';
}

function showDashboard(user) {
  hideBoot();
  document.getElementById('view-login').classList.add('hidden');
  document.getElementById('view-dashboard').classList.remove('hidden');
  document.getElementById('sidebar-username').textContent = user.user_name || user.nome || 'Administrador';
  buildSidebar();
  buildBottomNav();
  switchTab(tabValida(getState().activeTab));
}

function showLogin() {
  hideBoot();
  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-login').classList.remove('hidden');
  // Zera a navegação móvel para não sobrar estado da sessão anterior caso o
  // dashboard volte a ser exibido para outro usuário.
  const nav = document.getElementById('bottom-nav');
  if (nav) nav.innerHTML = '';
  document.getElementById('fab')?.classList.add('hidden');
  clearUI();
  clearSession();
}

const FILTER_TABS = new Set(['turmas', 'horarios', 'relatorios']);

function updateTurnoUI(turno) {
  document.querySelectorAll('.turno-btn').forEach(btn => {
    const isMat = btn.dataset.turno === 'Matutino';
    const isActive = btn.dataset.turno === turno;
    btn.classList.remove('active-mat', 'active-not');
    if (isActive) btn.classList.add(isMat ? 'active-mat' : 'active-not');
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
}

function updateSemestreUI(semestre) {
  document.querySelectorAll('.sem-btn').forEach(btn => {
    const isActive = btn.dataset.sem === semestre;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    if (isActive) btn.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  });
}

function updateFiltersVisibility(tabId) {
  const row = document.getElementById('filters-row');
  if (!row) return;
  row.classList.toggle('inactive', !FILTER_TABS.has(tabId));
}

function initFilters() {
  const state = getState();
  updateTurnoUI(state.turno);
  updateSemestreUI(state.semestre);

  document.querySelectorAll('.turno-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setState({ turno: btn.dataset.turno });
      updateTurnoUI(btn.dataset.turno);
      switchTab(getState().activeTab);
    });
  });

  document.querySelectorAll('.sem-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      setState({ semestre: btn.dataset.sem });
      updateSemestreUI(btn.dataset.sem);
      switchTab(getState().activeTab);
    });
  });
}

async function initLogin() {
  const form = document.getElementById('login-form');
  const emailEl = document.getElementById('login-email');
  const passEl = document.getElementById('login-password');
  const errEl = document.getElementById('login-error');
  const btnText = document.getElementById('login-btn-text');
  const spinner = document.getElementById('login-spinner');
  const togglePass = document.getElementById('toggle-password');

  togglePass.innerHTML = icon('eye', 18);
  spinner.innerHTML = icon('loader', 16);

  togglePass.addEventListener('click', () => {
    const isPass = passEl.type === 'password';
    passEl.type = isPass ? 'text' : 'password';
    togglePass.innerHTML = icon(isPass ? 'eye-off' : 'eye', 18);
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    errEl.classList.add('hidden');
    btnText.textContent = 'Entrando…';
    spinner.classList.remove('hidden');
    spinner.classList.add('spin');
    document.getElementById('login-btn').disabled = true;
    try {
      const data = await api.postForm('/auth/login', { username: emailEl.value, password: passEl.value });
      saveSession(data);
      showDashboard(data);
    } catch (err) {
      errEl.classList.remove('hidden');
      errEl.querySelector('p').textContent = extractError(err);
    } finally {
      btnText.textContent = 'Entrar';
      spinner.classList.add('hidden');
      spinner.classList.remove('spin');
      document.getElementById('login-btn').disabled = false;
    }
  });
}

async function init() {
  toast.init();
  confirm.init();
  setOnExpired(() => { toast.error('Sessão expirada. Faça login novamente.'); showLogin(); });

  document.querySelectorAll('.logo-icon').forEach(el => { el.innerHTML = icon('shield', 20); });
  document.getElementById('hamburger').addEventListener('click', openSidebar);
  initSidebarToggle();
  document.getElementById('sidebar-overlay').addEventListener('click', closeSidebar);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });
  const logoutBtn = document.getElementById('logout-btn');
  logoutBtn.dataset.label = 'Sair';
  logoutBtn.innerHTML = `${icon('log-out', 18)}<span>Sair</span>`;
  document.getElementById('logout-btn').addEventListener('click', () => {
    // Cookie scpi_refresh viaja sozinho; body vazio sinaliza fluxo portal.
    api.post('/auth/logout', {}).catch(() => {});
    showLogin();
  });
  document.getElementById('fab')?.addEventListener('click', () => runCreate());

  initKeyboard();
  initLogin();
  initFilters();

  const session = readSession();
  if (!session.ok) { showLogin(); return; }

  // O perfil em localStorage não prova sessão: confirma com o backend antes de
  // montar o dashboard. Cookie expirado/ausente cai direto no login.
  if (await validateSession()) showDashboard(session.user);
  else showLogin();
}

// Qualquer falha no init cai no login — nunca deixa o splash de boot preso.
document.addEventListener('DOMContentLoaded', () => { init().catch(() => showLogin()); });
