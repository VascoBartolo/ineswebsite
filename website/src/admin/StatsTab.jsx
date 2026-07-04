import { useEffect, useState, useCallback } from 'react';
import { adminApi } from './adminApi';
import MiniBarChart from './MiniBarChart';

const eur = (n) => `${Number(n || 0).toLocaleString('pt-PT', { maximumFractionDigits: 0 })}€`;

export default function StatsTab() {
  const [filters, setFilters] = useState({ date_from: '', date_to: '', regime: 'all', local_consulta: '', group_by: 'week' });
  const [locations, setLocations] = useState([]);
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'));
    if (!params.group_by) params.group_by = filters.group_by;
    setData(await adminApi.stats({ ...params, group_by: filters.group_by }));
  }, [filters]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { adminApi.locations().then((r) => setLocations(r.locations)).catch(() => {}); }, []);

  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  if (!data) return <div className="tab">A carregar…</div>;

  return (
    <div className="tab">
      <div className="filters">
        <div className="fld"><label>De</label><input type="date" value={filters.date_from} onChange={set('date_from')} /></div>
        <div className="fld"><label>Até</label><input type="date" value={filters.date_to} onChange={set('date_to')} /></div>
        <div className="fld"><label>Regime</label>
          <select value={filters.regime} onChange={set('regime')}>
            <option value="all">Todos</option><option value="presencial">Presencial</option><option value="online">Online</option>
          </select></div>
        <div className="fld"><label>Local</label>
          <select value={filters.local_consulta} onChange={set('local_consulta')}>
            <option value="">Todos</option>{locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select></div>
        <div className="fld"><label>Agrupar por</label>
          <div className="seg">
            {['day', 'week', 'month'].map((g) => (
              <button key={g} className={filters.group_by === g ? 'on' : ''} onClick={() => setFilters((f) => ({ ...f, group_by: g }))}>
                {g === 'day' ? 'Dia' : g === 'week' ? 'Semana' : 'Mês'}
              </button>
            ))}
          </div></div>
      </div>

      <div className="kpis">
        <div className="kpi"><div className="lab">Marcações</div><div className="val">{data.count}</div><div className="delta">confirmadas</div></div>
        <div className="kpi"><div className="lab">Faturado</div><div className="val">{eur(data.faturado)}</div><div className="delta">valor cobrado</div></div>
        <div className="kpi hi"><div className="lab">Lucro líquido</div><div className="val">{eur(data.lucro_liquido)}</div><div className="delta">70% pres · 100% online</div></div>
        <div className="kpi"><div className="lab">Canceladas</div><div className="val muted">{data.cancelled_count}</div><div className="delta">excluídas</div></div>
      </div>

      <div className="grid2">
        <MiniBarChart series={data.series} />
        <div className="card">
          <h3>Presencial vs Online</h3>
          {['presencial', 'online'].map((r) => (
            <div className="split-row" key={r}>
              <div className="split-line">
                <span className="nm"><span className={`dot ${r}`} />{r === 'presencial' ? 'Presencial' : 'Online'}</span>
                <span className="ct">{data.by_regime[r].count} · <strong>{eur(data.by_regime[r].lucro)}</strong> <span className="g">de {eur(data.by_regime[r].faturado)}</span></span>
              </div>
            </div>
          ))}
          <h3 style={{ marginTop: 22 }}>Por local <span>lucro líquido</span></h3>
          {data.by_location.length === 0 && <p className="empty">Sem presenciais no período.</p>}
          {data.by_location.map((l) => (
            <div className="loc" key={l.local_consulta}><span>{l.local_consulta}</span><span><span className="r">{eur(l.lucro)}</span> <span className="g">/ {l.count}</span></span></div>
          ))}
        </div>
      </div>
    </div>
  );
}
