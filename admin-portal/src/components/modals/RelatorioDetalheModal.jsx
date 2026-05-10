import React from 'react';
import { FileText, X } from 'lucide-react';

export function RelatorioDetalheModal({ data, onClose }) {
  if (!data) return null;

  const presentes_count = data.alunos.filter(a => a.aulas_presentes_count === a.total_aulas).length;
  const ausentes_count = data.alunos.filter(a => a.aulas_presentes_count === 0).length;
  const parciais_count = data.alunos.filter(a => a.aulas_presentes_count > 0 && a.aulas_presentes_count < a.total_aulas).length;

  const stats = [
    { label: 'Alunos', value: data.total_alunos, cls: 'text-white', bg: 'bg-white/[0.03] border-white/5' },
    { label: 'Presentes', value: presentes_count, cls: 'text-green-400', bg: 'bg-green-500/5 border-green-500/10' },
    { label: 'Ausentes', value: ausentes_count, cls: 'text-red-400', bg: 'bg-red-500/5 border-red-500/10' },
    { label: 'Parciais', value: parciais_count, cls: 'text-yellow-400', bg: 'bg-yellow-500/5 border-yellow-500/10' },
    {
      label: 'Presença',
      value: `${data.percentual}%`,
      cls: data.percentual >= 75 ? 'text-green-400' : 'text-red-400',
      bg: data.percentual >= 75 ? 'bg-green-500/5 border-green-500/10' : 'bg-red-500/5 border-red-500/10',
    },
  ];

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={onClose}>
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-3xl w-full p-10 max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center gap-4">
            <FileText className="text-[#4B39EF] shrink-0" size={28} />
            <div>
              <h3 className="text-2xl font-black text-white">{data.nome_disciplina}</h3>
              <p className="text-gray-500 text-sm font-bold mt-1">
                {data.data_chamada} • {data.horario_inicio} – {data.horario_fim} • Prof. {data.professor_nome}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all shrink-0">
            <X size={22} />
          </button>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-8">
          {stats.map(({ label, value, cls, bg }) => (
            <div key={label} className={`${bg} rounded-2xl p-4 text-center border`}>
              <p className={`text-2xl font-black ${cls}`}>{value}</p>
              <p className="text-xs text-gray-500 font-black uppercase tracking-widest mt-1">{label}</p>
            </div>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 -mx-2 px-2">
          {data.alunos.map((a) => {
            const parcial = a.aulas_presentes_count > 0 && a.aulas_presentes_count < a.total_aulas;
            const ausente = a.aulas_presentes_count === 0;
            const cardCls = ausente
              ? 'bg-red-500/[0.03] border-red-500/10'
              : parcial
              ? 'bg-yellow-500/[0.03] border-yellow-500/10'
              : 'bg-green-500/[0.03] border-green-500/10';
            const avatarCls = ausente
              ? 'bg-red-500/10 text-red-400'
              : parcial
              ? 'bg-yellow-500/10 text-yellow-400'
              : 'bg-green-500/10 text-green-400';
            const tagCls = ausente
              ? 'text-red-400 bg-red-500/10'
              : parcial
              ? 'text-yellow-400 bg-yellow-500/10'
              : 'text-green-400 bg-green-500/10';
            const tagLabel = ausente ? 'Ausente' : parcial ? 'Parcial' : 'Presente';
            return (
              <div key={a.aluno_id} className={`flex items-center gap-5 p-5 rounded-2xl border transition-all ${cardCls}`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-lg shrink-0 ${avatarCls}`}>
                  {a.nome.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-black text-white truncate">{a.nome}</p>
                  <p className="text-xs text-gray-500 font-bold mt-1">RA {a.ra}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {a.total_aulas > 1 && (
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500 bg-white/5 px-3 py-1 rounded-lg">
                      {a.aulas_presentes_count}/{a.total_aulas} aulas
                    </span>
                  )}
                  {a.aulas_presentes_count > 0 && a.tipo_registro !== '—' && (
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500 bg-white/5 px-3 py-1 rounded-lg">
                      {a.tipo_registro}
                    </span>
                  )}
                  <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg ${tagCls}`}>
                    {tagLabel}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-8 border-t border-white/5 mt-6">
          <button onClick={onClose} className="w-full py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
