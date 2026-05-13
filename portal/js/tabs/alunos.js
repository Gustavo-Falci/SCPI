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
  if (!state.cache.alunos) state.cache.alunos = await api.get('/admin/alunos');
  data = state.cache.alunos;
}

function filtered() {
  if (!search) return data;
  const q = search.toLowerCase();
  return data.filter(a => a.nome?.toLowerCase().includes(q) || a.email?.toLowerCase().includes(q) || a.ra?.toLowerCase().includes(q));
}

function turnoBadge(turno) {
  if (!turno) return '';
  const cls = turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500';
  return `<span class="${cls} text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter">${turno}</span>`;
}

function renderList(container) {
  const f = filtered();
  const { items, page: pg, total, count } = paginate(f, page, PER_PAGE);
  page = pg;
  const list = container.querySelector('#alunos-list');
  const pag = container.querySelector('#alunos-pagination');

  if (!items.length) {
    list.innerHTML = `<div class="flex flex-col items-center justify-center py-16 text-gray-600">${icon('user', 40)}<p class="mt-3 font-black text-sm">Nenhum aluno encontrado</p></div>`;
  } else {
    list.innerHTML = items.map(a => `
      <div class="group bg-[#151718] hover:bg-[#1A1C1E] px-5 py-4 rounded-2xl border border-white/5 flex items-center justify-between gap-4 transition-all hover:border-white/10">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-0.5">
            <p class="font-black text-white text-sm truncate">${a.nome}</p>
            ${turnoBadge(a.turno)}
          </div>
          <p class="text-gray-500 font-bold text-xs truncate">${a.email}${a.ra ? ` · RA: ${a.ra}` : ''}</p>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button data-id="${a.aluno_id}" class="edit-btn w-8 h-8 rounded-xl bg-accent/10 hover:bg-accent/20 flex items-center justify-center text-accent transition-all">${icon('pencil', 14)}</button>
          <button data-id="${a.aluno_id}" class="del-btn w-8 h-8 rounded-xl bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all">${icon('trash-2', 14)}</button>
        </div>
      </div>
    `).join('');
    list.querySelectorAll('.edit-btn').forEach(btn => {
      const aluno = data.find(a => String(a.aluno_id) === String(btn.dataset.id));
      btn.addEventListener('click', () => showEditModal(aluno, container));
    });
    list.querySelectorAll('.del-btn').forEach(btn => btn.addEventListener('click', () => deleteAluno(btn.dataset.id, container)));
  }
  renderPagination(pag, { page, total, count, perPage: PER_PAGE }, p => { page = p; renderList(container); });
}

async function deleteAluno(id, container) {
  const ok = await confirm.show('Excluir Aluno', 'Esta ação remove o aluno permanentemente. Continuar?');
  if (!ok) return;
  try {
    await api.del(`/admin/alunos/${id}`);
    invalidate('alunos');
    await load();
    renderList(container);
    toast.success('Aluno excluído.');
  } catch (err) { toast.error(extractError(err)); }
}

function showEditModal(aluno, container) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <h3 class="font-black text-lg">Editar Aluno</h3>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <form id="edit-aluno-form" class="space-y-4">
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome Completo</label>
          <input name="nome" type="text" value="${aluno.nome || ''}" class="scpi-input" required>
        </div>
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email</label>
          <input name="email" type="email" value="${aluno.email || ''}" class="scpi-input" required>
        </div>
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">RA</label>
          <input name="ra" type="text" value="${aluno.ra || ''}" class="scpi-input">
        </div>
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno</label>
          <select name="turno" class="scpi-input">
            <option value="">Não definido</option>
            <option value="Matutino" ${aluno.turno === 'Matutino' ? 'selected' : ''}>Matutino</option>
            <option value="Noturno" ${aluno.turno === 'Noturno' ? 'selected' : ''}>Noturno</option>
          </select>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="button" onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
          <button type="submit" id="edit-btn" class="flex-1 py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors">Salvar</button>
        </div>
      </form>
    </div>
  `);

  document.getElementById('edit-aluno-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('edit-btn');
    btn.disabled = true; btn.textContent = 'Salvando…';
    const form = e.target;
    try {
      await api.patch(`/admin/alunos/${aluno.aluno_id}`, {
        nome: form.querySelector('[name=nome]').value.trim(),
        email: form.querySelector('[name=email]').value.trim(),
        ra: form.querySelector('[name=ra]').value.trim() || null,
        turno: form.querySelector('[name=turno]').value || null,
      });
      invalidate('alunos');
      await load();
      renderList(container);
      closeModal();
      toast.success('Aluno atualizado.');
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = 'Salvar'; }
  });
}

function showPasswordModal(email, senha) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div><h3 class="font-black text-lg">Aluno Criado</h3><p class="text-gray-500 text-xs font-bold mt-0.5">Senha temporária gerada</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="space-y-3">
        <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5"><p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Email</p><p class="font-bold text-white">${email}</p></div>
        <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5">
          <p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Senha Temporária</p>
          <div class="flex items-center justify-between gap-3">
            <p class="font-black text-white text-lg tracking-wider">${senha}</p>
            <button id="copy-btn" class="px-3 py-1.5 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-black text-xs flex items-center gap-1.5">${icon('copy', 14)} Copiar</button>
          </div>
        </div>
      </div>
      <p class="text-yellow-400 text-xs font-bold mt-4 bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3">Compartilhe estas credenciais com o aluno.</p>
      <button onclick="closeModal()" class="w-full mt-4 py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors">Fechar</button>
    </div>
  `);
  document.getElementById('copy-btn').addEventListener('click', () => navigator.clipboard.writeText(senha).then(() => toast.success('Senha copiada!')));
}

async function createAluno(e, container) {
  e.preventDefault();
  const btn = document.getElementById('aluno-create-btn');
  const form = document.getElementById('aluno-form');
  btn.disabled = true; btn.textContent = 'Criando…';
  try {
    const res = await api.post('/admin/usuarios/aluno', {
      nome: form.querySelector('[name=nome]').value.trim(),
      email: form.querySelector('[name=email]').value.trim(),
      ra: form.querySelector('[name=ra]').value.trim() || null,
      turno: form.querySelector('[name=turno]').value || null,
    });
    form.reset();
    invalidate('alunos');
    await load();
    page = 1;
    renderList(container);
    const senha = res.senha_temporaria || res.password;
    if (senha) showPasswordModal(form.querySelector('[name=email]').value || res.email, senha);
    else toast.success('Aluno criado com sucesso!');
  } catch (err) { toast.error(extractError(err)); }
  finally { btn.disabled = false; btn.textContent = 'Criar Aluno'; }
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden">
      <div class="lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 overflow-y-auto">
        <h3 class="font-black text-base mb-5 flex items-center gap-2">${icon('plus', 16)}<span>Novo Aluno</span></h3>
        <form id="aluno-form" class="space-y-4">
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome Completo *</label>
            <input name="nome" type="text" placeholder="Maria Santos" class="scpi-input" required>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email *</label>
            <input name="email" type="email" placeholder="maria@escola.com" class="scpi-input" required>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">RA</label>
            <input name="ra" type="text" placeholder="2024001" class="scpi-input">
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno</label>
            <select name="turno" class="scpi-input">
              <option value="">Não definido</option>
              <option value="Matutino">Matutino</option>
              <option value="Noturno">Noturno</option>
            </select>
          </div>
          <button id="aluno-create-btn" type="submit" class="w-full py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Aluno</span></button>
        </form>
      </div>
      <div class="flex-1 flex flex-col overflow-hidden gap-3 min-h-0">
        <div class="relative flex-shrink-0">
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 16)}</span>
          <input id="alunos-search" type="search" placeholder="Buscar aluno..." class="scpi-input pl-10 w-full">
        </div>
        <div id="alunos-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
        <div id="alunos-pagination" class="flex-shrink-0"></div>
      </div>
    </div>
  `;
  container.querySelector('#aluno-form').addEventListener('submit', e => createAluno(e, container));
  container.querySelector('#alunos-search').addEventListener('input', e => { search = e.target.value; page = 1; renderList(container); });
  try { await load(); renderList(container); } catch (err) { toast.error(extractError(err)); }
}
