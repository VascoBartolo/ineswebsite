import { useState } from 'react';

export default function MiniBarChart({ series }) {
  const [metric, setMetric] = useState('lucro'); // 'lucro' | 'count'
  const key = metric === 'lucro' ? 'lucro_liquido' : 'count';
  const max = Math.max(1, ...series.map((s) => s[key]));

  return (
    <div className="card">
      <div className="chart-head">
        <h3>Evolução</h3>
        <div className="metric-seg">
          <button className={metric === 'count' ? 'on' : ''} onClick={() => setMetric('count')}>Nº consultas</button>
          <button className={metric === 'lucro' ? 'on' : ''} onClick={() => setMetric('lucro')}>Lucro líquido</button>
        </div>
      </div>
      <div className="chart-sub">a mostrar {metric === 'lucro' ? 'lucro líquido (€)' : 'nº de consultas'} por período</div>
      <div className="chart">
        {series.length === 0 && <p className="empty">Sem dados no período.</p>}
        {series.map((s) => (
          <div className="bar-col" key={s.period}>
            <div className="bar" style={{ height: `${(s[key] / max) * 100}%` }}>
              <b>{metric === 'lucro' ? `${Math.round(s.lucro_liquido)}€` : s.count}</b>
            </div>
            <small>{s.period.replace('2026-', '').replace('W', 'S')}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
