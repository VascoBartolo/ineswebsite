// First focusable element on each page: lets keyboard users jump past the
// header straight to the page's <main id="main">.
export default function SkipLink() {
  return <a href="#main" className="skip-link">Saltar para o conteúdo</a>;
}
