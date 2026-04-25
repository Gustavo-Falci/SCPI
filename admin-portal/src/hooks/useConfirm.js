import { useState, useCallback } from 'react';

export function useConfirm() {
  const [confirmDialog, setConfirmDialog] = useState({
    show: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  const showConfirm = useCallback((title, message, onConfirmFn) => {
    setConfirmDialog({ show: true, title, message, onConfirm: onConfirmFn });
  }, []);

  const dismissConfirm = useCallback(() => {
    setConfirmDialog((d) => ({ ...d, show: false }));
  }, []);

  const handleConfirm = useCallback(() => {
    const fn = confirmDialog.onConfirm;
    setConfirmDialog((d) => ({ ...d, show: false }));
    fn?.();
  }, [confirmDialog.onConfirm]);

  return { confirmDialog, showConfirm, dismissConfirm, handleConfirm };
}
