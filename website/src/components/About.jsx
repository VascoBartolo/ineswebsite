import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import { Sparkle, Smiley, HouseLine } from '@phosphor-icons/react';
import './About.css';

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, delay: i * 0.12, ease: [0.22, 1, 0.36, 1] },
  }),
};

const values = [
  {
    Icon: Sparkle,
    title: 'Abordagem Integrativa',
    desc: 'Visão global da criança e da família, respeitando o desenvolvimento nutricional em cada fase da infância e da rotina familiar.',
  },
  {
    Icon: Smiley,
    title: 'Relação Positiva com a Comida',
    desc: 'Sem pressões nem restrições — a refeição deve ser um momento de descoberta e prazer.',
  },
  {
    Icon: HouseLine,
    title: 'Apoio à Família',
    desc: 'A família é parceira do processo. Orientação prática para pais, mães e cuidadores.',
  },
];

export default function About() {
  const [ref, inView] = useInView();

  return (
    <section id="sobre" className="about" ref={ref}>
      <div className="about-inner">
        <motion.div
          className="about-image-side"
          initial={{ opacity: 0, x: -40 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="about-img-stack">
            <div className="about-img-main">
              <img src="/images/ines-nutri-177-2.jpg.jpeg" alt="Inês Bandarra — Nutricionista Pediátrica nos Açores" />
            </div>
            <div className="about-img-accent">
              <img src="/images/ines-nutri-159.jpg.jpeg" alt="Consulta de nutrição materno-infantil" />
            </div>
          </div>
          <div className="about-deco-circle" />
        </motion.div>

        <div className="about-text-side">
          <motion.span
            className="section-eyebrow"
            variants={fadeUp}
            custom={0}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            Sobre Mim
          </motion.span>

          <motion.h2
            className="section-title"
            variants={fadeUp}
            custom={1}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            Nutricionista pediátrica com <em>paixão por nutrir famílias</em>
          </motion.h2>

          <motion.p
            className="about-text"
            variants={fadeUp}
            custom={2}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            Olá, sou a Inês Bandarra! Sou nutricionista especializada em nutrição
            materno-infantil e pediátrica, com consultório na Ilha Terceira, Açores.
            Acompanho famílias desde a gravidez, o aleitamento materno, a introdução
            alimentar — incluindo BLW (Baby Led Weaning) — até à adolescência.
          </motion.p>

          <motion.p
            className="about-text"
            variants={fadeUp}
            custom={3}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            Acredito que cada criança é única e que a alimentação deve ser uma
            experiência positiva, de descoberta e afeto. Trabalho de forma personalizada
            com cada família, sempre com base em evidência científica, escuta ativa e
            muita empatia. Faço também consultas de nutrição online para famílias em
            todo o mundo.
          </motion.p>

          <motion.div
            className="about-values"
            variants={fadeUp}
            custom={4}
            initial="hidden"
            animate={inView ? 'visible' : 'hidden'}
          >
            {values.map((v) => (
              <div key={v.title} className="value-item">
                <div className="value-icon-box">
                  <v.Icon size={20} weight="regular" />
                </div>
                <div>
                  <strong>{v.title}</strong>
                  <p>{v.desc}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
