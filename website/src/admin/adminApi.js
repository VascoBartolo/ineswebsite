const BASE = '/api/admin';

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 401) throw new Error('unauthorized');
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // Carry the parsed body along: callers need the server's field-level detail
    // (e.g. which required fields were missing), not just the error code.
    const err = new Error(body.error || 'request_failed');
    err.body = body;
    throw err;
  }
  return body;
}

export const adminApi = {
  session: () => req('/session'),
  login: (password) => req('/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => req('/logout', { method: 'POST' }),
  bookings: (params, options) => req('/bookings?' + new URLSearchParams(params).toString(), options),
  locations: () => req('/locations'),
  stats: (params) => req('/stats?' + new URLSearchParams(params).toString()),
  createBooking: (data) => req('/bookings', { method: 'POST', body: JSON.stringify(data) }),
  editBooking: (ref, data) => req(`/bookings/${ref}`, { method: 'PUT', body: JSON.stringify(data) }),
  cancelBooking: (ref) => req(`/bookings/${ref}/cancel`, { method: 'POST' }),
  deleteBooking: (ref) => req(`/bookings/${ref}`, { method: 'DELETE' }),
};
