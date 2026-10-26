import { useAppStore } from '../store/useAppStore';
import { useSSE } from '../hooks/useSSE';

export default function Header() {
  const { theme, toggleTheme, connectionStatus, lastUpdateTime } = useAppStore();
  useSSE();
  const statusColor = connectionStatus === 'live' ? '#198754' : connectionStatus === 'reconnecting' ? '#FFC107' : '#DC3545';
  const statusLabel = connectionStatus === 'live' ? 'Live' : connectionStatus === 'reconnecting' ? 'Reconnecting' : 'Offline';
  const isMock = (import.meta as any).env.VITE_USE_MOCK === 'true';
  return (
    <header style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: '8px', border: '1px solid #DEE2E6', boxShadow: '0 2px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, color: '#212529' }}>UrbanPulse</h1>
        <span style={{ fontSize: 13, color: '#6C757D', borderLeft: '1px solid #DEE2E6', paddingLeft: 16 }}>Nagpur Crisis Intelligence</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', backgroundColor: '#F1F3F5', borderRadius: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: statusColor }} />
          <span style={{ fontSize: 12, fontWeight: 500, color: statusColor }}>{statusLabel}</span>
        </div>
        <span style={{ fontSize: 12, color: '#495057' }}>{lastUpdateTime || 'Waiting for data'}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isMock && <span style={{ fontSize: 11, padding: '4px 8px', backgroundColor: '#FFF3CD', color: '#856404', borderRadius: 4, border: '1px solid #FFE69C', fontWeight: 500 }}>SIMULATION</span>}
        <button onClick={toggleTheme} style={{ padding: '6px 16px', fontSize: 13, backgroundColor: '#0D6EFD', color: 'white', border: 'none', borderRadius: 4, fontWeight: 500, cursor: 'pointer' }}>{theme === 'dark' ? '☀️ Light' : '🌙 Dark'}</button>
      </div>
    </header>
  );
}
