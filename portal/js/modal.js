// Modal compartilhado entre main.js e as tabs.
//
// Estas funções moravam em main.js, e as tabs as importavam de volta —
// main.js → tabs/*.js → main.js. O ciclo em si o browser resolve, mas o
// index.html carrega o entrypoint com cache-busting (`js/main.js?v=N`) e as
// tabs importavam `../main.js` sem a query: duas URLs, duas instâncias do
// módulo, dois DOMContentLoaded, init() rodando duas vezes e todo listener
// registrado em dobro. Com as funções aqui, ninguém importa main.js e o
// entrypoint volta a ser instanciado uma única vez.

export function openModal(html, size = 'max-w-lg') {
  const box = document.getElementById('modal-box');
  box.className = `w-full ${size} bg-[#151718] rounded-3xl border border-white/10 shadow-2xl shadow-black/60 overflow-hidden max-h-[90vh] flex flex-col`;
  box.innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

export function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-box').innerHTML = '';
}

export async function animateRemove(el) {
  if (!el) return;
  el.classList.add('removing');
  await new Promise(r => setTimeout(r, 200));
}
