import React, { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { InputGroup } from '../../components/ui/InputGroup';
import { SearchableSelect } from '../../components/ui/SearchableSelect';
import { Pagination } from '../../components/ui/Pagination';
import { useDashboardData } from '../../contexts/DashboardDataContext';
import { usePagination } from '../../hooks/usePagination';
import { criarAluno } from '../../services/alunosService';
import { extractErrorMessage } from '../../services/apiClient';

const ALUNO_PER_PAGE = 8;

export function AlunosTab({ showToast, onCreatedComSenha }) {
  const { alunos, refetchAlunos } = useDashboardData();
  const [novoAluno, setNovoAluno] = useState({ nome: '', email: '', ra: '', turno: 'Matutino' });
  const { page, setPage, totalPages, paged } = usePagination(alunos, ALUNO_PER_PAGE);

  useEffect(() => { refetchAlunos(); }, [refetchAlunos]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await criarAluno(novoAluno);
      onCreatedComSenha({ nome: novoAluno.nome, senha: res.senha_temporaria, tipo: 'Aluno' });
      setNovoAluno({ nome: '', email: '', ra: '', turno: 'Matutino' });
      refetchAlunos();
    } catch (err) {
      showToast(`Erro ao criar aluno: ${extractErrorMessage(err)}`, 'error');
    }
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col min-h-0">
      <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Alunos</h2>
      <div className="flex gap-6 flex-1 overflow-hidden min-h-0">
        <div className="w-96 flex-shrink-0">
          <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl">
            <h3 className="text-base font-black text-white mb-4 flex items-center gap-2">
              <Plus size={18} className="text-[#4B39EF]" /> NOVO ALUNO
            </h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <InputGroup label="Nome Completo">
                <input required minLength={3} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Maria Souza" value={novoAluno.nome} onChange={(e) => setNovoAluno({ ...novoAluno, nome: e.target.value })} />
              </InputGroup>
              <InputGroup label="Email">
                <input required type="email" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="aluno@scpi.com" value={novoAluno.email} onChange={(e) => setNovoAluno({ ...novoAluno, email: e.target.value })} />
              </InputGroup>
              <InputGroup label="RA">
                <input required pattern="^[A-Za-z0-9]{4,20}$" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: 202400123" value={novoAluno.ra} onChange={(e) => setNovoAluno({ ...novoAluno, ra: e.target.value })} />
              </InputGroup>
              <InputGroup label="Turno">
                <SearchableSelect
                  searchable={false}
                  value={novoAluno.turno}
                  onChange={(val) => setNovoAluno({ ...novoAluno, turno: val })}
                  options={[{ value: 'Matutino', label: 'Matutino' }, { value: 'Noturno', label: 'Noturno' }]}
                  placeholder="Selecione o turno..."
                />
              </InputGroup>
              <button type="submit" className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">
                CADASTRAR ALUNO
              </button>
            </form>
          </div>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col gap-3">
          <div className="bg-[#151718] rounded-3xl border border-white/5 overflow-hidden shadow-2xl flex-1">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                  <th className="px-5 py-4">Nome</th>
                  <th className="px-5 py-4">Email</th>
                  <th className="px-5 py-4">RA</th>
                  <th className="px-5 py-4">Turno</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {paged.map((a) => (
                  <tr key={a.aluno_id} className="hover:bg-white/[0.01] transition-colors">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-gradient-to-br from-[#22C55E] to-[#4B39EF] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">{a.nome.charAt(0)}</div>
                        <p className="font-black text-white text-sm">{a.nome}</p>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-gray-300 font-bold text-sm">{a.email}</td>
                    <td className="px-5 py-3">
                      <div className="bg-white/5 inline-block px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest">{a.ra || '—'}</div>
                    </td>
                    <td className="px-5 py-3">
                      {a.turno ? (
                        <span className={`text-xs font-black px-2 py-0.5 rounded-md uppercase tracking-tighter ${a.turno === 'Matutino' ? 'bg-amber-500/10 text-amber-500' : 'bg-indigo-500/10 text-indigo-500'}`}>{a.turno}</span>
                      ) : (
                        <span className="text-xs text-gray-600 font-bold">—</span>
                      )}
                    </td>
                  </tr>
                ))}
                {alunos.length === 0 && (
                  <tr><td colSpan="4" className="px-5 py-12 text-center text-gray-500 font-black">Nenhum aluno cadastrado ainda.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            totalItems={alunos.length}
            itemLabel={`aluno${alunos.length !== 1 ? 's' : ''}`}
          />
        </div>
      </div>
    </div>
  );
}
