import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { paginate, renderPagination } from '../pagination.js';
import { getState, invalidate } from '../state.js';
import { openModal, closeModal } from '../main.js';

const PER_PAGE = 10;
let page = 1;
let search = '';
let data = [];

async function load() {
  const state = getState();
  if (!state.cache.professores) {
    state.cache.professores = await api.get('/admin/professores');
  }
  data = state.cache.professores;
}

function filtered() {
  if (!search) return data;
  const q = search.toLowerCase();
  return data.filter(p => p.nome?.toLowerCase().includes(q) || p.email?.toLowerCase().includes(q) || p.departamento?.toLowerCase().includes(q));
}

function renderList(container) {
  const f = filtered();
  const { items, page: pg, total, count } = paginate(f, page, PER_PAGE);
  page = pg;

  const list = container.querySelector('#prof-list');
  const pag = container.querySelector('#prof-pagination');

  if (!items.length) {
    list.innerHTML = `<div class="flex flex-col items-center justify-center py-16 text-gray-600">${icon('users', 40)}<p class="mt-3 font-black text-sm">Nenhum professor encontrado</p></div>`;
  } else {
    list.innerHTML = items.map(p => `
      <div class="group bg-[#151718] hover:bg-[#1A1C1E] px-5 py-4 rounded-2xl border border-white/5 flex items-center justify-between gap-4 transition-all hover:border-white/10">
        <div class="min-w-0 flex-1">
          <p class="font-black text-white text-sm truncate">${p.nome}</p>
          <p class="text-gray-500 font-bold text-xs truncate mt-0.5">${p.email}${p.departamento ? ` · ${p.departamento}` : ''}</p>
        </div>
        <button data-id="${p.professor_id}" class="del-btn flex-shrink-0 w-8 h-8 rounded-xl bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all opacity-0 group-hover:opacity-100">${icon('trash-2', 14)}</button>
      </div>
    `).join('');
    list.querySelectorAll('.del-btn').forEach(btn => btn.addEventListener('click', () => deleteProfessor(btn.dataset.id, container)));
  }

  renderPagination(pag, { page, total, count, perPage: PER_PAGE }, p => { page = p; renderList(container); });
}

async function deleteProfessor(id, container) {
  const ok = await confirm.show('Excluir Professor', 'Esta ação remove o professor e todos os seus dados. Continuar?');
  if (!ok) return;
  try {
    await api.del(`/admin/professores/${id}`);
    invalidate('professores');
    await load();
    renderList(container);
    toast.success('Professor excluído.');
  } catch (err) { toast.error(extractError(err)); }
}

function showPasswordModal(email, senha) {
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="font-black text-lg">Professor Criado</h3>
          <p class="text-gray-500 text-xs font-bold mt-0.5">Senha temporária gerada</p>
        </div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="space-y-3">
        <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5">
          <p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Email</p>
          <p class="font-bold text-white">${email}</p>
        </div>
        <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5">
          <p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Senha Temporária</p>
          <div class="flex items-center justify-between gap-3">
            <p class="font-black text-white text-lg tracking-wider">${senha}</p>
            <button id="copy-btn" class="flex-shrink-0 px-3 py-1.5 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-black text-xs flex items-center gap-1.5 transition-colors">${icon('copy', 14)} Copiar</button>
          </div>
        </div>
      </div>
      <p class="text-yellow-400 text-xs font-bold mt-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3">Compartilhe estas credenciais com o professor. A senha deverá ser alterada no primeiro acesso.</p>
      <button onclick="closeModal()" class="w-full mt-4 py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors">Fechar</button>
    </div>
  `);
  document.getElementById('copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(senha).then(() => toast.success('Senha copiada!'));
  });
  // expose closeModal globally for onclick
  window.closeModal = closeModal;
}

async function createProfessor(e, container) {
  e.preventDefault();
  const btn = document.getElementById('prof-create-btn');
  const form = document.getElementById('prof-form');
  const nome = form.querySelector('[name=nome]').value.trim();
  const email = form.querySelector('[name=email]').value.trim();
  const depto = form.querySelector('[name=departamento]').value.trim();
  if (!nome || !email) return toast.error('Nome e email são obrigatórios.');
  btn.disabled = true; btn.textContent = 'Criando…';
  try {
    const res = await api.post('/admin/usuarios/professor', { nome, email, departamento: depto || null });
    form.reset();
    invalidate('professores');
    await load();
    page = 1;
    renderList(container);
    const senha = res.senha_temporaria || res.password;
    if (senha) showPasswordModal(email, senha);
    else toast.success('Professor criado com sucesso!');
  } catch (err) { toast.error(extractError(err)); }
  finally { btn.disabled = false; btn.textContent = 'Criar Professor'; }
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden">
      <!-- Create Form -->
      <div class="lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 overflow-y-auto">
        <h3 class="font-black text-base mb-5 flex items-center gap-2">${icon('plus', 16)}<span>Novo Professor</span></h3>
        <form id="prof-form" class="space-y-4">
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome Completo *</label>
            <input name="nome" type="text" placeholder="Prof. João Silva" class="scpi-input" required>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email *</label>
            <input name="email" type="email" placeholder="joao@escola.com" class="scpi-input" required>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Departamento</label>
            <input name="departamento" type="text" placeholder="Engenharia de Software" class="scpi-input">
          </div>
          <button id="prof-create-btn" type="submit" class="w-full py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Professor</span></button>
        </form>
      </div>
      <!-- List -->
      <div class="flex-1 flex flex-col overflow-hidden gap-3 min-h-0">
        <div class="relative flex-shrink-0">
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 16)}</span>
          <input id="prof-search" type="search" placeholder="Buscar professor..." class="scpi-input pl-10 w-full">
        </div>
        <div id="prof-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
        <div id="prof-pagination" class="flex-shrink-0"></div>
      </div>
    </div>
  `;

  container.querySelector('#prof-form').addEventListener('submit', e => createProfessor(e, container));
  container.querySelector('#prof-search').addEventListener('input', e => { search = e.target.value; page = 1; renderList(container); });

  try {
    await load();
    renderList(container);
  } catch (err) { toast.error(extractError(err)); }
}
