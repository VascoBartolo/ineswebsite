const BASE = '/api/admin';

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 401) throw new Error('unauthorized');
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || 'request_failed');
  return body;
}

export const adminApi = {
  session: () => req('/session'),
  login: (password) => req('/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => req('/logout', { method: 'POST' }),
  bookings: (params) => req('/bookings?' + new URLSearchParams(params).toString()),
  locations: () => req('/locations'),
  stats: (params) => req('/stats?' + new URLSearchParams(params).toString()),
  editBooking: (ref, data) => req(`/bookings/${ref}`, { method: 'PUT', body: JSON.stringify(data) }),
  cancelBooking: (ref) => req(`/bookings/${ref}/cancel`, { method: 'POST' }),
  deleteBooking: (ref) => req(`/bookings/${ref}`, { method: 'DELETE' }),
};
