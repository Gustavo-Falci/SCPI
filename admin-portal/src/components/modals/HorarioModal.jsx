import React, { useState } from 'react';
import { Clock } from 'lucide-react';
import { InputGroup } from '../ui/InputGroup';
import { SelectInput } from '../ui/SelectInput';
import { getSlots, DIAS_SEMANA } from '../../config/slots';
import { criarHorario, detectarConflitoHorario } from '../../services/horariosService';
import { extractErrorMessage } from '../../services/apiClient';

export function HorarioModal({ open, onClose, dia_semana, turno, turmas, grade, onSuccess, showToast }) {
  const [form, setForm] = useState({ turma_id: '', slot_inicio: 1, slot_fim: 1, sala: '' });

  if (!open) return null;

  const slots = getSlots(turno);

  const reset = () => setForm({ turma_id: '', slot_inicio: 1, slot_fim: 1, sala: '' });

  const handleClose = () => { reset(); onClose(); };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const slotIni = slots.find((s) => s.id === Number(form.slot_inicio));
    const slotFim = slots.find((s) => s.id === Number(form.slot_fim));
    if (!slotIni || !slotFim || !form.turma_id) {
      showToast('Preencha turma e slots.', 'warning');
      return;
    }
    if (slotFim.id < slotIni.id) {
      showToast('Slot final deve ser ≥ slot inicial.', 'warning');
      return;
    }

    const conflito = detectarConflitoHorario(grade, {
      turma_id: form.turma_id,
      dia_semana,
      inicio: slotIni.inicio,
      fim: slotFim.fim,
    });
    if (conflito) {
      showToast(`Conflito: "${conflito.nome_disciplina}" já ocupa ${conflito.inicio}–${conflito.fim} neste dia.`, 'error');
      return;
    }

    try {
      await criarHorario({
        turma_id: form.turma_id,
        dia_semana,
        horario_inicio: slotIni.inicio,
        horario_fim: slotFim.fim,
        sala: form.sala,
      });
      reset();
      onSuccess();
    } catch (err) {
      showToast(extractErrorMessage(err, 'Erro ao adicionar horário'), 'error');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-6" onClick={handleClose}>
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-2xl w-full p-10" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-4 mb-8">
          <Clock className="text-[#4B39EF]" size={28} />
          <div>
            <h3 className="text-2xl font-black text-white">Novo Horário</h3>
            <p className="text-gray-500 text-sm font-bold mt-1">
              {DIAS_SEMANA[dia_semana]} • {turno}
            </p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          <InputGroup label="Turma">
            <SelectInput required value={form.turma_id} onChange={(e) => setForm({ ...form, turma_id: e.target.value })}>
              <option value="">Selecione uma turma...</option>
              {turmas.filter((t) => t.turno === turno).map((t) => (
                <option key={t.turma_id} value={t.turma_id}>{t.semestre}º • {t.nome_disciplina} ({t.codigo_turma})</option>
              ))}
            </SelectInput>
          </InputGroup>
          <div className="grid grid-cols-2 gap-6">
            <InputGroup label="Slot Inicial">
              <SelectInput
                value={form.slot_inicio}
                onChange={(e) => setForm({
                  ...form,
                  slot_inicio: e.target.value,
                  slot_fim: Math.max(Number(e.target.value), Number(form.slot_fim)),
                })}
              >
                {slots.map((s) => <option key={s.id} value={s.id}>{s.id}º — {s.inicio}</option>)}
              </SelectInput>
            </InputGroup>
            <InputGroup label="Slot Final">
              <SelectInput value={form.slot_fim} onChange={(e) => setForm({ ...form, slot_fim: e.target.value })}>
                {slots.filter((s) => s.id >= Number(form.slot_inicio)).map((s) => (
                  <option key={s.id} value={s.id}>{s.id}º — {s.fim}</option>
                ))}
              </SelectInput>
            </InputGroup>
          </div>
          <InputGroup label="Sala">
            <input
              required
              className="w-full bg-black/40 border border-white/10 rounded-2xl px-6 py-5 text-lg outline-none focus:border-[#4B39EF] transition-all"
              placeholder="Ex: Lab 01"
              value={form.sala}
              onChange={(e) => setForm({ ...form, sala: e.target.value })}
            />
          </InputGroup>
          <div className="flex gap-4 pt-4">
            <button type="button" onClick={handleClose} className="flex-1 py-5 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">Cancelar</button>
            <button type="submit" className="flex-1 bg-[#4B39EF] py-5 rounded-2xl font-black text-sm uppercase tracking-widest shadow-2xl shadow-[#4B39EF]/30 hover:scale-[1.02] transition-all active:scale-[0.98]">Adicionar</button>
          </div>
        </form>
      </div>
    </div>
  );
}
