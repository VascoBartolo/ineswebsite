import { useEffect } from 'react';

// Moves focus into a dialog when it opens and hands it back to whatever opened
// it when it closes, so keyboard users are never left on the page behind.
export function useDialogFocus(dialogRef) {
  useEffect(() => {
    const opener = document.activeElement;
    dialogRef.current?.querySelector('input, select, textarea, button')?.focus();
    return () => opener?.focus?.();
  }, [dialogRef]);
}
