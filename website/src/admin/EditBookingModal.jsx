import { useState } from 'react';
import { adminApi } from './adminApi';

const FIELDS = [
  ['nome', 'Nome', 'text'], ['email', 'Email', 'email'], ['contacto', 'Contacto', 'text'],
  ['idade', 'Idade', 'text'], ['sujeito', 'Sujeito', 'text'], ['tipo_consulta', 'Tipo de consulta', 'text'],
  ['slot_date', 'Data', 'date'], ['slot_time', 'Hora', 'time'], ['price', 'Preço (€)', 'number'],
];

export default function EditBookingModal({ booking, onClose, onSaved }) {
  const [form, setForm] = useState({ ...booking });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [askSend, setAskSend] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Always saves to the DB and reconciles the Google Calendar; `notify` decides
  // whether the client is emailed the updated details.
  const save = async (notify) => {
    setBusy(true); setErr('');
    try {
      await adminApi.editBooking(booking.reference, {
        ...form,
        price: Number(form.price),
        duration_minutes: Number(form.duration_minutes),
        notify,
      });
      onSaved();
    } catch { setErr('Não foi possível guardar.'); setBusy(false); setAskSend(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Editar {booking.reference}</h3>
        <div className="modal-grid">
          {FIELDS.map(([k, label, type]) => (
            <div className="fld" key={k}><label>{label}</label>
              <input type={type} value={form[k] ?? ''} onChange={set(k)} /></div>
          ))}
          <div className="fld"><label>Regime</label>
            <select value={form.regime} onChange={set('regime')}>
              <option value="presencial">Presencial</option><option value="online">Online</option>
            </select></div>
          <div className="fld"><label>Duração</label>
            <select value={form.duration_minutes} onChange={set('duration_minutes')}>
              <option value={60}>1h</option><option value={90}>1h30</option>
            </select></div>
          {form.regime === 'presencial' && (
            <div className="fld"><label>Local</label>
              <input value={form.local_consulta ?? ''} onChange={set('local_consulta')} /></div>
          )}
          <div className="fld"><label>Estado</label>
            <select value={form.status} onChange={set('status')}>
              <option value="pendente">Pendente</option><option value="confirmado">Confirmado</option><option value="revisao">Necessita Alteração</option><option value="cancelado">Cancelado</option>
            </select></div>
        </div>
        {err && <p className="modal-err">{err}</p>}
        {!askSend ? (
          <>
            <p className="modal-note">Ao guardar, a alteração é refletida automaticamente no Google Calendar.</p>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={onClose}>Cancelar</button>
              <button className="btn-red" onClick={() => setAskSend(true)} disabled={busy}>Guardar</button>
            </div>
          </>
        ) : (
          <>
            <p className="modal-note">Enviar um email ao cliente com os novos detalhes da marcação?</p>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setAskSend(false)} disabled={busy}>Voltar</button>
              <button className="btn-ghost" onClick={() => save(false)} disabled={busy}>{busy ? 'A guardar…' : 'Guardar sem email'}</button>
              <button className="btn-red" onClick={() => save(true)} disabled={busy}>{busy ? 'A guardar…' : 'Sim, enviar email'}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
