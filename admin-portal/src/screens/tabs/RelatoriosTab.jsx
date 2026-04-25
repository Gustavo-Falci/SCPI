import React, { useEffect, useMemo } from 'react';
import { ChevronRight, FileText } from 'lucide-react';
import { Pagination } from '../../components/ui/Pagination';
import { EmptyState } from '../../components/ui/EmptyState';
import { useDashboardData } from '../../contexts/DashboardDataContext';
import { usePagination } from '../../hooks/usePagination';
import { detalheRelatorio } from '../../services/relatoriosService';

const RELATORIO_PER_PAGE = 8;

export function RelatoriosTab({ showToast, onOpenDetalhe }) {
  const {
    relatorios, loadingRelatorios, refetchRelatorios,
    filterTurno, filterSemestre,
  } = useDashboardData();

  useEffect(() => { refetchRelatorios(); }, [refetchRelatorios]);

  const filtered = useMemo(() => relatorios.filter((r) => {
    const matchTurno = r.turno === filterTurno;
    const matchSemestre = filterSemestre === 'Todos' || String(r.semestre) === filterSemestre;
    return matchTurno && matchSemestre;
  }), [relatorios, filterTurno, filterSemestre]);

  const { page, setPage, totalPages, paged } = usePagination(filtered, RELATORIO_PER_PAGE);

  const handleOpen = async (chamada_id) => {
    try {
      const data = await detalheRelatorio(chamada_id);
      onOpenDetalhe(data);
    } catch {
      showToast('Erro ao carregar detalhe da chamada.', 'error');
    }
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col gap-3 min-h-0">
      {loadingRelatorios ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500 font-black text-base">Carregando relatórios...</p>
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={FileText} message="Nenhuma chamada para este filtro." />
      ) : (
        <>
          <div className="flex-1 overflow-hidden flex flex-col gap-2 min-h-0">
            {paged.map((r) => (
              <button
                key={r.chamada_id}
                onClick={() => handleOpen(r.chamada_id)}
                className="group w-full bg-[#151718] hover:bg-[#1A1C1E] px-5 py-3 rounded-2xl border border-white/5 flex items-center justify-between transition-all hover:border-[#4B39EF]/30 text-left flex-shrink-0"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg shrink-0 ${r.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                    {r.semestre}º
                  </div>
                  <div>
                    <div className="flex items-center gap-3 mb-0.5">
                      <h4 className="font-black text-white text-base tracking-tight">{r.nome_disciplina}</h4>
                      <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${r.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>{r.turno}</span>
                    </div>
                    <p className="text-gray-500 font-bold text-xs">
                      Prof. {r.professor_nome} • {r.codigo_turma} • {r.data_chamada} • {r.horario_inicio} – {r.horario_fim}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 shrink-0">
                  <div className="hidden md:flex items-center gap-4">
                    <div className="text-center"><p className="text-sm font-black text-white">{r.total_alunos}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Total</p></div>
                    <div className="text-center"><p className="text-sm font-black text-green-400">{r.presentes}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Pres.</p></div>
                    <div className="text-center"><p className="text-sm font-black text-red-400">{r.ausentes}</p><p className="text-xs text-gray-600 font-black uppercase tracking-widest">Aus.</p></div>
                  </div>
                  <div className="text-center min-w-[50px]">
                    <p className={`text-lg font-black ${r.percentual >= 75 ? 'text-green-400' : 'text-red-400'}`}>{r.percentual}%</p>
                    <p className="text-xs text-gray-600 font-black uppercase tracking-widest">Pres.</p>
                  </div>
                  <ChevronRight size={16} className="text-gray-600 group-hover:text-[#4B39EF] transition-colors" />
                </div>
              </button>
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            totalItems={filtered.length}
            itemLabel={`chamada${filtered.length !== 1 ? 's' : ''}`}
          />
        </>
      )}
    </div>
  );
}
