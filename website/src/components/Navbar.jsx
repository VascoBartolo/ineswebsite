import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './Navbar.css';

const navLinks = [
  { label: 'Início', href: '#inicio' },
  { label: 'Sobre Mim', href: '#sobre' },
  { label: 'Serviços', href: '#servicos' },
  { label: 'Galeria', href: '#galeria' },
  { label: 'Contacto', href: '#contacto' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  const handleLink = (e, href) => {
    e.preventDefault();
    setOpen(false);
    const el = document.querySelector(href);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <motion.header
      className={`navbar ${scrolled ? 'scrolled' : ''}`}
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <div className="navbar-inner">
        <a href="#inicio" className="navbar-logo" onClick={(e) => handleLink(e, '#inicio')}>
          <img src="/images/vermelho.png" alt="IB Nutrição" />
        </a>

        <nav className="navbar-links">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="navbar-link"
              onClick={(e) => handleLink(e, link.href)}
            >
              {link.label}
            </a>
          ))}
          <a
            href="#contacto"
            className="navbar-cta"
            onClick={(e) => handleLink(e, '#contacto')}
          >
            Marcar Consulta
          </a>
        </nav>

        <button className="navbar-burger" onClick={() => setOpen(!open)} aria-label="menu">
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            className="navbar-mobile"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="mobile-link"
                onClick={(e) => handleLink(e, link.href)}
              >
                {link.label}
              </a>
            ))}
            <a
              href="#contacto"
              className="mobile-cta"
              onClick={(e) => handleLink(e, '#contacto')}
            >
              Marcar Consulta
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
