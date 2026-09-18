import { useEffect, useState, useCallback } from 'react';
import { adminApi } from './adminApi';
import EditBookingModal from './EditBookingModal';
import ConfirmModal from './ConfirmModal';
import Toast from './Toast';

const REGIME_LABEL = { presencial: 'Presencial', online: 'Online' };
const STATUS_LABEL = { pendente: 'Pendente', confirmado: 'Confirmado', revisao: 'Necessita Alteração', cancelado: 'Cancelado' };
const STATUS_CLS = { pendente: 'pend', confirmado: 'ok', revisao: 'rev', cancelado: 'canc' };

function fmtDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('pt-PT', { day: 'numeric', month: 'short', year: 'numeric' });
}
function fmtDur(m) { return m === 90 ? '1h30' : '1h'; }

export default function BookingsTab() {
  const [filters, setFilters] = useState({ q: '', status: 'all', regime: 'all', local_consulta: '', date_from: '', date_to: '' });
  const [data, setData] = useState({ bookings: [], summary: {} });
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ total: 0, pages: 1, per_page: 30 });
  const [locations, setLocations] = useState([]);
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [order, setOrder] = useState('desc');
  const [toast, setToast] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [pendingCancel, setPendingCancel] = useState(null);
  const [busyAction, setBusyAction] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'));
    params.page = page;
    params.per_page = 30;
    params.order = order;
    try {
      const result = await adminApi.bookings(params);
      setData(result);
      setPagination(result.pagination || { total: 0, pages: 1, per_page: 30 });
    } finally { setLoading(false); }
  }, [filters, page, order]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { adminApi.locations().then((r) => setLocations(r.locations)).catch(() => {}); }, []);

  // Sorting is applied server-side, so flipping it has to restart at page 1 —
  // page 3 of the old order is a different slice of the new one.
  const toggleOrder = () => {
    setOrder((o) => (o === 'desc' ? 'asc' : 'desc'));
    setPage(1);
  };

  const set = (k) => (e) => {
    setFilters((f) => ({ ...f, [k]: e.target.value }));
    setPage(1);
  };

  // Cancel and delete differ only in the call and the wording; both confirm in a
  // dialog, report through a toast, and reload on success.
  const runAction = async (ref, call, done, failed, clear) => {
    setBusyAction(true);
    try {
      await call(ref);
      clear(null);
      setToast({ message: done, tone: 'ok' });
      load();
    } catch {
      setToast({ message: failed, tone: 'err' });
    } finally {
      setBusyAction(false);
    }
  };

  const cancel = () => runAction(
    pendingCancel, adminApi.cancelBooking,
    `Marcação ${pendingCancel} cancelada.`,
    `Não foi possível cancelar a marcação ${pendingCancel}.`,
    setPendingCancel,
  );

  const remove = () => runAction(
    pendingDelete, adminApi.deleteBooking,
    `Marcação ${pendingDelete} eliminada.`,
    `Não foi possível eliminar a marcação ${pendingDelete}.`,
    setPendingDelete,
  );

  return (
    <div className="tab">
      <div className="filters">
        <div className="fld grow"><label>Pesquisar</label>
          <input placeholder="Nome, email ou referência…" value={filters.q} onChange={set('q')} /></div>
        <div className="fld"><label>Estado</label>
          <select value={filters.status} onChange={set('status')}>
            <option value="all">Todos</option><option value="pendente">Pendente</option><option value="confirmado">Confirmado</option><option value="revisao">Necessita Alteração</option><option value="cancelado">Cancelado</option>
          </select></div>
        <div className="fld"><label>Regime</label>
          <select value={filters.regime} onChange={set('regime')}>
            <option value="all">Todos</option><option value="presencial">Presencial</option><option value="online">Online</option>
          </select></div>
        <div className="fld"><label>Local</label>
          <select value={filters.local_consulta} onChange={set('local_consulta')}>
            <option value="">Todos</option>{locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select></div>
        <div className="fld"><label>De</label><input type="date" value={filters.date_from} onChange={set('date_from')} /></div>
        <div className="fld"><label>Até</label><input type="date" value={filters.date_to} onChange={set('date_to')} /></div>
      </div>

      <div className="tbl-actions">
        <button className="btn-add" onClick={() => setCreating(true)}>+ Nova marcação</button>
      </div>

      <div className="table-wrap">
        <table className="adm-table">
          <thead><tr>
            <th>Ref.</th>
            <th>
              <button type="button" className="th-sort" onClick={toggleOrder}
                      title={order === 'desc' ? 'Mais recentes primeiro' : 'Mais antigas primeiro'}>
                Data / Hora <span className="th-arrow">{order === 'desc' ? '↓' : '↑'}</span>
              </button>
            </th>
            <th>Cliente</th><th>Consulta</th><th>Regime / Local</th><th>Preço</th><th>Estado</th><th>Ações</th>
          </tr></thead>
          <tbody>
            {data.bookings.map((b) => (
              <tr key={b.reference} className={b.status === 'cancelado' ? 'row-canc' : ''}>
                <td data-label="Ref." className="ref">{b.reference}</td>
                <td data-label="Data">{fmtDate(b.slot_date)}<div className="sub">{b.slot_time} · {fmtDur(b.duration_minutes)}</div></td>
                <td data-label="Cliente">{b.nome}<div className="sub">{b.email} · {b.contacto}</div></td>
                <td data-label="Consulta">{b.tipo_consulta}<div className="sub">{b.sujeito} · {b.idade}</div></td>
                <td data-label="Regime"><span className={`pill ${b.regime === 'online' ? 'onl' : 'pres'}`}>{REGIME_LABEL[b.regime] || b.regime}</span>{b.local_consulta && <div className="sub">{b.local_consulta}</div>}</td>
                <td data-label="Preço">{Number(b.price).toFixed(0)}€</td>
                <td data-label="Estado"><span className={`pill ${STATUS_CLS[b.status] || 'ok'}`}>{STATUS_LABEL[b.status] || b.status}</span></td>
                <td data-label="Ações"><div className="acts">
                  <button className="ic" title="Editar" onClick={() => setEditing(b)}>✎</button>
                  {b.status !== 'cancelado' && <button className="ic" title="Cancelar" onClick={() => setPendingCancel(b.reference)}>⊘</button>}
                  <button className="ic" title="Eliminar" onClick={() => setPendingDelete(b.reference)}>🗑</button>
                </div></td>
              </tr>
            ))}
            {!loading && data.bookings.length === 0 && <tr><td colSpan="8" className="empty">Sem marcações para estes filtros.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="adm-foot">
        <span>{data.summary.count || 0} marcações · {data.summary.confirmed_count || 0} confirmadas</span>
        <span>Faturado no período: <strong>{Number(data.summary.faturado || 0).toFixed(0)}€</strong></span>
      </div>

      {pagination.pages > 1 && (
        <div className="pagination">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Anterior</button>
          <span>Página {page} de {pagination.pages}</span>
          <button disabled={page >= pagination.pages} onClick={() => setPage((p) => p + 1)}>Seguinte →</button>
        </div>
      )}

      {editing && (
        <EditBookingModal
          booking={editing} locations={locations}
          onClose={() => setEditing(null)}
          onSaved={() => {
            const ref = editing.reference;
            setEditing(null);
            setToast({ message: `Marcação ${ref} atualizada.`, tone: 'ok' });
            load();
          }}
        />
      )}
      {creating && (
        <EditBookingModal
          create locations={locations}
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            setPage(1);
            setToast({ message: 'Marcação criada.', tone: 'ok' });
            load();
          }}
        />
      )}
      {pendingCancel && (
        <ConfirmModal
          title="Cancelar marcação"
          body={`A marcação ${pendingCancel} será cancelada e o cliente notificado por email.`}
          confirmLabel="Cancelar marcação" cancelLabel="Voltar" danger busy={busyAction}
          onConfirm={cancel}
          onCancel={() => setPendingCancel(null)}
        />
      )}
      {pendingDelete && (
        <ConfirmModal
          title="Eliminar marcação"
          body={`A marcação ${pendingDelete} será eliminada permanentemente. Esta ação não pode ser revertida.`}
          confirmLabel="Eliminar" danger busy={busyAction}
          onConfirm={remove}
          onCancel={() => setPendingDelete(null)}
        />
      )}
      <Toast toast={toast} onDone={() => setToast(null)} />
    </div>
  );
}
