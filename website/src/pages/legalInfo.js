// Single source of truth for the identification details that both legal pages
// must show. Portuguese law requires these on a commercial website:
//   - RGPD art. 13.º n.º 1 al. a) — identity and contacts of the controller
//   - DL n.º 7/2004 art. 10.º    — e-commerce provider identification
export const ENTITY = {
  name: 'Inês Bandarra',
  brand: 'IB Nutrição',
  role: 'Nutricionista Materno-Infantil e Pediátrica',
  nif: '266758320',
  professionalOrder: 'Ordem dos Nutricionistas',
  professionalId: 'Cédula profissional n.º 5976N',
  email: 'inesbandarranutricao@gmail.com',
  phone: '+351 969 743 355',
  phoneHref: '+351969743355',
  site: 'https://inesbandarranutricao.com',
  siteLabel: 'inesbandarranutricao.com',
};

// Where consultations are actually held. Used instead of a private residential
// address: there is no separate office, and a home address should not be
// published. Note this is a mitigation, not an exemption — DL n.º 7/2004
// art. 10.º and DL n.º 24/2014 art. 4.º both require a geographic address for
// the establishment, so this only holds while the practice genuinely operates
// from these clinics. See the compliance notes in docs/.
export const PRACTICE_LOCATIONS = [
  'Clínica Manus — Angra do Heroísmo, Ilha Terceira, Açores',
  'Centro de Psicologia Flávia Bessa — Angra do Heroísmo, Ilha Terceira, Açores',
];

// Short single-line form for the page footers.
export const PRACTICE_REGION = 'Angra do Heroísmo, Ilha Terceira, Açores, Portugal';

// Shown as "last updated" on both pages. Update whenever the text changes.
export const LAST_UPDATED = '8 de setembro de 2026';

// Minimum notice, in hours, for a client to cancel or reschedule without the
// consultation counting as a missed appointment. Stated in the Terms.
// TODO: confirm this matches the policy actually applied in practice.
export const CANCELLATION_NOTICE_HOURS = 24;
