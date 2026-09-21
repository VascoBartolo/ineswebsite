import { useEffect, useState } from 'react';
import { adminApi, setUnauthorizedHandler } from './adminApi';
import AdminLogin from './AdminLogin';
import AdminDashboard from './AdminDashboard';
import { usePageTitle } from '../hooks/usePageTitle';
import './admin.css';

export default function AdminPage() {
  usePageTitle('Painel de Administração');
  const [state, setState] = useState('loading'); // loading | out | in

  const check = () => adminApi.session()
    .then((r) => setState(r.authenticated ? 'in' : 'out'))
    .catch(() => setState('out'));

  useEffect(() => { check(); }, []);
  useEffect(() => {
    setUnauthorizedHandler(() => setState('out'));
    return () => setUnauthorizedHandler(null);
  }, []);

  // React 19 hoists this into <head>; the most restrictive robots rule wins, so
  // it overrides the site-wide "index, follow" for this page only.
  const noindex = <meta name="robots" content="noindex, nofollow" />;
  if (state === 'loading') return <>{noindex}<div className="admin-loading">A carregar…</div></>;
  if (state === 'out') return <>{noindex}<AdminLogin onSuccess={() => setState('in')} /></>;
  return <>{noindex}<AdminDashboard onLogout={() => setState('out')} /></>;
}
