import React, { createContext, useContext } from 'react';
import { Toast } from '../components/ui/Toast';
import { useToast } from '../hooks/useToast';

const ToastContext = createContext(null);

/**
 * Provider que expõe a API de toasts a toda a árvore.
 * Renderiza o container `<Toast />` automaticamente.
 */
export function ToastProvider({ children }) {
  const toastApi = useToast();

  return (
    <ToastContext.Provider value={toastApi}>
      <Toast toasts={toastApi.toasts} onDismiss={toastApi.dismissToast} />
      {children}
    </ToastContext.Provider>
  );
}

/**
 * Acesso global ao sistema de toasts.
 * Uso:
 *   const { showToast, showError, showSuccess } = useToastContext();
 */
export function useToastContext() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToastContext precisa estar dentro de ToastProvider');
  }
  return ctx;
}
