import React from 'react';
import { CheckCircle2, X, AlertTriangle } from 'lucide-react';

export function Toast({ toast, onDismiss }) {
  if (!toast.show) return null;

  const borderClass =
    toast.type === 'success' ? 'border-green-500/50' :
    toast.type === 'error'   ? 'border-red-500/50'   :
                               'border-amber-400/50';

  return (
    <div className={`fixed top-6 right-6 z-[200] flex items-center gap-4 px-6 py-4 rounded-2xl bg-[#151718] border shadow-2xl max-w-sm ${borderClass}`}>
      {toast.type === 'success' && <CheckCircle2 size={20} className="text-green-400 shrink-0" />}
      {toast.type === 'error'   && <X size={20} className="text-red-400 shrink-0" />}
      {toast.type === 'warning' && <AlertTriangle size={20} className="text-amber-400 shrink-0" />}
      <p className="text-sm font-bold text-white flex-1">{toast.message}</p>
      <button onClick={onDismiss} className="text-gray-500 hover:text-white transition-colors ml-2">
        <X size={16} />
      </button>
    </div>
  );
}
