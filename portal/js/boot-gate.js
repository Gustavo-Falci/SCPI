// Rede de segurança independente de main.js (inclusive versão em cache).
(function () {
  var boot = document.getElementById('view-boot');
  if (!boot) return;
  var dismiss = function () { boot.style.display = 'none'; };
  // Sem perfil salvo não há o que validar: vai direto ao login, sem splash.
  try { if (!localStorage.getItem('admin_user')) return dismiss(); } catch (e) { return dismiss(); }
  // Teto absoluto: nenhum caminho deixa o splash preso.
  setTimeout(dismiss, 6000);
})();
