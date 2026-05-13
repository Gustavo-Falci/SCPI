import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export function SenhaTemporariaModal({ data, onClose }) {
  if (!data) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[150] flex items-center justify-center p-6">
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-md w-full p-10">
        <div className="flex flex-col items-center text-center gap-6">
          <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center">
            <CheckCircle2 size={28} className="text-green-400" />
          </div>
          <div>
            <h3 className="text-2xl font-black text-white mb-3">{data.tipo} Criado!</h3>
            <p className="text-gray-400 font-medium">{data.nome} foi cadastrado com sucesso.</p>
          </div>
          <div className="w-full bg-black/40 rounded-2xl p-6 border border-white/10">
            <p className="text-xs text-gray-500 font-black uppercase tracking-widest mb-3">Senha Temporária</p>
            <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">Enviada para</p>
            <p className="text-base font-black text-white font-mono break-all">{data.email}</p>
            <p className="text-xs text-gray-600 mt-4">O usuário deverá alterar a senha no primeiro acesso.</p>
          </div>
          <button onClick={onClose} className="w-full py-4 rounded-2xl bg-[#4B39EF] font-black text-sm uppercase tracking-widest text-white hover:bg-[#5E47FF] transition-all">
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
