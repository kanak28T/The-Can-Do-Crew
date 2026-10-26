import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../lib/api';
import type { ZoneData, Driver, RecommendedAction } from '../types';

/* ── Detail Modal ──────────────────────────────────────────── */

function ZoneDetailModal({ zone, onClose }: { zone: ZoneData; onClose: () => void }) {
  const riskPct = Math.round(zone.risk * 100);
  const riskColor = zone.risk >= 0.7 ? '#ef4444' : zone.risk >= 0.4 ? '#f59e0b' : '#10b981';
  const drivers = zone.drivers || [];
  const actions = zone.actions || [];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0,0,0,0.5)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: '12px',
          width: '520px',
          maxHeight: '80vh',
          overflowY: 'auto',
          boxShadow: '0 24px 60px rgba(0,0,0,0.25)',
          animation: 'slideUp 0.2s ease-out',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--color-raised)',
          borderRadius: '12px 12px 0 0',
        }}>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-text)' }}>
              {zone.name}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--color-muted)', marginTop: 2 }}>
              Zone {zone.id} · {zone.cells?.length || 0} cell{(zone.cells?.length || 0) !== 1 ? 's' : ''}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: 'var(--color-muted)',
              padding: '4px 8px',
              borderRadius: '4px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Risk Overview */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '72px',
              height: '72px',
              borderRadius: '50%',
              background: `conic-gradient(${riskColor} ${riskPct * 3.6}deg, rgba(0,0,0,0.06) 0deg)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'var(--color-surface)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
              }}>
                <span style={{ fontSize: '18px', fontWeight: 800, color: riskColor, lineHeight: 1 }}>
                  {riskPct}%
                </span>
                <span style={{ fontSize: '8px', color: 'var(--color-muted)', fontWeight: 600 }}>RISK</span>
              </div>
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ backgroundColor: 'var(--color-raised)', padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '9px', color: 'var(--color-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Range</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text)', marginTop: 2 }}>
                    {Math.round(zone.lo * 100)}% – {Math.round(zone.hi * 100)}%
                  </div>
                </div>
                <div style={{ backgroundColor: 'var(--color-raised)', padding: '8px 10px', borderRadius: '6px', border: '1px solid var(--color-border)' }}>
                  <div style={{ fontSize: '9px', color: 'var(--color-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Confidence</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text)', marginTop: 2 }}>
                    {Math.round(zone.confidence * 100)}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Drivers */}
        {drivers.length > 0 && (
          <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: '10px', letterSpacing: '0.04em' }}>
              ⚠️ Vulnerability Drivers
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {drivers.map((d, i) => (
                <div key={i} style={{
                  backgroundColor: 'var(--color-raised)',
                  padding: '10px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--color-border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '20px',
                        height: '20px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 700,
                        backgroundColor: driverKeyColor(d.key) + '18',
                        color: driverKeyColor(d.key),
                      }}>
                        {driverKeyIcon(d.key)}
                      </span>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text)' }}>
                        {d.label}
                      </span>
                    </div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: '#ef4444',
                      backgroundColor: '#ef444415',
                      padding: '2px 6px',
                      borderRadius: '3px',
                    }}>
                      +{Math.round(d.delta * 100)}%
                    </span>
                  </div>
                  <div style={{ height: '4px', backgroundColor: 'rgba(0,0,0,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${Math.min(d.delta * 100 * 3, 100)}%`,
                      backgroundColor: driverKeyColor(d.key),
                      borderRadius: '2px',
                      transition: 'width 0.3s ease',
                    }} />
                  </div>
                  {d.evidence && (
                    <div style={{ fontSize: '10px', color: 'var(--color-muted)', marginTop: '4px', fontStyle: 'italic' }}>
                      {d.evidence}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Actions */}
        {actions.length > 0 && (
          <div style={{ padding: '14px 20px' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: '10px', letterSpacing: '0.04em' }}>
              🛡️ Recommended Interventions
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {actions.map((a, i) => (
                <div key={i} style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                  padding: '10px 12px',
                  borderRadius: '6px',
                }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text)', marginBottom: 4 }}>
                    {a.action}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px' }}>
                    <span style={{ color: riskColor, fontWeight: 700 }}>{riskPct}%</span>
                    <span style={{ color: 'var(--color-muted)' }}>→</span>
                    <span style={{ color: '#10b981', fontWeight: 700 }}>{Math.round(a.risk_after * 100)}%</span>
                    <span style={{ color: '#10b981', fontSize: '10px' }}>
                      (-{riskPct - Math.round(a.risk_after * 100)}% reduction)
                    </span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--color-muted)', marginTop: 2 }}>
                    Projected range: {Math.round(a.lo * 100)}%–{Math.round(a.hi * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cell IDs */}
        {zone.cells && zone.cells.length > 0 && (
          <div style={{ padding: '10px 20px 16px', borderTop: '1px solid var(--color-border)' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-muted)', marginBottom: 4 }}>
              H3 Cells: {zone.cells.map(c => c.substring(0, 10) + '…').join(', ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Helper functions ──────────────────────────────────────── */

function driverKeyColor(key: string): string {
  switch (key) {
    case 'power': return '#f59e0b';
    case 'road': return '#ef4444';
    case 'health': return '#8b5cf6';
    case 'water': return '#06b6d4';
    case 'comms': return '#3b82f6';
    case 'transit': return '#f97316';
    default: return '#64748b';
  }
}

function driverKeyIcon(key: string): string {
  switch (key) {
    case 'power': return '⚡';
    case 'road': return '🛣';
    case 'health': return '🏥';
    case 'water': return '💧';
    case 'comms': return '📡';
    case 'transit': return '🚌';
    default: return '📊';
  }
}

/* ── Zone Card (compact, clickable) ────────────────────────── */

function ZoneCard({ zone, onClick }: { zone: ZoneData; onClick: () => void }) {
  const riskPct = Math.round(zone.risk * 100);
  const riskColor = zone.risk >= 0.7 ? '#ef4444' : zone.risk >= 0.4 ? '#f59e0b' : '#10b981';
  const drivers = zone.drivers || [];
  const topDriver = drivers[0];

  return (
    <div
      onClick={onClick}
      style={{
        backgroundColor: 'var(--color-raised)',
        padding: '10px 12px',
        borderRadius: '8px',
        border: '1px solid var(--color-border)',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        minWidth: '200px',
        flex: '1 1 200px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '6px',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = riskColor;
        e.currentTarget.style.boxShadow = `0 0 0 1px ${riskColor}33, 0 4px 12px rgba(0,0,0,0.08)`;
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--color-border)';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'none';
      }}
    >
      {/* Top: Name + Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '6px' }}>
        <span style={{
          fontSize: '11.5px',
          fontWeight: 700,
          color: 'var(--color-text)',
          lineHeight: 1.3,
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical' as any,
        }}>
          {zone.name}
        </span>
        <span style={{
          fontSize: '9px',
          padding: '2px 6px',
          borderRadius: '3px',
          background: `${riskColor}15`,
          color: riskColor,
          fontWeight: 700,
          whiteSpace: 'nowrap',
          flexShrink: 0,
        }}>
          {zone.risk >= 0.7 ? 'HIGH' : zone.risk >= 0.4 ? 'WATCH' : 'LOW'}
        </span>
      </div>

      {/* Risk Score */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
        <span style={{ color: riskColor, fontSize: '22px', fontWeight: 800, lineHeight: 1 }}>
          {riskPct}%
        </span>
        <span style={{ fontSize: '10px', color: 'var(--color-muted)' }}>
          [{Math.round(zone.lo * 100)}–{Math.round(zone.hi * 100)}%]
        </span>
      </div>

      {/* Top driver preview */}
      {topDriver && (
        <div style={{
          fontSize: '10px',
          color: 'var(--color-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(0,0,0,0.03)',
          padding: '4px 6px',
          borderRadius: '4px',
        }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>
            {driverKeyIcon(topDriver.key)} {topDriver.label}
          </span>
          <span style={{ color: '#ef4444', fontWeight: 700, flexShrink: 0, marginLeft: '4px' }}>
            +{Math.round(topDriver.delta * 100)}%
          </span>
        </div>
      )}

      {/* Confidence + Driver count */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '9.5px',
        color: 'var(--color-muted)',
        paddingTop: '4px',
        borderTop: '1px dashed var(--color-border)',
      }}>
        <span>Confidence: <strong style={{ color: 'var(--color-text)' }}>{Math.round(zone.confidence * 100)}%</strong></span>
        <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>
          {drivers.length} driver{drivers.length !== 1 ? 's' : ''} · Click for detail →
        </span>
      </div>
    </div>
  );
}

/* ── Main Component ────────────────────────────────────────── */

export default function LandscapeDrivers() {
  const zones = useAppStore((s) => s.zones);
  const setZones = useAppStore((s) => s.setZones);
  const [detailZone, setDetailZone] = useState<ZoneData | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch zones from backend on mount
  useEffect(() => {
    if (zones.length > 0) return; // already have data from mock or prior fetch
    setLoading(true);
    api.getZones()
      .then((data) => {
        if (data && data.length > 0) setZones(data);
      })
      .catch((err) => console.warn('[LandscapeDrivers] Fetch zones error:', err))
      .finally(() => setLoading(false));
  }, []);

  const handleZoneClick = async (zone: ZoneData) => {
    // Try to fetch full detail with drivers/actions
    try {
      const detail = await api.getZone(zone.id);
      setDetailZone({ ...zone, ...detail });
    } catch {
      setDetailZone(zone);
    }
  };

  return (
    <>
      <div
        className="panel-surface"
        style={{
          padding: '8px 10px',
          borderRadius: '8px',
          border: '1px solid var(--color-border)',
          minHeight: '120px',
          maxHeight: '180px',
          boxSizing: 'border-box',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '6px',
          flexShrink: 0,
        }}>
          <span style={{
            fontSize: '10px',
            fontWeight: 700,
            textTransform: 'uppercase',
            color: 'var(--color-muted)',
            letterSpacing: '0.05em',
          }}>
            Zone Analysis · {zones.length} Zones
          </span>
          <span style={{ fontSize: '9px', color: 'var(--color-muted)' }}>
            Click any zone for full details
          </span>
        </div>

        {/* Zone Cards Row */}
        <div style={{
          display: 'flex',
          gap: '8px',
          overflow: 'auto',
          flex: 1,
          minHeight: 0,
        }}>
          {loading && zones.length === 0 && (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-muted)', fontSize: '12px' }}>
              Loading zones…
            </div>
          )}
          {zones.map((z) => (
            <ZoneCard key={z.id} zone={z} onClick={() => handleZoneClick(z)} />
          ))}
          {!loading && zones.length === 0 && (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-muted)', fontSize: '12px' }}>
              No active zones detected
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {detailZone && (
        <ZoneDetailModal zone={detailZone} onClose={() => setDetailZone(null)} />
      )}

      {/* CSS keyframes */}
      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  );
}
