import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useInView } from '../hooks/useInView';
import { BowlFood, Heart, Baby, Stethoscope, FlowerLotus } from '@phosphor-icons/react';
import './Services.css';

const services = [
  {
    Icon: FlowerLotus,
    title: 'Nutrição Pré-Conceção',
    desc: 'Consultas onde o objetivo é preparar o corpo da mulher para uma gestação, promovendo uma base nutricional saudável desde o início. O pai também é muito importante nesta fase.',
  },
  {
    Icon: Heart,
    title: 'Nutrição na Gravidez',
    desc: 'Acompanhamento nutricional adaptado a cada trimestre, garantindo o suporte ideal para mãe e bebé. Muito mais do que um plano — é um acompanhamento contínuo e personalizado.',
  },
  {
    Icon: Baby,
    title: 'Nutrição Pós-Parto',
    desc: 'A nutrição no pós-parto foca-se na recuperação da mãe, no aumento de energia, no equilíbrio hormonal e no bem-estar geral, com planos alimentares ajustados a cada fase e individualizados.',
  },
  {
    Icon: BowlFood,
    title: 'Introdução Alimentar & BLW',
    desc: 'Acompanhamento especializado na diversificação alimentar — Baby Led Weaning (BLW), método tradicional e alimentação complementar. Orientação segura para uma introdução aos alimentos positiva e sem stress.',
    highlight: true,
  },
  {
    Icon: Stethoscope,
    title: 'Nutrição Pediátrica',
    desc: 'Consultas de nutrição infantil para todas as fases do crescimento — recém-nascidos, bebés, crianças e adolescentes. Planos alimentares adaptados a cada etapa do desenvolvimento, a cada criança e família.',
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
            Como te posso ajudar
          </motion.span>
          <motion.h2
            className="section-title"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Serviços de nutrição pensados <em>para a tua família</em>
          </motion.h2>
          <motion.p
            className="services-subtitle"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Nutrição materno-infantil e pediátrica baseada em evidência científica.
            Consultas presenciais na Ilha Terceira, Açores, e online para todo o mundo.
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
          <Link to="/marcar-consulta" className="btn-primary">
            Agendar Consulta
          </Link>
        </motion.div>
      </div>
    </section>
  );
}
