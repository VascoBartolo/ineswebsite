import { useState } from 'react';
import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import { MapPin, Phone, Mail, Clock } from 'lucide-react';

function InstagramIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
      <circle cx="12" cy="12" r="4"/>
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
    </svg>
  );
}
import './Contact.css';

export default function Contact() {
  const [ref, inView] = useInView();
  const [form, setForm] = useState({ name: '', email: '', phone: '', subject: '', message: '' });
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError('');
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        setSent(true);
      } else {
        setError('Erro ao enviar a mensagem. Por favor tente novamente.');
      }
    } catch {
      setError('Erro de ligação. Verifica a tua conexão e tenta novamente.');
    } finally {
      setSending(false);
    }
  };

  return (
    <section id="contacto" className="contact" ref={ref}>
      <div className="contact-inner">
        <div className="contact-info">
          <motion.span
            className="section-eyebrow"
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            Contacto
          </motion.span>

          <motion.h2
            className="section-title"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            O primeiro passo <em>começa aqui</em>
          </motion.h2>

          <motion.p
            className="contact-lead"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Estou aqui para responder às tuas dúvidas e agendar a tua consulta.
            Entra em contacto por qualquer um dos canais abaixo.
          </motion.p>

          <motion.div
            className="contact-details"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <div className="contact-detail">
              <div className="detail-icon"><MapPin size={18} /></div>
              <div>
                <strong>Localização</strong>
                <span>Ilha Terceira, Açores, Portugal</span>
              </div>
            </div>
            <div className="contact-detail">
              <div className="detail-icon"><Phone size={18} /></div>
              <div>
                <strong>Telefone / WhatsApp</strong>
                <span>+351 969 743 355</span>
              </div>
            </div>
            <div className="contact-detail">
              <div className="detail-icon"><Mail size={18} /></div>
              <div>
                <strong>Email</strong>
                <span>inesbandarranutricao@gmail.com</span>
              </div>
            </div>
            <div className="contact-detail">
              <div className="detail-icon"><Clock size={18} /></div>
              <div>
                <strong>Horário</strong>
                <span>Segunda a Sexta, 16h – 19h</span>
              </div>
            </div>
            <div className="contact-detail">
              <div className="detail-icon"><InstagramIcon size={18} /></div>
              <div>
                <strong>Instagram</strong>
                <span>@inesbandarra.nutricao</span>
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div
          className="contact-form-wrapper"
          initial={{ opacity: 0, x: 40 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
        >
          {sent ? (
            <div className="form-success">
              <span className="success-icon">✓</span>
              <h3>Mensagem enviada!</h3>
              <p>Obrigada pelo contacto. Responderei em breve.</p>
            </div>
          ) : (
            <form className="contact-form" onSubmit={handleSubmit}>
              <h3 className="form-title">Entra em contacto comigo</h3>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="name">Nome</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    placeholder="O teu nome"
                    value={form.name}
                    onChange={handleChange}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="email">Email</label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    placeholder="O teu email"
                    value={form.email}
                    onChange={handleChange}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="phone">Telefone</label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    placeholder="+351 9XX XXX XXX"
                    value={form.phone}
                    onChange={handleChange}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="subject">Assunto</label>
                  <select
                    id="subject"
                    name="subject"
                    value={form.subject}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Selecionar...</option>
                    <option>Nutrição Pré-Conceção</option>
                    <option>Nutrição na Gravidez</option>
                    <option>Nutrição Pós-Parto</option>
                    <option>Introdução Alimentar & BLW</option>
                    <option>Nutrição Pediátrica</option>
                    <option>Consulta Online</option>
                    <option>Outro</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="message">Mensagem</label>
                <textarea
                  id="message"
                  name="message"
                  rows={4}
                  placeholder="Conta-me um pouco sobre o que procuras..."
                  value={form.message}
                  onChange={handleChange}
                  required
                />
              </div>
              {error && <p className="contact-form-error">{error}</p>}
              <button type="submit" className="btn-primary form-submit" disabled={sending}>
                {sending ? 'A enviar...' : 'Enviar Mensagem'}
              </button>
            </form>
          )}
        </motion.div>
      </div>
    </section>
  );
}
