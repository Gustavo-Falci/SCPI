import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import { ErrorToast, ToastData, ToastType } from "../components/ErrorToast";
import { friendlyErrorMessage } from "../services/errorMessages";

interface ToastApi {
  showError: (message: string | unknown, title?: string) => void;
  showSuccess: (message: string, title?: string) => void;
  showWarning: (message: string, title?: string) => void;
  showInfo: (message: string, title?: string) => void;
  showToast: (type: ToastType, message: string, title?: string, duration?: number) => void;
  /** Conveniência: aceita um Error e mostra a mensagem amigável. */
  showApiError: (err: unknown, fallback?: string) => void;
  dismissToast: () => void;
}

const ErrorToastContext = createContext<ToastApi | null>(null);

/**
 * Provider global de toasts mobile. Renderiza um único <ErrorToast />
 * no topo da árvore — toasts subsequentes substituem o atual.
 *
 * Uso (em app/_layout.tsx):
 *   <ErrorToastProvider>{children}</ErrorToastProvider>
 */
export function ErrorToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastData | null>(null);
  const idRef = useRef(0);

  const dismissToast = useCallback(() => setToast(null), []);

  const handleDismissed = useCallback((id: number) => {
    setToast((current) => (current?.id === id ? null : current));
  }, []);

  const showToast = useCallback(
    (type: ToastType, message: string, title?: string, duration?: number) => {
      idRef.current += 1;
      setToast({
        id: idRef.current,
        type,
        message,
        title,
        duration,
      });
    },
    []
  );

  const showError = useCallback(
    (message: string | unknown, title?: string) => {
      const msg =
        typeof message === "string" ? message : friendlyErrorMessage(message);
      showToast("error", msg, title);
    },
    [showToast]
  );

  const showSuccess = useCallback(
    (message: string, title?: string) => showToast("success", message, title),
    [showToast]
  );

  const showWarning = useCallback(
    (message: string, title?: string) => showToast("warning", message, title),
    [showToast]
  );

  const showInfo = useCallback(
    (message: string, title?: string) => showToast("info", message, title),
    [showToast]
  );

  const showApiError = useCallback(
    (err: unknown, fallback?: string) => {
      const msg = friendlyErrorMessage(err, fallback);
      showToast("error", msg);
    },
    [showToast]
  );

  const value: ToastApi = {
    showError,
    showSuccess,
    showWarning,
    showInfo,
    showToast,
    showApiError,
    dismissToast,
  };

  return React.createElement(
    ErrorToastContext.Provider,
    { value },
    children,
    React.createElement(ErrorToast, { toast, onDismiss: handleDismissed })
  );
}

/**
 * Hook para acessar o sistema de toasts em qualquer tela.
 *
 * Exemplo:
 *   const { showError, showSuccess } = useErrorToast();
 *   try { ... } catch (e) { showError(e); }
 */
export function useErrorToast(): ToastApi {
  const ctx = useContext(ErrorToastContext);
  if (!ctx) {
    throw new Error(
      "useErrorToast precisa estar dentro de <ErrorToastProvider />. " +
        "Adicione o provider em app/_layout.tsx."
    );
  }
  return ctx;
}
