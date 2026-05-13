import { icon } from './icons.js';

export function paginate(items, page, perPage) {
  const total = Math.ceil(items.length / perPage);
  const safePage = Math.min(Math.max(1, page), Math.max(1, total));
  const start = (safePage - 1) * perPage;
  return { items: items.slice(start, start + perPage), page: safePage, total, count: items.length };
}

export function renderPagination(container, { page, total, count, perPage }, onPage) {
  if (!container) return;
  if (total <= 1) { container.innerHTML = ''; return; }
  const start = (page - 1) * perPage + 1;
  const end = Math.min(page * perPage, count);
  container.innerHTML = `
    <div class="flex items-center justify-between">
      <span class="text-xs text-gray-600 font-black">${start}–${end} de ${count}</span>
      <div class="flex items-center gap-1">
        <button data-p="${page - 1}" ${page <= 1 ? 'disabled' : ''} class="w-8 h-8 rounded-xl border border-white/10 flex items-center justify-center text-gray-500 hover:text-white hover:border-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all">${icon('chevron-left', 14)}</button>
        <span class="text-xs font-black text-gray-400 px-2">${page} / ${total}</span>
        <button data-p="${page + 1}" ${page >= total ? 'disabled' : ''} class="w-8 h-8 rounded-xl border border-white/10 flex items-center justify-center text-gray-500 hover:text-white hover:border-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all">${icon('chevron-right', 14)}</button>
      </div>
    </div>
  `;
  container.querySelectorAll('[data-p]').forEach(btn => {
    if (!btn.disabled) btn.addEventListener('click', () => onPage(+btn.dataset.p));
  });
}
