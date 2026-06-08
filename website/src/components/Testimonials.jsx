import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Margarida F.',
    role: 'Mãe de gémeos, 14 meses',
    text: 'A Inês foi uma luz no meu caminho! A introdução alimentar com gémeos parecia um pesadelo, mas com o apoio dela tudo se tornou tão natural. Recomendo de coração.',
    initials: 'MF',
  },
  {
    name: 'Beatriz S.',
    role: 'Mãe do Tomás, 2 anos',
    text: 'Consulta muito completa e personalizada. A Inês ouviu todas as minhas preocupações e deu-me ferramentas práticas para lidar com a seletividade alimentar do meu filho.',
    initials: 'BS',
  },
  {
    name: 'Ana & Rui',
    role: 'Pais da Leonor, 8 meses',
    text: 'Começámos o BLW com muito medo e a Inês ajudou-nos a ganhar confiança. A nossa filha come de tudo e adora explorar novos sabores. Obrigada!',
    initials: 'AR',
  },
];

const faqs = [
  {
    q: 'Quando devo começar a introdução alimentar / diversificação alimentar?',
    a: 'A introdução alimentar complementar deve começar por volta dos 6 meses, quando o bebé mostra sinais de prontidão. Ofereço consultas pré-introdução para preparar a família, tanto para BLW (Baby Led Weaning) como para papas tradicionais.',
  },
  {
    q: 'O que é o BLW (Baby Led Weaning)?',
    a: 'BLW, ou Baby Led Weaning, é uma abordagem de introdução alimentar em que o bebé explora os alimentos sólidos de forma autónoma, ao seu próprio ritmo. É uma alternativa às papas que promove a autorregulação e uma relação positiva com a comida desde cedo.',
  },
  {
    q: 'Faz consultas de nutrição online?',
    a: 'Sim! Realizo consultas de nutrição materno-infantil e pediátrica por videochamada para famílias em todo o Portugal e no estrangeiro. Ideal para quem está fora dos Açores ou prefere a comodidade de casa.',
  },
  {
    q: 'O que inclui uma consulta de nutrição pediátrica?',
    a: 'Avaliação nutricional e antropométrica completa, plano alimentar personalizado para a criança, guias de orientação para os pais e acompanhamento por mensagem entre consultas.',
  },
];

export default function Testimonials() {
  const [ref, inView] = useInView();

  return (
    <section className="testimonials" ref={ref}>
      <div className="testimonials-inner">
        <div className="testimonials-header">
          <motion.span
            className="section-eyebrow"
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            Testemunhos
          </motion.span>
          <motion.h2
            className="section-title"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            O que dizem as <em>famílias</em>
          </motion.h2>
        </div>

        <div className="testimonials-grid">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              className="testimonial-card"
              initial={{ opacity: 0, y: 32 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.15 + i * 0.12 }}
            >
              <p className="testimonial-text">"{t.text}"</p>
              <div className="testimonial-author">
                <div className="testimonial-avatar">{t.initials}</div>
                <div>
                  <strong>{t.name}</strong>
                  <span>{t.role}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="faq-section">
          <motion.h3
            className="faq-title"
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            Perguntas Frequentes
          </motion.h3>
          <div className="faq-list">
            {faqs.map((faq, i) => (
              <motion.details
                key={faq.q}
                className="faq-item"
                initial={{ opacity: 0, y: 16 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.55 + i * 0.08 }}
              >
                <summary className="faq-question">{faq.q}</summary>
                <p className="faq-answer">{faq.a}</p>
              </motion.details>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
