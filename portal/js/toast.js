import { icon } from './icons.js';

const DURATIONS = { success: 3000, info: 3500, warning: 5000, error: 6000 };
const COLORS = {
  success: 'border-green-500/30 bg-green-500/10 text-green-400',
  error: 'border-red-500/30 bg-red-500/10 text-red-400',
  warning: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
  info: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
};
const ICONS = { success: 'check-circle', error: 'x-circle', warning: 'alert-circle', info: 'info' };

let container = null;

export const toast = {
  init() { container = document.getElementById('toast-container'); },
  show(message, type = 'info', title = null) {
    if (!container) return;
    const id = `toast-${Date.now()}-${Math.random()}`;
    const duration = DURATIONS[type] || 4000;
    const colors = COLORS[type];
    const iconName = ICONS[type];

    const el = document.createElement('div');
    el.id = id;
    el.className = `toast-item pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-2xl border shadow-xl ${colors} backdrop-blur-sm`;
    el.innerHTML = `
      <span class="mt-0.5 flex-shrink-0">${icon(iconName, 16)}</span>
      <div class="flex-1 min-w-0">
        ${title ? `<p class="font-black text-sm">${title}</p>` : ''}
        <p class="${title ? 'text-xs opacity-80' : 'font-bold text-sm'}">${message}</p>
        <div class="toast-progress mt-2 h-0.5 rounded-full bg-current opacity-30 origin-left" style="animation: toast-shrink ${duration}ms linear forwards"></div>
      </div>
      <button class="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity" onclick="document.getElementById('${id}')?.remove()">
        ${icon('x', 14)}
      </button>
    `;
    container.appendChild(el);
    setTimeout(() => el.remove(), duration + 300);
  },
  success: (msg, title) => toast.show(msg, 'success', title),
  error: (msg, title) => toast.show(msg, 'error', title),
  warning: (msg, title) => toast.show(msg, 'warning', title),
  info: (msg, title) => toast.show(msg, 'info', title),
};
