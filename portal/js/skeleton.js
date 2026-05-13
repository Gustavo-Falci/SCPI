const card = (i) => `
  <div class="anim-item bg-[#151718] px-5 py-4 rounded-2xl border border-white/5 flex items-center gap-4" style="animation-delay:${i * 60}ms">
    <div class="w-10 h-10 skeleton rounded-2xl flex-shrink-0"></div>
    <div class="flex-1 space-y-2">
      <div class="skeleton h-3.5 rounded-lg" style="width:${55 + (i % 3) * 15}%"></div>
      <div class="skeleton h-2.5 rounded-lg" style="width:${35 + (i % 4) * 10}%"></div>
    </div>
    <div class="w-8 h-8 skeleton rounded-xl flex-shrink-0"></div>
  </div>`;

const sideForm = () => `
  <div class="lg:w-72 xl:w-80 flex-shrink-0 bg-[#151718] rounded-3xl p-6 border border-white/5 space-y-4">
    <div class="skeleton h-4 rounded-lg w-2/5 mb-5"></div>
    ${[1,2,3,4].map(() => `<div class="space-y-2"><div class="skeleton h-2.5 rounded w-1/3"></div><div class="skeleton h-10 rounded-2xl"></div></div>`).join('')}
    <div class="skeleton h-11 rounded-2xl mt-2"></div>
  </div>`;

const listSide = (n = 6) => `
  <div class="flex-1 flex flex-col gap-3 min-h-0 overflow-hidden">
    <div class="skeleton h-10 rounded-2xl flex-shrink-0"></div>
    <div class="flex-1 space-y-2 overflow-hidden">${Array.from({length: n}, (_, i) => card(i)).join('')}</div>
  </div>`;

export const skeletons = {
  twoCol: (n = 6) => `<div class="flex flex-col lg:flex-row gap-4 h-full overflow-hidden tab-anim">${sideForm()}${listSide(n)}</div>`,
  list:   (n = 8) => `<div class="flex-1 overflow-hidden flex flex-col gap-3 min-h-0 tab-anim">${listSide(n)}</div>`,
  grid: () => `
    <div class="flex-1 overflow-hidden min-h-0 tab-anim">
      <div class="bg-[#151718] rounded-3xl border border-white/5 h-full overflow-auto p-6">
        <div class="grid gap-4" style="grid-template-columns:repeat(7,minmax(140px,1fr))">
          ${Array.from({length: 7}, (_, i) => `
            <div class="space-y-3" style="animation-delay:${i * 50}ms">
              <div class="skeleton h-3 rounded w-3/4 mx-auto"></div>
              ${[1,2].map(() => `<div class="skeleton h-24 rounded-2xl"></div>`).join('')}
              <div class="skeleton h-14 rounded-2xl opacity-50"></div>
            </div>`).join('')}
        </div>
      </div>
    </div>`,
  panels: () => `
    <div class="flex-1 overflow-hidden flex flex-col lg:flex-row gap-4 min-h-0 tab-anim">
      ${[1,2].map(() => `
        <div class="flex-1 bg-[#151718] rounded-3xl border border-white/5 overflow-hidden flex flex-col">
          <div class="px-5 py-4 border-b border-white/5 flex items-center justify-between flex-shrink-0">
            <div class="space-y-2"><div class="skeleton h-3.5 rounded w-36"></div><div class="skeleton h-2.5 rounded w-24"></div></div>
            <div class="w-8 h-8 skeleton rounded-xl"></div>
          </div>
          <div class="flex-1 p-3 space-y-2 overflow-hidden">
            ${Array.from({length: 5}, (_, i) => `<div class="skeleton h-14 rounded-2xl" style="animation-delay:${i * 70}ms"></div>`).join('')}
          </div>
        </div>`).join('')}
    </div>`,
};
