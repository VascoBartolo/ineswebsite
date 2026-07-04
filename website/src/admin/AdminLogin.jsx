import { useState } from 'react';
import { adminApi } from './adminApi';

export default function AdminLogin({ onSuccess }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      await adminApi.login(password);
      onSuccess();
    } catch {
      setError('Palavra-passe incorreta.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-login">
      <form className="admin-login-card" onSubmit={submit}>
        <img src="/images/vermelho.png" alt="IB Nutrição" className="admin-login-logo" />
        <h1>Painel de Administração</h1>
        <p>Introduz a palavra-passe para continuar.</p>
        <input
          type="password" value={password} autoFocus
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Palavra-passe"
        />
        {error && <span className="admin-login-error">{error}</span>}
        <button type="submit" disabled={busy}>{busy ? 'A entrar…' : 'Entrar'}</button>
      </form>
    </div>
  );
}
