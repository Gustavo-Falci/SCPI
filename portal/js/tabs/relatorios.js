import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { icon } from '../icons.js';
import { debounce } from '../utils.js';
import { paginate, renderPagination } from '../pagination.js';
import { getState } from '../state.js';
import { openModal, closeModal } from '../main.js';

const PER_PAGE = 8;
let page = 1;
let data = [];

async function load() {
  const state = getState();
  if (!state.cache.relatorios) state.cache.relatorios = await api.get('/admin/relatorios/chamadas');
  data = state.cache.relatorios;
}

function filtered() {
  const { turno, semestre } = getState();
  return data.filter(r => r.turno === turno && (semestre === 'Todos' || String(r.semestre) === String(semestre)));
}

function statCard(label, value, color) {
  return `<div class="text-center"><p class="text-sm font-black ${color}">${value}</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-0.5">${label}</p></div>`;
}

function renderList(container) {
  const f = filtered();
  const { items, page: pg, total, count } = paginate(f, page, PER_PAGE);
  page = pg;
  const list = container.querySelector('#rel-list');
  const pag = container.querySelector('#rel-pagination');

  if (!items.length) {
    list.innerHTML = `<div class="flex flex-col items-center justify-center py-16 text-gray-600 gap-2">${icon('file-text', 40)}<p class="font-black text-sm">Nenhuma chamada para este filtro</p><p class="text-xs text-gray-700">Tente mudar o turno ou semestre</p></div>`;
  } else {
    const isNight = getState().turno === 'Noturno';
    const colorBadge = isNight ? 'bg-indigo-500/10 text-indigo-500' : 'bg-amber-500/10 text-amber-500';
    const colorSem = isNight ? 'bg-indigo-500/10 text-indigo-500' : 'bg-amber-500/10 text-amber-500';

    list.innerHTML = items.map((r, i) => {
      const freq = r.percentual ?? 0;
      const freqColor = freq >= 75 ? 'text-green-400' : 'text-red-400';
      return `
        <button data-id="${r.chamada_id}" class="anim-item group rel-item w-full bg-[#151718] hover:bg-[#1A1C1E] px-5 py-3 rounded-2xl border border-white/5 flex items-center justify-between gap-4 transition-all hover:border-accent/20 text-left flex-shrink-0" style="animation-delay:${i * 55}ms">
          <div class="flex items-center gap-4 min-w-0">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg flex-shrink-0 ${colorSem}">${r.semestre}º</div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 mb-0.5 flex-wrap">
                <h4 class="font-black text-white text-sm">${r.nome_disciplina}</h4>
                <span class="text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${colorBadge}">${r.turno}</span>
              </div>
              <p class="text-gray-500 font-bold text-xs truncate">Prof. ${r.professor_nome} · ${r.codigo_turma} · ${r.data_chamada} · ${r.horario_inicio} – ${r.horario_fim}</p>
            </div>
          </div>
          <div class="flex items-center gap-4 xl:gap-6 flex-shrink-0">
            <div class="hidden md:flex items-center gap-4">
              ${statCard('Alunos', r.total_alunos, 'text-white')}
              ${statCard('Presentes', r.presentes_alunos ?? '—', 'text-green-400')}
              ${statCard('Ausentes', r.ausentes_alunos ?? '—', 'text-red-400')}
              ${statCard('Parciais', r.parciais_alunos ?? '—', 'text-yellow-400')}
            </div>
            <div class="flex md:hidden items-center gap-2 text-xs font-black">
              <span class="text-green-400">${r.presentes_alunos ?? 0}P</span>
              <span class="text-gray-700">/</span>
              <span class="text-red-400">${r.ausentes_alunos ?? 0}A</span>
            </div>
            <div class="text-center min-w-[54px]">
              <p class="text-base font-black ${freqColor}">${freq}%</p>
              <div class="mt-1 w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div class="prog-bar-fill h-full rounded-full" style="width:${freq}%;background:${freq >= 75 ? '#4ade80' : freq >= 50 ? '#facc15' : '#f87171'}"></div>
              </div>
            </div>
            <span class="text-gray-600 group-hover:text-accent transition-colors">${icon('chevron-right', 16)}</span>
          </div>
        </button>
      `;
    }).join('');

    list.querySelectorAll('.rel-item').forEach(btn => btn.addEventListener('click', () => openDetalhe(btn.dataset.id)));
  }
  renderPagination(pag, { page, total, count, perPage: PER_PAGE }, p => { page = p; renderList(container); });
}

async function openDetalhe(chamadaId) {
  window.closeModal = closeModal;
  openModal(`<div class="p-8 flex items-center justify-center"><div class="spin opacity-50">${icon('loader', 28)}</div></div>`, 'max-w-3xl');
  try {
    const d = await api.get(`/admin/relatorios/chamadas/${chamadaId}`);
    const isNight = d.turno === 'Noturno';
    const colorBadge = isNight ? 'bg-indigo-500/10 text-indigo-500' : 'bg-amber-500/10 text-amber-500';
    const freq = d.percentual ?? 0;
    const freqColor = freq >= 75 ? 'text-green-400' : 'text-red-400';

    document.getElementById('modal-box').innerHTML = `
      <div class="flex items-center justify-between p-6 border-b border-white/5 flex-shrink-0">
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <h3 class="font-black text-lg">${d.nome_disciplina}</h3>
            <span class="text-xs font-black px-2 py-0.5 rounded-md uppercase ${colorBadge}">${d.turno}</span>
          </div>
          <p class="text-gray-500 text-xs font-bold">Prof. ${d.professor_nome} · ${d.codigo_turma} · ${d.data_chamada} · ${d.horario_inicio} – ${d.horario_fim}</p>
        </div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500 flex-shrink-0">${icon('x', 16)}</button>
      </div>
      <div class="p-6 overflow-y-auto">
        <!-- Stats -->
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          <div class="bg-[#0C0C12] rounded-2xl p-4 text-center border border-white/5"><p class="text-xl font-black text-white">${d.total_alunos}</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-1">Total</p></div>
          <div class="bg-green-500/5 rounded-2xl p-4 text-center border border-green-500/10"><p class="text-xl font-black text-green-400">${d.presentes ?? '—'}</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-1">Slots Presentes</p></div>
          <div class="bg-[#0C0C12] rounded-2xl p-4 text-center border border-white/5"><p class="text-xl font-black ${freqColor}">${freq}%</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-1">Frequência</p></div>
          <div class="bg-[#0C0C12] rounded-2xl p-4 text-center border border-white/5"><p class="text-xl font-black text-white">${d.total_aulas}</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-1">Aulas</p></div>
          <div class="bg-[#0C0C12] rounded-2xl p-4 text-center border border-white/5"><p class="text-xl font-black text-yellow-400">${d.ausentes}</p><p class="text-xs text-gray-600 font-black uppercase tracking-widest mt-1">Slots Ausentes</p></div>
        </div>
        <!-- Alunos table -->
        <div class="bg-[#0C0C12] rounded-2xl border border-white/5 overflow-hidden">
          <div class="grid text-xs font-black text-gray-600 uppercase tracking-widest px-4 py-3 border-b border-white/5" style="grid-template-columns: 1fr auto auto auto">
            <span>Aluno</span><span class="text-center">Aulas</span><span class="text-center mx-4">Tipo</span><span class="text-center">Status</span>
          </div>
          ${(d.alunos || []).map(a => {
            const pct = d.total_aulas > 0 ? Math.round(a.aulas_presentes_count / d.total_aulas * 100) : 0;
            const status = a.aulas_presentes_count === 0 ? { label: 'Ausente', cls: 'bg-red-500/10 text-red-400' }
              : a.aulas_presentes_count >= d.total_aulas ? { label: 'Presente', cls: 'bg-green-500/10 text-green-400' }
              : { label: 'Parcial', cls: 'bg-yellow-500/10 text-yellow-400' };
            return `
              <div class="grid items-center px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors" style="grid-template-columns: 1fr auto auto auto">
                <div><p class="font-black text-sm text-white">${a.nome}</p><p class="text-xs text-gray-600 font-bold">${a.ra !== '—' ? `RA: ${a.ra}` : ''}</p></div>
                <span class="text-center font-black text-sm text-white">${a.aulas_presentes_count}/${d.total_aulas}</span>
                <span class="text-center font-bold text-xs text-gray-500 mx-4">${a.tipo_registro !== '—' ? a.tipo_registro : '—'}</span>
                <span class="text-xs font-black px-2 py-1 rounded-lg ${status.cls}">${status.label}</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  } catch (err) {
    document.getElementById('modal-box').innerHTML = `<div class="p-8 text-red-400 font-black text-center">${extractError(err)}<br><button onclick="closeModal()" class="mt-4 px-4 py-2 rounded-xl border border-white/10 text-white text-sm">Fechar</button></div>`;
  }
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex-1 overflow-hidden flex flex-col gap-3 min-h-0 tab-anim">
      <div id="rel-list" class="flex-1 overflow-y-auto space-y-2 pr-1"></div>
      <div id="rel-pagination" class="flex-shrink-0"></div>
    </div>
  `;
  try { await load(); renderList(container); } catch (err) { toast.error(extractError(err)); }
}
