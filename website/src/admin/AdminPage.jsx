import { useEffect, useState } from 'react';
import { adminApi } from './adminApi';
import AdminLogin from './AdminLogin';
import AdminDashboard from './AdminDashboard';
import './admin.css';

export default function AdminPage() {
  const [state, setState] = useState('loading'); // loading | out | in

  const check = () => adminApi.session()
    .then((r) => setState(r.authenticated ? 'in' : 'out'))
    .catch(() => setState('out'));

  useEffect(() => { check(); }, []);

  if (state === 'loading') return <div className="admin-loading">A carregar…</div>;
  if (state === 'out') return <AdminLogin onSuccess={() => setState('in')} />;
  return <AdminDashboard onLogout={() => setState('out')} />;
}
