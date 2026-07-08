import { useState } from 'react';
import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import './Testimonials.css';

const testimonials = [
  {
    name: 'Micaela Sampaio',
    role: 'Mãe · bebé com 1 ano',
    text: 'O Noah é seguido desde os seus primeiros meses de vida pela querida Inês, posso vos dizer que foi a melhor decisão tomada, desde a IA até agora surgem sempre dúvidas e "medos" e quando isso acontece lá está a minha querida Inês sempre pronta ajudar e dar aquela confiança que qualquer uma mãe, principalmente de primeira viagem precisa!',
    image: '/images/cliente-micaela.jpg',
    initials: 'MS',
  },
  {
    name: 'Rita Lopes',
    role: 'Grávida · 20 semanas',
    text: 'A Inês é uma nutricionista atenciosa e muito dedicada e tem sido uma ajuda fundamental na minha gravidez aos 44 anos! Não é pessoa de extremos e sabe adequar o acompanhamento às necessidades nutricionais mediante as nossas preferências alimentares. Sou muito grata pela atenção que tem tido comigo.',
    image: '/images/cliente-rita.jpg',
    initials: 'RL',
  },
  {
    name: 'Inês Casulo',
    role: 'Mãe · bebé com 11 meses',
    text: 'Quando a nossa bebé nasceu, o nosso mundo mudou por completo. A informação era tanta no campo da puericultura, que nos sentimos um pouco perdidos no que tocava à Introdução Alimentar. Até que conhecemos a Drª Inês, que foi uma grande ajuda nesse processo. Desde a primeira consulta presencial até ao acompanhamento on-line, sentimos sempre que foi a nossa melhor escolha. Seguimos todas as sugestões e dicas de como introduzir os alimentos, e mesmo a medo, fomos desconstruindo mitos sobre a alimentação de bebés. Hoje a caminho de um ano de idade, não há um alimento que a nossa filha rejeite ou não queira experimentar. Somos muito gratos por sermos seguidos pela Drª Inês na nutrição da nossa filha e recomendamos!',
    image: '/images/cliente-ines.jpg',
    initials: 'IC',
  },
];

function TestimonialAvatar({ name, image, initials }) {
  const [failed, setFailed] = useState(false);
  if (image && !failed) {
    return (
      <div className="testimonial-avatar">
        <img src={image} alt={name} loading="lazy" onError={() => setFailed(true)} />
      </div>
    );
  }
  return <div className="testimonial-avatar">{initials}</div>;
}

const faqs = [
  {
    q: 'Quando devo começar a introdução alimentar / diversificação alimentar?',
    a: 'A introdução alimentar complementar deve começar por volta dos 6 meses, quando o bebé mostra os sinais de prontidão. Ofereço consultas pré-introdução para preparar a família, tanto para BLW (Baby Led Weaning) como para o método tradicional.',
  },
  {
    q: 'O que é o BLW (Baby Led Weaning)?',
    a: 'BLW, ou Baby Led Weaning, é uma abordagem de introdução alimentar em que o bebé explora os alimentos sólidos de forma autónoma, ao seu próprio ritmo. É uma alternativa aos purés que promove a autorregulação e uma relação positiva com a comida desde cedo. Contudo, o melhor método é aquele que se adapta à tua família!',
  },
  {
    q: 'Como funciona a consulta e o acompanhamento?',
    a: 'Cada consulta é adaptada às tuas necessidades e à fase em que te encontras. Em conjunto, definimos objetivos e estratégias nutricionais ajustadas à tua rotina, preferências e realidade. O acompanhamento é contínuo e personalizado, permitindo esclarecer dúvidas, ajustar o plano sempre que necessário e apoiar-te em cada etapa, de forma prática, simples e sempre baseada na evidência científica.',
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
                <TestimonialAvatar name={t.name} image={t.image} initials={t.initials} />
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
