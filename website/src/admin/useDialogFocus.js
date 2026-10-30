import { useEffect } from 'react';

// Moves focus into a dialog when it opens and hands it back to whatever opened
// it when it closes, so keyboard users are never left on the page behind. The
// page behind also stops scrolling while the dialog is open.
export function useDialogFocus(dialogRef) {
  useEffect(() => {
    const opener = document.activeElement;
    // The page scrolls on <html> (overflow-y: auto there), not on <body>.
    const root = document.documentElement;
    const overflow = root.style.overflow;
    root.style.overflow = 'hidden';
    dialogRef.current?.querySelector('input, select, textarea, button')?.focus();
    return () => { root.style.overflow = overflow; opener?.focus?.(); };
  }, [dialogRef]);
}
