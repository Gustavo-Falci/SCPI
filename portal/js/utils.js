export const debounce = (fn, ms = 250) => {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
};

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
