import { useState } from 'react';
import { adminApi } from './adminApi';
import BookingsTab from './BookingsTab';
import StatsTab from './StatsTab';

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
        <button className={tab === 'bookings' ? 'on' : ''} onClick={() => setTab('bookings')}>Marcações</button>
        <button className={tab === 'stats' ? 'on' : ''} onClick={() => setTab('stats')}>Estatísticas</button>
      </nav>

      {tab === 'bookings' ? <BookingsTab /> : <StatsTab />}
    </div>
  );
}
