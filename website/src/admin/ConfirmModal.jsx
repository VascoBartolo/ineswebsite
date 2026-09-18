import { useEffect } from 'react';

// Styled replacement for window.confirm(), matching the panel's modal layout.
// `danger` turns the confirm button red for irreversible actions.
export default function ConfirmModal({
  title, body, confirmLabel = 'Confirmar', cancelLabel = 'Cancelar',
  danger = false, busy = false, onConfirm, onCancel,
}) {
  // Escape cancels, matching EditBookingModal. Ignored mid-request so a stray
  // keypress cannot dismiss the dialog while the action is in flight.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !busy) onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onCancel]);

  return (
    <div className="modal-backdrop" onClick={busy ? undefined : onCancel}>
      <div className="modal modal-sm" role="alertdialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <p className="modal-note">{body}</p>
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
