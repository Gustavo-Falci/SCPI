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
  const blob = new Blob([conteudo], { type: 'text/csv;charset=utf-8' });
  baixarArquivo(blob, nomeArquivo);
}

const PALETTE = ['#4B39EF','#10B981','#F59E0B','#EF4444','#8B5CF6','#EC4899','#06B6D4','#F97316'];

export function avatar(nome = '?', size = 38) {
  const words = (nome || '?').trim().split(/\s+/);
  const ini = words.length >= 2
    ? (words[0][0] + words[words.length - 1][0]).toUpperCase()
    : words[0].slice(0, 2).toUpperCase();
  // Índice da paleta, não o hex: cor e tamanho viraram classe em app.css
  // (.av-0..7, .avatar/.avatar-lg) porque o CSP bloqueia atributo `style=`.
  // A paleta tem 8 entradas e só dois tamanhos são usados no portal (38 e 40).
  const idx = (nome.charCodeAt(0) || 0) % PALETTE.length;
  const tamanho = size >= 40 ? 'avatar avatar-lg' : 'avatar';
  // `ini` sai do nome vindo do banco: 2 caracteres não montam payload, mas
  // quebram a marcação do próprio avatar. Escapa junto com o resto.
  return `<div class="${tamanho} av-${idx}">${escapeHtml(ini)}</div>`;
}

export function baixarArquivo(blob, nomeFallback) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = nomeFallback;
  a.click();
  URL.revokeObjectURL(url);
}
