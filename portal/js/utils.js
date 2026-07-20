export const debounce = (fn, ms = 250) => {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

const HTML_ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, ch => HTML_ENTITIES[ch]);
}

// ';' + BOM: é o que o Excel pt-BR abre em colunas separadas. O backend detecta
// o delimitador, então vírgula continua funcionando no upload.
export function baixarModeloCsv(nomeArquivo, colunas, exemplo) {
  const conteudo = '﻿' + colunas.join(';') + '\n' + exemplo.join(';') + '\n';
  const url = URL.createObjectURL(new Blob([conteudo], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = nomeArquivo;
  a.click();
  URL.revokeObjectURL(url);
}

const PALETTE = ['#4B39EF','#10B981','#F59E0B','#EF4444','#8B5CF6','#EC4899','#06B6D4','#F97316'];

export function avatar(nome = '?', size = 36) {
  const words = (nome || '?').trim().split(/\s+/);
  const ini = words.length >= 2
    ? (words[0][0] + words[words.length - 1][0]).toUpperCase()
    : words[0].slice(0, 2).toUpperCase();
  const color = PALETTE[(nome.charCodeAt(0) || 0) % PALETTE.length];
  const r = Math.round(size / 3.5);
  return `<div style="width:${size}px;height:${size}px;background:${color}22;border:1.5px solid ${color}55;border-radius:${r}px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;font-size:${Math.round(size / 2.7)}px;font-weight:900;color:${color}">${ini}</div>`;
}
