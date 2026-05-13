import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { getState, invalidate } from '../state.js';
import { openModal, closeModal } from '../main.js';
import { DIAS_SEMANA, SLOTS_MATUTINO, SLOTS_NOTURNO } from '../config.js';

async function loadGrade() {
  const state = getState();
  if (!state.cache.grade) state.cache.grade = await api.get('/admin/horarios-todos');
  if (!state.cache.turmas) state.cache.turmas = await api.get('/admin/turmas-completas');
  return { grade: state.cache.grade, turmas: state.cache.turmas };
}

function renderGrid(container) {
  const state = getState();
  const grade = state.cache.grade || [];
  const turno = state.turno;
  const semestre = state.semestre;

  const filtered = grade.filter(g => g.turno === turno && (semestre === 'Todos' || String(g.semestre) === String(semestre)));
  const isNight = turno === 'Noturno';
  const colorCard = isNight ? 'bg-indigo-500/5 border-indigo-500/15 hover:border-indigo-500/30' : 'bg-amber-500/5 border-amber-500/15 hover:border-amber-500/30';
  const colorTime = isNight ? 'text-indigo-400' : 'text-amber-500';

  const grid = container.querySelector('#horarios-grid');
  grid.innerHTML = DIAS_SEMANA.map((dia, idx) => {
    const aulas = filtered.filter(g => g.dia_semana === idx).sort((a, b) => (a.inicio || a.horario_inicio || '').localeCompare(b.inicio || b.horario_inicio || ''));
    return `
      <div class="min-w-[140px]">
        <div class="text-center font-black text-gray-600 text-xs uppercase tracking-[0.2em] mb-3">${dia}</div>
        <div class="space-y-3">
          ${aulas.map(h => `
            <div class="group p-3 rounded-2xl border-2 transition-all ${colorCard}">
              <p class="text-[10px] font-black uppercase mb-1.5 ${colorTime}">${h.inicio || h.horario_inicio} — ${h.fim || h.horario_fim}</p>
              <p class="text-sm font-black text-white leading-tight mb-1.5">${h.nome_disciplina}</p>
              <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-1 opacity-40">
                  ${icon('map-pin', 10)}
                  <span class="text-[10px] font-black uppercase">${h.sala || '—'}</span>
                </div>
                <button data-id="${h.horario_id}" class="del-horario w-6 h-6 rounded-lg bg-red-500/20 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0 opacity-0 group-hover:opacity-100">${icon('trash-2', 11)}</button>
              </div>
            </div>
          `).join('')}
          <button data-dia="${idx}" class="add-horario w-full py-4 border-2 border-dashed border-white/5 rounded-2xl flex items-center justify-center text-gray-700 hover:border-accent/40 hover:text-accent transition-all">${icon('plus', 20)}</button>
        </div>
      </div>
    `;
  }).join('');

  grid.querySelectorAll('.del-horario').forEach(btn => btn.addEventListener('click', () => deleteHorario(btn.dataset.id, container)));
  grid.querySelectorAll('.add-horario').forEach(btn => btn.addEventListener('click', () => showAddModal(+btn.dataset.dia, container)));
}

async function deleteHorario(id, container) {
  const ok = await confirm.show('Remover Horário', 'Remover esta aula da grade semanal?');
  if (!ok) return;
  try {
    await api.del(`/admin/horarios/${id}`);
    invalidate('grade');
    await loadGrade();
    renderGrid(container);
    toast.success('Horário removido.');
  } catch (err) { toast.error(extractError(err)); }
}

function showAddModal(diaIdx, container) {
  const state = getState();
  const turmas = (state.cache.turmas || []).filter(t => t.turno === state.turno && (state.semestre === 'Todos' || String(t.semestre) === String(state.semestre)));
  const slots = state.turno === 'Noturno' ? SLOTS_NOTURNO : SLOTS_MATUTINO;

  window.closeModal = closeModal;
  openModal(`
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <div><h3 class="font-black text-lg">Adicionar Aula</h3><p class="text-gray-500 text-xs font-bold mt-0.5">${DIAS_SEMANA[diaIdx]}</p></div>
        <button onclick="closeModal()" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500">${icon('x', 16)}</button>
      </div>
      <form id="horario-form" class="space-y-4">
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Disciplina *</label>
          <select name="turma_id" class="scpi-input" required>
            <option value="">Selecione...</option>
            ${turmas.map(t => `<option value="${t.turma_id}">${t.nome_disciplina} — ${t.codigo_turma}</option>`).join('')}
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Início *</label>
            <select name="horario_inicio" class="scpi-input" required>
              <option value="">Selecione...</option>
              ${slots.map(s => `<option value="${s.inicio}">${s.inicio}</option>`).join('')}
            </select>
          </div>
          <div>
            <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Fim *</label>
            <select name="horario_fim" class="scpi-input" required>
              <option value="">Selecione...</option>
              ${slots.map(s => `<option value="${s.fim}">${s.fim}</option>`).join('')}
            </select>
          </div>
        </div>
        <div>
          <label class="text-xs font-black text-gray-500 uppercase tracking-widest mb-2 block">Sala *</label>
          <input name="sala" type="text" placeholder="Lab 01" class="scpi-input" required>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="button" onclick="closeModal()" class="flex-1 py-3 rounded-2xl border border-white/10 font-black text-sm hover:bg-white/5 transition-colors">Cancelar</button>
          <button type="submit" id="horario-save-btn" class="flex-1 py-3 rounded-2xl bg-accent hover:bg-accent-dark text-white font-black text-sm transition-colors">Adicionar</button>
        </div>
      </form>
    </div>
  `);

  document.getElementById('horario-form').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = document.getElementById('horario-save-btn');
    btn.disabled = true; btn.textContent = 'Salvando…';
    const form = e.target;
    try {
      await api.post('/admin/horarios', {
        turma_id: form.querySelector('[name=turma_id]').value,
        dia_semana: diaIdx,
        horario_inicio: form.querySelector('[name=horario_inicio]').value,
        horario_fim: form.querySelector('[name=horario_fim]').value,
        sala: form.querySelector('[name=sala]').value.trim(),
      });
      invalidate('grade');
      await loadGrade();
      renderGrid(container);
      closeModal();
      toast.success('Horário adicionado.');
    } catch (err) { toast.error(extractError(err)); btn.disabled = false; btn.textContent = 'Adicionar'; }
  });
}

export async function mount(container) {
  container.innerHTML = `
    <div class="flex-1 overflow-hidden min-h-0">
      <div class="bg-[#151718] rounded-3xl border border-white/5 shadow-2xl shadow-black/40 h-full overflow-auto p-6">
        <div id="horarios-grid" class="grid gap-4" style="grid-template-columns: repeat(7, minmax(140px, 1fr))"></div>
      </div>
    </div>
  `;
  try {
    await loadGrade();
    renderGrid(container);
  } catch (err) { toast.error(extractError(err)); }
}
