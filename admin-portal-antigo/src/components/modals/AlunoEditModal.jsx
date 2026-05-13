import React, { useState, useEffect } from 'react';
import { UserPen } from 'lucide-react';
import { InputGroup } from '../ui/InputGroup';
import { SearchableSelect } from '../ui/SearchableSelect';
import { atualizarAluno } from '../../services/alunosService';
import { extractErrorMessage } from '../../services/apiClient';

export function AlunoEditModal({ open, aluno, onClose, onSuccess, showToast }) {
  const [form, setForm] = useState({ nome: '', email: '', ra: '', turno: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (aluno) {
      setForm({ nome: aluno.nome || '', email: aluno.email || '', ra: aluno.ra || '', turno: aluno.turno || 'Matutino' });
    }
  }, [aluno]);

  if (!open || !aluno) return null;

  const handleClose = () => { onClose(); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {};
    if (form.nome !== aluno.nome) payload.nome = form.nome;
    if (form.email !== aluno.email) payload.email = form.email;
    if (form.ra !== aluno.ra) payload.ra = form.ra;
    if (form.turno !== aluno.turno) payload.turno = form.turno;

    if (Object.keys(payload).length === 0) {
      showToast('Nenhuma alteração detectada.', 'warning');
      return;
    }

    setLoading(true);
    try {
      await atualizarAluno(aluno.aluno_id, payload);
      onSuccess();
      onClose();
    } catch (err) {
      showToast(`Erro ao atualizar aluno: ${extractErrorMessage(err)}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={handleClose}>
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-lg w-full p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-4 mb-8">
          <UserPen className="text-[#4B39EF]" size={28} />
          <div>
            <h3 className="text-2xl font-black text-white">Editar Aluno</h3>
            <p className="text-gray-500 text-sm font-bold mt-1 truncate max-w-xs">{aluno.nome}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
          <InputGroup label="Nome Completo">
            <input
              required
              minLength={3}
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
            />
          </InputGroup>
          <InputGroup label="Email">
            <input
              required
              type="email"
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </InputGroup>
          <InputGroup label="RA/CPF">
            <input
              required
              pattern="^[A-Za-z0-9]{4,20}$"
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all uppercase"
              value={form.ra}
              onChange={(e) => setForm({ ...form, ra: e.target.value })}
            />
          </InputGroup>
          <InputGroup label="Turno">
            <SearchableSelect
              searchable={false}
              value={form.turno}
              onChange={(val) => setForm({ ...form, turno: val })}
              options={[{ value: 'Matutino', label: 'Matutino' }, { value: 'Noturno', label: 'Noturno' }]}
              placeholder="Selecione o turno..."
            />
          </InputGroup>
          <div className="flex gap-4 pt-4">
            <button type="button" onClick={handleClose} className="flex-1 py-5 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
              Cancelar
            </button>
            <button type="submit" disabled={loading} className="flex-1 bg-[#4B39EF] py-5 rounded-2xl font-black text-sm uppercase tracking-widest shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98] disabled:opacity-50 disabled:scale-100">
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
