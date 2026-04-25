import React from 'react';

const TITLES = {
  turmas: 'Turmas',
  horarios: 'Grade Semanal',
  relatorios: 'Relatórios',
};

const SUBTITLES = {
  turmas: 'Gestão estratégica de disciplinas e alunos.',
  horarios: 'Visualize e organize o calendário acadêmico.',
  relatorios: 'Histórico imutável de todas as chamadas realizadas.',
};

export function DashboardHeader({
  activeTab,
  filterTurno, onChangeTurno,
  filterSemestre, onChangeSemestre,
  onResetPages,
}) {
  if (!['turmas', 'horarios', 'relatorios'].includes(activeTab)) return null;

  const handleTurno = (t) => { onChangeTurno(t); onResetPages?.(); };
  const handleSemestre = (s) => { onChangeSemestre(s); onResetPages?.(); };

  return (
    <div className="w-full mb-4 flex-shrink-0">
      <div className="flex justify-between items-center mb-3">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight">{TITLES[activeTab]}</h2>
          <p className="text-gray-500 text-sm mt-1 font-medium">{SUBTITLES[activeTab]}</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-[#151718] p-1.5 rounded-2xl border border-white/5 flex gap-1.5">
            {['Matutino', 'Noturno'].map((t) => (
              <button
                key={t}
                onClick={() => handleTurno(t)}
                className={`px-6 py-2 rounded-xl text-xs font-black transition-all ${filterTurno === t ? 'bg-[#4B39EF] text-white shadow-lg' : 'text-gray-500 hover:text-white'}`}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {['Todos', '1', '2', '3', '4', '5', '6'].map((s) => (
          <button
            key={s}
            onClick={() => handleSemestre(s)}
            className={`px-4 py-1.5 rounded-full border text-xs font-black tracking-widest transition-all ${filterSemestre === s ? 'bg-white text-black border-white shadow-xl' : 'border-white/10 text-gray-500 hover:border-white/30'}`}
          >
            {s === 'Todos' ? 'TODOS' : `${s}º SEM`}
          </button>
        ))}
      </div>
    </div>
  );
}
