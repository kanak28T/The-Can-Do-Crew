import { useAppStore } from '../store/useAppStore';
import { useSSE } from '../hooks/useSSE';

export default function Header() {
  const { theme, toggleTheme, connectionStatus, lastUpdateTime } = useAppStore();
  useSSE();

  const statusColor = connectionStatus === 'live'
    ? '#22c55e'
    : connectionStatus === 'reconnecting'
    ? '#f59e0b'
    : '#ef4444';
  const statusLabel = connectionStatus === 'live'
    ? 'Live'
    : connectionStatus === 'reconnecting'
    ? 'Reconnecting…'
    : 'Offline';

  const isMock = (import.meta as any).env.VITE_USE_MOCK === 'true';

  return (
    <header
      style={{
        gridColumn: '1 / -1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        /* Always use a solid dark-ish surface regardless of theme so text is always readable */
        backgroundColor: theme === 'dark' ? '#151F2B' : '#ffffff',
        borderRadius: '8px',
        border: '1px solid ' + (theme === 'dark' ? 'rgba(255,255,255,0.10)' : '#DEE2E6'),
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        position: 'relative',
        zIndex: 10,
      }}
    >
      {/* Left — brand + status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* Logo mark */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 15, fontWeight: 900, color: '#fff', flexShrink: 0,
          }}>U</div>
          <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: theme === 'dark' ? '#f1f5f9' : '#1e293b', letterSpacing: '-0.01em' }}>
            UrbanPulse
          </h1>
        </div>

        <div style={{ width: 1, height: 20, backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.15)' : '#DEE2E6' }} />

        <span style={{ fontSize: 12, color: theme === 'dark' ? '#94a3b8' : '#64748b', fontWeight: 500 }}>
          Nagpur Crisis Intelligence
        </span>

        {/* Connection status pill */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px',
          backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.07)' : '#f8fafc',
          borderRadius: 20,
          border: `1px solid ${statusColor}40`,
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            backgroundColor: statusColor,
            boxShadow: `0 0 6px ${statusColor}`,
            animation: connectionStatus === 'live' ? 'pulse 2s infinite' : 'none',
          }} />
          <span style={{ fontSize: 11, fontWeight: 600, color: statusColor }}>{statusLabel}</span>
        </div>

        {lastUpdateTime && (
          <span style={{ fontSize: 11, color: theme === 'dark' ? '#64748b' : '#94a3b8' }}>
            Last update: {lastUpdateTime}
          </span>
        )}
      </div>

      {/* Right — badges + theme toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {isMock && (
          <span style={{
            fontSize: 10, padding: '3px 8px',
            backgroundColor: 'rgba(245,158,11,0.15)',
            color: '#f59e0b',
            borderRadius: 4,
            border: '1px solid rgba(245,158,11,0.30)',
            fontWeight: 700, letterSpacing: '0.06em',
          }}>
            SIMULATION
          </span>
        )}

        {/* Privacy badge */}
        <span style={{
          fontSize: 10, padding: '3px 8px',
          backgroundColor: 'rgba(34,197,94,0.12)',
          color: '#22c55e',
          borderRadius: 4,
          border: '1px solid rgba(34,197,94,0.25)',
          fontWeight: 600,
        }}>
          🔒 Zero PII
        </span>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          style={{
            padding: '5px 14px',
            fontSize: 12,
            backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.10)' : '#f1f5f9',
            color: theme === 'dark' ? '#e2e8f0' : '#374151',
            border: theme === 'dark' ? '1px solid rgba(255,255,255,0.15)' : '1px solid #d1d5db',
            borderRadius: 6,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background 0.15s',
          }}
        >
          {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </header>
  );
}
