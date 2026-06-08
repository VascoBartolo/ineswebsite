import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import { BowlFood, Heart, Drop, Stethoscope, VideoCamera, ClipboardText } from '@phosphor-icons/react';
import './Services.css';

const services = [
  {
    Icon: BowlFood,
    title: 'Introdução Alimentar & BLW',
    desc: 'Acompanhamento especializado na diversificação alimentar — Baby Led Weaning (BLW), papas e alimentação complementar. Orientação segura para uma introdução aos sólidos positiva e sem stress.',
    highlight: true,
  },
  {
    Icon: Heart,
    title: 'Nutrição na Gravidez',
    desc: 'Plano alimentar materno adaptado a cada trimestre, garantindo o aporte nutricional ideal para mãe e bebé. Consultas presenciais na Ilha Terceira ou online.',
  },
  {
    Icon: Drop,
    title: 'Aleitamento Materno',
    desc: 'Apoio nutricional durante a amamentação para maximizar a qualidade do leite materno, manter a energia da mãe e superar os principais desafios da lactação.',
  },
  {
    Icon: Stethoscope,
    title: 'Nutrição Pediátrica',
    desc: 'Consultas de nutrição infantil para todas as fases do crescimento — recém-nascidos, bebés, crianças e adolescentes. Planos alimentares adaptados a cada etapa do desenvolvimento.',
  },
  {
    Icon: VideoCamera,
    title: 'Consulta Online',
    desc: 'Consultas de nutrição materno-infantil por videochamada para famílias em qualquer parte de Portugal ou do mundo. Todo o acompanhamento sem sair de casa.',
  },
  {
    Icon: ClipboardText,
    title: 'Plano Alimentar',
    desc: 'Planos alimentares 100% personalizados para bebés e crianças, construídos com base nas preferências, rotinas e necessidades nutricionais específicas de cada família.',
  },
];

export default function Services() {
  const [ref, inView] = useInView();

  return (
    <section id="servicos" className="services" ref={ref}>
      <div className="services-inner">
        <div className="services-header">
          <motion.span
            className="section-eyebrow"
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            O que ofereço
          </motion.span>
          <motion.h2
            className="section-title"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Serviços de nutrição pensados <em>para a sua família</em>
          </motion.h2>
          <motion.p
            className="services-subtitle"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Nutrição pediátrica e materno-infantil baseada em evidência científica.
            Consultas presenciais na Ilha Terceira, Açores, e online para todo o país.
          </motion.p>
        </div>

        <div className="services-grid">
          {services.map((s, i) => (
            <motion.div
              key={s.title}
              className={`service-card ${s.highlight ? 'service-card--highlight' : ''}`}
              initial={{ opacity: 0, y: 32 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.1 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
            >
              <div className="service-icon-box">
                <s.Icon size={26} weight="regular" />
              </div>
              <h3 className="service-title">{s.title}</h3>
              <p className="service-desc">{s.desc}</p>
            </motion.div>
          ))}
        </div>

        <motion.div
          className="services-cta"
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <a
            href="#contacto"
            className="btn-primary"
            onClick={(e) => {
              e.preventDefault();
              document.querySelector('#contacto')?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Agendar Consulta
          </a>
        </motion.div>
      </div>
    </section>
  );
}
