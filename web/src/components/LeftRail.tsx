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

      {/* Feed Status Card (6 Domains) */}
      <div className='panel-surface' style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className='panel-title'>Feed Status</div>
          <span style={{ fontSize: 11, color: s.feedCutPct > 0 ? 'var(--color-watch)' : 'var(--color-low)', fontWeight: 600 }}>
            {s.feedCutPct > 0 ? `${s.feedCutPct}% Stress Cut` : '6/6 Operational'}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            {
              domain: 'Power',
              icon: '⚡',
              provider: 'MSEDCL SCADA',
              status: s.feedCutPct > 40 ? 'offline' : s.feedCutPct > 15 ? 'degraded' : 'live'
            },
            {
              domain: 'Transit',
              icon: '🚌',
              provider: 'Aapli Bus GTFS',
              status: s.feedCutPct > 30 ? 'degraded' : s.feedCutPct > 50 ? 'offline' : 'live'
            },
            {
              domain: 'Road',
              icon: '🚧',
              provider: 'Traffic Police GIS',
              status: s.feedCutPct > 45 ? 'degraded' : 'live'
            },
            {
              domain: 'Water',
              icon: '💧',
              provider: 'OCW Pressure Telemetry',
              status: s.feedCutPct > 25 ? 'degraded' : 'live'
            },
            {
              domain: 'Comms',
              icon: '📡',
              provider: 'BTS Tower Load',
              status: s.feedCutPct > 35 ? 'degraded' : 'live'
            },
            {
              domain: 'Health',
              icon: '🏥',
              provider: 'EMRI 108 Ambulance',
              status: s.feedCutPct > 55 ? 'offline' : 'live'
            }
          ].map((feed) => {
            const isLive = feed.status === 'live';
            const isDegraded = feed.status === 'degraded';
            const badgeColor = isLive ? 'var(--color-low)' : isDegraded ? 'var(--color-watch)' : 'var(--color-high)';
            const badgeBg = isLive ? 'rgba(25, 135, 84, 0.12)' : isDegraded ? 'rgba(255, 193, 7, 0.12)' : 'rgba(220, 53, 69, 0.12)';

            return (
              <div
                key={feed.domain}
                className='panel-raised'
                style={{
                  padding: '8px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderRadius: 6
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14 }}>{feed.icon}</span>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>
                      {feed.domain}
                    </div>
                    <div className='text-muted' style={{ fontSize: 10 }}>
                      {feed.provider}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: badgeColor,
                      boxShadow: `0 0 6px ${badgeColor}`
                    }}
                  />
                  <span
                    style={{
                      fontSize: 10.5,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      color: badgeColor,
                      backgroundColor: badgeBg,
                      padding: '2px 6px',
                      borderRadius: 4
                    }}
                  >
                    {feed.status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
