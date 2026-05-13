import React, { useState, useMemo } from 'react';
import {
  Plus, Trash2, Search, Filter, UserCog, UserPlus, Upload,
} from 'lucide-react';
import { InputGroup } from '../../components/ui/InputGroup';
import { SelectInput } from '../../components/ui/SelectInput';
import { SearchableSelect } from '../../components/ui/SearchableSelect';
import { Pagination } from '../../components/ui/Pagination';
import { EmptyState } from '../../components/ui/EmptyState';
import { useDashboardData } from '../../contexts/DashboardDataContext';
import { usePagination } from '../../hooks/usePagination';
import { criarTurma, deletarTurma, importarAlunosCSV } from '../../services/turmasService';
import { extractErrorMessage } from '../../services/apiClient';

const TURMAS_PER_PAGE = 6;

export function TurmasTab({ showToast, showConfirm, onOpenProfessorModal, onOpenMatriculaModal }) {
  const {
    turmas, professores, refetchTurmasProfsGrade,
    filterTurno, filterSemestre, searchTerm, setSearchTerm,
  } = useDashboardData();

  const [newTurma, setNewTurma] = useState({
    professor_id: '', codigo_turma: '', nome_disciplina: '',
    periodo_letivo: '2025-1', sala_padrao: '', turno: 'Matutino', semestre: '1',
  });

  const filteredTurmas = useMemo(() => turmas.filter((t) => {
    const matchTurno = t.turno === filterTurno;
    const matchSemestre = filterSemestre === 'Todos' || t.semestre === filterSemestre;
    const q = searchTerm.toLowerCase();
    const matchSearch = t.nome_disciplina.toLowerCase().includes(q) || t.codigo_turma.toLowerCase().includes(q);
    return matchTurno && matchSemestre && matchSearch;
  }), [turmas, filterTurno, filterSemestre, searchTerm]);

  const { page, setPage, totalPages, paged } = usePagination(filteredTurmas, TURMAS_PER_PAGE);

  const handleCreateTurma = async (e) => {
    e.preventDefault();
    try {
      await criarTurma(newTurma);
      showToast('Turma criada com sucesso!');
      setNewTurma({ ...newTurma, nome_disciplina: '', codigo_turma: '', sala_padrao: '' });
      refetchTurmasProfsGrade();
    } catch (err) {
      showToast(extractErrorMessage(err, 'Erro ao criar turma'), 'error');
    }
  };

  const handleImportCSV = async (turmaId, file) => {
    if (!file) return;
    try {
      const data = await importarAlunosCSV(turmaId, file);
      const geradas = Array.isArray(data.senhas_geradas) ? data.senhas_geradas : [];
      if (geradas.length > 0) {
        const header = 'email,senha_temporaria\n';
        const rows = geradas
          .map((g) => `${g.email},${g.senha_temporaria}`)
          .join('\n');
        const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `senhas_temporarias_${turmaId}_${Date.now()}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showToast(`${data.mensagem} ${geradas.length} senha(s) gerada(s) — CSV baixado.`);
      } else {
        showToast(data.mensagem);
      }
      refetchTurmasProfsGrade();
    } catch (err) {
      showToast(extractErrorMessage(err, 'Erro na importação de alunos'), 'error');
    }
  };

  const handleDeleteTurma = (id) => {
    showConfirm(
      'Excluir Turma',
      'Deseja realmente excluir esta turma? Todos os alunos e horários vinculados serão removidos.',
      async () => {
        try {
          await deletarTurma(id);
          refetchTurmasProfsGrade();
        } catch {
          showToast('Erro ao excluir turma', 'error');
        }
      }
    );
  };

  return (
    <div className="flex-1 overflow-hidden flex gap-6 min-h-0">
      <div className="w-96 flex-shrink-0 flex flex-col">
        <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl flex-1 flex flex-col">
          <h3 className="text-base font-black text-white mb-4 flex items-center gap-2 flex-shrink-0">
            <Plus size={18} className="text-[#4B39EF]" /> NOVA TURMA
          </h3>
          <form onSubmit={handleCreateTurma} className="flex-1 flex flex-col justify-between">
            <InputGroup label="Nome da Disciplina">
              <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Cálculo I" value={newTurma.nome_disciplina} onChange={(e) => setNewTurma({ ...newTurma, nome_disciplina: e.target.value })} />
            </InputGroup>
            <div className="grid grid-cols-2 gap-3">
              <InputGroup label="Código">
                <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="MAT-01" value={newTurma.codigo_turma} onChange={(e) => setNewTurma({ ...newTurma, codigo_turma: e.target.value })} />
              </InputGroup>
              <InputGroup label="Semestre">
                <SelectInput value={newTurma.semestre} onChange={(e) => setNewTurma({ ...newTurma, semestre: e.target.value })}>
                  {[1, 2, 3, 4, 5, 6].map((v) => <option key={v} value={v}>{v}º</option>)}
                </SelectInput>
              </InputGroup>
            </div>
            <InputGroup label="Turno">
              <SearchableSelect
                searchable={false}
                value={newTurma.turno}
                onChange={(val) => setNewTurma({ ...newTurma, turno: val })}
                options={[{ value: 'Matutino', label: 'Matutino' }, { value: 'Noturno', label: 'Noturno' }]}
                placeholder="Selecione o turno..."
              />
            </InputGroup>
            <InputGroup label="Sala Padrão">
              <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Lab 01" required value={newTurma.sala_padrao} onChange={(e) => setNewTurma({ ...newTurma, sala_padrao: e.target.value })} />
            </InputGroup>
            <InputGroup label="Professor">
              <SearchableSelect
                value={newTurma.professor_id}
                onChange={(val) => setNewTurma({ ...newTurma, professor_id: val })}
                options={professores.map((p) => ({ value: p.professor_id, label: p.nome }))}
                placeholder="Selecione um professor..."
              />
            </InputGroup>
            <button className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">
              CADASTRAR TURMA
            </button>
          </form>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden min-h-0">
        <div className="relative mb-3 flex-shrink-0">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
          <input
            className="w-full bg-[#151718] border border-white/5 rounded-2xl py-3 pl-12 pr-6 outline-none focus:ring-2 focus:ring-[#4B39EF]/30 transition-all font-bold text-sm"
            placeholder="Pesquisar por disciplina ou código..."
            value={searchTerm}
            onChange={(e) => { setSearchTerm(e.target.value); setPage(1); }}
          />
        </div>

        <div className="flex-1 overflow-hidden flex flex-col gap-2 min-h-0">
          {paged.map((t) => (
            <div key={t.turma_id} className="group bg-[#151718] hover:bg-[#1A1C1E] px-5 rounded-2xl border border-white/5 flex items-center justify-between transition-all hover:border-[#4B39EF]/40 flex-1 min-h-0">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg flex-shrink-0 ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                  {t.semestre}º
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <h4 className="font-black text-white text-base tracking-tight">{t.nome_disciplina}</h4>
                    <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${t.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                      {t.turno}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 font-bold mt-0.5 italic">
                    Prof. {t.professor_nome} • <span className="text-gray-600">{t.codigo_turma}</span>
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-right mr-4 hidden md:block">
                  <p className="text-base font-black text-white">{t.total_alunos}</p>
                  <p className="text-xs text-gray-600 font-black uppercase tracking-widest">Alunos</p>
                </div>
                <button onClick={() => onOpenProfessorModal(t)} title="Atribuir professor" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-amber-400 transition-all border border-white/5 hover:border-amber-400/30">
                  <UserCog size={18} />
                </button>
                <button onClick={() => onOpenMatriculaModal(t)} title="Matricular aluno" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-[#4B39EF] transition-all border border-white/5 hover:border-[#4B39EF]/30">
                  <UserPlus size={18} />
                </button>
                <label title="Importar CSV" className="cursor-pointer w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-[#22C55E] transition-all border border-white/5 hover:border-[#22C55E]/30">
                  <Upload size={18} />
                  <input type="file" accept=".csv" className="hidden" onChange={(e) => handleImportCSV(t.turma_id, e.target.files[0])} />
                </label>
                <button onClick={() => handleDeleteTurma(t.turma_id)} title="Excluir turma" className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))}

          {filteredTurmas.length === 0 && (
            <EmptyState icon={Filter} message="Nenhuma turma para este filtro." />
          )}
        </div>

        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
          totalItems={filteredTurmas.length}
          itemLabel={`turma${filteredTurmas.length !== 1 ? 's' : ''}`}
        />
      </div>
    </div>
  );
}
