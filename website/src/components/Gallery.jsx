import { motion } from 'framer-motion';
import { useInView } from '../hooks/useInView';
import './Gallery.css';

const images = [
  {
    src: '/images/baby3.jpg',
    alt: 'Momento de introdução alimentar',
    span: 'normal',
  },
  {
    src: '/images/baby2.jpg',
    alt: 'Bebé a explorar novos alimentos',
    span: 'normal',
  },
  {
    src: '/images/baby1.jpg',
    alt: 'Refeição de bebé',
    span: 'normal',
  },
];

export default function Gallery() {
  const [ref, inView] = useInView();

  return (
    <section id="galeria" className="gallery" ref={ref}>
      <div className="gallery-inner">
        <div className="gallery-header">
          <motion.span
            className="section-eyebrow"
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            Galeria
          </motion.span>
          <motion.h2
            className="section-title"
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Momentos de <em>descoberta e alegria</em>
          </motion.h2>
        </div>

        <div className="gallery-grid">
          {images.map((img, i) => (
            <motion.div
              key={img.src}
              className={`gallery-item gallery-item--${img.span}`}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={inView ? { opacity: 1, scale: 1 } : {}}
              transition={{ duration: 0.6, delay: 0.1 + i * 0.1, ease: [0.22, 1, 0.36, 1] }}
            >
              <img src={img.src} alt={img.alt} loading="lazy" />
              <div className="gallery-overlay" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
