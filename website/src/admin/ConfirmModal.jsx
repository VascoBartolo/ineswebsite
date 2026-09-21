import { useEffect, useId, useRef } from 'react';
import { useDialogFocus } from './useDialogFocus';

// Styled replacement for window.confirm(), matching the panel's modal layout.
// `danger` turns the confirm button red for irreversible actions; `children`
// holds any extra choice the action needs (e.g. whether to notify the client).
export default function ConfirmModal({
  title, body, confirmLabel = 'Confirmar', cancelLabel = 'Cancelar',
  danger = false, busy = false, onConfirm, onCancel, children,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const bodyId = useId();
  // Focus lands on the first control — never the confirm button — so a stray Enter cannot confirm.
  useDialogFocus(dialogRef);

  // Escape cancels, matching EditBookingModal. Ignored mid-request so a stray
  // keypress cannot dismiss the dialog while the action is in flight.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !busy) onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onCancel]);

  return (
    <div className="modal-backdrop" onClick={busy ? undefined : onCancel}>
      <div className="modal modal-sm" role="alertdialog" aria-modal="true" ref={dialogRef}
           aria-labelledby={titleId} aria-describedby={bodyId} onClick={(e) => e.stopPropagation()}>
        <h3 id={titleId}>{title}</h3>
        <p className="modal-note" id={bodyId}>{body}</p>
        {children}
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>{cancelLabel}</button>
          <button className={danger ? 'btn-red' : 'btn-ghost'} onClick={onConfirm} disabled={busy}>
            {busy ? 'A processar…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
