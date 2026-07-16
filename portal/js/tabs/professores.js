import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { avatar, debounce, escapeHtml } from '../utils.js';
import { paginate, renderPagination } from '../pagination.js';
import { getState, invalidate } from '../state.js';
import { openModal, closeModal, animateRemove } from '../main.js';
import { setCreate } from '../registry.js';

const PER_PAGE = 10;
let page = 1;
let search = '';
let data = [];

async function load() {
  const state = getState();
  if (!state.cache.professores) state.cache.professores = await api.get('/admin/professores');
  data = state.cache.professores;
}

function filtered() {
  if (!search) return data;
  const q = search.toLowerCase();
  return data.filter(p => p.nome?.toLowerCase().includes(q) || p.email?.toLowerCase().includes(q));
}

function renderList(container) {
  const f = filtered();
  const { items, page: pg, total, count } = paginate(f, page, PER_PAGE);
  page = pg;
  const list = container.querySelector('#prof-list');
  const pag = container.querySelector('#prof-pagination');

  if (!items.length) {
    list.innerHTML = `
      <div class="flex flex-col items-center justify-center py-16 text-gray-600 gap-3">
        ${icon('users', 40)}
        <p class="font-black text-sm">${search ? 'Nenhum professor encontrado' : 'Nenhum professor cadastrado'}</p>
        ${!search ? `<button id="cta-create-prof" class="mt-1 px-4 py-2 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-black text-xs flex items-center gap-1.5 transition-colors">${icon('plus', 14)} Criar primeiro professor</button>` : ''}
      </div>`;
    document.getElementById('cta-create-prof')?.addEventListener('click', () => {
      document.querySelector('#prof-form [name=nome]')?.focus();
    });
  } else {
    list.innerHTML = items.map((p, i) => `
      <div data-prof-id="${p.professor_id}" class="anim-item group bg-[#151718] hover:bg-[#1A1C1E] px-5 py-4 rounded-2xl border border-white/5 flex items-center gap-4 transition-all hover:border-white/10" style="animation-delay:${i * 45}ms">
        ${avatar(p.nome, 38)}
        <div class="min-w-0 flex-1">
          <p class="font-black text-white text-sm truncate">${escapeHtml(p.nome)}</p>
          <p class="text-gray-500 font-bold text-xs truncate mt-0.5">${escapeHtml(p.email)}</p>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button data-id="${p.professor_id}" class="edit-btn w-8 h-8 rounded-xl bg-accent/10 hover:bg-accent/20 flex items-center justify-center text-accent transition-all">${icon('pencil', 14)}</button>
          <button data-id="${p.professor_id}" class="del-btn w-8 h-8 rounded-xl bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all">${icon('trash-2', 14)}</button>
        </div>
      </div>`).join('');
    list.querySelectorAll('.edit-btn').forEach(btn => {
      const prof = data.find(p => String(p.professor_id) === String(btn.dataset.id));
      btn.addEventListener('click', () => showEditModal(prof, container));
    });
    list.querySelectorAll('.del-btn').forEach(btn => btn.addEventListener('click', () => deleteProfessor(btn.dataset.id, container)));
  }
  renderPagination(pag, { page, total, count, perPage: PER_PAGE }, p => { page = p; renderList(container); });
}

async function deleteProfessor(id, container) {
  const ok = await confirm.show('Excluir Professor', 'Remove o professor e todos os seus dados. Continuar?');
  if (!ok) return;
  const el = container.querySelector(`[data-prof-id="${id}"]`);
  await animateRemove(el);
  try {
    await api.del(`/admin/professores/${id}`);
    invalidate('professores');
    await load();
    renderList(container);
    toast.success('Professor excluído.');
  } catch (err) { toast.error(extractError(err)); await load(); renderList(container); }
}

function showEditModal(prof, container) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">${avatar(prof.nome, 40)}<div><h3 class="font-black text-lg">Editar Professor</h3><p class="text-gray-500 text-xs font-bold">${escapeHtml(prof.email || '')}</p></div></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <form id="edit-prof-form" class="space-y-4">
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome</label><input name="nome" type="text" value="${escapeHtml(prof.nome || '')}" class="scpi-input" required></div>
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email</label><input name="email" type="email" value="${escapeHtml(prof.email || '')}" class="scpi-input" required></div>
        <div class="flex gap-3 pt-2">
          <button type="button" onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
          <button type="submit" id="edit-prof-btn" class="flex-1 py-3 rounded-2xl bg-accent text-white font-black text-sm transition-colors">Salvar</button>
        </div>
      </form>
    </div>`);
  document.getElementById('edit-prof-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('edit-prof-btn');
    btn.disabled = true; btn.textContent = 'Salvando…';
    try {
      await api.patch(`/admin/professores/${prof.professor_id}`, {
        nome: e.target.querySelector('[name=nome]').value.trim(),
        email: e.target.querySelector('[name=email]').value.trim(),
      });
      invalidate('professores'); await load(); renderList(container);
      closeModal(); toast.success('Professor atualizado.');
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = 'Salvar'; }
  });
}

function showCreatedModal(email) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div><h3 class="font-black text-lg">Professor Criado</h3><p class="text-gray-500 text-xs font-bold mt-0.5">Credenciais enviadas por email</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5 mb-3">
        <p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Email</p>
        <p class="font-bold text-white">${email}</p>
      </div>
      <p class="text-blue-300 text-xs font-bold bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
        Senha temporária enviada para o email acima. O professor definirá uma nova senha no primeiro acesso.
      </p>
      <button onclick="closeModal()" class="w-full mt-4 py-3 rounded-2xl bg-accent text-white font-black text-sm transition-colors">Fechar</button>
    </div>`);
}

function formHTML() {
  return `
    <form id="prof-form" class="space-y-4">
      <div>
        <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome Completo *</label>
        <input name="nome" type="text" placeholder="Prof. João Silva" class="scpi-input" required>
      </div>
      <div>
        <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email *</label>
        <input name="email" type="email" placeholder="joao@escola.com" class="scpi-input" required>
      </div>
      <button id="prof-create-btn" type="submit" class="w-full py-3 rounded-2xl bg-accent text-white font-black text-sm transition-all flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Professor</span></button>
    </form>`;
}

async function handleImportCsv(file, container) {
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await api.postMultipart('/admin/importar-professores', formData);
    invalidate('professores');
    await load(); page = 1;
    if (container) renderList(container);
    const dupSuffix = res.duplicados ? ` ${res.duplicados} duplicado(s) ignorado(s).` : '';
    const msg = `${res.mensagem || ''} ${res.emails_enviados || 0} email(s) enviado(s).${dupSuffix}`;
    if (res.erros && res.erros.length) {
      toast.error(`${msg}\nErros:\n${res.erros.join('\n')}`);
    } else {
      toast.success(msg);
    }
  } catch (err) { toast.error(extractError(err)); }
}

async function handleCreate(form, container) {
  const btn = form.querySelector('[type=submit]');
  btn.disabled = true; btn.querySelector('span').textContent = 'Criando…';
  try {
    const email = form.querySelector('[name=email]').value.trim();
    const res = await api.post('/admin/usuarios/professor', {
      nome: form.querySelector('[name=nome]').value.trim(),
      email,
    });
    form.reset();
    invalidate('professores');
    await load(); page = 1;
    if (container) renderList(container);
    showCreatedModal(email);
  } catch (err) { toast.error(extractError(err)); }
  finally { btn.disabled = false; btn.querySelector('span').textContent = 'Criar Professor'; }
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden tab-anim">
      <div class="hidden lg:block lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 overflow-y-auto">
        <h3 class="font-black text-base mb-5 flex items-center gap-2">${icon('plus', 16)}<span>Novo Professor</span></h3>
        ${formHTML()}
        <div class="mt-6 pt-6 border-t border-white/5">
          <h4 class="font-black text-xs uppercase tracking-widest text-gray-500 mb-3">Importar em massa</h4>
          <label for="prof-csv-input" class="cursor-pointer w-full py-3 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-black text-sm transition-all flex items-center justify-center gap-2 border border-white/10">
            ${icon('upload', 16)}<span>Importar CSV</span>
          </label>
          <input id="prof-csv-input" type="file" accept=".csv" class="hidden">
          <p class="text-[10px] text-gray-600 font-bold mt-2 text-center">Colunas: nome, email</p>
        </div>
      </div>
      <div class="flex-1 flex flex-col overflow-hidden gap-3 min-h-0">
        <div class="relative flex-shrink-0">
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 16)}</span>
          <input id="prof-search" type="search" placeholder="Buscar professor..." class="scpi-input pl-10 w-full">
        </div>
        <div id="prof-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
        <div id="prof-pagination" class="flex-shrink-0"></div>
      </div>
    </div>`;

  container.querySelector('#prof-form').addEventListener('submit', e => { e.preventDefault(); handleCreate(e.target, container); });
  container.querySelector('#prof-search').addEventListener('input', debounce(e => { search = e.target.value; page = 1; renderList(container); }, 200));

  // Registra FAB mobile → abre modal com o formulário
  setCreate(() => {
    window.closeModal = closeModal;
    openModal(`
      <div class="p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-black text-lg">Novo Professor</h3>
          <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
        </div>
        ${formHTML()}
      </div>`);
    document.getElementById('prof-form').addEventListener('submit', async e => {
      e.preventDefault();
      await handleCreate(e.target, container);
      if (!document.getElementById('prof-form')) closeModal();
    });
  });

  const csvInput = container.querySelector('#prof-csv-input');
  if (csvInput) {
    csvInput.addEventListener('change', async e => {
      const file = e.target.files?.[0];
      if (file) await handleImportCsv(file, container);
      csvInput.value = '';
    });
  }

  try { await load(); renderList(container); } catch (err) { toast.error(extractError(err)); }
}
