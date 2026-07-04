import { Heart } from 'lucide-react';

function InstagramIcon({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
      <circle cx="12" cy="12" r="4"/>
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
    </svg>
  );
}
import './Footer.css';

const navLinks = [
  { label: 'Início', href: '#inicio' },
  { label: 'Sobre Mim', href: '#sobre' },
  { label: 'Serviços', href: '#servicos' },
  { label: 'Galeria', href: '#galeria' },
  { label: 'Contacto', href: '#contacto' },
];

export default function Footer() {
  const handleLink = (e, href) => {
    e.preventDefault();
    document.querySelector(href)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <img src="/images/vermelho.png" alt="IB Nutrição" className="footer-logo" />
          <p className="footer-tagline">
            Nutrição materno-infantil com amor e ciência,<br />
            na Ilha Terceira, Açores.
          </p>
          <a
            href="https://instagram.com/inesbandarra.nutricao"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-social"
            aria-label="Instagram"
          >
            <InstagramIcon size={20} />
          </a>
        </div>

        <nav className="footer-nav">
          <span className="footer-nav-title">Navegação</span>
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="footer-link"
              onClick={(e) => handleLink(e, link.href)}
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="footer-contact-col">
          <span className="footer-nav-title">Contacto</span>
          <p>Ilha Terceira, Açores</p>
          <p>inesbandarranutricao@gmail.com</p>
          <p>+351 969 743 355</p>
        </div>
      </div>

      <div className="footer-bottom">
        <p>
          © {new Date().getFullYear()} IB Nutrição · Feito com{' '}
          <Heart size={12} className="footer-heart" /> em Portugal
        </p>
      </div>
    </footer>
  );
}
