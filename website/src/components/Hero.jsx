import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import './Hero.css';

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] },
  }),
};

export default function Hero() {
  return (
    <section id="inicio" className="hero">
      <div className="hero-bg-blob blob-1" />
      <div className="hero-bg-blob blob-2" />

      <div className="hero-inner">
        <div className="hero-content">
          <motion.span
            className="hero-eyebrow"
            variants={fadeUp}
            custom={0}
            initial="hidden"
            animate="visible"
          >
            Nutricionista Materno-Infantil & Pediátrica · Ilha Terceira, Açores
          </motion.span>

          <motion.h1
            className="hero-title"
            variants={fadeUp}
            custom={1}
            initial="hidden"
            animate="visible"
          >
            Alimentar com amor,{' '}
            <em>crescer com saúde</em>
          </motion.h1>

          <motion.p
            className="hero-subtitle"
            variants={fadeUp}
            custom={2}
            initial="hidden"
            animate="visible"
          >
            Consultas de pré-conceção, gravidez, pós-parto, introdução
            alimentar, BLW (Baby Led Weaning), nutrição pediátrica —
            presencialmente nos Açores ou online para todo o mundo.
          </motion.p>

          <motion.div
            className="hero-actions"
            variants={fadeUp}
            custom={3}
            initial="hidden"
            animate="visible"
          >
            <Link to="/marcar-consulta" className="btn-primary">
              Marcar Consulta
            </Link>
            <a
              href="#sobre"
              className="btn-secondary"
              onClick={(e) => {
                e.preventDefault();
                document.querySelector('#sobre')?.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              Saber Mais
            </a>
          </motion.div>

          <motion.div
            className="hero-badges"
            variants={fadeUp}
            custom={4}
            initial="hidden"
            animate="visible"
          >
            <div className="badge">
              <span className="badge-num">100+</span>
              <span className="badge-label">Famílias acompanhadas</span>
            </div>
            <div className="badge-divider" />
            <div className="badge">
              <span className="badge-num">2+</span>
              <span className="badge-label">Anos de experiência</span>
            </div>
            <div className="badge-divider" />
            <div className="badge">
              <span className="badge-num">100%</span>
              <span className="badge-label">Consultas personalizadas</span>
            </div>
          </motion.div>
        </div>

        <motion.div
          className="hero-image-wrapper"
          initial={{ opacity: 0, scale: 0.92, x: 40 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          transition={{ duration: 0.9, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="hero-image-frame">
            <img
              src="/images/ines-nutri-57.jpg.jpeg"
              alt="Inês Bandarra — Nutricionista"
              className="hero-img"
            />
          </div>
          <div className="hero-image-deco" />
        </motion.div>
      </div>

      <div className="hero-scroll-hint">
        <motion.div
          className="scroll-line"
          initial={{ scaleY: 0 }}
          animate={{ scaleY: 1 }}
          transition={{ delay: 1.2, duration: 0.8 }}
        />
      </div>
    </section>
  );
}
