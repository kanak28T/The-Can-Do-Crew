import { useAppStore } from '../store/useAppStore';

export default function RightPanel() {
  const selectedCellH3 = useAppStore((s) => s.selectedCellH3);
  const cells = useAppStore((s) => s.cells);
  const zones = useAppStore((s) => s.zones);

  const cell = selectedCellH3 ? cells.get(selectedCellH3) : null;
  const zone = zones.find((z) => z.cells.includes(selectedCellH3 || '')) || zones[0];

  if (!cell && !zone) {
    return (
      <div style={{ width: 360, padding: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className='panel-surface' style={{ padding: 24, textAlign: 'center' }}>
          <div className='text-muted'>Select a zone on the map to see details.</div>
        </div>
      </div>
    );
  }

  const risk = cell ? cell.risk : zone ? zone.risk : 0;
  const lo = cell ? cell.lo : zone ? zone.lo : 0;
  const hi = cell ? cell.hi : zone ? zone.hi : 1;
  const confidence = cell ? cell.confidence : zone ? zone.confidence : 0.85;
  const name = zone ? zone.name : (cell ? cell.h3 : 'Unknown');
  const riskColor = risk >= 0.7 ? 'var(--color-high)' : risk >= 0.4 ? 'var(--color-watch)' : 'var(--color-low)';

  const mockDrivers = [
    { key: 'power', label: 'Feeder F-12 low voltage', delta: 0.22, evidence: 'Voltage drop -35%' },
    { key: 'road', label: 'Road R-14 closed', delta: 0.18, evidence: 'Bus route 4 suspended' },
    { key: 'health', label: 'Distance to clinic > 2.2km', delta: 0.10, evidence: 'Nearest clinic closed' },
  ];

  return (
    <div style={{ width: 360, padding: 16, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className='panel-surface' style={{ padding: 16 }}>
        <div className='panel-title' style={{ marginBottom: 4 }}>{name}</div>
        {cell && <div className='text-muted' style={{ fontSize: 12.5, marginBottom: 12 }}>{cell.h3}</div>}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
          <span className='text-big' style={{ color: riskColor }}>{Math.round(risk * 100)}%</span>
          <span className='text-muted'>range {Math.round(lo * 100)}-{Math.round(hi * 100)}%</span>
        </div>
        <div className='text-secondary'>Confidence: {Math.round(confidence * 100)}%</div>
        {cell && cell.imputed && <div className='text-muted' style={{ marginTop: 8, fontStyle: 'italic' }}>Some inputs were imputed.</div>}
      </div>

      <div className='panel-surface' style={{ padding: 16 }}>
        <div className='panel-title' style={{ marginBottom: 12 }}>Drivers</div>
        {mockDrivers.map((d) => (
          <div key={d.key} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span className='text-secondary'>{d.label}</span>
              <span className='text-muted' style={{ color: 'var(--color-high)' }}>-{Math.round(d.delta * 100)}%</span>
            </div>
            <div style={{ height: 6, backgroundColor: 'var(--color-raised)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: Math.round(d.delta * 100) + '%', backgroundColor: 'var(--color-high)', borderRadius: 3 }} />
            </div>
            <div className='text-muted' style={{ fontSize: 12, marginTop: 2 }}>{d.evidence}</div>
          </div>
        ))}
      </div>

      <div className='panel-surface' style={{ padding: 16 }}>
        <div className='panel-title' style={{ marginBottom: 12 }}>What-if</div>
        <div className='text-secondary' style={{ marginBottom: 8 }}>Reopen road R-14 and restore route 4</div>
        <div className='text-muted'>Risk: {Math.round(risk * 100)}% to {Math.round(risk * 0.46 * 100)}%</div>
      </div>

      <div className='panel-surface' style={{ padding: 16 }}>
        <div className='panel-title' style={{ marginBottom: 12 }}>Recommended actions</div>
        <div className='text-secondary'>1. Deploy mobile generator to substation C</div>
        <div className='text-secondary'>2. Dispatch clearance crew to R-14</div>
        <div className='text-secondary'>3. Emergency water tanker deployment</div>
      </div>
    </div>
  );
}
