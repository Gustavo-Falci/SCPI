import { useState, useCallback } from 'react';

export function useToast() {
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });

  const showToast = useCallback((message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => setToast((t) => ({ ...t, show: false })), 3500);
  }, []);

  const dismissToast = useCallback(() => {
    setToast((t) => ({ ...t, show: false }));
  }, []);

  return { toast, showToast, dismissToast };
}
