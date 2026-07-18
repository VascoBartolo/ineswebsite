import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Clock, Euro, MapPin, Monitor, User, CheckCircle } from 'lucide-react';
import './BookingPage.css';

// ---- Constants ----

const CONSULTATION_TYPES = {
  adulto: [
    { id: 'consulta de pré-concepção', label: 'Consulta de Pré-concepção', intro: true },
    { id: 'consulta na gravidez', label: 'Consulta na Gravidez', intro: false },
    { id: 'consulta no pós-parto', label: 'Consulta no Pós-Parto', intro: false },
    { id: 'consulta gestão de peso', label: 'Consulta de Gestão de Peso', intro: false },
  ],
  bebé: [
    { id: 'introdução alimentar', label: 'Introdução Alimentar', intro: true },
    { id: 'seletividade alimentar', label: 'Seletividade Alimentar', intro: false },
    { id: 'nutrição pediátrica', label: 'Nutrição Pediátrica', intro: false },
  ],
};

const CLINICS = [
  'Clínica Manus (Angra do Heroísmo)',
  'Centro de Psicologia Flávia Bessa (Angra do Heroísmo)',
];

function getPrice(isFirst, regime) {
  if (!regime) return null;
  if (regime.toLowerCase() === 'presencial') return isFirst ? 55 : 50;
  return 50; // online: always 50€
}

function getDuration(sujeito, isFirst) {
  if (sujeito === 'bebé' && isFirst) return 90;
  return 60;
}

function fmtDuration(min) {
  return min === 90 ? '1h30m' : '1h';
}

const MONTH_NAMES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
const DAY_NAMES_SHORT = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
const WEEKDAY_NAMES = ['Domingo','Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sábado'];

function fmtDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T12:00:00');
  return `${WEEKDAY_NAMES[d.getDay()]}, ${d.getDate()} de ${MONTH_NAMES[d.getMonth()].toLowerCase()} de ${d.getFullYear()}`;
}

// ---- Calendar Component ----

function CalendarPicker({ selectedDate, onSelect }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); }
    else setViewMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); }
    else setViewMonth(m => m + 1);
  };

  const firstDay = new Date(viewYear, viewMonth, 1);
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const startOffset = firstDay.getDay();

  const cells = [];
  for (let i = 0; i < startOffset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(viewYear, viewMonth, d));

  const isWeekend = d => d.getDay() === 0 || d.getDay() === 6;
  const isPast = d => d < today;
  const isSel = d => selectedDate && d.toISOString().split('T')[0] === selectedDate;
  const isTdy = d => d.getTime() === today.getTime();

  const canGoPrev = () => {
    const cur = new Date(viewYear, viewMonth, 1);
    const now = new Date(today.getFullYear(), today.getMonth(), 1);
    return cur > now;
  };

  return (
    <div className="cal-picker">
      <div className="cal-header">
        <button className="cal-nav" onClick={prevMonth} type="button" disabled={!canGoPrev()}>‹</button>
        <span className="cal-month-label">{MONTH_NAMES[viewMonth]} {viewYear}</span>
        <button className="cal-nav" onClick={nextMonth} type="button">›</button>
      </div>
      <div className="cal-grid">
        {DAY_NAMES_SHORT.map(d => <div key={d} className="cal-day-header">{d}</div>)}
        {cells.map((d, i) => {
          const disabled = !d || isWeekend(d) || isPast(d);
          return (
            <div
              key={i}
              className={[
                'cal-cell',
                !d ? 'cal-empty' : '',
                disabled ? 'cal-disabled' : 'cal-available',
                d && isSel(d) ? 'cal-selected' : '',
                d && isTdy(d) && !isSel(d) ? 'cal-today' : '',
              ].join(' ').trim()}
              onClick={() => !disabled && d && onSelect(d.toISOString().split('T')[0])}
            >
              {d ? d.getDate() : ''}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---- Step Indicator ----

const STEP_LABELS = ['Consulta', 'Regime', 'Data & Hora', 'Dados Pessoais'];

function StepIndicator({ current, total }) {
  return (
    <div className="step-indicator">
      {Array.from({ length: total }, (_, i) => i + 1).map(s => (
        <div key={s} className="step-item">
          <div className={`step-circle ${s < current ? 'done' : ''} ${s === current ? 'active' : ''}`}>
            {s < current ? <CheckCircle size={16} /> : s}
          </div>
          <span className={`step-label ${s === current ? 'active' : ''}`}>{STEP_LABELS[s - 1]}</span>
          {s < total && <div className={`step-line ${s < current ? 'done' : ''}`} />}
        </div>
      ))}
    </div>
  );
}

// ---- Booking Summary Bar ----

function SummaryBar({ form }) {
  const isFirst = form.primeiraConsulta === 'primeira';
  const price = getPrice(isFirst, form.regime);
  const duration = getDuration(form.sujeito, isFirst);
  const localLabel = form.regime === 'presencial' ? form.localConsulta : 'Online';
  return (
    <div className="summary-bar">
      <span className="summary-item">{form.tipoConsulta}</span>
      {localLabel && <><span className="summary-sep">·</span><span className="summary-item">{localLabel}</span></>}
      {form.slotDate && (
        <><span className="summary-sep">·</span><span className="summary-item">{fmtDate(form.slotDate)}{form.slotTime ? ` às ${form.slotTime}` : ''}</span></>
      )}
      {price && <span className="summary-price">{price}€ · {fmtDuration(duration)}</span>}
    </div>
  );
}

// ---- Main Component ----

const TOTAL_STEPS = 4;

const emptyForm = {
  sujeito: '',
  tipoConsulta: '',
  primeiraConsulta: '', // 'primeira' | 'seguimento'
  regime: '',
  localConsulta: '',
  slotDate: '',
  slotTime: '',
  nome: '',
  idade: '',
  email: '',
  contacto: '',
  contexto: '',
};

export default function BookingPage() {
  const [activeTab, setActiveTab] = useState('nova');

  // Booking form state
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(emptyForm);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [formError, setFormError] = useState('');

  // Lookup state
  const [lookupRef, setLookupRef] = useState('');
  const [lookupEmail, setLookupEmail] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editMessage, setEditMessage] = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const [editSent, setEditSent] = useState(false);

  const isFirst = form.primeiraConsulta === 'primeira';
  const price = getPrice(isFirst, form.regime);
  const duration = getDuration(form.sujeito, isFirst);
  const consultTypes = form.sujeito ? CONSULTATION_TYPES[form.sujeito] : [];

  useEffect(() => {
    if (form.slotDate && form.primeiraConsulta && form.regime) {
      fetchSlots(form.slotDate, getDuration(form.sujeito, form.primeiraConsulta === 'primeira'), form.regime, form.localConsulta);
    }
  }, [form.slotDate, form.sujeito, form.primeiraConsulta, form.regime, form.localConsulta]);

  async function fetchSlots(dateStr, dur, regime, localConsulta) {
    setLoadingSlots(true);
    setAvailableSlots([]);
    setForm(prev => ({ ...prev, slotTime: '' }));
    try {
      const params = new URLSearchParams({ date: dateStr, duration: dur });
      if (regime) params.set('regime', regime);
      if (localConsulta) params.set('local_consulta', localConsulta);
      const res = await fetch(`/api/availability?${params}`);
      const data = await res.json();
      setAvailableSlots(data.slots || []);
    } catch {
      setAvailableSlots([]);
    } finally {
      setLoadingSlots(false);
    }
  }

  function canProceed() {
    if (step === 1) return !!(form.sujeito && form.tipoConsulta && form.primeiraConsulta);
    if (step === 2) return !!(form.regime && (form.regime === 'online' || form.localConsulta));
    if (step === 3) return !!(form.slotDate && form.slotTime);
    if (step === 4) return !!(form.nome && form.idade && form.email && form.contacto);
    return false;
  }

  function setField(key, value) {
    setForm(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    setSubmitting(true);
    setFormError('');
    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sujeito: form.sujeito,
          tipo_consulta: form.tipoConsulta,
          is_first: form.primeiraConsulta === 'primeira',
          regime: form.regime,
          local_consulta: form.localConsulta || undefined,
          slot_date: form.slotDate,
          slot_time: form.slotTime,
          nome: form.nome,
          idade: parseInt(form.idade),
          email: form.email,
          contacto: form.contacto,
          contexto: form.contexto || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.error === 'slot_unavailable') {
          setFormError('Este horário já não está disponível. Por favor escolha outro.');
          setStep(3);
          fetchSlots(form.slotDate, duration, form.regime, form.localConsulta);
        } else {
          setFormError(data.message || 'Erro ao processar a marcação. Tente novamente.');
        }
      } else {
        setConfirmedBooking(data.booking);
      }
    } catch {
      setFormError('Erro de ligação. Verifica a tua conexão e tenta novamente.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleLookup(e) {
    e.preventDefault();
    setLookupError('');
    setLookupResult(null);
    setLookupLoading(true);
    setCancelConfirm(false);
    setEditMode(false);
    setEditSent(false);
    try {
      const res = await fetch(`/api/bookings/lookup?reference=${encodeURIComponent(lookupRef)}&email=${encodeURIComponent(lookupEmail)}`);
      const data = await res.json();
      if (!res.ok) {
        setLookupError('Marcação não encontrada. Verifique a referência e o email.');
      } else {
        setLookupResult(data.booking);
      }
    } catch {
      setLookupError('Erro de ligação. Tente novamente.');
    } finally {
      setLookupLoading(false);
    }
  }

  async function handleCancel() {
    setCancelLoading(true);
    try {
      const res = await fetch(`/api/bookings/${lookupResult.reference}/cancel`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: lookupEmail }),
      });
      const data = await res.json();
      if (res.ok) {
        setLookupResult(data.booking);
        setCancelConfirm(false);
      } else {
        setLookupError(data.message || 'Erro ao cancelar.');
      }
    } catch {
      setLookupError('Erro de ligação.');
    } finally {
      setCancelLoading(false);
    }
  }

  async function handleEditRequest(e) {
    e.preventDefault();
    setEditLoading(true);
    try {
      const res = await fetch(`/api/bookings/${lookupResult.reference}/edit-request`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: lookupEmail, message: editMessage }),
      });
      if (res.ok) {
        setEditSent(true);
        setEditMode(false);
      } else {
        setLookupError('Erro ao enviar pedido.');
      }
    } catch {
      setLookupError('Erro de ligação.');
    } finally {
      setEditLoading(false);
    }
  }

  // ---- Success Screen ----

  if (confirmedBooking) {
    return (
      <div className="booking-page">
        <div className="booking-header">
          <div className="booking-header-inner">
            <Link to="/" className="back-link"><ArrowLeft size={16} /> Voltar ao início</Link>
            <img src="/images/vermelho.png" alt="IB Nutrição" className="booking-logo" />
          </div>
        </div>
        <div className="booking-container">
          <motion.div
            className="success-screen"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div className="success-check">✓</div>
            <h2 className="success-title">Consulta Marcada!</h2>
            <p className="success-subtitle">Receberás uma confirmação no teu email em breve.</p>

            <div className="success-ref-box">
              <span className="success-ref-label">Referência da consulta</span>
              <span className="success-ref">{confirmedBooking.reference}</span>
            </div>

            <div className="success-details">
              <div className="success-row"><span>Consulta</span><strong>{confirmedBooking.tipo_consulta}</strong></div>
              <div className="success-row"><span>Regime</span><strong>{confirmedBooking.regime}{confirmedBooking.local_consulta ? ` — ${confirmedBooking.local_consulta}` : ''}</strong></div>
              <div className="success-row"><span>Data</span><strong>{fmtDate(confirmedBooking.slot_date)}</strong></div>
              <div className="success-row"><span>Hora</span><strong>{confirmedBooking.slot_time}</strong></div>
              <div className="success-row"><span>Duração</span><strong>{fmtDuration(confirmedBooking.duration_minutes)}</strong></div>
              <div className="success-row"><span>Preço</span><strong>{confirmedBooking.price}€</strong></div>
            </div>

            <p className="success-note">
              Guarda a referência <strong>{confirmedBooking.reference}</strong> — é necessária para consultares ou alterares a tua marcação.
            </p>

            <div className="success-actions">
              <button
                className="btn-secondary"
                onClick={() => { setActiveTab('verificar'); setConfirmedBooking(null); setLookupRef(confirmedBooking.reference); setLookupEmail(confirmedBooking.email); }}
              >
                Ver detalhes da marcação
              </button>
              <Link to="/" className="btn-primary">Voltar ao início</Link>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  // ---- Main Page ----

  return (
    <div className="booking-page">
      <div className="booking-header">
        <div className="booking-header-inner">
          <Link to="/" className="back-link"><ArrowLeft size={16} /> Voltar ao início</Link>
          <img src="/images/vermelho.png" alt="IB Nutrição" className="booking-logo" />
        </div>
      </div>

      <div className="booking-hero">
        <span className="booking-eyebrow">IB Nutrição</span>
        <h1 className="booking-title">Marcar Consulta</h1>
        <p className="booking-subtitle">Consultas na gravidez, introdução alimentar, nutrição pediátrica e muito mais — presencialmente na Ilha Terceira ou online.</p>
      </div>

      <div className="booking-container">
        <div className="booking-tabs">
          <button className={`booking-tab ${activeTab === 'nova' ? 'active' : ''}`} onClick={() => setActiveTab('nova')}>
            Nova Marcação
          </button>
          <button className={`booking-tab ${activeTab === 'verificar' ? 'active' : ''}`} onClick={() => setActiveTab('verificar')}>
            Verificar / Cancelar
          </button>
        </div>

        <AnimatePresence mode="wait">
          {activeTab === 'nova' ? (

            // ======= BOOKING FORM =======
            <motion.div key="nova" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <StepIndicator current={step} total={TOTAL_STEPS} />

              <AnimatePresence mode="wait">
                <motion.div
                  key={step}
                  initial={{ opacity: 0, x: 24 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -24 }}
                  transition={{ duration: 0.28 }}
                  className="form-card"
                >

                  {/* ---- STEP 1: Consulta ---- */}
                  {step === 1 && (
                    <>
                      <h2 className="form-step-title">Sobre a Consulta</h2>

                      <div className="form-section">
                        <p className="field-label">Para quem é a consulta?</p>
                        <div className="choice-cards">
                          <button
                            type="button"
                            className={`choice-card ${form.sujeito === 'adulto' ? 'selected' : ''}`}
                            onClick={() => { setField('sujeito', 'adulto'); setField('tipoConsulta', ''); }}
                          >
                            <User size={28} strokeWidth={1.5} />
                            <span className="choice-label">Adulto</span>
                          </button>
                          <button
                            type="button"
                            className={`choice-card ${form.sujeito === 'bebé' ? 'selected' : ''}`}
                            onClick={() => { setField('sujeito', 'bebé'); setField('tipoConsulta', ''); }}
                          >
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="3"/><path d="M8 14s-3 0-3 3v1h14v-1c0-3-3-3-3-3H8z"/><path d="M9 8c0 0-.5-2 1-3 1-1 3-.5 3-.5"/></svg>
                            <span className="choice-label">Bebé/Criança</span>
                          </button>
                        </div>
                      </div>

                      {form.sujeito && (
                        <motion.div className="form-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                          <p className="field-label">Tipo de consulta</p>
                          <div className="radio-list">
                            {consultTypes.map(t => (
                              <label key={t.id} className={`radio-item ${form.tipoConsulta === t.id ? 'selected' : ''}`}>
                                <input
                                  type="radio"
                                  name="tipoConsulta"
                                  value={t.id}
                                  checked={form.tipoConsulta === t.id}
                                  onChange={() => setForm(prev => ({ ...prev, tipoConsulta: t.id, primeiraConsulta: '' }))}
                                />
                                <span className="radio-label">{t.label}</span>
                              </label>
                            ))}
                          </div>
                        </motion.div>
                      )}

                      {form.tipoConsulta && (
                        <motion.div className="form-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                          <p className="field-label">É uma primeira consulta ou consulta de seguimento?</p>
                          <div className="choice-cards">
                            <button
                              type="button"
                              className={`choice-card ${form.primeiraConsulta === 'primeira' ? 'selected' : ''}`}
                              onClick={() => setField('primeiraConsulta', 'primeira')}
                            >
                              <span className="choice-label">Primeira Consulta</span>
                              <span className="choice-sub">
                                Presencial 55€&nbsp;·&nbsp;Online 50€&nbsp;·&nbsp;{getDuration(form.sujeito, true) === 90 ? '1h30m' : '1h'}
                              </span>
                            </button>
                            <button
                              type="button"
                              className={`choice-card ${form.primeiraConsulta === 'seguimento' ? 'selected' : ''}`}
                              onClick={() => setField('primeiraConsulta', 'seguimento')}
                            >
                              <span className="choice-label">Consulta de Seguimento</span>
                              <span className="choice-sub">50€&nbsp;·&nbsp;1h</span>
                            </button>
                          </div>
                        </motion.div>
                      )}
                    </>
                  )}

                  {/* ---- STEP 2: Regime ---- */}
                  {step === 2 && (
                    <>
                      <h2 className="form-step-title">Regime & Local</h2>

                      <div className="form-section">
                        <p className="field-label">Modo da consulta</p>
                        <div className="choice-cards">
                          <button
                            type="button"
                            className={`choice-card ${form.regime === 'presencial' ? 'selected' : ''}`}
                            onClick={() => { setField('regime', 'presencial'); setField('localConsulta', ''); }}
                          >
                            <MapPin size={28} strokeWidth={1.5} />
                            <span className="choice-label">Presencial</span>
                            <span className="choice-sub">Ilha Terceira, Açores</span>
                          </button>
                          <button
                            type="button"
                            className={`choice-card ${form.regime === 'online' ? 'selected' : ''}`}
                            onClick={() => { setField('regime', 'online'); setField('localConsulta', ''); }}
                          >
                            <Monitor size={28} strokeWidth={1.5} />
                            <span className="choice-label">Online</span>
                            <span className="choice-sub">Todo o Portugal</span>
                          </button>
                        </div>
                      </div>

                      {form.regime === 'presencial' && (
                        <motion.div className="form-section" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                          <p className="field-label">Escolha a clínica</p>
                          <div className="radio-list">
                            {CLINICS.map(c => (
                              <label key={c} className={`radio-item ${form.localConsulta === c ? 'selected' : ''}`}>
                                <input
                                  type="radio"
                                  name="localConsulta"
                                  value={c}
                                  checked={form.localConsulta === c}
                                  onChange={() => setField('localConsulta', c)}
                                />
                                <span className="radio-label">{c}</span>
                              </label>
                            ))}
                          </div>
                        </motion.div>
                      )}

                      {form.regime && (
                        <motion.div className="price-card" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                          <div className="price-card-row">
                            <div className="price-card-item">
                              <Euro size={18} />
                              <span>Preço estimado</span>
                              <strong>{getPrice(isFirst, form.regime)}€</strong>
                            </div>
                            <div className="price-card-divider" />
                            <div className="price-card-item">
                              <Clock size={18} />
                              <span>Duração</span>
                              <strong>{fmtDuration(getDuration(form.sujeito, isFirst))}</strong>
                            </div>
                          </div>
                          <div className="price-card-note">
                            <span>Presencial: Primeira 55€ · Seguimento 50€</span>
                            <span>·</span>
                            <span>Online: sempre 50€</span>
                          </div>
                        </motion.div>
                      )}
                    </>
                  )}

                  {/* ---- STEP 3: Date & Time ---- */}
                  {step === 3 && (
                    <>
                      <h2 className="form-step-title">Data & Hora</h2>
                      <p className="form-step-sub">Disponibilidade: segunda a sexta-feira, das 16h00 às 19h00</p>

                      <div className="date-time-layout">
                        <div className="form-section">
                          <p className="field-label">Escolha uma data</p>
                          <CalendarPicker
                            selectedDate={form.slotDate}
                            onSelect={d => setField('slotDate', d)}
                          />
                        </div>

                        <div className="form-section slots-section">
                          <p className="field-label">
                            {form.slotDate ? `Horários — ${fmtDate(form.slotDate)}` : 'Selecione uma data para ver os horários'}
                          </p>
                          {!form.slotDate && (
                            <div className="slots-placeholder">
                              <Clock size={32} strokeWidth={1.2} />
                              <span>Escolha uma data à esquerda</span>
                            </div>
                          )}
                          {form.slotDate && loadingSlots && (
                            <div className="slots-loading">A verificar disponibilidade...</div>
                          )}
                          {form.slotDate && !loadingSlots && availableSlots.length === 0 && (
                            <div className="slots-empty">
                              Sem horários disponíveis para esta data.<br />Por favor escolha outro dia.
                            </div>
                          )}
                          {form.slotDate && !loadingSlots && availableSlots.length > 0 && (
                            <div className="slots-grid">
                              {availableSlots.map(slot => (
                                <button
                                  key={slot}
                                  type="button"
                                  className={`slot-btn ${form.slotTime === slot ? 'selected' : ''}`}
                                  onClick={() => setField('slotTime', slot)}
                                >
                                  {slot}
                                </button>
                              ))}
                            </div>
                          )}
                          {form.slotDate && !loadingSlots && (
                            <p className="slots-note">
                              Duração da consulta: <strong>{fmtDuration(duration)}</strong>
                            </p>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {/* ---- STEP 4: Personal Details ---- */}
                  {step === 4 && (
                    <>
                      <h2 className="form-step-title">Dados Pessoais</h2>
                      <SummaryBar form={form} />

                      <div className="personal-grid">
                        <div className="p-field">
                          <label>Nome completo <span className="req">*</span></label>
                          <input
                            type="text"
                            value={form.nome}
                            onChange={e => setField('nome', e.target.value)}
                            placeholder="Nome e apelido"
                          />
                        </div>
                        <div className="p-field">
                          <label>Idade <span className="req">*</span></label>
                          <input
                            type="number"
                            value={form.idade}
                            onChange={e => setField('idade', e.target.value)}
                            placeholder="Anos"
                            min="0"
                            max="120"
                          />
                        </div>
                        <div className="p-field">
                          <label>Email <span className="req">*</span></label>
                          <input
                            type="email"
                            value={form.email}
                            onChange={e => setField('email', e.target.value)}
                            placeholder="O teu email"
                          />
                        </div>
                        <div className="p-field">
                          <label>Contacto telefónico <span className="req">*</span></label>
                          <input
                            type="tel"
                            value={form.contacto}
                            onChange={e => setField('contacto', e.target.value)}
                            placeholder="+351 9XX XXX XXX"
                          />
                        </div>
                        <div className="p-field full-width">
                          <label>Contexto sobre a consulta <span className="optional">(opcional)</span></label>
                          <textarea
                            value={form.contexto}
                            onChange={e => setField('contexto', e.target.value)}
                            placeholder="Descreva brevemente o motivo da consulta, dúvidas ou informações relevantes..."
                            rows={4}
                          />
                        </div>
                      </div>

                      {formError && <div className="form-error-msg">{formError}</div>}
                    </>
                  )}

                </motion.div>
              </AnimatePresence>

              {/* Navigation */}
              <div className="form-nav">
                {step > 1 && (
                  <button type="button" className="btn-secondary" onClick={() => setStep(s => s - 1)}>
                    ← Anterior
                  </button>
                )}
                {step < TOTAL_STEPS ? (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={!canProceed()}
                    onClick={() => { setFormError(''); setStep(s => s + 1); }}
                  >
                    Seguinte →
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={!canProceed() || submitting}
                    onClick={handleSubmit}
                  >
                    {submitting ? 'A processar...' : 'Confirmar Marcação'}
                  </button>
                )}
              </div>
            </motion.div>

          ) : (

            // ======= LOOKUP TAB =======
            <motion.div key="verificar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="lookup-wrapper">
                <h2 className="lookup-title">Verificar Marcação</h2>
                <p className="lookup-sub">Introduza a referência (ex: IB-XXXXXXXX) e o email utilizado na marcação.</p>

                <form className="lookup-form" onSubmit={handleLookup}>
                  <div className="p-field">
                    <label>Referência</label>
                    <input
                      type="text"
                      value={lookupRef}
                      onChange={e => setLookupRef(e.target.value.toUpperCase())}
                      placeholder="IB-XXXXXXXX"
                      required
                    />
                  </div>
                  <div className="p-field">
                    <label>Email</label>
                    <input
                      type="email"
                      value={lookupEmail}
                      onChange={e => setLookupEmail(e.target.value)}
                      placeholder="O email usado na marcação"
                      required
                    />
                  </div>
                  {lookupError && <div className="form-error-msg">{lookupError}</div>}
                  <button type="submit" className="btn-primary" disabled={lookupLoading}>
                    {lookupLoading ? 'A procurar...' : 'Verificar'}
                  </button>
                </form>

                {lookupResult && (
                  <motion.div
                    className="lookup-result"
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="lr-header">
                      <span className="lr-ref">{lookupResult.reference}</span>
                      <span className={`lr-status ${lookupResult.status}`}>
                        {lookupResult.status === 'confirmado' ? 'Confirmado' : 'Cancelado'}
                      </span>
                    </div>

                    <div className="lr-grid">
                      <div className="lr-row"><span>Nome</span><strong>{lookupResult.nome}</strong></div>
                      <div className="lr-row"><span>Consulta</span><strong>{lookupResult.tipo_consulta}</strong></div>
                      <div className="lr-row"><span>Regime</span><strong>{lookupResult.regime}{lookupResult.local_consulta ? ` — ${lookupResult.local_consulta}` : ''}</strong></div>
                      <div className="lr-row"><span>Data</span><strong>{fmtDate(lookupResult.slot_date)}</strong></div>
                      <div className="lr-row"><span>Hora</span><strong>{lookupResult.slot_time}</strong></div>
                      <div className="lr-row"><span>Duração</span><strong>{fmtDuration(lookupResult.duration_minutes)}</strong></div>
                      <div className="lr-row"><span>Preço</span><strong>{lookupResult.price}€</strong></div>
                    </div>

                    {lookupResult.status === 'confirmado' && !cancelConfirm && !editMode && !editSent && (
                      <div className="lr-actions">
                        <button className="btn-outline" onClick={() => setEditMode(true)}>
                          Pedir Alteração
                        </button>
                        <button className="btn-danger" onClick={() => setCancelConfirm(true)}>
                          Cancelar Consulta
                        </button>
                      </div>
                    )}

                    {cancelConfirm && (
                      <div className="confirm-box">
                        <p>Tem a certeza que deseja cancelar a consulta de <strong>{lookupResult.nome}</strong> a <strong>{fmtDate(lookupResult.slot_date)}</strong> às <strong>{lookupResult.slot_time}</strong>?</p>
                        <div className="confirm-actions">
                          <button className="btn-danger" onClick={handleCancel} disabled={cancelLoading}>
                            {cancelLoading ? 'A cancelar...' : 'Confirmar cancelamento'}
                          </button>
                          <button className="btn-outline" onClick={() => setCancelConfirm(false)}>
                            Voltar
                          </button>
                        </div>
                      </div>
                    )}

                    {editMode && (
                      <form className="edit-form" onSubmit={handleEditRequest}>
                        <p className="edit-intro">Descreva a alteração pretendida. A nutricionista entrará em contacto para confirmar.</p>
                        <div className="p-field">
                          <label>Mensagem</label>
                          <textarea
                            value={editMessage}
                            onChange={e => setEditMessage(e.target.value)}
                            placeholder="Ex: Gostaria de alterar para a semana seguinte, de preferência quarta-feira..."
                            rows={3}
                            required
                          />
                        </div>
                        <div className="confirm-actions">
                          <button type="submit" className="btn-primary" disabled={editLoading || !editMessage.trim()}>
                            {editLoading ? 'A enviar...' : 'Enviar Pedido'}
                          </button>
                          <button type="button" className="btn-outline" onClick={() => setEditMode(false)}>
                            Cancelar
                          </button>
                        </div>
                      </form>
                    )}

                    {editSent && (
                      <div className="edit-sent">
                        Pedido de alteração enviado. Será contactado em breve pela nutricionista.
                      </div>
                    )}

                    {lookupResult.status === 'cancelado' && (
                      <div className="cancelled-notice">
                        <p>Esta consulta foi cancelada.</p>
                        <button className="btn-outline" onClick={() => setActiveTab('nova')}>
                          Fazer nova marcação
                        </button>
                      </div>
                    )}
                  </motion.div>
                )}
              </div>
            </motion.div>

          )}
        </AnimatePresence>
      </div>

      <footer className="booking-footer">
        <p>IB Nutrição · Inês Bandarra · Nutricionista Materno-Infantil &amp; Pediátrica</p>
        <p>Ilha Terceira, Açores · <a href="mailto:inesbandarranutricao@gmail.com">inesbandarranutricao@gmail.com</a></p>
      </footer>
    </div>
  );
}
