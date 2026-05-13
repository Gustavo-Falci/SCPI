import React, { useState, useEffect } from 'react';
import { UserCog, X } from 'lucide-react';
import { atribuirProfessor } from '../../services/turmasService';
import { extractErrorMessage } from '../../services/apiClient';

export function ProfessorAssignModal({ turma, professores, onClose, onSuccess, showToast }) {
  const [selectedProfessorId, setSelectedProfessorId] = useState(turma?.professor_id || '');

  useEffect(() => {
    setSelectedProfessorId(turma?.professor_id || '');
  }, [turma]);

  if (!turma) return null;

  const handleConfirm = async () => {
    try {
      await atribuirProfessor(turma.turma_id, selectedProfessorId);
      onSuccess();
    } catch (err) {
      showToast(`Erro ao atribuir professor: ${extractErrorMessage(err)}`, 'error');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={onClose}>
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-xl w-full p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-center gap-4">
            <UserCog className="text-amber-400" size={28} />
            <div>
              <h3 className="text-2xl font-black text-white">Atribuir Professor</h3>
              <p className="text-gray-500 text-sm font-bold mt-1">
                {turma.nome_disciplina} • {turma.codigo_turma}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all">
            <X size={22} />
          </button>
        </div>

        <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
          <label className={`flex items-center gap-5 p-5 rounded-2xl border transition-all cursor-pointer ${selectedProfessorId === '' ? 'bg-amber-400/10 border-amber-400/40' : 'bg-white/[0.03] border-white/5 hover:border-white/20'}`}>
            <input type="radio" name="professor" value="" checked={selectedProfessorId === ''} onChange={() => setSelectedProfessorId('')} className="w-5 h-5 accent-amber-400" />
            <p className="font-black text-gray-400 italic">Sem professor</p>
          </label>
          {professores.map((p) => (
            <label key={p.professor_id} className={`flex items-center gap-5 p-5 rounded-2xl border transition-all cursor-pointer ${selectedProfessorId === p.professor_id ? 'bg-amber-400/10 border-amber-400/40' : 'bg-white/[0.03] border-white/5 hover:border-white/20'}`}>
              <input type="radio" name="professor" value={p.professor_id} checked={selectedProfessorId === p.professor_id} onChange={() => setSelectedProfessorId(p.professor_id)} className="w-5 h-5 accent-amber-400" />
              <div className="flex-1">
                <p className="font-black text-white">{p.nome}</p>
                <p className="text-xs text-gray-500 font-bold mt-1">{p.email}</p>
              </div>
            </label>
          ))}
        </div>

        <div className="flex gap-4 pt-8 border-t border-white/5 mt-6">
          <button type="button" onClick={onClose} className="px-10 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
          <button type="button" onClick={handleConfirm} className="flex-1 py-4 rounded-2xl bg-amber-400 font-black text-sm uppercase tracking-widest text-black hover:bg-amber-300 transition-all">Confirmar</button>
        </div>
      </div>
    </div>
  );
}
