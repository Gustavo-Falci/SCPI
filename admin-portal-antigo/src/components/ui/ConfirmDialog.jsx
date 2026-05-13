import React from 'react';
import { Trash2 } from 'lucide-react';

export function ConfirmDialog({ dialog, onCancel, onConfirm }) {
  if (!dialog.show) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[150] flex items-center justify-center p-6">
      <div className="bg-[#151718] rounded-[40px] border border-white/5 shadow-2xl max-w-md w-full p-10">
        <div className="flex flex-col items-center text-center gap-6">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center">
            <Trash2 size={28} className="text-red-500" />
          </div>
          <div>
            <h3 className="text-2xl font-black text-white mb-3">{dialog.title}</h3>
            <p className="text-gray-400 font-medium whitespace-pre-line leading-relaxed">{dialog.message}</p>
          </div>
          <div className="flex gap-4 w-full pt-2">
            <button
              onClick={onCancel}
              className="flex-1 py-4 rounded-2xl bg-white/5 font-black text-sm uppercase tracking-widest text-gray-400 hover:bg-white/10 transition-all">
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 py-4 rounded-2xl bg-red-500 font-black text-sm uppercase tracking-widest text-white hover:bg-red-400 transition-all shadow-2xl shadow-red-500/20">
              Confirmar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
