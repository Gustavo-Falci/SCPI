import React from 'react';
import { Plus, Trash2, MapPin } from 'lucide-react';
import { DIAS_SEMANA } from '../../config/slots';
import { useDashboardData } from '../../contexts/DashboardDataContext';
import { deletarHorario } from '../../services/horariosService';

export function HorariosTab({ showToast, showConfirm, onOpenHorarioModal }) {
  const { grade, filterTurno, filterSemestre, refetchTurmasProfsGrade } = useDashboardData();

  const handleDeleteHorario = (id) => {
    showConfirm(
      'Excluir Horário',
      'Deseja realmente remover esta aula da grade semanal?',
      async () => {
        try {
          await deletarHorario(id);
          refetchTurmasProfsGrade();
        } catch {
          showToast('Erro ao remover horário', 'error');
        }
      }
    );
  };

  return (
    <div className="flex-1 overflow-hidden min-h-0">
      <div className="bg-[#151718] p-6 rounded-3xl border border-white/5 shadow-2xl shadow-black/40 h-full overflow-y-auto">
        <div className="grid grid-cols-5 gap-4">
          {DIAS_SEMANA.slice(0, 5).map((dia, idx) => (
            <div key={dia} className="space-y-3">
              <div className="text-center font-black text-gray-600 text-xs uppercase tracking-[0.3em] mb-2">{dia}</div>
              <div className="space-y-3">
                {grade
                  .filter((g) => g.dia_semana === idx && g.turno === filterTurno && (filterSemestre === 'Todos' || g.semestre === filterSemestre))
                  .sort((a, b) => a.inicio.localeCompare(b.inicio))
                  .map((item) => {
                    const isNight = item.turno === 'Noturno';
                    return (
                      <div key={item.horario_id} className={`p-4 rounded-2xl border-2 group transition-all ${isNight ? 'bg-indigo-500/5 border-indigo-500/10' : 'bg-amber-500/5 border-amber-500/10'}`}>
                        <p className={`text-[10px] font-black uppercase mb-1.5 ${isNight ? 'text-indigo-400' : 'text-amber-500'}`}>{item.inicio} — {item.fim}</p>
                        <p className="text-sm font-black text-white leading-tight mb-1.5">{item.nome_disciplina}</p>
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-1.5 opacity-40">
                            <MapPin size={10} />
                            <span className="text-[10px] font-black uppercase">{item.sala}</span>
                          </div>
                          <button
                            onClick={() => handleDeleteHorario(item.horario_id)}
                            className="w-7 h-7 rounded-lg bg-red-500/20 hover:bg-red-500 flex items-center justify-center text-red-400 hover:text-white transition-all flex-shrink-0"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                <button
                  onClick={() => onOpenHorarioModal(idx)}
                  className="w-full py-4 border-2 border-dashed border-white/5 rounded-2xl flex items-center justify-center text-gray-700 hover:border-[#4B39EF]/40 hover:text-[#4B39EF] transition-all"
                >
                  <Plus size={22} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
