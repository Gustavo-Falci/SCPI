import React, { useState, useEffect } from 'react';
import { UserPlus, X, Search } from 'lucide-react';
import { listarAlunos } from '../../services/alunosService';
import { matricularAlunos } from '../../services/turmasService';
import { extractErrorMessage } from '../../services/apiClient';

export function MatriculaModal({ turma, onClose, onSuccess, showToast }) {
  const [alunosDisponiveis, setAlunosDisponiveis] = useState([]);
  const [selectedAlunoIds, setSelectedAlunoIds] = useState(new Set());
  const [searchAluno, setSearchAluno] = useState('');
  const [loadingAlunos, setLoadingAlunos] = useState(false);

  useEffect(() => {
    if (!turma) return;
    setSelectedAlunoIds(new Set());
    setSearchAluno('');
    setLoadingAlunos(true);
    (async () => {
      try {
        const data = await listarAlunos({ turma_id: turma.turma_id });
        setAlunosDisponiveis(data);
      } catch {
        showToast('Erro ao carregar alunos.', 'error');
        onClose();
      } finally {
        setLoadingAlunos(false);
      }
    })();
  }, [turma, onClose, showToast]);

  if (!turma) return null;

  const toggleAluno = (aluno_id) => {
    setSelectedAlunoIds((prev) => {
      const next = new Set(prev);
      if (next.has(aluno_id)) next.delete(aluno_id);
      else next.add(aluno_id);
      return next;
    });
  };

  const handleMatricular = async () => {
    if (selectedAlunoIds.size === 0) {
      showToast('Selecione pelo menos um aluno.', 'warning');
      return;
    }
    try {
      const data = await matricularAlunos(turma.turma_id, Array.from(selectedAlunoIds));
      showToast(data.mensagem);
      onSuccess();
    } catch (err) {
      showToast(`Erro ao matricular: ${extractErrorMessage(err)}`, 'error');
    }
  };

  const q = searchAluno.toLowerCase();
  const turmaTurno = turma.turno;
  const filtrados = alunosDisponiveis.filter((a) =>
    a.nome.toLowerCase().includes(q) ||
    (a.email || '').toLowerCase().includes(q) ||
    (a.ra || '').toLowerCase().includes(q)
  );

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={onClose}>
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-3xl w-full p-10 max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center gap-4">
            <UserPlus className="text-[#4B39EF]" size={28} />
            <div>
              <h3 className="text-2xl font-black text-white">Matricular Aluno</h3>
              <p className="text-gray-500 text-sm font-bold mt-1">
                {turma.nome_disciplina} • {turma.codigo_turma}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all">
            <X size={22} />
          </button>
        </div>

        <div className="relative mb-6">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
          <input
            className="w-full bg-black/40 border border-white/10 rounded-2xl py-4 pl-14 pr-6 outline-none focus:border-[#4B39EF] transition-all font-medium"
            placeholder="Buscar por nome, email ou RA..."
            value={searchAluno}
            onChange={(e) => setSearchAluno(e.target.value)}
          />
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 -mx-2 px-2" style={{ minHeight: 200 }}>
          {loadingAlunos ? (
            <div className="py-20 text-center text-gray-500 font-bold">Carregando alunos...</div>
          ) : filtrados.length === 0 ? (
            <div className="py-20 text-center text-gray-500 font-bold">Nenhum aluno encontrado.</div>
          ) : (
            filtrados.map((a) => {
              const checked = selectedAlunoIds.has(a.aluno_id);
              const turnoIncompativel = turmaTurno && a.turno && a.turno !== turmaTurno;
              const disabled = a.ja_matriculado || turnoIncompativel;
              return (
                <label
                  key={a.aluno_id}
                  className={`flex items-center gap-5 p-5 rounded-2xl border transition-all ${
                    disabled
                      ? 'bg-white/[0.02] border-white/5 opacity-50 cursor-not-allowed'
                      : checked
                        ? 'bg-[#4B39EF]/10 border-[#4B39EF]/40 cursor-pointer'
                        : 'bg-white/[0.03] border-white/5 hover:border-white/20 cursor-pointer'
                  }`}
                >
                  <input
                    type="checkbox"
                    disabled={disabled}
                    checked={checked || a.ja_matriculado}
                    onChange={() => !disabled && toggleAluno(a.aluno_id)}
                    className="w-5 h-5 accent-[#4B39EF] cursor-pointer disabled:cursor-not-allowed"
                  />
                  <div className="flex-1">
                    <p className="font-black text-white">{a.nome}</p>
                    <p className="text-xs text-gray-500 font-bold mt-1">
                      RA {a.ra || '—'} • {a.email}
                      {a.turno && <span className="ml-2 text-gray-600">• {a.turno}</span>}
                    </p>
                  </div>
                  {a.ja_matriculado && (
                    <span className="text-[10px] font-black uppercase tracking-widest text-[#22C55E] bg-[#22C55E]/10 px-3 py-1 rounded-lg">Já matriculado</span>
                  )}
                  {turnoIncompativel && (
                    <span className="text-[10px] font-black uppercase tracking-widest text-yellow-400 bg-yellow-400/10 px-3 py-1 rounded-lg">Turno {a.turno}</span>
                  )}
                </label>
              );
            })
          )}
        </div>

        <div className="flex gap-4 pt-8 border-t border-white/5 mt-6">
          <div className="flex-1 flex items-center text-gray-500 font-bold text-sm">
            {selectedAlunoIds.size} selecionado(s)
          </div>
          <button type="button" onClick={onClose} className="px-10 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
          <button
            type="button"
            onClick={handleMatricular}
            disabled={selectedAlunoIds.size === 0}
            className="px-10 py-4 rounded-2xl bg-[#4B39EF] font-black text-sm uppercase tracking-widest text-white shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            Matricular
          </button>
        </div>
      </div>
    </div>
  );
}
