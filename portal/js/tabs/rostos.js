import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { debounce, escapeHtml } from '../utils.js';
import { getState } from '../state.js';
import { loadTab, saveTab } from '../persist.js';

let inventario = { rekognition: [], s3: [], alunos: [], resumo: null, indisponivel: [] };
let selectedRek = new Set();
let selectedS3 = new Set();
let expandedRek = new Set();
let expandedS3 = new Set();
let angulosPorAluno = new Map();

// Um conjunto de filtros por painel: Rekognition e S3 são filtráveis de forma
// independente.
let filtros = { rek: { busca: '', situacao: '' }, s3: { busca: '', situacao: '' } };

async function loadAll() {
  const state = getState();
  if (!state.cache.rostos_inventario) {
    state.cache.rostos_inventario = await api.get('/admin/rostos/inventario');
  }
  inventario = state.cache.rostos_inventario;
  // Índice por aluno para o cabeçalho do grupo mostrar ângulos faltantes sem
  // varrer a lista de alunos a cada render.
  angulosPorAluno = new Map(inventario.alunos.map(a => [String(a.aluno_id), a]));
}

function rotuloOrfao(painel, item) {
  if (painel === 'rek') return item.external_image_id || '(sem identificação)';
  return (item.key || '').replace(/^alunos\//, '').replace(/_[a-f0-9]{32}\.(jpg|png|jpeg)$/i, '');
}

function idDoItem(painel, item) {
  return painel === 'rek' ? item.face_id : item.key;
}

function passaNoFiltro(painel, item) {
  const f = filtros[painel];

  if (f.situacao === 'orfao' && item.status !== 'orfao') return false;
  if (f.situacao === 'revogado' && item.status !== 'revogado') return false;
  if (f.situacao === 'divergente' && !item.divergente) return false;
  if (f.situacao === 'incompleto') {
    // Filtro de aluno, não de item: passa quem pertence a um aluno incompleto.
    if (!item.aluno) return false;
    const dados = angulosPorAluno.get(String(item.aluno.aluno_id));
    if (!dados || !dados.incompleto) return false;
  }

  if (!f.busca) return true;
  const q = f.busca.toLowerCase();
  const alvos = [
    item.aluno?.nome, item.aluno?.ra, item.angulo,
    painel === 'rek' ? item.external_image_id : item.key,
    painel === 'rek' ? item.face_id : '',
  ];
  return alvos.some(v => v && String(v).toLowerCase().includes(q));
}

// Agrupa por aluno quando o item tem dono; órfãos caem num grupo próprio,
// identificado pelo external_image_id (Rekognition) ou pelo nome derivado da
// key (S3), que é o máximo que se sabe sobre eles.
function agrupar(painel) {
  const todos = painel === 'rek' ? inventario.rekognition : inventario.s3;
  const itens = todos.filter(item => passaNoFiltro(painel, item));
  const grupos = new Map();
  itens.forEach(item => {
    const chave = item.aluno ? `aluno:${item.aluno.aluno_id}` : `orfao:${rotuloOrfao(painel, item)}`;
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        chave,
        nome: item.aluno ? item.aluno.nome : rotuloOrfao(painel, item),
        aluno: item.aluno,
        itens: [],
      });
    }
    grupos.get(chave).itens.push(item);
  });
  return [...grupos.values()].sort((a, b) => a.nome.localeCompare(b.nome));
}

function badgeResumo(qtdGrupos, resumo, isRek) {
  if (!resumo) return '';
  const problema = (valor, rotulo, situacao) => valor
    ? `<button data-chip="${situacao}" class="badge-chip text-amber-400 hover:underline">${valor} ${rotulo}</button>`
    : '';
  return `
    <span class="text-xs font-black text-gray-500 flex flex-wrap items-center gap-x-2">
      <span>${qtdGrupos} grupos · ${resumo.total} ${isRek ? 'faces' : 'arquivos'}</span>
      ${problema(resumo.orfaos, 'órfãos', 'orfao')}
      ${problema(resumo.revogados, 'revogados', 'revogado')}
      ${problema(resumo.divergentes, 'divergentes', 'divergente')}
    </span>`;
}

// Ângulo faltando é do aluno, não do item: mora no cabeçalho do grupo.
function selosDoGrupo(g) {
  if (!g.aluno) return ' · <span class="text-red-400">sem cadastro</span>';
  const dados = angulosPorAluno.get(String(g.aluno.aluno_id));
  if (!dados || !dados.incompleto) return '';
  const total = dados.angulos_presentes.length + dados.angulos_faltantes.length;
  return ` · <span class="text-amber-400" title="Faltam: ${escapeHtml(dados.angulos_faltantes.join(', '))}">${dados.angulos_presentes.length}/${total} ângulos</span>`;
}

// Só o que precisa de ação ganha selo: item ok e sem divergência fica limpo.
function seloStatus(item) {
  const selo = (cls, texto) => ` · <span class="${cls} font-black uppercase tracking-tighter">${texto}</span>`;
  let out = '';
  if (item.status === 'orfao') out += selo('text-red-400', 'órfão');
  else if (item.status === 'revogado') out += selo('text-red-400', 'revogado');
  if (item.divergente) out += selo('text-amber-400', 'sem par');
  return out;
}

function renderFiltros(container, panelId) {
  const alvo = container.querySelector(`#panel-${panelId} .panel-filtros`);
  if (!alvo) return;
  const f = filtros[panelId];
  const isRek = panelId === 'rek';

  const chip = (valor, rotulo) => `
    <button data-chip="${valor}" class="chip-situacao px-2.5 py-1 rounded-lg font-black text-[11px] transition-colors whitespace-nowrap ${
      f.situacao === valor ? 'bg-accent text-white' : 'bg-white/5 text-gray-500 hover:bg-white/10'
    }">${rotulo}</button>`;

  alvo.innerHTML = `
    <div class="px-3 pb-2 flex flex-col gap-2">
      <input type="search" class="filtro-busca scpi-input py-2 text-xs" placeholder="Buscar aluno, RA ou chave..." value="${escapeHtml(f.busca)}">
      <div class="flex flex-wrap items-center gap-1.5">
        ${chip('', 'Todos')}
        ${chip('orfao', 'Órfãos')}
        ${chip('revogado', 'Revogados')}
        ${chip('divergente', 'Divergentes')}
        ${isRek ? chip('incompleto', 'Incompletos') : ''}
      </div>
    </div>`;

  const aplicar = () => {
    saveTab('rostos', { filtros });
    renderPanel(container, panelId);
  };

  alvo.querySelector('.filtro-busca').addEventListener('input', debounce(e => {
    f.busca = e.target.value;
    aplicar();
  }, 200));
  alvo.querySelectorAll('.chip-situacao').forEach(btn => {
    btn.addEventListener('click', () => {
      f.situacao = btn.dataset.chip;
      aplicar();
    });
  });
}

function renderPanel(container, panelId) {
  const isRek = panelId === 'rek';
  const grupos = agrupar(panelId);
  const selected = isRek ? selectedRek : selectedS3;
  const expanded = isRek ? expandedRek : expandedS3;
  const resumo = inventario.resumo ? inventario.resumo[isRek ? 'rekognition' : 's3'] : null;

  const panel = container.querySelector(`#panel-${panelId}`);
  if (!panel) return;

  panel.querySelector('.panel-badge').innerHTML = badgeResumo(grupos.length, resumo, isRek);

  const nomeLado = isRek ? 'rekognition' : 's3';
  const fora = (inventario.indisponivel || []).includes(nomeLado);
  const avisoEl = panel.querySelector('.panel-aviso');
  if (avisoEl) {
    avisoEl.innerHTML = !inventario.indisponivel?.length ? '' : `
      <div class="mx-3 mb-2 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-bold">
        ${fora ? 'Listagem indisponível ou incompleta — o que aparece aqui pode não ser tudo.' : 'Checagem de divergência suspensa: o outro lado não pôde ser lido.'}
      </div>`;
  }

  const listEl = panel.querySelector('.panel-list');
  if (!grupos.length) {
    const temFiltro = Boolean(filtros[panelId].busca || filtros[panelId].situacao);
    listEl.innerHTML = `<div class="flex flex-col items-center justify-center py-12 text-gray-600">${icon('scan-face', 36)}<p class="mt-3 font-black text-sm">${temFiltro ? 'Nada para este filtro' : 'Sem registros'}</p></div>`;
    ligarBadgeChips(container, panel, panelId);
    return;
  }

  listEl.innerHTML = grupos.map(g => {
    const allIds = g.itens.map(item => idDoItem(panelId, item));
    const selAll = allIds.every(id => selected.has(id));
    const selSome = allIds.some(id => selected.has(id)) && !selAll;
    const isOpen = expanded.has(g.chave);

    return `
      <div class="bg-[#0C0C12] rounded-2xl border border-white/5 overflow-hidden">
        <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors group-row" data-group="${escapeHtml(g.chave)}" data-panel="${panelId}">
          <label class="custom-checkbox flex-shrink-0" onclick="event.stopPropagation()">
            <input type="checkbox" class="group-check sr-only" data-panel="${panelId}" data-ids="${escapeHtml(JSON.stringify(allIds))}" ${selAll ? 'checked' : ''} ${selSome ? 'data-indeterminate="true"' : ''}>
            <span class="checkbox-ui ${selSome ? 'indeterminate' : ''}"></span>
          </label>
          <div class="flex-1 min-w-0">
            <p class="font-black text-sm text-white truncate">${escapeHtml(g.nome)}</p>
            <p class="text-xs text-gray-600 font-bold">${allIds.length} ${isRek ? 'face(s)' : 'arquivo(s)'}${selosDoGrupo(g)}</p>
          </div>
          <button data-panel="${panelId}" data-ids="${escapeHtml(JSON.stringify(allIds))}" class="del-group w-7 h-7 rounded-lg bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0 group-hover-btn">${icon('trash-2', 13)}</button>
          <span class="text-gray-600 transition-transform ${isOpen ? 'rotate-90' : ''}">${icon('chevron-right', 14)}</span>
        </div>
        ${isOpen ? `
          <div class="border-t border-white/5">
            ${g.itens.map(item => {
              const id = idDoItem(panelId, item);
              const detalhe = isRek
                ? `<p class="text-xs font-black text-gray-400 truncate font-mono">${escapeHtml(item.face_id)}</p>`
                : `<p class="text-xs font-black text-gray-400 truncate">${escapeHtml(item.key)}</p>`;
              const subtitulo = isRek
                ? escapeHtml(item.angulo || 'ângulo desconhecido')
                : `${item.size ? (item.size / 1024).toFixed(1) + ' KB' : ''}${item.angulo ? ' · ' + escapeHtml(item.angulo) : ''}`;
              return `
                <div class="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                  <label class="custom-checkbox flex-shrink-0" onclick="event.stopPropagation()">
                    <input type="checkbox" class="item-check sr-only" data-panel="${panelId}" data-id="${escapeHtml(id)}" ${selected.has(id) ? 'checked' : ''}>
                    <span class="checkbox-ui"></span>
                  </label>
                  <div class="flex-1 min-w-0">
                    ${detalhe}
                    <p class="text-xs text-gray-600 font-bold">${subtitulo}${seloStatus(item)}</p>
                  </div>
                  <button data-panel="${panelId}" data-id="${id}" class="del-item w-6 h-6 rounded-lg bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0">${icon('trash-2', 11)}</button>
                </div>
              `;
            }).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');

  // Attach events
  listEl.querySelectorAll('.group-row').forEach(row => {
    row.addEventListener('click', e => {
      if (e.target.closest('.custom-checkbox') || e.target.closest('.del-group')) return;
      const g = row.dataset.group;
      const p = row.dataset.panel;
      const set = p === 'rek' ? expandedRek : expandedS3;
      if (set.has(g)) set.delete(g); else set.add(g);
      renderPanel(container, p);
    });
    const btn = row.querySelector('.del-group');
    if (btn) {
      row.addEventListener('mouseenter', () => btn.classList.add('opacity-100'));
      row.addEventListener('mouseleave', () => btn.classList.remove('opacity-100'));
    }
  });

  listEl.querySelectorAll('.group-check').forEach(chk => {
    const el = chk;
    if (el.dataset.indeterminate === 'true') { el.indeterminate = true; el.checked = false; }
    el.addEventListener('change', e => {
      e.stopPropagation();
      const ids = JSON.parse(el.dataset.ids);
      const sel = el.dataset.panel === 'rek' ? selectedRek : selectedS3;
      ids.forEach(id => el.checked ? sel.add(id) : sel.delete(id));
      renderPanel(container, el.dataset.panel);
      updateBulkBar(container);
    });
  });

  listEl.querySelectorAll('.item-check').forEach(chk => {
    chk.addEventListener('change', () => {
      const sel = chk.dataset.panel === 'rek' ? selectedRek : selectedS3;
      chk.checked ? sel.add(chk.dataset.id) : sel.delete(chk.dataset.id);
      updateBulkBar(container);
    });
  });

  listEl.querySelectorAll('.del-group').forEach(btn => {
    btn.addEventListener('click', async e => {
      e.stopPropagation();
      const ids = JSON.parse(btn.dataset.ids);
      const ok = await confirm.show('Excluir Grupo', `Excluir ${ids.length} ${isRek ? 'face(s)' : 'arquivo(s)'}?`);
      if (!ok) return;
      await bulkDelete(btn.dataset.panel, ids, container);
    });
  });

  listEl.querySelectorAll('.del-item').forEach(btn => {
    btn.addEventListener('click', async () => {
      const ok = await confirm.show('Excluir', 'Excluir este registro?');
      if (!ok) return;
      await bulkDelete(btn.dataset.panel, [btn.dataset.id], container);
    });
  });

  ligarBadgeChips(container, panel, panelId);
}

// Contador do cabeçalho vira atalho para o filtro correspondente.
function ligarBadgeChips(container, panel, panelId) {
  panel.querySelectorAll('.badge-chip').forEach(btn => {
    btn.addEventListener('click', () => {
      filtros[panelId].situacao = btn.dataset.chip;
      saveTab('rostos', { filtros });
      renderPanel(container, panelId);
      renderFiltros(container, panelId);
    });
  });
}

function updateBulkBar(container) {
  const bar = container.querySelector('#bulk-bar');
  const totalSel = selectedRek.size + selectedS3.size;
  if (totalSel > 0) {
    bar.classList.remove('hidden');
    bar.querySelector('#bulk-count').textContent = `${totalSel} selecionado(s)`;
  } else {
    bar.classList.add('hidden');
  }
}

async function bulkDelete(panel, ids, container) {
  try {
    if (panel === 'rek') {
      if (ids.length === 1) await api.del(`/admin/rostos/rekognition/${ids[0]}`);
      else await api.del('/admin/rostos/rekognition/bulk', { face_ids: ids });
      ids.forEach(id => selectedRek.delete(id));
    } else {
      for (const key of ids) await api.del('/admin/rostos/s3', { key });
      ids.forEach(id => selectedS3.delete(id));
    }
    // O inventário é indivisível: excluir de um lado muda a divergência do outro.
    getState().cache.rostos_inventario = null;
    await loadAll();
    renderPanel(container, 'rek');
    renderPanel(container, 's3');
    updateBulkBar(container);
    toast.success(`${ids.length} registro(s) excluído(s).`);
  } catch (err) { toast.error(extractError(err)); }
}

export async function mount(container) {
  selectedRek = new Set(); selectedS3 = new Set(); expandedRek = new Set(); expandedS3 = new Set();

  const salvo = loadTab('rostos', { filtros: null });
  if (salvo.filtros) filtros = salvo.filtros;

  container.innerHTML = `
    <div class="flex-1 overflow-hidden flex flex-col gap-3 min-h-0 tab-anim">
      <!-- Bulk bar -->
      <div id="bulk-bar" class="hidden flex-shrink-0 flex items-center justify-between px-4 py-3 bg-accent/10 border border-accent/20 rounded-2xl">
        <span id="bulk-count" class="font-black text-accent text-sm"></span>
        <div class="flex gap-2">
          <button id="bulk-del-rek" class="px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white font-black text-xs transition-colors flex items-center gap-1.5">${icon('trash-2', 13)} Excluir Rekognition</button>
          <button id="bulk-del-s3" class="px-3 py-1.5 rounded-xl bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white font-black text-xs transition-colors flex items-center gap-1.5">${icon('trash-2', 13)} Excluir S3</button>
          <button id="bulk-clear" class="px-3 py-1.5 rounded-xl border border-white/10 hover:bg-white/5 font-black text-xs transition-colors">Limpar</button>
        </div>
      </div>
      <!-- Panels -->
      <div class="flex-1 overflow-hidden flex flex-col lg:flex-row gap-4 min-h-0">
        <!-- Rekognition panel -->
        <div id="panel-rek" class="flex-1 flex flex-col overflow-hidden min-h-0 bg-[#151718] rounded-3xl border border-white/5">
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/5 flex-shrink-0">
            <div>
              <h3 class="font-black text-sm flex items-center gap-2">${icon('scan-face', 16)} Rekognition Collection</h3>
              <div class="panel-badge mt-0.5"></div>
            </div>
            <button id="refresh-rek" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500 hover:text-white transition-all">${icon('refresh-cw', 15)}</button>
          </div>
          <div class="panel-filtros flex-shrink-0"></div>
          <div class="panel-aviso flex-shrink-0"></div>
          <div class="panel-list flex-1 overflow-y-auto p-3 space-y-2"></div>
        </div>
        <!-- S3 panel -->
        <div id="panel-s3" class="flex-1 flex flex-col overflow-hidden min-h-0 bg-[#151718] rounded-3xl border border-white/5">
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/5 flex-shrink-0">
            <div>
              <h3 class="font-black text-sm flex items-center gap-2">${icon('upload', 16)} S3 Bucket</h3>
              <div class="panel-badge mt-0.5"></div>
            </div>
            <button id="refresh-s3" class="w-8 h-8 rounded-xl hover:bg-white/5 flex items-center justify-center text-gray-500 hover:text-white transition-all">${icon('refresh-cw', 15)}</button>
          </div>
          <div class="panel-filtros flex-shrink-0"></div>
          <div class="panel-aviso flex-shrink-0"></div>
          <div class="panel-list flex-1 overflow-y-auto p-3 space-y-2"></div>
        </div>
      </div>
    </div>
  `;

  // Bulk bar actions
  container.querySelector('#bulk-del-rek').addEventListener('click', async () => {
    if (!selectedRek.size) return;
    const ok = await confirm.show('Excluir Seleção', `Excluir ${selectedRek.size} face(s) do Rekognition?`);
    if (!ok) return;
    await bulkDelete('rek', [...selectedRek], container);
  });
  container.querySelector('#bulk-del-s3').addEventListener('click', async () => {
    if (!selectedS3.size) return;
    const ok = await confirm.show('Excluir Seleção', `Excluir ${selectedS3.size} arquivo(s) do S3?`);
    if (!ok) return;
    await bulkDelete('s3', [...selectedS3], container);
  });
  container.querySelector('#bulk-clear').addEventListener('click', () => { selectedRek.clear(); selectedS3.clear(); updateBulkBar(container); renderPanel(container, 'rek'); renderPanel(container, 's3'); });

  // Refresh: o inventário é indivisível, então atualizar um lado recarrega os dois.
  const atualizar = async (rotulo) => {
    getState().cache.rostos_inventario = null;
    await loadAll();
    renderPanel(container, 'rek');
    renderPanel(container, 's3');
    toast.info(`${rotulo} atualizado.`);
  };
  container.querySelector('#refresh-rek').addEventListener('click', () => atualizar('Rekognition'));
  container.querySelector('#refresh-s3').addEventListener('click', () => atualizar('S3'));

  try {
    await loadAll();
    renderPanel(container, 'rek');
    renderPanel(container, 's3');
    // renderFiltros fica FORA de renderPanel de propósito: se fosse chamada de
    // lá, cada tecla digitada recriaria o input e o cursor sairia do campo.
    renderFiltros(container, 'rek');
    renderFiltros(container, 's3');
  } catch (err) { toast.error(extractError(err)); }
}
