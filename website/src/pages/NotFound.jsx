import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import SkipLink from '../components/SkipLink';
import { usePageTitle } from '../hooks/usePageTitle';
import { ENTITY } from './legalInfo';
import './LegalPage.css';

// Catch-all route: an unknown address used to render a blank page. Reuses the
// legal pages' shell so it matches the rest of the site.
export default function NotFound() {
  usePageTitle('Página não encontrada');
  return (
    <div className="legal-page">
      <SkipLink />
      <header className="legal-header">
        <div className="legal-header-inner">
          <Link to="/" className="legal-back-link">
            <ArrowLeft size={16} aria-hidden="true" />
            Voltar ao site
          </Link>
          <img src="/images/vermelho.png" alt={ENTITY.brand} className="legal-logo" />
        </div>
      </header>

      <main className="legal-main" id="main" tabIndex={-1}>
        <div className="legal-hero">
          <span className="legal-eyebrow">Erro 404</span>
          <h1 className="legal-title">Página não encontrada</h1>
          <p className="legal-updated">A página que procura não existe ou foi movida.</p>
        </div>
        <div className="legal-content">
          <p>
            <Link to="/">Voltar à página inicial</Link> ou{' '}
            <Link to="/marcar-consulta">marcar uma consulta</Link>.
          </p>
        </div>
      </main>
    </div>
  );
}
