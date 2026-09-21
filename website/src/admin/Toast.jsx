import { useEffect } from 'react';

// Transient confirmation that a change was saved; dismisses itself. `toast` is
// {message, tone} or null — tone 'err' is styled as a failure so a problem is
// never shown in the same colour as a success.
export default function Toast({ toast, onDone, duration = 3200 }) {
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(onDone, duration);
    return () => clearTimeout(t);
  }, [toast, onDone, duration]);

  if (!toast) return null;
  return (
    <div className={`toast ${toast.tone === 'err' ? 'toast-err' : 'toast-ok'}`}
         role="status" aria-live="polite">
      {toast.message}
    </div>
  );
}
