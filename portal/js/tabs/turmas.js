import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { debounce, escapeHtml } from '../utils.js';
import { paginate, renderPagination } from '../pagination.js';
import { getState, invalidate } from '../state.js';
import { openModal, closeModal, animateRemove } from '../main.js';
import { setCreate } from '../registry.js';
import { SEMESTRES, TURNOS, PERIODOS } from '../config.js';

const PER_PAGE = 8;
let page = 1;
let search = '';
let turmas = [];
let professores = [];

async function load() {
  const state = getState();
  if (!state.cache.turmas) state.cache.turmas = await api.get('/admin/turmas-completas');
  if (!state.cache.professores) state.cache.professores = await api.get('/admin/professores');
  turmas = state.cache.turmas;
  professores = state.cache.professores;
}

function filtered() {
  const { turno, semestre } = getState();
  let f = turmas.filter(t => t.turno === turno && (semestre === 'Todos' || String(t.semestre) === String(semestre)));
  if (search) { const q = search.toLowerCase(); f = f.filter(t => t.nome_disciplina?.toLowerCase().includes(q) || t.codigo_turma?.toLowerCase().includes(q)); }
  return f;
}

function renderList(container) {
  const f = filtered();
  const { items, page: pg, total, count } = paginate(f, page, PER_PAGE);
  page = pg;
  const list = container.querySelector('#turmas-list');
  const pag = container.querySelector('#turmas-pagination');
  const { turno } = getState();
  const isNight = turno === 'Noturno';
  const colorBadge = isNight ? 'bg-indigo-500/10 text-indigo-500' : 'bg-amber-500/10 text-amber-500';

  if (!items.length) {
    list.innerHTML = `
      <div class="flex flex-col items-center justify-center py-16 text-gray-600 gap-3">
        ${icon('graduation-cap', 40)}
        <p class="font-black text-sm">${search ? 'Nenhuma turma encontrada' : 'Nenhuma turma cadastrada'}</p>
        ${!search ? `<button id="cta-create-turma" class="mt-1 px-4 py-2 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-black text-xs flex items-center gap-1.5 transition-colors">${icon('plus', 14)} Criar primeira turma</button>` : ''}
      </div>`;
    document.getElementById('cta-create-turma')?.addEventListener('click', () => document.querySelector('#turma-form [name=nome_disciplina]')?.focus());
  } else {
    // Ações: `hidden lg:flex` em vez de `opacity-0 group-hover:opacity-100`.
    // opacity-0 escondia visualmente mas mantinha os ~168px no fluxo (o que
    // truncava o texto cedo demais no celular) e os botões seguiam clicáveis —
    // incluindo Excluir, invisível e sujeito a toque acidental.
    list.innerHTML = items.map((t, i) => `
      <div data-turma-id="${t.turma_id}" class="turma-card anim-item group bg-[#151718] hover:bg-[#1A1C1E] px-4 sm:px-5 py-4 rounded-2xl border border-white/5 flex items-center justify-between gap-3 sm:gap-4 transition-all hover:border-white/10" style="animation-delay:${i * 45}ms">
        <div class="flex items-center gap-3 sm:gap-4 min-w-0 flex-1">
          <div class="w-10 h-10 rounded-2xl flex items-center justify-center font-black text-base flex-shrink-0 ${colorBadge}">${t.semestre}º</div>
          <div class="min-w-0">
            <p class="font-black text-white text-sm truncate">${escapeHtml(t.nome_disciplina)}</p>
            <p class="text-gray-500 font-bold text-xs truncate">${escapeHtml(t.codigo_turma)} · ${escapeHtml(t.professor_nome || 'Sem professor')}<span class="hidden lg:inline"> · ${t.total_alunos ?? 0} alunos</span></p>
            <p class="text-gray-600 font-bold text-xs lg:hidden">${t.total_alunos ?? 0} alunos</p>
          </div>
        </div>
        <div class="hidden lg:flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button title="Atribuir professor" data-id="${t.turma_id}" class="btn-prof w-8 h-8 rounded-xl bg-accent/10 hover:bg-accent/20 flex items-center justify-center text-accent transition-all">${icon('user-check', 14)}</button>
          <button title="Matricular alunos" data-id="${t.turma_id}" class="btn-mat w-8 h-8 rounded-xl bg-green-500/10 hover:bg-green-500/20 flex items-center justify-center text-green-400 transition-all">${icon('user-plus', 14)}</button>
          <button title="Importar CSV" data-id="${t.turma_id}" class="btn-csv w-8 h-8 rounded-xl bg-yellow-500/10 hover:bg-yellow-500/20 flex items-center justify-center text-yellow-400 transition-all">${icon('upload', 14)}</button>
          <button title="Excluir" data-id="${t.turma_id}" class="btn-del w-8 h-8 rounded-xl bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all">${icon('trash-2', 14)}</button>
        </div>
        <span class="lg:hidden text-gray-600 flex-shrink-0" aria-hidden="true">${icon('chevron-right', 18)}</span>
      </div>
    `).join('');

    // stopPropagation: no desktop os atalhos de hover não podem abrir o modal
    // de detalhe junto com a própria ação.
    const bindAction = (sel, fn) => list.querySelectorAll(sel).forEach(btn => {
      btn.addEventListener('click', e => { e.stopPropagation(); fn(btn); });
    });
    bindAction('.btn-prof', btn => showProfModal(turmas.find(x => String(x.turma_id) === String(btn.dataset.id)), container));
    bindAction('.btn-mat', btn => showMatriculaModal(btn.dataset.id, container));
    bindAction('.btn-csv', btn => importCSV(btn.dataset.id, container));
    bindAction('.btn-del', btn => deleteTurma(btn.dataset.id, container));

    list.querySelectorAll('.turma-card').forEach(card => {
      card.addEventListener('click', () => {
        const t = turmas.find(x => String(x.turma_id) === String(card.dataset.turmaId));
        if (t) showTurmaDetail(t, container);
      });
    });
  }
  renderPagination(pag, { page, total, count, perPage: PER_PAGE }, p => { page = p; renderList(container); });
}

// Detalhe da turma: no celular é a única via para as ações, já que os atalhos
// de hover só existem em lg+. Nome sem truncate e ações com rótulo — é aqui
// que a informação cortada na lista aparece inteira.
function showTurmaDetail(turma, container) {
  const acao = (cls, iconName, label, tone) => `
    <button class="${cls} w-full flex items-center gap-3 px-4 py-3.5 rounded-2xl font-black text-sm text-left transition-colors ${tone}">
      ${icon(iconName, 18)}<span>${label}</span>
    </button>`;

  openModal(`
    <div class="p-6">
      <div class="flex items-start justify-between gap-3 mb-1">
        <h3 class="font-black text-lg leading-tight">${escapeHtml(turma.nome_disciplina)}</h3>
        <button id="td-close" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500 flex-shrink-0">${icon('x', 16)}</button>
      </div>
      <p class="text-gray-500 text-xs font-bold mb-5">
        ${escapeHtml(turma.codigo_turma)} · ${turma.semestre}º semestre · ${escapeHtml(turma.turno || '')}${turma.sala_padrao ? ` · Sala ${escapeHtml(turma.sala_padrao)}` : ''}
      </p>

      <div class="grid grid-cols-2 gap-2 mb-5">
        <div class="px-4 py-3 rounded-2xl bg-surface border border-white/5 min-w-0">
          <p class="text-[10px] font-black text-gray-600 uppercase tracking-widest">Professor</p>
          <p class="font-black text-sm truncate mt-0.5">${escapeHtml(turma.professor_nome || 'Sem professor')}</p>
        </div>
        <div class="px-4 py-3 rounded-2xl bg-surface border border-white/5">
          <p class="text-[10px] font-black text-gray-600 uppercase tracking-widest">Alunos</p>
          <p class="font-black text-sm mt-0.5">${turma.total_alunos ?? 0}</p>
        </div>
      </div>

      <div class="space-y-1.5">
        ${acao('td-prof', 'user-check', 'Atribuir professor', 'text-accent hover:bg-accent/10')}
        ${acao('td-mat', 'user-plus', 'Matricular alunos', 'text-green-400 hover:bg-green-500/10')}
        ${acao('td-csv', 'upload', 'Importar alunos por CSV', 'text-yellow-400 hover:bg-yellow-500/10')}
      </div>
      <div class="mt-4 pt-4 border-t border-white/5">
        ${acao('td-del', 'trash-2', 'Excluir turma', 'text-red-400 hover:bg-red-500/10')}
      </div>
    </div>
  `);

  const box = document.getElementById('modal-box');
  box.querySelector('#td-close').addEventListener('click', closeModal);
  // Cada ação substitui o conteúdo do modal (showProfModal/showMatriculaModal
  // chamam openModal de novo) ou o fecha antes de seguir.
  box.querySelector('.td-prof').addEventListener('click', () => showProfModal(turma, container));
  box.querySelector('.td-mat').addEventListener('click', () => showMatriculaModal(turma.turma_id, container));
  box.querySelector('.td-csv').addEventListener('click', () => { closeModal(); importCSV(turma.turma_id, container); });
  box.querySelector('.td-del').addEventListener('click', () => { closeModal(); deleteTurma(turma.turma_id, container); });
}

async function deleteTurma(id, container) {
  const ok = await confirm.show('Excluir Turma', 'Remove a turma e todos os horários e matrículas associados. Continuar?');
  if (!ok) return;
  const el = container.querySelector(`[data-turma-id="${id}"]`);
  await animateRemove(el);
  try {
    await api.del(`/admin/turmas/${id}`);
    invalidate('turmas', 'grade');
    await load(); renderList(container);
    toast.success('Turma excluída.');
  } catch (err) { toast.error(extractError(err)); await load(); renderList(container); }
}

function showProfModal(turma, container) {
  window.closeModal = closeModal;
  const opts = [{ professor_id: null, nome: 'Sem professor' }, ...professores];
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div><h3 class="font-black text-lg">Atribuir Professor</h3><p class="text-gray-500 text-xs font-bold mt-0.5">${escapeHtml(turma.nome_disciplina)}</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="space-y-2 max-h-72 overflow-y-auto mb-6">
        ${opts.map(p => `
          <label class="flex items-center gap-3 px-4 py-3 rounded-2xl border border-white/5 hover:border-accent/30 hover:bg-accent/5 cursor-pointer transition-all">
            <input type="radio" name="professor" value="${p.professor_id ?? ''}" ${String(turma.professor_id) === String(p.professor_id) ? 'checked' : ''} class="accent-[#4B39EF]">
            <div><p class="font-black text-sm text-white">${escapeHtml(p.nome)}</p>${p.email ? `<p class="text-xs text-gray-600 font-bold">${escapeHtml(p.email)}</p>` : ''}</div>
          </label>
        `).join('')}
      </div>
      <div class="flex gap-3">
        <button onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
        <button id="prof-assign-btn" class="flex-1 py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors">Salvar</button>
      </div>
    </div>
  `);

  document.getElementById('prof-assign-btn').addEventListener('click', async () => {
    const val = document.querySelector('input[name="professor"]:checked')?.value;
    const btn = document.getElementById('prof-assign-btn');
    btn.disabled = true; btn.textContent = 'Salvando…';
    try {
      await api.patch(`/admin/turmas/${turma.turma_id}/professor`, { professor_id: val || null });
      invalidate('turmas');
      await load();
      renderList(container);
      closeModal();
      toast.success('Professor atribuído.');
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = 'Salvar'; }
  });
}

async function showMatriculaModal(turmaId, container) {
  const turma = turmas.find(t => String(t.turma_id) === String(turmaId));
  window.closeModal = closeModal;

  openModal(`<div class="p-8 flex items-center justify-center"><div class="spin opacity-50">${icon('loader', 28)}</div></div>`, 'max-w-xl');

  let allAlunos = [];
  try { allAlunos = await api.get('/admin/alunos'); } catch (err) { toast.error(extractError(err)); closeModal(); return; }

  let matriculados = new Set();
  let matriculadosList = [];
  try {
    matriculadosList = await api.get(`/admin/turmas/${turmaId}/alunos`).catch(() => []);
    matriculadosList.forEach(a => matriculados.add(String(a.aluno_id)));
  } catch {}

  const MAT_PER_PAGE = 8;
  let aba = 'matricular'; // 'matricular' | 'matriculados'
  const estado = {
    matricular:   { search: '', selected: new Set(), page: 1 },
    matriculados: { search: '', selected: new Set(), page: 1 },
  };

  function elegivel(a) { return !matriculados.has(String(a.aluno_id)) && (!turma.turno || !a.turno || a.turno === turma.turno); }
  const elegiveis = allAlunos.filter(elegivel);

  function renderMatList() {
    const st = estado[aba];
    const fonte = aba === 'matricular' ? elegiveis : matriculadosList;
    const isRemover = aba === 'matriculados';

    const filtered = st.search
      ? fonte.filter(a => a.nome.toLowerCase().includes(st.search.toLowerCase()) || a.ra?.toLowerCase().includes(st.search.toLowerCase()))
      : fonte;
    const { items, page: pg, total, count } = paginate(filtered, st.page, MAT_PER_PAGE);
    st.page = pg;
    const allSelected = filtered.length > 0 && filtered.every(a => st.selected.has(String(a.aluno_id)));
    const someSelected = filtered.some(a => st.selected.has(String(a.aluno_id)));
    const selCount = st.selected.size;

    const tabBtn = (id, label) => `<button data-aba="${id}" class="aba-btn flex-1 py-2 rounded-xl font-black text-xs transition-colors ${aba === id ? 'bg-accent text-white' : 'text-gray-500 hover:bg-white/5'}">${label}</button>`;
    const emptyMsg = isRemover ? 'Nenhum aluno matriculado' : 'Nenhum aluno elegível';
    const actionLabel = isRemover ? 'Desmatricular' : 'Matricular';
    const actionColor = isRemover ? 'bg-red-500 hover:bg-red-600' : 'bg-accent hover:bg-accent-dark';

    document.getElementById('modal-box').innerHTML = `
      <div class="flex items-center justify-between p-6 border-b border-white/5 flex-shrink-0">
        <div><h3 class="font-black text-lg">Alunos da Turma</h3><p class="text-gray-500 text-xs font-bold mt-0.5">${escapeHtml(turma.nome_disciplina)} · ${turma.turno}</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <div class="p-4 border-b border-white/5 flex-shrink-0 flex gap-2">
        ${tabBtn('matricular', 'Matricular')}
        ${tabBtn('matriculados', 'Matriculados')}
      </div>
      <div class="p-4 border-b border-white/5 flex-shrink-0">
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 15)}</span>
          <input id="mat-search" type="search" value="${st.search}" placeholder="Buscar aluno..." class="scpi-input pl-9 w-full">
        </div>
      </div>
      <div class="p-4 border-b border-white/5 flex-shrink-0">
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" id="select-all-mat" ${allSelected ? 'checked' : ''} ${someSelected && !allSelected ? 'data-indeterminate="true"' : ''} class="accent-[#4B39EF] w-4 h-4">
          <span class="font-black text-sm text-white">Selecionar todos${selCount > 0 ? ` · ${selCount} selecionado(s)` : ''}</span>
        </label>
      </div>
      <div class="flex-1 overflow-y-auto">
        ${!items.length ? `<div class="flex flex-col items-center py-10 text-gray-600">${icon('user', 28)}<p class="mt-2 font-black text-xs">${emptyMsg}</p></div>` : items.map(a => `
          <label class="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/5 cursor-pointer transition-colors">
            <input type="checkbox" class="mat-check accent-[#4B39EF] w-4 h-4" data-id="${a.aluno_id}" ${st.selected.has(String(a.aluno_id)) ? 'checked' : ''}>
            <div class="flex-1 min-w-0"><p class="font-black text-sm text-white truncate">${escapeHtml(a.nome)}</p><p class="text-xs text-gray-600 font-bold">${escapeHtml(a.ra || '')}</p></div>
          </label>
        `).join('')}
      </div>
      ${total > 1 ? `<div class="px-4 py-3 border-t border-white/5 flex-shrink-0 flex items-center justify-between"><span class="text-xs text-gray-600 font-black">${count} ${isRemover ? 'matriculados' : 'elegíveis'}</span><div class="flex items-center gap-1"><button id="mat-prev" ${st.page <= 1 ? 'disabled' : ''} class="w-7 h-7 rounded-lg border border-white/10 flex items-center justify-center text-gray-500 disabled:opacity-30">${icon('chevron-left', 13)}</button><span class="text-xs font-black text-gray-500 px-2">${st.page}/${total}</span><button id="mat-next" ${st.page >= total ? 'disabled' : ''} class="w-7 h-7 rounded-lg border border-white/10 flex items-center justify-center text-gray-500 disabled:opacity-30">${icon('chevron-right', 13)}</button></div></div>` : ''}
      <div class="p-4 border-t border-white/5 flex gap-3 flex-shrink-0">
        <button onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
        <button id="mat-submit" ${!selCount ? 'disabled' : ''} class="flex-1 py-3 rounded-2xl ${actionColor} disabled:opacity-40 text-white font-black text-sm transition-colors">${actionLabel} ${selCount > 0 ? `(${selCount})` : ''}</button>
      </div>
    `;

    const saEl = document.getElementById('select-all-mat');
    if (saEl?.dataset.indeterminate === 'true') { saEl.indeterminate = true; saEl.checked = false; }

    document.querySelectorAll('.aba-btn').forEach(b => b.addEventListener('click', () => { aba = b.dataset.aba; renderMatList(); }));

    saEl?.addEventListener('change', () => {
      filtered.forEach(a => saEl.checked ? st.selected.add(String(a.aluno_id)) : st.selected.delete(String(a.aluno_id)));
      renderMatList();
    });

    document.querySelectorAll('.mat-check').forEach(chk => {
      chk.addEventListener('change', () => { chk.checked ? st.selected.add(chk.dataset.id) : st.selected.delete(chk.dataset.id); renderMatList(); });
    });

    document.getElementById('mat-search')?.addEventListener('input', e => { st.search = e.target.value; st.page = 1; renderMatList(); });
    document.getElementById('mat-prev')?.addEventListener('click', () => { st.page--; renderMatList(); });
    document.getElementById('mat-next')?.addEventListener('click', () => { st.page++; renderMatList(); });

    document.getElementById('mat-submit')?.addEventListener('click', isRemover ? onDesmatricular : onMatricular);
  }

  async function onMatricular() {
    const st = estado.matricular;
    const btn = document.getElementById('mat-submit');
    btn.disabled = true; btn.textContent = 'Matriculando…';
    try {
      await api.post(`/admin/turmas/${turmaId}/matricular-alunos`, { aluno_ids: [...st.selected] });
      invalidate('turmas');
      await load();
      renderList(container);
      closeModal();
      toast.success(`${st.selected.size} aluno(s) matriculado(s).`);
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = `Matricular (${st.selected.size})`; }
  }

  async function onDesmatricular() {
    const st = estado.matriculados;
    const n = st.selected.size;
    const ok = await confirm.show('Desmatricular Alunos', `Remover ${n} aluno(s) desta turma? O histórico de presença é mantido.`);
    if (!ok) return;
    const btn = document.getElementById('mat-submit');
    btn.disabled = true; btn.textContent = 'Desmatriculando…';
    try {
      await api.post(`/admin/turmas/${turmaId}/desmatricular-alunos`, { aluno_ids: [...st.selected] });
      invalidate('turmas');
      await load();
      renderList(container);
      closeModal();
      toast.success(`${n} aluno(s) desmatriculado(s).`);
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = `Desmatricular (${n})`; }
  }

  renderMatList();
}

function importCSV(turmaId, container) {
  const input = document.createElement('input');
  input.type = 'file'; input.accept = '.csv';
  input.addEventListener('change', async () => {
    if (!input.files[0]) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    toast.info('Importando CSV…');
    try {
      const res = await api.postMultipart(`/admin/turmas/${turmaId}/importar-alunos`, fd);
      invalidate('turmas', 'alunos');
      await load();
      renderList(container);
      // If response is a CSV blob, trigger download
      if (res?.csv_download_url || res?.senhas_csv) {
        toast.success('CSV importado! Arquivo de senhas disponível para download.');
      } else {
        toast.success('Alunos importados com sucesso!');
      }
    } catch (err) { toast.error(extractError(err)); }
  });
  input.click();
}

async function createTurma(e, container) {
  e.preventDefault();
  const btn = document.getElementById('turma-create-btn');
  const form = document.getElementById('turma-form');
  btn.disabled = true; btn.textContent = 'Criando…';
  try {
    await api.post('/admin/turmas', {
      nome_disciplina: form.querySelector('[name=nome_disciplina]').value.trim(),
      codigo_turma: form.querySelector('[name=codigo_turma]').value.trim(),
      semestre: form.querySelector('[name=semestre]').value,
      turno: form.querySelector('[name=turno]').value,
      sala_padrao: form.querySelector('[name=sala_padrao]').value.trim() || null,
      periodo_letivo: form.querySelector('[name=periodo_letivo]').value,
    });
    form.reset();
    invalidate('turmas');
    await load();
    page = 1;
    renderList(container);
    toast.success('Turma criada!');
  } catch (err) { toast.error(extractError(err)); }
  finally { btn.disabled = false; btn.textContent = 'Criar Turma'; }
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden tab-anim">
      <div class="hidden lg:block lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 overflow-y-auto">
        <h3 class="font-black text-base mb-5 flex items-center gap-2">${icon('plus', 16)}<span>Nova Turma</span></h3>
        <form id="turma-form" class="space-y-4">
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Disciplina *</label>
            <input name="nome_disciplina" type="text" placeholder="Engenharia de Software" class="scpi-input" required>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Código *</label>
            <input name="codigo_turma" type="text" placeholder="ES-2025-1" class="scpi-input" required>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Semestre *</label>
              <select name="semestre" class="scpi-input" required>
                ${SEMESTRES.map(s => `<option value="${s}">${s}º</option>`).join('')}
              </select>
            </div>
            <div>
              <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno *</label>
              <select name="turno" class="scpi-input" required>
                ${TURNOS.map(t => `<option value="${t}">${t}</option>`).join('')}
              </select>
            </div>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Sala Padrão</label>
            <input name="sala_padrao" type="text" placeholder="Lab 01" class="scpi-input">
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Período Letivo *</label>
            <select name="periodo_letivo" class="scpi-input" required>
              ${PERIODOS.map(p => `<option value="${p}">${p}</option>`).join('')}
            </select>
          </div>
          <button id="turma-create-btn" type="submit" class="w-full py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Turma</span></button>
        </form>
      </div>
      <div class="flex-1 flex flex-col overflow-hidden gap-3 min-h-0">
        <div class="relative flex-shrink-0">
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600">${icon('search', 16)}</span>
          <input id="turmas-search" type="search" placeholder="Buscar turma..." class="scpi-input pl-10 w-full">
        </div>
        <div id="turmas-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
        <div id="turmas-pagination" class="flex-shrink-0"></div>
      </div>
    </div>
  `;
  container.querySelector('#turma-form').addEventListener('submit', e => createTurma(e, container));
  container.querySelector('#turmas-search').addEventListener('input', debounce(e => { search = e.target.value; page = 1; renderList(container); }, 200));

  setCreate(() => {
    window.closeModal = closeModal;
    openModal(`
      <div class="p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-black text-lg">Nova Turma</h3>
          <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
        </div>
        <form id="turma-form-modal" class="space-y-4">
          <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Disciplina *</label><input name="nome_disciplina" class="scpi-input" placeholder="Engenharia de Software" required></div>
          <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Código *</label><input name="codigo_turma" class="scpi-input" placeholder="ES-2025-1" required></div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Semestre</label><select name="semestre" class="scpi-input">${SEMESTRES.map(s => `<option value="${s}">${s}º</option>`).join('')}</select></div>
            <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Turno</label><select name="turno" class="scpi-input">${TURNOS.map(t => `<option value="${t}">${t}</option>`).join('')}</select></div>
          </div>
          <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Sala</label><input name="sala_padrao" class="scpi-input" placeholder="Lab 01"></div>
          <div><label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Período</label><select name="periodo_letivo" class="scpi-input">${PERIODOS.map(p => `<option value="${p}">${p}</option>`).join('')}</select></div>
          <button type="submit" class="w-full py-3 rounded-2xl bg-accent text-white font-black text-sm transition-all flex items-center justify-center gap-2">${icon('plus', 16)}<span>Criar Turma</span></button>
        </form>
      </div>`);
    document.getElementById('turma-form-modal').addEventListener('submit', async e => {
      e.preventDefault();
      const btn = e.target.querySelector('[type=submit] span');
      btn.textContent = 'Criando…';
      try {
        await api.post('/admin/turmas', {
          nome_disciplina: e.target.querySelector('[name=nome_disciplina]').value.trim(),
          codigo_turma: e.target.querySelector('[name=codigo_turma]').value.trim(),
          semestre: e.target.querySelector('[name=semestre]').value,
          turno: e.target.querySelector('[name=turno]').value,
          sala_padrao: e.target.querySelector('[name=sala_padrao]').value.trim() || null,
          periodo_letivo: e.target.querySelector('[name=periodo_letivo]').value,
        });
        invalidate('turmas'); await load(); page = 1; renderList(container);
        closeModal(); toast.success('Turma criada!');
      } catch (err) { toast.error(extractError(err)); btn.textContent = 'Criar Turma'; }
    });
  });

  try { await load(); renderList(container); } catch (err) { toast.error(extractError(err)); }
}
