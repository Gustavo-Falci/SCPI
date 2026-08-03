/**
 * Config do Tailwind CLI. Substitui js/tailwind-config.js, que existia só para
 * o build de browser (`tailwind.config = {...}` numa global).
 *
 * `content` precisa cobrir TODO arquivo que contenha nome de classe. O portal
 * monta HTML em template string dentro de js/, então varrer só o index.html
 * deixaria a maior parte da interface sem estilo — e o modo de falha é mudo:
 * a classe simplesmente não existe no CSS final.
 *
 * Classes montadas por variável (`class="${cls} ..."`) funcionam porque os
 * valores possíveis aparecem como string literal na fonte (ex.: o ternário em
 * turnoBadge, os selos de rostos.js). O scanner do Tailwind lê o arquivo como
 * texto e acha esses literais. Se algum dia uma classe passar a ser concatenada
 * (`'text-' + cor + '-400'`), ela some do CSS sem aviso — daí o teste
 * test_portal_tailwind_build.py, que confere a cobertura.
 */
module.exports = {
  // privacy.html fica de fora: não usa Tailwind (só classes próprias, estilizadas
  // no <style> da própria página). Incluí-la faria o scanner extrair palavras da
  // prosa jurídica que por acaso são nomes de utilitário — "block", "table",
  // "grid" — e gerar CSS morto.
  content: [
    './index.html',
    './js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        surface: '#0C0C12',
        card: '#151718',
        'card-hover': '#1A1C1E',
        accent: '#4B39EF',
        'accent-dark': '#3D2DD4',
        // Dois tons de texto secundário, ambos acima dos 4,5:1 que a WCAG AA
        // exige para texto pequeno — as labels do portal são de 10-12px, então
        // o limite frouxo de 3:1 (texto grande) não vale para nenhuma delas.
        //
        // Substituem text-gray-500/600/700, que reprovavam contra os três
        // fundos do tema: o pior caso era gray-700 sobre card-hover, 1,66:1.
        // Contraste contra surface / card / card-hover:
        //   muted 7,68 / 7,08 / 6,73
        //   faint 6,08 / 5,61 / 5,33
        // A margem do faint é de propósito: o cinza mais escuro que ainda
        // passaria é #80848c, a 4,55:1 — zero folga para qualquer ajuste de
        // fundo. Ver BackEnd/tests/test_portal_contraste_wcag.py, que recalcula
        // estes números e falha se algum fundo ou token sair da faixa.
        muted: '#9ca3af',
        faint: '#8b9099',
      },
    },
  },
  plugins: [],
};
