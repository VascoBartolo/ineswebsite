import { useEffect, useRef, useState } from 'react';
import { adminApi } from './adminApi';
import { useDialogFocus } from './useDialogFocus';
import { CLINICS, CONSULTATION_TYPE_GROUPS, ALL_CONSULTATION_TYPE_IDS } from '../constants/booking';

const FIELDS = [
  ['nome', 'Nome', 'text'], ['email', 'Email', 'email'], ['contacto', 'Contacto', 'text'],
  ['idade', 'Idade', 'text'], ['sujeito', 'Sujeito', 'sujeito'], ['tipo_consulta', 'Tipo de consulta', 'consulta'],
  ['slot_date', 'Data', 'date'], ['slot_time', 'Hora', 'time'], ['price', 'Preço (€)', 'number'],
];

// The same two subjects the public form offers; any other stored value is kept
// as its own option (see unlistedSujeito) so opening the modal never rewrites it.
const SUJEITO_OPTIONS = [['adulto', 'Adulto'], ['bebé', 'Bebé / Criança']];

// Labels for every field the server can report as missing, so the error names
// what the admin sees on screen rather than the column name.
const LABELS = {
  ...Object.fromEntries(FIELDS.map(([k, label]) => [k, label])),
  regime: 'Regime', duration_minutes: 'Duração', local_consulta: 'Local', status: 'Estado',
  is_first: 'Primeira / Seguimento',
};

// Turns the server's validation answer into a sentence naming the field as it
// appears on screen.
function saveErrorMessage(body) {
  const name = LABELS[body?.field] || body?.field;
  switch (body?.error) {
    case 'missing_fields':
      return `Preencha: ${(body.fields || []).map((f) => LABELS[f] || f).join(', ')}.`;
    case 'empty_field':
      return `Preencha: ${name}.`;
    case 'invalid_email':
      return 'Email inválido.';
    case 'field_too_long':
      return `${name}: texto demasiado longo.`;
    case 'invalid_fields':
      return 'Verifique a data, a hora, a duração e o preço.';
    case 'capture_failed':
      return 'Não foi possível cobrar o pagamento (a cativação pode ter expirado), pelo que a marcação não foi confirmada.';
    case 'payments_unavailable':
      return 'Os pagamentos online não estão configurados.';
    case 'payment_error':
      return `Não foi possível criar o link de pagamento${body.message ? `: ${body.message}` : '.'}`;
    default:
      if (body?.error?.startsWith('invalid_') && name) return `Valor inválido em: ${name}.`;
      return 'Não foi possível guardar.';
  }
}

// A blank booking. Price is deliberately left empty: defaulting it would let a
// consultation be saved at the wrong price without anyone choosing one.
const EMPTY = {
  nome: '', email: '', contacto: '', idade: '', sujeito: '', tipo_consulta: '',
  slot_date: '', slot_time: '', price: '', regime: 'presencial',
  duration_minutes: 60, local_consulta: '', status: 'confirmado', is_first: '',
};

// Same rule as the public form and compute_price: online is always 50€; presencial
// is 55€ for a first consultation, 50€ otherwise. 60 min for a first, 45 for a follow-up.
function withDefaults(f) {
  const price = f.regime === 'online' ? 50 : f.is_first === 'true' ? 55 : 50;
  const duration = f.is_first === 'true' ? 60 : f.is_first === 'false' ? 45 : f.duration_minutes;
  return { ...f, price, duration_minutes: duration };
}

export default function EditBookingModal({ booking, create = false, locations = [], onClose, onSaved, onRefund }) {
  const [form, setForm] = useState(() => {
    const base = create ? EMPTY : booking;
    // A <select> holds strings; is_first travels as true/false/null.
    return { ...base, is_first: base.is_first === true ? 'true' : base.is_first === false ? 'false' : '' };
  });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [askSend, setAskSend] = useState(false);
  const [payLink, setPayLink] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [copied, setCopied] = useState(false);
  const withLink = create && payLink && form.regime === 'online';
  // Once the link exists the booking is saved, so any close must refresh the list.
  const close = linkUrl ? onSaved : onClose;
  const set = (k) => (e) => setForm((f) => {
    const next = { ...f, [k]: e.target.value };
    // Only a new booking is priced automatically; an existing one keeps what was agreed.
    return create && ['tipo_consulta', 'regime', 'is_first'].includes(k) ? withDefaults(next) : next;
  });
  const dialogRef = useRef(null);
  useDialogFocus(dialogRef);

  // Escape closes the modal, matching the backdrop click. Ignored mid-save so a
  // stray keypress cannot dismiss the dialog while a request is in flight.
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !busy) close(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, close]);

  // A booking may already hold a type this list no longer offers (an older name,
  // or one typed by hand). Show it as its own option so opening the modal cannot
  // silently rewrite it.
  const currentType = form.tipo_consulta ?? '';
  const unlistedType = currentType && !ALL_CONSULTATION_TYPE_IDS.includes(currentType) ? currentType : null;
  const currentSujeito = form.sujeito ?? '';
  const unlistedSujeito = currentSujeito && !SUJEITO_OPTIONS.some(([v]) => v === currentSujeito) ? currentSujeito : null;

  // Suggestions only — the input stays free text, so a one-off location is fine.
  const localSuggestions = [...new Set([...CLINICS, ...locations])];

  // Always writes to the DB and reconciles the Google Calendar; `notify` decides
  // whether the client is emailed the details.
  const save = async (notify) => {
    setBusy(true); setErr('');
    const payload = {
      ...form,
      // Blank stays blank, so the server reports it missing; Number('') would save 0€.
      price: form.price === '' ? '' : Number(form.price),
      duration_minutes: Number(form.duration_minutes),
      // '' means "not recorded" and must stay null, not collapse to false.
      is_first: form.is_first === '' ? null : form.is_first === 'true',
      notify,
      payment_link: withLink,
    };
    try {
      if (create) {
        const res = await adminApi.createBooking(payload);
        // Keep the modal open so she can copy the link to send it.
        if (res.payment_url) { setLinkUrl(res.payment_url); setBusy(false); return; }
      } else await adminApi.editBooking(booking.reference, payload);
      onSaved();
    } catch (e) {
      setErr(saveErrorMessage(e?.body));
      setBusy(false); setAskSend(false);
    }
  };

  return (
    // A click on the backdrop itself closes (Escape is the keyboard equivalent);
    // inert mid-save, like Escape, so a stray click cannot discard edits in flight.
    <div className="modal-backdrop" role="presentation"
         onClick={(e) => { if (e.target === e.currentTarget && !busy) close(); }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="edit-modal-title"
           ref={dialogRef}>
        <h3 id="edit-modal-title">{create ? 'Nova marcação' : `Editar ${booking.reference}`}</h3>
        <div className="modal-body">
        <div className="modal-grid">
          {FIELDS.map(([k, label, type]) => (
            <div className="fld" key={k}><label htmlFor={`em-${k}`}>{label}</label>
              {type === 'consulta' ? (
                <select id={`em-${k}`} value={currentType} onChange={set(k)}>
                  <option value="">Selecione…</option>
                  {unlistedType && <option value={unlistedType}>{unlistedType}</option>}
                  {CONSULTATION_TYPE_GROUPS.map((g) => (
                    <optgroup key={g.label} label={g.label}>
                      {g.options.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                    </optgroup>
                  ))}
                </select>
              ) : type === 'sujeito' ? (
                <select id={`em-${k}`} value={currentSujeito} onChange={set(k)}>
                  <option value="">Selecione…</option>
                  {unlistedSujeito && <option value={unlistedSujeito}>{unlistedSujeito}</option>}
                  {SUJEITO_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              ) : (
                <input id={`em-${k}`} type={type} value={form[k] ?? ''} onChange={set(k)} />
              )}</div>
          ))}
          <div className="fld"><label htmlFor="em-regime">Regime</label>
            <select id="em-regime" value={form.regime} onChange={set('regime')}>
              <option value="presencial">Presencial</option><option value="online">Online</option>
            </select></div>
          <div className="fld"><label htmlFor="em-duration">Duração</label>
            <select id="em-duration" value={form.duration_minutes} onChange={set('duration_minutes')}>
              <option value={45}>45m</option><option value={60}>1h</option><option value={90}>1h30</option>
            </select></div>
          {form.regime === 'presencial' && (
            <div className="fld"><label htmlFor="em-local">Local</label>
              <input id="em-local" list="local-consulta-opts" value={form.local_consulta ?? ''} onChange={set('local_consulta')} />
              <datalist id="local-consulta-opts">
                {localSuggestions.map((l) => <option key={l} value={l} />)}
              </datalist></div>
          )}
          <div className="fld"><label htmlFor="em-first">Primeira / Seguimento</label>
            <select id="em-first" value={form.is_first} onChange={set('is_first')}>
              <option value="">Não registado</option>
              <option value="true">Primeira consulta</option>
              <option value="false">Consulta de seguimento</option>
            </select></div>
          {!withLink && <div className="fld"><label htmlFor="em-status">Estado</label>
            <select id="em-status" value={form.status} onChange={set('status')}>
              <option value="pendente">Pendente</option><option value="confirmado">Confirmado</option><option value="revisao">Necessita Alteração</option><option value="cancelado">Cancelado</option>
            </select></div>}
        </div>
        {create && form.regime === 'online' && (
          <label htmlFor="em-paylink" className={`modal-option${payLink ? ' on' : ''}`}>
            <input id="em-paylink" type="checkbox" checked={payLink} onChange={(e) => setPayLink(e.target.checked)} disabled={busy || !!linkUrl} />
            <strong>Criar link de pagamento</strong>
            <span className="sub">A consulta só fica confirmada após o pagamento. Se não for paga em 24h, é cancelada e o horário libertado.</span>
          </label>
        )}
        {booking?.payment_status === 'authorized' && (
          <p className="modal-note">Pagamento cativo: ao guardar como <strong>Confirmado</strong>, o valor é cobrado ao cliente.</p>
        )}
        </div>
        <div className="modal-foot">
        {err && <p className="modal-err" role="alert">{err}</p>}
        {linkUrl ? (
          <>
            <p className="modal-note">Marcação criada, a aguardar pagamento. Envie este link ao cliente (válido 24h):</p>
            <input aria-label="Link de pagamento" readOnly value={linkUrl} style={{ width: '100%' }} onFocus={(e) => e.target.select()} />
            <div className="modal-actions">
              <button className="btn-ghost" onClick={async () => {
                try { await navigator.clipboard.writeText(linkUrl); setCopied(true); } catch { /* the field stays selectable */ }
              }}>{copied ? 'Copiado ✓' : 'Copiar link'}</button>
              <button className="btn-red" onClick={onSaved}>Fechar</button>
            </div>
          </>
        ) : !askSend ? (
          <>
            <p className="modal-note">
              {withLink
                ? 'O horário fica reservado e o evento no Google Calendar é criado quando o cliente pagar.'
                : create
                ? 'A marcação é criada sem verificar a disponibilidade do horário, e é refletida automaticamente no Google Calendar.'
                : 'Ao guardar, a alteração é refletida automaticamente no Google Calendar.'}
            </p>
            <div className="modal-actions">
              <button className="btn-ghost" onClick={onClose}>Cancelar</button>
              {!create && booking.refundable > 0 && onRefund && (
                <button className="btn-ghost" onClick={onRefund} disabled={busy}>Reembolsar</button>
              )}
              <button className="btn-red" onClick={() => setAskSend(true)} disabled={busy}>{create ? 'Criar' : 'Guardar'}</button>
            </div>
          </>
        ) : (
          <>
            <p className="modal-note">
              {withLink
                ? 'Enviar também o link de pagamento por email ao cliente?'
                : create
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
    </div>
  );
}
