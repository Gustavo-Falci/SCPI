import { icon } from './icons.js';

let _resolve = null;

export const confirm = {
  init() {
    const overlay = document.getElementById('confirm-overlay');
    document.getElementById('confirm-cancel').addEventListener('click', () => { overlay.classList.add('hidden'); _resolve?.(false); _resolve = null; });
    document.getElementById('confirm-ok').addEventListener('click', () => { overlay.classList.add('hidden'); _resolve?.(true); _resolve = null; });
    overlay.addEventListener('click', e => { if (e.target === overlay) { overlay.classList.add('hidden'); _resolve?.(false); _resolve = null; } });
  },
  show(title, message, okLabel = 'Confirmar', danger = true) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    const btn = document.getElementById('confirm-ok');
    btn.textContent = okLabel;
    btn.className = `flex-1 py-3 rounded-2xl font-black text-sm transition-colors ${danger ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-accent hover:bg-accent-dark text-white'}`;
    document.getElementById('confirm-overlay').classList.remove('hidden');
    return new Promise(resolve => { _resolve = resolve; });
  },
};
