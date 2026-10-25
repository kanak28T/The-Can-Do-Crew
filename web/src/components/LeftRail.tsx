import { useAppStore } from '../store/useAppStore';

export default function LeftRail() {
  const s = useAppStore();
  const statusColor = (level: string) => level === 'high' ? 'var(--color-high)' : level === 'watch' ? 'var(--color-watch)' : level === 'low' ? 'var(--color-low)' : 'var(--color-unknown)';
  const liveItems = [
    { label: 'High zones', value: s.highZones, color: 'var(--color-high)' },
    { label: 'Watch zones', value: s.watchZones, color: 'var(--color-watch)' },
    { label: 'Unknown cells', value: s.unknownCells, color: 'var(--color-unknown)' },
    { label: 'Event delay', value: s.eventDelay.toFixed(1) + 's', color: 'var(--color-accent)' },
  ];

  return (
    <div style={{ width: 280, display: 'flex', flexDirection: 'column', gap: 12, padding: 12, overflowY: 'auto' }}>
      {/* Stress Console */}
      <div className='panel-surface' style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className='panel-title'>Stress console</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => s.setSimRunning(true)} className='text-secondary' style={{ flex: 1, background: 'var(--color-raised)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '6px 0', fontSize: 12.5, color: s.simRunning ? 'var(--color-low)' : 'var(--color-text)' }}>Start</button>
          <button onClick={() => s.setSimPaused(!s.simPaused)} className='text-secondary' style={{ flex: 1, background: 'var(--color-raised)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '6px 0', fontSize: 12.5 }}>Pause</button>
          <button onClick={() => { s.setSimRunning(false); s.setSimPaused(false); s.setFeedCutPct(0); }} className='text-secondary' style={{ flex: 1, background: 'var(--color-raised)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '6px 0', fontSize: 12.5 }}>Reset</button>
        </div>
        <div>
          <div className='text-muted' style={{ marginBottom: 4 }}>Speed: {s.simSpeed}x</div>
          <input type='range' min='0.5' max='5' step='0.5' value={s.simSpeed} onChange={(e) => s.setSimSpeed(Number(e.target.value))} style={{ width: '100%' }} aria-label='Simulation speed' />
        </div>
        <div>
          <div className='text-muted' style={{ marginBottom: 4 }}>Cut feeds: {s.feedCutPct}%</div>
          <input type='range' min='0' max='60' step='5' value={s.feedCutPct} onChange={(e) => s.setFeedCutPct(Number(e.target.value))} style={{ width: '100%' }} aria-label='Feed cut percentage' />
        </div>
        <div>
          <div className='text-muted' style={{ marginBottom: 4 }}>Loss pattern</div>
          <select value={s.lossPattern} onChange={(e) => s.setLossPattern(e.target.value as any)} className='text-secondary' style={{ width: '100%', backgroundColor: 'var(--color-raised)', border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 8px', fontSize: 12.5 }} aria-label='Loss pattern'>
            <option value='random'>Random</option>
            <option value='domain'>By domain</option>
            <option value='area'>By area</option>
          </select>
        </div>
      </div>
      {/* Live Numbers */}
      <div className='panel-surface' style={{ padding: 16 }}>
        <div className='panel-title' style={{ marginBottom: 12 }}>Live numbers</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {liveItems.map((item) => (
            <div key={item.label} className='panel-raised' style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span className='text-muted' style={{ fontSize: 12.5 }}>{item.label}</span>
              <span className='text-big' style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
