// Estado da sidebar antes do primeiro paint. Sem isto ela pinta com 256px e
// salta para o rail quando o main.js roda, meio segundo depois.
// try/catch: localStorage lança em modo de cookies bloqueados, e uma exceção
// aqui mataria o resto do <head>.
try {
  if (localStorage.getItem('scpi.sidebar.collapsed') === '1') {
    document.documentElement.classList.add('sidebar-collapsed');
  }
} catch (e) {}
