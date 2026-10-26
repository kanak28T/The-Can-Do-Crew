import { useAppStore } from '../store/useAppStore';
import type { InterventionLogEntry } from '../types';

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString([], { day: '2-digit', month: 'short' });
}

function RiskBar({ before, after }: { before: number; after: number }) {
  const drop = before - after;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ fontSize: 11, color: 'var(--color-high)', fontWeight: 600 }}>
        {Math.round(before * 100)}%
      </span>
      <div style={{ position: 'relative', width: 56, height: 6, backgroundColor: 'var(--color-raised)', borderRadius: 3, overflow: 'hidden' }}>
        {/* Before bar (full) */}
        <div style={{ position: 'absolute', left: 0, top: 0, width: `${before * 100}%`, height: '100%', backgroundColor: 'var(--color-high)', opacity: 0.35, borderRadius: 3 }} />
        {/* After bar */}
        <div style={{ position: 'absolute', left: 0, top: 0, width: `${after * 100}%`, height: '100%', backgroundColor: 'var(--color-low)', borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, color: 'var(--color-low)', fontWeight: 600 }}>
        {Math.round(after * 100)}%
      </span>
      <span style={{ fontSize: 10, color: 'var(--color-muted)' }}>
        (↓{Math.round(drop * 100)}pp)
      </span>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: InterventionLogEntry['decision'] }) {
  const cfg = {
    approved:   { bg: 'rgba(16,185,129,0.12)', color: '#10b981', icon: '✓', label: 'Approved' },
    rejected:   { bg: 'rgba(239,68,68,0.12)',  color: '#ef4444', icon: '✕', label: 'Rejected' },
    dispatched: { bg: 'rgba(99,102,241,0.12)', color: '#818cf8', icon: '→', label: 'Dispatched' },
  }[decision];
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 4, backgroundColor: cfg.bg, color: cfg.color, fontSize: 11, fontWeight: 700 }}>
      <span>{cfg.icon}</span>{cfg.label}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: InterventionLogEntry['priority'] }) {
  const cfg = {
    P1: { bg: 'rgba(239,68,68,0.12)',   color: '#ef4444' },
    P2: { bg: 'rgba(245,158,11,0.12)',  color: '#f59e0b' },
    P3: { bg: 'rgba(99,102,241,0.12)', color: '#818cf8' },
  }[priority];
  return (
    <span style={{ padding: '1px 6px', borderRadius: 3, backgroundColor: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 800 }}>
      {priority}
    </span>
  );
}

export default function InterventionLog() {
  const log = useAppStore((s) => s.interventionLog);
  const clearInterventionLog = useAppStore((s) => s.clearInterventionLog);

  if (log.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 10, color: 'var(--color-muted)', padding: 24 }}>
        <span style={{ fontSize: 28 }}>📋</span>
        <span style={{ fontSize: 13, fontWeight: 600 }}>No interventions logged yet</span>
        <span style={{ fontSize: 11, textAlign: 'center', maxWidth: 280 }}>
          Approve or reject a dispatch recommendation in the "Dispatch Actions" tab to begin the audit trail.
        </span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }} role="region" aria-label="Intervention Audit Log">

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Intervention Audit Trail
          </span>
          <span style={{ fontSize: 11, padding: '1px 7px', borderRadius: 10, backgroundColor: 'var(--color-raised)', color: 'var(--color-secondary)', border: '1px solid var(--color-border)' }}>
            {log.length} action{log.length !== 1 ? 's' : ''}
          </span>
        </div>
        <button
          type="button"
          onClick={clearInterventionLog}
          style={{ fontSize: 10, color: 'var(--color-muted)', background: 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 8px', cursor: 'pointer' }}
          aria-label="Clear intervention log"
        >
          Clear log
        </button>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'auto', borderRadius: 6, border: '1px solid var(--color-border)', backgroundColor: 'rgba(0,0,0,0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }} aria-label="Intervention log table">
          <thead>
            <tr style={{ backgroundColor: 'var(--color-raised)', borderBottom: '1px solid var(--color-border)' }}>
              {['Time', 'Pri', 'Zone', 'Intervention', 'Resource', 'Risk Δ', 'ETA', 'Decision', 'Actor'].map((h) => (
                <th key={h} scope="col" style={{ padding: '6px 10px', textAlign: 'left', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-secondary)', whiteSpace: 'nowrap' }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {log.map((entry, i) => (
              <tr
                key={entry.id + '-' + entry.timestamp}
                style={{
                  borderBottom: '1px solid var(--color-border)',
                  backgroundColor: i === 0 ? 'rgba(99,102,241,0.04)' : 'transparent',
                  transition: 'background 0.15s',
                }}
              >
                {/* Time */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text)', fontFamily: 'monospace' }}>
                    {formatTime(entry.timestamp)}
                  </div>
                  <div style={{ fontSize: 9, color: 'var(--color-muted)' }}>
                    {formatDate(entry.timestamp)}
                  </div>
                </td>

                {/* Priority */}
                <td style={{ padding: '7px 10px' }}>
                  <PriorityBadge priority={entry.priority} />
                </td>

                {/* Zone */}
                <td style={{ padding: '7px 10px', maxWidth: 160 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text)', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.zone}
                  </span>
                </td>

                {/* Action */}
                <td style={{ padding: '7px 10px', minWidth: 180, maxWidth: 240 }}>
                  <span style={{ fontSize: 11, color: 'var(--color-text)', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={entry.action}>
                    {entry.action}
                  </span>
                </td>

                {/* Resource */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--color-secondary)' }}>
                    {entry.resource}
                  </span>
                </td>

                {/* Risk Δ */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <RiskBar before={entry.risk_before} after={entry.risk_after} />
                </td>

                {/* ETA */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: 11, color: 'var(--color-secondary)' }}>{entry.eta}</span>
                </td>

                {/* Decision */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <DecisionBadge decision={entry.decision} />
                </td>

                {/* Actor */}
                <td style={{ padding: '7px 10px', whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: 10, color: 'var(--color-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    {entry.actor}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      <div style={{ marginTop: 8, display: 'flex', gap: 16, flexShrink: 0 }}>
        {(['approved', 'rejected', 'dispatched'] as const).map((decision) => {
          const count = log.filter((e) => e.decision === decision).length;
          const color = decision === 'approved' ? '#10b981' : decision === 'rejected' ? '#ef4444' : '#818cf8';
          return (
            <div key={decision} style={{ fontSize: 11, color: 'var(--color-muted)', display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ fontWeight: 700, color }}>{count}</span>
              <span style={{ textTransform: 'capitalize' }}>{decision}</span>
            </div>
          );
        })}
        <div style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--color-muted)' }}>
          Avg risk reduction: {log.filter(e => e.decision === 'approved').length > 0
            ? Math.round(log.filter(e => e.decision === 'approved').reduce((s, e) => s + e.expected_risk_drop, 0) / log.filter(e => e.decision === 'approved').length * 100)
            : 0}pp per approved action
        </div>
      </div>
    </div>
  );
}
