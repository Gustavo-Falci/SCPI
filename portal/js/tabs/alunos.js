import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { avatar, baixarModeloCsv, debounce, escapeHtml } from '../utils.js';
import { renderPagination } from '../pagination.js';
import { getState, invalidate } from '../state.js';
import { openModal, closeModal, animateRemove } from '../modal.js';
import { setCreate } from '../registry.js';
import { loadTab, saveTab } from '../persist.js';

const PER_PAGE = 10;
let page = 1;
let search = '';
let filtros = { turma_id: '', periodo_letivo: '', situacao: '' };
let data = [];
let total = 0;
let ocultosPendentes = 0;

// Assinatura da consulta: busca, filtros locais, página e o escopo global de
// turno/semestre do header. Serve de querystring e de chave de cache.
function queryParams() {
  const { turno, semestre } = getState();
  const params = new URLSearchParams({ turno, page: String(page), limit: String(PER_PAGE) });
  if (semestre !== 'Todos') params.append('semestre', semestre);
  if (search) params.append('q', search);
  if (filtros.turma_id) params.append('turma_id', filtros.turma_id);
  if (filtros.periodo_letivo) params.append('periodo_letivo', filtros.periodo_letivo);
  if (filtros.situacao) params.append('situacao', filtros.situacao);
  return params;
}

async function load() {
  const state = getState();
  const sig = queryParams().toString();
  const cached = state.cache.alunos;
  if (!cached || cached.sig !== sig) {
    const res = await api.get(`/admin/alunos?${sig}`);
    state.cache.alunos = { sig, ...res };
  }
  const atual = state.cache.alunos;
  data = atual.items;
  total = atual.total;
  ocultosPendentes = atual.ocultos_pendentes;
}

// Os selects de turma e período saem das turmas já cacheadas pelo portal.
// Se o cache estiver frio (F5 direto nesta aba), busca uma vez.
async function carregarTurmas() {
  const state = getState();
  if (!state.cache.turmas) state.cache.turmas = await api.get('/admin/turmas-completas');
  return state.cache.turmas;
}

// Toda mudança de filtro passa por aqui: refaz a consulta e redesenha. Erro de
// rede não pode deixar a lista velha na tela fingindo que o filtro pegou.
async function recarregar(container) {
  try {
    await load();
    // Excluir o último aluno de uma página deixa `page` além do fim: o servidor
    // devolve lista vazia com total>0 e a tela fingiria que não há aluno nenhum.
    const ultimaPagina = Math.max(1, Math.ceil(total / PER_PAGE));
    if (!data.length && total > 0 && page > ultimaPagina) {
      page = ultimaPagina;
      saveTab('alunos', { search, page, ...filtros });
      await load();
    }
    renderList(container);
  } catch (err) {
    toast.error(extractError(err));
  }
}

function renderFiltros(container, turmas) {
  const { turno, semestre } = getState();
  const periodos = [...new Set(turmas.map(t => t.periodo_letivo).filter(Boolean))].sort();
  const temFiltroLocal = Boolean(filtros.turma_id || filtros.periodo_letivo || filtros.situacao);
  const escopo = `${turno}${semestre !== 'Todos' ? ` · ${semestre}º sem.` : ''}`;

  const chip = (valor, rotulo) => `
    <button data-situacao="${valor}" class="chip-situacao px-3 py-1.5 rounded-xl font-black text-[11px] transition-colors whitespace-nowrap ${
      filtros.situacao === valor ? 'bg-accent text-white' : 'bg-white/5 text-gray-500 hover:bg-white/10'
    }">${rotulo}</button>`;

  container.querySelector('#alunos-filtros').innerHTML = `
    <div class="flex flex-wrap items-center gap-2">
      <select id="filtro-turma" class="scpi-input py-2 text-xs font-black w-auto max-w-[15rem]">
        <option value="">Todas as turmas</option>
        ${turmas.map(t => `<option value="${escapeHtml(String(t.turma_id))}" ${filtros.turma_id === String(t.turma_id) ? 'selected' : ''}>${escapeHtml(t.codigo_turma)} · ${escapeHtml(t.nome_disciplina)}</option>`).join('')}
      </select>
      <select id="filtro-periodo" class="scpi-input py-2 text-xs font-black w-auto max-w-[11rem]">
        <option value="">Todos os períodos</option>
        ${periodos.map(p => `<option value="${escapeHtml(p)}" ${filtros.periodo_letivo === p ? 'selected' : ''}>${escapeHtml(p)}</option>`).join('')}
      </select>
      <div class="flex items-center gap-1.5">
        ${chip('', 'Todos')}
        ${chip('sem_turma', 'Sem turma')}
        ${chip('sem_biometria', 'Sem biometria')}
        ${chip('pendentes', 'Pendentes')}
      </div>
      ${temFiltroLocal ? `<button id="filtro-limpar" class="px-3 py-1.5 rounded-xl font-black text-[11px] text-gray-500 hover:text-white transition-colors">Limpar</button>` : ''}
      <span class="text-[11px] font-black text-gray-600 ml-auto whitespace-nowrap">Escopo: ${escapeHtml(escopo)}</span>
    </div>`;

  const aplicar = async () => {
    page = 1;
    saveTab('alunos', { search, page, ...filtros });
    await recarregar(container);
    renderFiltros(container, turmas);
  };

  container.querySelector('#filtro-turma').addEventListener('change', e => {
    filtros.turma_id = e.target.value;
    aplicar();
  });
  container.querySelector('#filtro-periodo').addEventListener('change', e => {
    filtros.periodo_letivo = e.target.value;
    aplicar();
  });
  container.querySelectorAll('.chip-situacao').forEach(btn => {
    btn.addEventListener('click', () => {
      filtros.situacao = btn.dataset.situacao;
      aplicar();
    });
  });
  container.querySelector('#filtro-limpar')?.addEventListener('click', () => {
    filtros = { turma_id: '', periodo_letivo: '', situacao: '' };
    aplicar();
  });
}

// Filtro de turno/semestre esconde quem não tem turno definido ou matrícula no
// escopo. Sem este aviso, o admin acha que o aluno sumiu do sistema.
function renderBannerOcultos(container) {
  const el = container.querySelector('#alunos-banner-ocultos');
  if (!el) return;
  if (!ocultosPendentes) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <div class="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-amber-500/10 border border-amber-500/20">
      <span class="text-amber-400 flex-shrink-0">${icon('user', 14)}</span>
      <p class="text-amber-300 text-xs font-bold flex-1">
        ${ocultosPendentes} aluno(s) sem turno ou sem turma ocultos por este filtro.
      </p>
      <button id="ver-ocultos" class="px-3 py-1 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 font-black text-[11px] transition-colors">Ver</button>
    </div>`;
  container.querySelector('#ver-ocultos').addEventListener('click', async () => {
    filtros.situacao = 'pendentes';
    page = 1;
    saveTab('alunos', { search, page, ...filtros });
    await recarregar(container);
    renderFiltros(container, getState().cache.turmas || []);
  });
}

function turnoBadge(turno) {
  if (!turno) return '';
  const cls = turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500';
  return `<span class="${cls} text-[10px] font-black px-1.5 py-0.5 rounded-md uppercase tracking-tighter">${escapeHtml(turno)}</span>`;
}

function renderList(container) {
  const items = data;
  const totalPaginas = Math.max(1, Math.ceil(total / PER_PAGE));
  // ocultosPendentes entra na conta porque o escopo global de turno/semestre
  // também esconde gente: sem isso, um turno que zera a lista mostraria
  // "Nenhum aluno cadastrado" e o CTA de primeiro cadastro, ambos falsos.
  const temFiltro = Boolean(
    search || filtros.turma_id || filtros.periodo_letivo || filtros.situacao || ocultosPendentes
  );
  const list = container.querySelector('#alunos-list');
  const pag = container.querySelector('#alunos-pagination');

  if (!items.length) {
    list.innerHTML = `
      <div class="flex flex-col items-center justify-center py-16 text-gray-600 gap-3">
        ${icon('user', 40)}
        <p class="font-black text-sm">${temFiltro ? 'Nenhum aluno para este filtro' : 'Nenhum aluno cadastrado'}</p>
        ${!temFiltro ? `<button id="cta-create-aluno" class="mt-1 px-4 py-2 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-black text-xs flex items-center gap-1.5 transition-colors">${icon('plus', 14)} Criar primeiro aluno</button>` : ''}
      </div>`;
    document.getElementById('cta-create-aluno')?.addEventListener('click', () => document.querySelector('#aluno-form [name=nome]')?.focus());
  } else {
    list.innerHTML = items.map((a, i) => `
      <div data-aluno-id="${a.aluno_id}" class="anim-item group bg-[#151718] hover:bg-[#1A1C1E] px-4 sm:px-5 py-4 rounded-2xl border border-white/5 flex items-center gap-3 sm:gap-4 transition-all hover:border-white/10" style="animation-delay:${i * 45}ms">
        ${avatar(a.nome, 38)}
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-0.5">
            <p class="font-black text-white text-sm truncate">${escapeHtml(a.nome)}</p>
            ${turnoBadge(a.turno)}
            ${a.tem_biometria ? '' : `<span class="bg-gray-500/10 text-gray-400 text-[10px] font-black px-1.5 py-0.5 rounded-md uppercase tracking-tighter" title="Sem rosto cadastrado">sem biometria</span>`}
          </div>
          <!-- Email e RA numa linha só truncavam os dois no celular; em lg+
               cabem inline, então lá seguem juntos. -->
          <p class="text-gray-500 font-bold text-xs truncate">${escapeHtml(a.email)}${a.ra ? `<span class="hidden lg:inline"> · RA/CPF: ${escapeHtml(a.ra)}</span>` : ''}</p>
          ${a.ra ? `<p class="text-gray-600 font-bold text-xs truncate lg:hidden">RA/CPF: ${escapeHtml(a.ra)}</p>` : ''}
        </div>
        <!-- Mobile: sempre visíveis. opacity-0 sem hover deixava os botões
             invisíveis mas ainda clicáveis — incluindo Excluir. Só em lg+,
             onde hover existe, eles voltam a aparecer no hover. -->
        <div class="flex items-center gap-2 flex-shrink-0 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity">
          <button title="Editar" data-id="${a.aluno_id}" class="edit-btn w-9 h-9 lg:w-8 lg:h-8 rounded-xl bg-accent/10 hover:bg-accent/20 flex items-center justify-center text-accent transition-all">${icon('pencil', 14)}</button>
          <button title="Excluir" data-id="${a.aluno_id}" class="del-btn w-9 h-9 lg:w-8 lg:h-8 rounded-xl bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all">${icon('trash-2', 14)}</button>
        </div>
      </div>`).join('');
    list.querySelectorAll('.edit-btn').forEach(btn => {
      const aluno = data.find(a => String(a.aluno_id) === String(btn.dataset.id));
      btn.addEventListener('click', () => showEditModal(aluno, container));
    });
    list.querySelectorAll('.del-btn').forEach(btn => btn.addEventListener('click', () => deleteAluno(btn.dataset.id, container)));
  }
  renderPagination(pag, { page, total: totalPaginas, count: total, perPage: PER_PAGE }, async p => {
    page = p;
    saveTab('alunos', { search, page, ...filtros });
    await recarregar(container);
  });
  renderBannerOcultos(container);
}

async function deleteAluno(id, container) {
  const ok = await confirm.show('Excluir Aluno', 'Remove o aluno permanentemente. Continuar?');
  if (!ok) return;
  const el = container.querySelector(`[data-aluno-id="${id}"]`);
  await animateRemove(el);
  try {
    await api.del(`/admin/alunos/${id}`);
    invalidate('alunos');
    await recarregar(container);
    toast.success('Aluno excluído.');
  } catch (err) {
    toast.error(extractError(err));
    // A linha já saiu da tela pela animação: recarrega para ela voltar.
    invalidate('alunos');
    await recarregar(container);
  }
}

function showEditModal(aluno, container) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">${avatar(aluno.nome, 40)}<div><h3 class="font-black text-lg">Editar Aluno</h3><p class="text-gray-500 text-xs font-bold">${escapeHtml(aluno.ra || '')}</p></div></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <form id="edit-aluno-form" class="space-y-4">
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome</label><input name="nome" type="text" value="${escapeHtml(aluno.nome || '')}" class="scpi-input" required></div>
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email</label><input name="email" type="email" value="${escapeHtml(aluno.email || '')}" class="scpi-input" required></div>
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">RA</label><input name="ra" type="text" value="${escapeHtml(aluno.ra || '')}" class="scpi-input"></div>
        <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno</label>
          <select name="turno" class="scpi-input"><option value="">Não definido</option><option value="Matutino" ${aluno.turno === 'Matutino' ? 'selected' : ''}>Matutino</option><option value="Noturno" ${aluno.turno === 'Noturno' ? 'selected' : ''}>Noturno</option></select></div>
        <div class="flex gap-3 pt-2">
          <button type="button" onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
          <button type="submit" id="edit-btn" class="flex-1 py-3 rounded-2xl bg-accent text-white font-black text-sm transition-colors">Salvar</button>
        </div>
      </form>
    </div>`);
  document.getElementById('edit-aluno-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('edit-btn');
    btn.disabled = true; btn.textContent = 'Salvando…';
    try {
      await api.patch(`/admin/alunos/${aluno.aluno_id}`, {
        nome: e.target.querySelector('[name=nome]').value.trim(),
        email: e.target.querySelector('[name=email]').value.trim(),
        ra: e.target.querySelector('[name=ra]').value.trim() || null,
        turno: e.target.querySelector('[name=turno]').value || null,
      });
      invalidate('alunos'); await recarregar(container);
      closeModal(); toast.success('Aluno atualizado.');
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = 'Salvar'; }
  });
}

function showCreatedModal(email) {
  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div><h3 class="font-black text-lg">Aluno Criado</h3><p class="text-gray-500 text-xs font-bold mt-0.5">Credenciais enviadas por email</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="bg-[#0C0C12] rounded-2xl p-4 border border-white/5 mb-3">
        <p class="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Email</p>
        <p class="font-bold text-white">${escapeHtml(email)}</p>
      </div>
      <p class="text-blue-300 text-xs font-bold bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
        Senha temporária enviada para o email acima. O aluno definirá uma nova senha no primeiro acesso.
      </p>
      <button onclick="closeModal()" class="w-full mt-4 py-3 rounded-2xl bg-accent text-white font-black text-sm transition-colors">Fechar</button>
    </div>`);
}

function formHTML() {
  return `
    <form id="aluno-form" class="space-y-4">
      <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Nome Completo *</label><input name="nome" type="text" placeholder="Maria Santos" class="scpi-input" required></div>
      <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Email *</label><input name="email" type="email" placeholder="maria@escola.com" class="scpi-input" required></div>
      <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">RA/CPF</label><input name="ra" type="text" placeholder="2024001" class="scpi-input"></div>
      <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno</label>
        <select name="turno" class="scpi-input"><option value="">Não definido</option><option value="Matutino">Matutino</option><option value="Noturno">Noturno</option></select></div>
      <button id="aluno-create-btn" type="submit" class="w-full py-3 rounded-2xl bg-accent text-white font-black text-sm transition-all flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Aluno</span></button>
    </form>`;
}

async function handleCreate(form, container) {
  const btn = form.querySelector('[type=submit]');
  btn.disabled = true; btn.querySelector('span').textContent = 'Criando…';
  try {
    const email = form.querySelector('[name=email]').value.trim();
    await api.post('/admin/usuarios/aluno', {
      nome: form.querySelector('[name=nome]').value.trim(),
      email,
      ra: form.querySelector('[name=ra]').value.trim() || null,
      turno: form.querySelector('[name=turno]').value || null,
    });
    form.reset();
    invalidate('alunos'); page = 1;
    if (container) await recarregar(container);
    showCreatedModal(email);
  } catch (err) { toast.error(extractError(err)); }
  finally { btn.disabled = false; btn.querySelector('span').textContent = 'Criar Aluno'; }
}

function showImportResultModal(res) {
  window.closeModal = closeModal;
  const card = (valor, rotulo) => `
    <div class="flex-1 bg-[#0C0C12] rounded-2xl p-3 border border-white/5 text-center">
      <p class="font-black text-white text-xl">${valor ?? 0}</p>
      <p class="text-[10px] font-black text-gray-500 uppercase tracking-widest mt-0.5">${rotulo}</p>
    </div>`;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-5">
        <div><h3 class="font-black text-lg">Importação concluída</h3><p class="text-gray-500 text-xs font-bold mt-0.5">${res.erros.length} linha(s) com erro</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="flex gap-2 mb-3">
        ${card(res.importados, 'Criados')}
        ${card(res.duplicados, 'Duplicados')}
        ${card(res.matriculados, 'Matriculados')}
      </div>
      <p class="text-gray-500 text-xs font-bold mb-4">${res.emails_enviados ?? 0} e-mail(s) de senha temporária enviado(s).</p>
      <div class="max-h-48 overflow-y-auto space-y-1.5 pr-1">
        ${res.erros.map(e => `<p class="text-red-400 text-xs font-bold bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">${escapeHtml(e)}</p>`).join('')}
      </div>
      <button onclick="closeModal()" class="w-full mt-4 py-3 rounded-2xl bg-accent text-white font-black text-sm transition-colors">Fechar</button>
    </div>`);
}

async function handleImportCsv(file, container) {
  const fd = new FormData();
  fd.append('file', file);
  toast.info('Importando CSV…');
  try {
    const res = await api.postMultipart('/admin/importar-alunos', fd);
    invalidate('alunos', 'turmas');
    page = 1;
    if (container) await recarregar(container);
    if (res.erros && res.erros.length) {
      showImportResultModal(res);
    } else {
      const mat = res.matriculados ? ` ${res.matriculados} matriculado(s).` : '';
      const dup = res.duplicados ? ` ${res.duplicados} duplicado(s).` : '';
      toast.success(`${res.mensagem || 'Importação concluída.'}${mat}${dup} ${res.emails_enviados || 0} e-mail(s) enviado(s).`);
    }
  } catch (err) { toast.error(extractError(err)); }
}

export async function mount(container) {
  const saved = loadTab('alunos', { search: '', page: 1, turma_id: '', periodo_letivo: '', situacao: '' });
  search = saved.search;
  page = saved.page;
  filtros = { turma_id: saved.turma_id, periodo_letivo: saved.periodo_letivo, situacao: saved.situacao };
  container.innerHTML = `
    <div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden tab-anim">
      <div class="hidden lg:block lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 overflow-y-auto">
        <h3 class="font-black text-base mb-5 flex items-center gap-2">${icon('plus', 16)}<span>Novo Aluno</span></h3>
        ${formHTML()}
        <div class="mt-6 pt-6 border-t border-white/5">
          <h4 class="font-black text-xs uppercase tracking-widest text-gray-500 mb-3">Importar em massa</h4>
          <label for="aluno-csv-input" class="cursor-pointer w-full py-3 rounded-2xl bg-white/5 hover:bg-white/10 text-white font-black text-sm transition-all flex items-center justify-center gap-2 border border-white/10">
            ${icon('upload', 16)}<span>Importar CSV</span>
          </label>
          <input id="aluno-csv-input" type="file" accept=".csv" class="hidden">
          <p class="text-[10px] text-gray-600 font-bold mt-2 text-center">Colunas: nome, email, ra, turno, turma</p>
          <p class="text-[10px] text-gray-700 font-bold text-center">turno e turma são opcionais · turma = código da turma</p>
          <button id="aluno-csv-modelo" class="w-full mt-2 text-[10px] font-black text-accent hover:underline">Baixar modelo</button>
        </div>
      </div>
      <div class="flex-1 flex flex-col overflow-hidden gap-3 min-h-0">
        <div class="relative flex-shrink-0">
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 16)}</span>
          <input id="alunos-search" type="search" value="${escapeHtml(search)}" placeholder="Buscar aluno..." class="scpi-input pl-10 w-full">
        </div>
        <div id="alunos-filtros" class="flex-shrink-0"></div>
        <div id="alunos-banner-ocultos" class="flex-shrink-0"></div>
        <div id="alunos-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
        <div id="alunos-pagination" class="flex-shrink-0"></div>
      </div>
    </div>`;

  container.querySelector('#aluno-form').addEventListener('submit', e => { e.preventDefault(); handleCreate(e.target, container); });
  container.querySelector('#alunos-search').addEventListener('input', debounce(async e => {
    search = e.target.value;
    page = 1;
    saveTab('alunos', { search, page, ...filtros });
    await recarregar(container);
  }, 250));

  const csvInput = container.querySelector('#aluno-csv-input');
  csvInput.addEventListener('change', async () => {
    if (!csvInput.files[0]) return;
    await handleImportCsv(csvInput.files[0], container);
    csvInput.value = '';  // permite reenviar o mesmo arquivo depois de corrigir
  });
  container.querySelector('#aluno-csv-modelo').addEventListener('click', () => baixarModeloCsv(
    'modelo-alunos.csv',
    ['nome', 'email', 'ra', 'turno', 'turma'],
    ['Maria Santos', 'maria@escola.com', '2024001', 'Matutino', 'MAT-101'],
  ));

  setCreate(() => {
    window.closeModal = closeModal;
    openModal(`
      <div class="p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-black text-lg">Novo Aluno</h3>
          <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
        </div>
        ${formHTML()}
      </div>`);
    document.getElementById('aluno-form').addEventListener('submit', async e => {
      e.preventDefault();
      await handleCreate(e.target, container);
      if (!document.getElementById('aluno-form')) closeModal();
    });
  });

  try {
    const turmas = await carregarTurmas();
    await load();
    renderFiltros(container, turmas);
    renderList(container);
  } catch (err) { toast.error(extractError(err)); }
}
