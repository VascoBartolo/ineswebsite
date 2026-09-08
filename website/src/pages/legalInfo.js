// Single source of truth for the identification details that both legal pages
// must show. Portuguese law requires these on a commercial website:
//   - RGPD art. 13.º n.º 1 al. a) — identity and contacts of the controller
//   - DL n.º 7/2004 art. 10.º    — e-commerce provider identification
// TODO: replace the values marked "A PREENCHER" with the real registration data
// before going live — an incomplete identification block is itself a breach.
export const ENTITY = {
  name: 'Inês Bandarra',
  brand: 'IB Nutrição',
  role: 'Nutricionista Materno-Infantil e Pediátrica',
  nif: '[NIF — A PREENCHER]',
  professionalOrder: 'Ordem dos Nutricionistas',
  professionalId: '[Cédula profissional n.º — A PREENCHER]',
  address: '[Morada profissional completa — A PREENCHER], Ilha Terceira, Açores, Portugal',
  email: 'inesbandarranutricao@gmail.com',
  phone: '+351 969 743 355',
  phoneHref: '+351969743355',
  site: 'https://inesbandarranutricao.com',
  siteLabel: 'inesbandarranutricao.com',
};

// Shown as "last updated" on both pages. Update whenever the text changes.
export const LAST_UPDATED = '8 de setembro de 2026';

// Minimum notice, in hours, for a client to cancel or reschedule without the
// consultation counting as a missed appointment. Stated in the Terms.
// TODO: confirm this matches the policy actually applied in practice.
export const CANCELLATION_NOTICE_HOURS = 24;
