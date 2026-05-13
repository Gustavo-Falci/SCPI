import { api, extractError } from '../api.js';
import { toast } from '../toast.js';
import { confirm } from '../confirm.js';
import { icon } from '../icons.js';
import { getState } from '../state.js';

let rekData = [];
let s3Data = [];
let selectedRek = new Set();
let selectedS3 = new Set();
let expandedRek = new Set();
let expandedS3 = new Set();

async function loadAll(container) {
  const state = getState();
  [rekData, s3Data] = await Promise.all([
    state.cache.rostos_rek || api.get('/admin/rostos/rekognition').then(d => { state.cache.rostos_rek = d; return d; }),
    state.cache.rostos_s3 || api.get('/admin/rostos/s3').then(d => { state.cache.rostos_s3 = d; return d; }),
  ]);
  rekData = getState().cache.rostos_rek || [];
  s3Data = getState().cache.rostos_s3 || [];
}

function groupRek() {
  const groups = {};
  rekData.forEach(f => {
    const key = f.external_image_id;
    if (!groups[key]) groups[key] = [];
    groups[key].push(f);
  });
  return Object.entries(groups).map(([name, faces]) => ({ name, faces }));
}

function groupS3() {
  const groups = {};
  s3Data.forEach(f => {
    const key = f.key || '';
    const name = key.replace(/^alunos\//, '').replace(/_[a-f0-9]{32}\.(jpg|png|jpeg)$/i, '');
    if (!groups[name]) groups[name] = [];
    groups[name].push(f);
  });
  return Object.entries(groups).map(([name, files]) => ({ name, files }));
}

function renderPanel(container, panelId) {
  const isRek = panelId === 'rek';
  const groups = isRek ? groupRek() : groupS3();
  const selected = isRek ? selectedRek : selectedS3;
  const expanded = isRek ? expandedRek : expandedS3;
  const totalFaces = isRek ? rekData.length : s3Data.length;

  const panel = container.querySelector(`#panel-${panelId}`);
  if (!panel) return;

  const headerBadge = `<span class="text-xs font-black text-gray-500">${groups.length} alunos · ${totalFaces} ${isRek ? 'faces' : 'arquivos'}</span>`;

  panel.querySelector('.panel-badge').innerHTML = headerBadge;

  const listEl = panel.querySelector('.panel-list');
  if (!groups.length) {
    listEl.innerHTML = `<div class="flex flex-col items-center justify-center py-12 text-gray-600">${icon('scan-face', 36)}<p class="mt-3 font-black text-sm">Sem registros</p></div>`;
    return;
  }

  listEl.innerHTML = groups.map(g => {
    const allIds = isRek ? g.faces.map(f => f.face_id) : g.files.map(f => f.key);
    const selAll = allIds.every(id => selected.has(id));
    const selSome = allIds.some(id => selected.has(id)) && !selAll;
    const isOpen = expanded.has(g.name);

    return `
      <div class="bg-[#0C0C12] rounded-2xl border border-white/5 overflow-hidden">
        <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors group-row" data-group="${g.name}" data-panel="${panelId}">
          <label class="custom-checkbox flex-shrink-0" onclick="event.stopPropagation()">
            <input type="checkbox" class="group-check sr-only" data-panel="${panelId}" data-ids='${JSON.stringify(allIds)}' ${selAll ? 'checked' : ''} ${selSome ? 'data-indeterminate="true"' : ''}>
            <span class="checkbox-ui ${selSome ? 'indeterminate' : ''}"></span>
          </label>
          <div class="flex-1 min-w-0">
            <p class="font-black text-sm text-white truncate">${g.name}</p>
            <p class="text-xs text-gray-600 font-bold">${allIds.length} ${isRek ? 'face(s)' : 'arquivo(s)'}</p>
          </div>
          <button data-panel="${panelId}" data-ids='${JSON.stringify(allIds)}' class="del-group w-7 h-7 rounded-lg bg-red-500/10 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0 opacity-0 group-hover-btn">${icon('trash-2', 13)}</button>
          <span class="text-gray-600 transition-transform ${isOpen ? 'rotate-90' : ''}">${icon('chevron-right', 14)}</span>
        </div>
        ${isOpen ? `
          <div class="border-t border-white/5">
            ${(isRek ? g.faces : g.files).map(item => {
              const id = isRek ? item.face_id : item.key;
              return `
                <div class="flex items-center gap-3 px-4 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors">
                  <label class="custom-checkbox flex-shrink-0" onclick="event.stopPropagation()">
                    <input type="checkbox" class="item-check sr-only" data-panel="${panelId}" data-id="${id}" ${selected.has(id) ? 'checked' : ''}>
                    <span class="checkbox-ui"></span>
                  </label>
                  <div class="flex-1 min-w-0">
                    ${isRek
                      ? `<p class="text-xs font-black text-gray-400 truncate font-mono">${item.face_id}</p><p class="text-xs text-gray-600 font-bold">Conf: ${(item.confidence || 0).toFixed(1)}%</p>`
                      : `<p class="text-xs font-black text-gray-400 truncate">${item.key}</p><p class="text-xs text-gray-600 font-bold">${item.size ? (item.size / 1024).toFixed(1) + ' KB' : ''}</p>`
                    }
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
      getState().cache.rostos_rek = null;
    } else {
      for (const key of ids) await api.del('/admin/rostos/s3', { key });
      ids.forEach(id => selectedS3.delete(id));
      getState().cache.rostos_s3 = null;
    }
    await loadAll(container);
    renderPanel(container, 'rek');
    renderPanel(container, 's3');
    updateBulkBar(container);
    toast.success(`${ids.length} registro(s) excluído(s).`);
  } catch (err) { toast.error(extractError(err)); }
}

export async function mount(container) {
  selectedRek = new Set(); selectedS3 = new Set(); expandedRek = new Set(); expandedS3 = new Set();

  container.innerHTML = `
    <div class="flex-1 overflow-hidden flex flex-col gap-3 min-h-0">
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

  // Refresh buttons
  container.querySelector('#refresh-rek').addEventListener('click', async () => { getState().cache.rostos_rek = null; await loadAll(container); renderPanel(container, 'rek'); toast.info('Rekognition atualizado.'); });
  container.querySelector('#refresh-s3').addEventListener('click', async () => { getState().cache.rostos_s3 = null; await loadAll(container); renderPanel(container, 's3'); toast.info('S3 atualizado.'); });

  try {
    await loadAll(container);
    renderPanel(container, 'rek');
    renderPanel(container, 's3');
  } catch (err) { toast.error(extractError(err)); }
}
