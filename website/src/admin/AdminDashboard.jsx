import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { adminApi } from './adminApi';
import BookingsTab from './BookingsTab';
import StatsTab from './StatsTab';

const TABS = [
  { id: 'bookings', label: 'Marcações' },
  { id: 'stats', label: 'Estatísticas' },
];

export default function AdminDashboard({ onLogout }) {
  const [tab, setTab] = useState('bookings');

  const logout = async () => {
    try { await adminApi.logout(); } finally { onLogout(); }
  };

  return (
    <div className="admin">
      <header className="admin-top">
        <div className="admin-brand">
          <img src="/images/vermelho.png" alt="IB Nutrição" />
          <div>
            <span className="admin-brand-name">IB Nutrição</span>
            <small>Painel de Administração</small>
          </div>
        </div>
        <button className="admin-logout" onClick={logout}>Terminar sessão</button>
      </header>

      <nav className="admin-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'on' : ''}
            onClick={() => setTab(t.id)}
          >
            {tab === t.id && (
              <motion.span
                layoutId="admin-tab-pill"
                className="tab-pill"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            )}
            <span className="tab-label">{t.label}</span>
          </button>
        ))}
      </nav>

      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        >
          {tab === 'bookings' ? <BookingsTab /> : <StatsTab />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
