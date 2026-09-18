import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { ENTITY, LAST_UPDATED, PRACTICE_REGION } from './legalInfo';
import './LegalPage.css';

/**
 * Shell shared by the standalone legal documents (privacy policy, terms).
 * These live outside the one-page site on their own routes, so they carry their
 * own header/footer instead of the home page's Navbar/Footer.
 */
export default function LegalLayout({ eyebrow, title, documentTitle, children }) {
  // These are deep-linked from the footer and from emails, so they must open at
  // the top and carry their own <title> for the browser tab and for sharing.
  useEffect(() => {
    window.scrollTo(0, 0);
    const previous = document.title;
    document.title = `${documentTitle} · ${ENTITY.brand}`;
    return () => { document.title = previous; };
  }, [documentTitle]);

  return (
    <div className="legal-page">
      <header className="legal-header">
        <div className="legal-header-inner">
          <Link to="/" className="legal-back-link">
            <ArrowLeft size={16} />
            Voltar ao site
          </Link>
          <img src="/images/vermelho.png" alt={ENTITY.brand} className="legal-logo" />
        </div>
      </header>

      <div className="legal-hero">
        <span className="legal-eyebrow">{eyebrow}</span>
        <h1 className="legal-title">{title}</h1>
        <p className="legal-updated">Última atualização: {LAST_UPDATED}</p>
      </div>

      <main className="legal-content">{children}</main>

      <footer className="legal-footer">
        <p>{ENTITY.brand} · {ENTITY.name} · {ENTITY.role}</p>
        <p>
          {PRACTICE_REGION} ·{' '}
          <a href={`mailto:${ENTITY.email}`}>{ENTITY.email}</a>
        </p>
        <div className="legal-footer-links">
          <Link to="/politica-de-privacidade">Política de Privacidade</Link>
          <span aria-hidden="true">·</span>
          <Link to="/termos-e-condicoes">Termos e Condições</Link>
        </div>
      </footer>
    </div>
  );
}
