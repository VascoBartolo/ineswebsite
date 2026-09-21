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
    } catch (e) {
      setError(
        e.message === 'rate_limited' ? 'Demasiadas tentativas. Tente novamente mais tarde.'
          : e.message === 'unauthorized' ? 'Palavra-passe incorreta.'
            : 'Não foi possível entrar. Verifique a ligação e tente novamente.',
      );
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
          // eslint-disable-next-line jsx-a11y/no-autofocus -- sole field on a login-only screen
          type="password" value={password} autoFocus
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Palavra-passe"
          aria-label="Palavra-passe"
          autoComplete="current-password"
        />
        {error && <span className="admin-login-error" role="alert">{error}</span>}
        <button type="submit" disabled={busy}>{busy ? 'A entrar…' : 'Entrar'}</button>
      </form>
    </div>
  );
}
