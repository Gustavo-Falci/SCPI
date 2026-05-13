import { toast } from './toast.js';
import { confirm } from './confirm.js';
import { getState, setState } from './state.js';
import { readSession, saveSession, clearSession } from './auth.js';
import { api, setOnExpired, extractError } from './api.js';
import { icon } from './icons.js';
import { skeletons } from './skeleton.js';
import { runCreate, hasCreate, clearCreate } from './registry.js';
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

function buildSidebar() {
  const nav = document.getElementById('sidebar-nav');
  nav.innerHTML = TABS.map(t => `
    <button data-tab="${t.id}" class="nav-item w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-black text-sm transition-all text-left text-gray-500 hover:text-white hover:bg-white/5">
      ${icon(t.iconName, 18)}<span>${t.label}</span>
    </button>
  `).join('');
  nav.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
}

function buildBottomNav() {
  const nav = document.getElementById('bottom-nav');
  if (!nav) return;
  nav.innerHTML = TABS.map(t => `
    <button data-tab="${t.id}" class="bnav-item">
      ${icon(t.iconName, 20)}
      <span>${t.bLabel}</span>
      <div class="bnav-dot"></div>
    </button>
  `).join('');
  nav.querySelectorAll('.bnav-item').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
}

function setActiveNav(tabId) {
  document.querySelectorAll('.nav-item').forEach(btn => {
    const a = btn.dataset.tab === tabId;
    btn.className = `nav-item w-full flex items-center gap-3 px-4 py-3 rounded-2xl font-black text-sm transition-all text-left ${a ? 'bg-accent/10 text-accent border border-accent/20' : 'text-gray-500 hover:text-white hover:bg-white/5'}`;
  });
  document.querySelectorAll('.bnav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  // FAB: show only for tabs with create form
  const fab = document.getElementById('fab');
  if (fab) fab.classList.toggle('hidden', !TABS_WITH_CREATE.has(tabId));
}

function updateHeader(tab) {
  document.getElementById('header-title').textContent = tab.title;
  document.getElementById('header-subtitle').textContent = tab.subtitle;
}

function switchTab(tabId) {
  const tab = TABS.find(t => t.id === tabId);
  if (!tab) return;
  clearCreate();
  setState({ activeTab: tabId });
  setActiveNav(tabId);
  updateHeader(tab);
  closeSidebar();

  const content = document.getElementById('tab-content');
  content.innerHTML = tab.skeleton ? tab.skeleton() : `<div class="flex-1 flex items-center justify-center"><div class="spin opacity-50">${icon('loader', 28)}</div></div>`;
  tab.mount(content).catch(err => {
    content.innerHTML = `<div class="tab-anim flex-1 flex items-center justify-center text-red-400 font-black text-sm">${extractError(err)}</div>`;
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

function showDashboard(user) {
  document.getElementById('view-login').classList.add('hidden');
  document.getElementById('view-dashboard').classList.remove('hidden');
  document.getElementById('sidebar-username').textContent = user.user_name || user.nome || 'Administrador';
  buildSidebar();
  buildBottomNav();
  switchTab('turmas');
}

function showLogin() {
  document.getElementById('view-dashboard').classList.add('hidden');
  document.getElementById('view-login').classList.remove('hidden');
  clearSession();
}

function initFilters() {
  const state = getState();
  document.querySelectorAll('.turno-btn').forEach(btn => {
    const active = btn.dataset.turno === state.turno;
    btn.className = `turno-btn px-3 sm:px-4 py-2 rounded-xl font-black text-xs transition-all ${active ? 'bg-accent text-white' : 'text-gray-500 hover:text-white'}`;
    btn.addEventListener('click', () => {
      setState({ turno: btn.dataset.turno });
      document.querySelectorAll('.turno-btn').forEach(b => {
        const a = b.dataset.turno === btn.dataset.turno;
        b.className = `turno-btn px-3 sm:px-4 py-2 rounded-xl font-black text-xs transition-all ${a ? 'bg-accent text-white' : 'text-gray-500 hover:text-white'}`;
      });
      switchTab(getState().activeTab);
    });
  });
  const sel = document.getElementById('semestre-filter');
  sel.value = state.semestre;
  sel.addEventListener('change', () => { setState({ semestre: sel.value }); switchTab(getState().activeTab); });
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

function init() {
  toast.init();
  confirm.init();
  setOnExpired(() => { toast.error('Sessão expirada. Faça login novamente.'); showLogin(); });

  document.querySelectorAll('.logo-icon').forEach(el => { el.innerHTML = icon('shield', 20); });
  document.getElementById('hamburger').addEventListener('click', openSidebar);
  document.getElementById('sidebar-overlay').addEventListener('click', closeSidebar);
  document.getElementById('modal-overlay').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });
  document.getElementById('logout-btn').innerHTML = `${icon('log-out', 18)}<span>Sair</span>`;
  document.getElementById('logout-btn').addEventListener('click', () => {
    api.post('/auth/logout', { refresh_token: localStorage.getItem('admin_refresh_token') }).catch(() => {});
    showLogin();
  });
  document.getElementById('fab')?.addEventListener('click', () => runCreate());

  initKeyboard();
  initLogin();
  initFilters();

  const session = readSession();
  if (session.ok) showDashboard(session.user);
  else showLogin();
}

export function openModal(html, size = 'max-w-lg') {
  const box = document.getElementById('modal-box');
  box.className = `w-full ${size} bg-[#151718] rounded-3xl border border-white/10 shadow-2xl shadow-black/60 overflow-hidden max-h-[90vh] flex flex-col`;
  box.innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

export function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-box').innerHTML = '';
}

export async function animateRemove(el) {
  if (!el) return;
  el.classList.add('removing');
  await new Promise(r => setTimeout(r, 200));
}

document.addEventListener('DOMContentLoaded', init);
