import { useEffect, useState } from 'react';
import { adminApi } from './adminApi';
import { CLINICS, CONSULTATION_TYPE_GROUPS, ALL_CONSULTATION_TYPE_IDS } from '../constants/booking';

const FIELDS = [
  ['nome', 'Nome', 'text'], ['email', 'Email', 'email'], ['contacto', 'Contacto', 'text'],
  ['idade', 'Idade', 'text'], ['sujeito', 'Sujeito', 'text'], ['tipo_consulta', 'Tipo de consulta', 'consulta'],
  ['slot_date', 'Data', 'date'], ['slot_time', 'Hora', 'time'], ['price', 'Preço (€)', 'number'],
];

// Labels for every field the server can report as missing, so the error names
// what the admin sees on screen rather than the column name.
const LABELS = {
  ...Object.fromEntries(FIELDS.map(([k, label]) => [k, label])),
  regime: 'Regime', duration_minutes: 'Duração', local_consulta: 'Local', status: 'Estado',
  is_first: 'Primeira / Seguimento',
};

// A blank booking. Price is deliberately left empty: defaulting it would let a
// consultation be saved at the wrong price without anyone choosing one.
const EMPTY = {
  nome: '', email: '', contacto: '', idade: '', sujeito: '', tipo_consulta: '',
  slot_date: '', slot_time: '', price: '', regime: 'presencial',
  duration_minutes: 60, local_consulta: '', status: 'confirmado', is_first: '',
};

export default function EditBookingModal({ booking, create = false, locations = [], onClose, onSaved }) {
  const [form, setForm] = useState(() => {
    const base = create ? EMPTY : booking;
    // A <select> holds strings; is_first travels as true/false/null.
    return { ...base, is_first: base.is_first === true ? 'true' : base.is_first === false ? 'false' : '' };
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [askSend, setAskSend] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Escape closes the modal, matching the backdrop click. Ignored mid-save so a
  // stray keypress cannot dismiss the dialog while a request is in flight.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !busy) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  // A booking may already hold a type this list no longer offers (an older name,
  // or one typed by hand). Show it as its own option so opening the modal cannot
  // silently rewrite it.
  const currentType = form.tipo_consulta ?? '';
  const unlistedType = currentType && !ALL_CONSULTATION_TYPE_IDS.includes(currentType) ? currentType : null;

  // Suggestions only — the input stays free text, so a one-off location is fine.
  const localSuggestions = [...new Set([...CLINICS, ...locations])];

  // Always writes to the DB and reconciles the Google Calendar; `notify` decides
  // whether the client is emailed the details.
  const save = async (notify) => {
    setBusy(true); setErr('');
    const payload = {
      ...form,
      price: Number(form.price),
      duration_minutes: Number(form.duration_minutes),
      // '' means "not recorded" and must stay null, not collapse to false.
      is_first: form.is_first === '' ? null : form.is_first === 'true',
      notify,
    };
    try {
      if (create) await adminApi.createBooking(payload);
      else await adminApi.editBooking(booking.reference, payload);
      onSaved();
    } catch (e) {
      const missing = e?.body?.fields;
      setErr(missing?.length
        ? `Preencha: ${missing.map((f) => LABELS[f] || f).join(', ')}.`
        : 'Não foi possível guardar.');
      setBusy(false); setAskSend(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{create ? 'Nova marcação' : `Editar ${booking.reference}`}</h3>
        <div className="modal-grid">
          {FIELDS.map(([k, label, type]) => (
            <div className="fld" key={k}><label>{label}</label>
              {type === 'consulta' ? (
                <select value={currentType} onChange={set(k)}>
                  <option value="">Selecione…</option>
                  {unlistedType && <option value={unlistedType}>{unlistedType}</option>}
                  {CONSULTATION_TYPE_GROUPS.map((g) => (
                    <optgroup key={g.label} label={g.label}>
                      {g.options.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                    </optgroup>
                  ))}
                </select>
              ) : (
                <input type={type} value={form[k] ?? ''} onChange={set(k)} />
              )}</div>
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
              <input list="local-consulta-opts" value={form.local_consulta ?? ''} onChange={set('local_consulta')} />
              <datalist id="local-consulta-opts">
                {localSuggestions.map((l) => <option key={l} value={l} />)}
              </datalist></div>
          )}
          <div className="fld"><label>Primeira / Seguimento</label>
            <select value={form.is_first} onChange={set('is_first')}>
              <option value="">Não registado</option>
              <option value="true">Primeira consulta</option>
              <option value="false">Consulta de seguimento</option>
            </select></div>
          <div className="fld"><label>Estado</label>
            <select value={form.status} onChange={set('status')}>
              <option value="pendente">Pendente</option><option value="confirmado">Confirmado</option><option value="revisao">Necessita Alteração</option><option value="cancelado">Cancelado</option>
            </select></div>
        </div>
        {err && <p className="modal-err">{err}</p>}
        {!askSend ? (
          <>
            <p className="modal-note">
              {create
                ? 'A marcação é criada sem verificar a disponibilidade do horário, e é refletida automaticamente no Google Calendar.'
                : 'Ao guardar, a alteração é refletida automaticamente no Google Calendar.'}
            </p>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={onClose}>Cancelar</button>
              <button className="btn-red" onClick={() => setAskSend(true)} disabled={busy}>{create ? 'Criar' : 'Guardar'}</button>
            </div>
          </>
        ) : (
          <>
            <p className="modal-note">
              {create
                ? 'Enviar um email ao cliente com os detalhes da marcação?'
                : 'Enviar um email ao cliente com os novos detalhes da marcação?'}
            </p>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setAskSend(false)} disabled={busy}>Voltar</button>
              <button className="btn-ghost" onClick={() => save(false)} disabled={busy}>{busy ? 'A guardar…' : (create ? 'Criar sem email' : 'Guardar sem email')}</button>
              <button className="btn-red" onClick={() => save(true)} disabled={busy}>{busy ? 'A guardar…' : 'Sim, enviar email'}</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
