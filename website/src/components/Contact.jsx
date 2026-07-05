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

function WhatsAppIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.71.306 1.263.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
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
              <div className="form-actions">
                <button type="submit" className="btn-primary form-submit" disabled={sending}>
                  {sending ? 'A enviar...' : 'Enviar Mensagem'}
                </button>
                <a
                  className="whatsapp-btn"
                  href="https://wa.me/351969743355"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <WhatsAppIcon size={20} />
                  Falar no WhatsApp
                </a>
              </div>
            </form>
          )}
        </motion.div>
      </div>
    </section>
  );
}
