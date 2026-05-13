import { useState, useCallback, useRef } from 'react';

/**
 * Durações padrão por tipo (ms).
 */
const DEFAULT_DURATIONS = {
  success: 3000,
  info: 3500,
  warning: 5000,
  error: 6000,
};

/**
 * Hook de toasts empilháveis.
 *
 * API:
 *  - toasts: Array<{ id, message, type, duration, title? }>  (preferida)
 *  - toast:  { show, message, type } — compat retroativo (último toast)
 *  - showToast(message, type='success', duration?)  → mantém assinatura antiga
 *  - addToast(message, type, duration?, title?) → retorna id
 *  - dismissToast(id?) → remove um (ou todos, se id ausente)
 */
export function useToast() {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);
  const timersRef = useRef(new Map());

  const dismissToast = useCallback((id) => {
    if (id === undefined || id === null) {
      // Modo legado: limpa todos
      timersRef.current.forEach((t) => clearTimeout(t));
      timersRef.current.clear();
      setToasts([]);
      return;
    }
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration, title) => {
    const id = ++idRef.current;
    const finalDuration = duration ?? DEFAULT_DURATIONS[type] ?? 3500;
    const newToast = { id, message, type, duration: finalDuration, title };

    setToasts((prev) => [...prev, newToast]);

    const timer = setTimeout(() => {
      timersRef.current.delete(id);
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, finalDuration);
    timersRef.current.set(id, timer);

    return id;
  }, []);

  // Compat: API antiga showToast(message, type)
  const showToast = useCallback(
    (message, type = 'success', duration) => addToast(message, type, duration),
    [addToast]
  );

  // Helpers semânticos
  const showSuccess = useCallback((message, duration) => addToast(message, 'success', duration), [addToast]);
  const showError = useCallback((message, duration) => addToast(message, 'error', duration), [addToast]);
  const showWarning = useCallback((message, duration) => addToast(message, 'warning', duration), [addToast]);
  const showInfo = useCallback((message, duration) => addToast(message, 'info', duration), [addToast]);

  // Mantém shape legado (último toast) para callers antigos que liam `toast.show`
  const last = toasts[toasts.length - 1];
  const legacyToast = last
    ? { show: true, message: last.message, type: last.type }
    : { show: false, message: '', type: 'success' };

  return {
    toasts,
    toast: legacyToast,
    showToast,
    addToast,
    dismissToast,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
}
