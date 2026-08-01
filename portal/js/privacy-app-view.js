// Aberto pelo app do aluno (?app=1): o link levaria à área administrativa,
// que ele não deveria sequer enxergar. O documento é o mesmo nos dois
// contextos de propósito — duplicar o texto jurídico garante divergência.
if (new URLSearchParams(location.search).has('app')) {
  document.getElementById('back-link').remove();
}
