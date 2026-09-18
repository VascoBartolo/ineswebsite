// Shared by the public booking form and the admin panel, so the options the
// nutritionist picks from can never drift from the ones clients are offered.

export const CONSULTATION_TYPES = {
  adulto: [
    { id: 'consulta de pré-concepção', label: 'Consulta de Pré-concepção', intro: true },
    { id: 'consulta na gravidez', label: 'Consulta na Gravidez', intro: false },
    { id: 'consulta no pós-parto', label: 'Consulta no Pós-Parto', intro: false },
    { id: 'consulta gestão de peso', label: 'Consulta de Gestão de Peso', intro: false },
  ],
  bebé: [
    { id: 'introdução alimentar', label: 'Introdução Alimentar', intro: true },
    { id: 'seletividade alimentar', label: 'Seletividade Alimentar', intro: false },
    { id: 'nutrição pediátrica', label: 'Nutrição Pediátrica', intro: false },
  ],
};

export const CLINICS = [
  'Clínica Manus (Angra do Heroísmo)',
  'Centro de Psicologia Flávia Bessa (Angra do Heroísmo)',
];

// Every type, grouped for a <select> in the admin panel, where a booking is
// entered without first choosing adulto/bebé.
export const CONSULTATION_TYPE_GROUPS = [
  { label: 'Adulto', options: CONSULTATION_TYPES.adulto },
  { label: 'Bebé / Criança', options: CONSULTATION_TYPES.bebé },
];

export const ALL_CONSULTATION_TYPE_IDS = [
  ...CONSULTATION_TYPES.adulto,
  ...CONSULTATION_TYPES.bebé,
].map((t) => t.id);
