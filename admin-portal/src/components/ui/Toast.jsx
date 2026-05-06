import React, { useEffect, useState } from 'react';
import { CheckCircle2, X, AlertTriangle, Info, AlertOctagon } from 'lucide-react';

/**
 * Configuração visual por tipo (dark theme).
 */
const TYPE_CONFIG = {
  success: {
    icon: CheckCircle2,
    iconClass: 'text-green-400',
    borderClass: 'border-green-500/60',
    accent: 'bg-green-500',
    titleClass: 'text-green-100',
    title: 'Sucesso',
  },
  error: {
    icon: AlertOctagon,
    iconClass: 'text-red-400',
    borderClass: 'border-red-500/60',
    accent: 'bg-red-500',
    titleClass: 'text-red-100',
    title: 'Erro',
  },
  warning: {
    icon: AlertTriangle,
    iconClass: 'text-amber-300',
    borderClass: 'border-amber-400/60',
    accent: 'bg-amber-400',
    titleClass: 'text-amber-100',
    title: 'Atenção',
  },
  info: {
    icon: Info,
    iconClass: 'text-blue-300',
    borderClass: 'border-blue-400/60',
    accent: 'bg-blue-400',
    titleClass: 'text-blue-100',
    title: 'Informação',
  },
};

function getConfig(type) {
  return TYPE_CONFIG[type] || TYPE_CONFIG.info;
}

/**
 * Toast individual — animação slide-in + barra de progresso.
 */
function ToastItem({ toast, onDismiss }) {
  const cfg = getConfig(toast.type);
  const Icon = cfg.icon;
  const duration = toast.duration || 3500;

  // Animações de entrada/saída
  const [visible, setVisible] = useState(false);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    // requestAnimationFrame para garantir transição
    const id = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const handleDismiss = () => {
    if (leaving) return;
    setLeaving(true);
    setTimeout(() => onDismiss(toast.id), 200);
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={`
        relative overflow-hidden flex items-start gap-3 px-4 py-3
        rounded-xl bg-[#151718] border shadow-2xl w-80
        transition-all duration-200 ease-out
        ${cfg.borderClass}
        ${visible && !leaving ? 'translate-x-0 opacity-100' : 'translate-x-8 opacity-0'}
      `}
    >
      <Icon size={20} className={`${cfg.iconClass} shrink-0 mt-0.5`} />

      <div className="flex-1 min-w-0">
        <p className={`text-xs font-bold uppercase tracking-wide ${cfg.titleClass}`}>
          {toast.title || cfg.title}
        </p>
        <p className="text-sm text-white/90 mt-0.5 break-words">{toast.message}</p>
      </div>

      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dispensar notificação"
        className="text-gray-500 hover:text-white transition-colors shrink-0 -mr-1 -mt-1 p-1"
      >
        <X size={14} />
      </button>

      {/* Barra de progresso */}
      <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-white/5">
        <div
          className={`h-full ${cfg.accent}`}
          style={{
            width: '100%',
            animation: visible && !leaving
              ? `toast-progress ${duration}ms linear forwards`
              : 'none',
          }}
        />
      </div>

      <style>{`
        @keyframes toast-progress {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
    </div>
  );
}

/**
 * Container que recebe `toasts` (array) ou `toast` (compat retro).
 *
 * Props:
 *  - toasts: Array<{ id, message, type, duration, title? }>
 *  - toast (legacy): { show, message, type } — exibido se toasts não fornecido
 *  - onDismiss(id): remove toast específico
 */
export function Toast({ toasts, toast, onDismiss }) {
  // Modo legado: objeto único
  if (!toasts && toast) {
    if (!toast.show) return null;
    const legacy = { id: 'legacy', ...toast };
    return (
      <div className="fixed top-6 right-6 z-[200] flex flex-col gap-3">
        <ToastItem toast={legacy} onDismiss={() => onDismiss?.()} />
      </div>
    );
  }

  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="fixed top-6 right-6 z-[200] flex flex-col gap-3">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
