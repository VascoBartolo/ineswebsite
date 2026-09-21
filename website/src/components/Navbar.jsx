import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
  const location = useLocation();
  const navigate = useNavigate();
  const burgerRef = useRef(null);
  const panelRef = useRef(null);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  // Opening the mobile menu moves focus into it; Escape closes it and returns
  // focus to the burger, so keyboard users never lose their place.
  useEffect(() => {
    if (!open) return undefined;
    panelRef.current?.querySelector('a')?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        burgerRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const handleLink = (e, href) => {
    e.preventDefault();
    const menuWasOpen = open;
    setOpen(false);

    const scrollTo = () => {
      const el = document.querySelector(href);
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (el) el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' });
    };

    if (location.pathname !== '/') {
      // Navigate home first, then scroll once the page has rendered
      navigate('/');
      setTimeout(scrollTo, 100);
    } else if (menuWasOpen) {
      // Wait for the mobile menu close animation (300ms) before scrolling
      setTimeout(scrollTo, 300);
    } else {
      // Desktop nav: no menu animation, scroll immediately
      scrollTo();
    }
  };

  const handleLogoClick = (e) => {
    e.preventDefault();
    setOpen(false);
    if (location.pathname === '/') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      navigate('/');
    }
  };

  return (
    <motion.header
      className={`navbar ${scrolled ? 'scrolled' : ''}`}
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <div className="navbar-inner">
        <a href="/" className="navbar-logo" onClick={handleLogoClick}>
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
          <Link to="/marcar-consulta" className="navbar-cta">
            Marcar Consulta
          </Link>
        </nav>

        <button
          type="button"
          ref={burgerRef}
          className="navbar-burger"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={open}
          aria-controls="navbar-mobile"
        >
          {open ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
        </button>
      </div>

      <AnimatePresence>
        {open && (
          <motion.nav
            id="navbar-mobile"
            ref={panelRef}
            aria-label="Menu"
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
            <Link
              to="/marcar-consulta"
              className="mobile-cta"
              onClick={() => setOpen(false)}
            >
              Marcar Consulta
            </Link>
          </motion.nav>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
