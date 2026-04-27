import React, { useState, useMemo } from 'react';
import { Plus, Trash2, Search } from 'lucide-react';
import { InputGroup } from '../../components/ui/InputGroup';
import { Pagination } from '../../components/ui/Pagination';
import { useDashboardData } from '../../contexts/DashboardDataContext';
import { usePagination } from '../../hooks/usePagination';
import { criarProfessor, deletarProfessor } from '../../services/professoresService';
import { extractErrorMessage } from '../../services/apiClient';

const PROF_PER_PAGE = 8;

export function ProfessoresTab({ showToast, showConfirm, onCreatedComSenha }) {
  const { professores, refetchTurmasProfsGrade } = useDashboardData();
  const [novoProfessor, setNovoProfessor] = useState({ nome: '', email: '', departamento: '' });
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return professores;
    return professores.filter((p) =>
      p.nome.toLowerCase().includes(q) ||
      (p.email || '').toLowerCase().includes(q) ||
      (p.departamento || '').toLowerCase().includes(q)
    );
  }, [professores, search]);

  const { page, setPage, totalPages, paged } = usePagination(filtered, PROF_PER_PAGE);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const res = await criarProfessor(novoProfessor);
      onCreatedComSenha({ nome: novoProfessor.nome, senha: res.senha_temporaria, tipo: 'Professor' });
      setNovoProfessor({ nome: '', email: '', departamento: '' });
      refetchTurmasProfsGrade();
    } catch (err) {
      showToast(`Erro ao criar professor: ${extractErrorMessage(err)}`, 'error');
    }
  };

  const handleDelete = (professor_id, nome) => {
    showConfirm(
      'Excluir Professor',
      `Deseja realmente excluir o professor "${nome}"?\n\nAs disciplinas atribuídas a ele ficarão sem professor.`,
      async () => {
        try {
          await deletarProfessor(professor_id);
          refetchTurmasProfsGrade();
        } catch {
          showToast('Erro ao excluir professor', 'error');
        }
      }
    );
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col min-h-0">
      <h2 className="text-2xl font-black text-white tracking-tight mb-4 flex-shrink-0">Professores</h2>
      <div className="flex gap-6 flex-1 overflow-hidden min-h-0">
        <div className="w-96 flex-shrink-0">
          <div className="bg-[#151718] p-6 rounded-[32px] border border-white/5 shadow-2xl">
            <h3 className="text-base font-black text-white mb-4 flex items-center gap-2">
              <Plus size={18} className="text-[#4B39EF]" /> NOVO PROFESSOR
            </h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <InputGroup label="Nome Completo">
                <input required minLength={3} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: João Silva" value={novoProfessor.nome} onChange={(e) => setNovoProfessor({ ...novoProfessor, nome: e.target.value })} />
              </InputGroup>
              <InputGroup label="Email">
                <input required type="email" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="professor@scpi.com" value={novoProfessor.email} onChange={(e) => setNovoProfessor({ ...novoProfessor, email: e.target.value })} />
              </InputGroup>
              <InputGroup label="Departamento">
                <input className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#4B39EF] transition-all" placeholder="Ex: Informática" value={novoProfessor.departamento} onChange={(e) => setNovoProfessor({ ...novoProfessor, departamento: e.target.value })} />
              </InputGroup>
              <button type="submit" className="w-full bg-[#4B39EF] py-3 rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">
                CADASTRAR PROFESSOR
              </button>
            </form>
          </div>
        </div>

        <div className="flex-1 overflow-hidden flex flex-col gap-3">
          <div className="relative flex-shrink-0">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" size={18} />
            <input
              className="w-full bg-[#151718] border border-white/5 rounded-2xl py-3 pl-11 pr-5 outline-none focus:ring-2 focus:ring-[#4B39EF]/30 transition-all font-bold text-sm"
              placeholder="Buscar por nome, email ou departamento..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <div className="bg-[#151718] rounded-3xl border border-white/5 overflow-hidden shadow-2xl overflow-y-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-white/[0.03] text-gray-500 uppercase text-xs tracking-[0.2em]">
                  <th className="px-5 py-4">Nome</th>
                  <th className="px-5 py-4">Departamento</th>
                  <th className="px-5 py-4">Email</th>
                  <th className="px-5 py-4">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {paged.map((p) => (
                  <tr key={p.professor_id} className="hover:bg-white/[0.01] transition-colors group">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 bg-gradient-to-br from-[#4B39EF] to-[#8E44AD] rounded-xl flex items-center justify-center font-black text-white text-sm shadow-lg shrink-0">{p.nome.charAt(0)}</div>
                        <p className="font-black text-white text-sm">{p.nome}</p>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <div className="bg-white/5 inline-block px-3 py-1 rounded-lg text-xs font-black text-gray-400 border border-white/5 uppercase tracking-widest">{p.departamento || '—'}</div>
                    </td>
                    <td className="px-5 py-3 text-gray-300 font-bold text-sm">{p.email}</td>
                    <td className="px-5 py-3">
                      <button onClick={() => handleDelete(p.professor_id, p.nome)} title="Excluir professor" className="w-9 h-9 bg-white/5 rounded-xl flex items-center justify-center text-gray-500 hover:text-red-500 transition-all border border-white/5 hover:border-red-500/30">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr><td colSpan="4" className="px-5 py-12 text-center text-gray-500 font-black">
                    {search ? 'Nenhum professor encontrado para esta busca.' : 'Nenhum professor cadastrado ainda.'}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            totalItems={filtered.length}
            itemLabel={`professor${filtered.length !== 1 ? 'es' : ''}`}
          />
        </div>
      </div>
    </div>
  );
}
