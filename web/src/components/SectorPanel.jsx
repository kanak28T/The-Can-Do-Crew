import React, { useEffect } from 'react';
import './SectorPanel.css';

export default function SectorPanel({ isOpen, onClose, cellData }) {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!cellData) return null;

  const {
    h3_cell = 'Unknown Cell',
    ward = 'Nagpur Sector',
    risk = 0.5,
    status = 'medium',
    confidence = 'High (85% coverage)',
    domain_stresses = [
      { domain: 'Power', stress: 0.85, color: '#ef4444' },
      { domain: 'Transit', stress: 0.65, color: '#f59e0b' },
      { domain: 'Road Isolation', stress: 0.78, color: '#ef4444' },
      { domain: 'Water Pressure', stress: 0.35, color: '#10b981' },
      { domain: 'Communications', stress: 0.20, color: '#10b981' },
      { domain: 'Health Distance', stress: 0.45, color: '#f59e0b' },
    ],
    drivers = [
      'Feeder F-12 low voltage (-35%)',
      'Road R-14 closed; bus route 4 suspended',
      'Distance to nearest open clinic > 2.2 km',
    ],
    what_if = 'Reopen R-14 and restore route 4 -> Expected risk drops to 0.38 (Low)',
  } = cellData;

  const getRiskColor = (s) => {
    switch (s) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#10b981';
      default: return '#9ca3af';
    }
  };

  const riskPct = risk !== null && risk !== undefined ? Math.round(risk * 100) : 0;

  return (
    <>
      {isOpen && <div className="sector-panel-backdrop" onClick={onClose} />}
      <aside
        className={`sector-panel-container ${isOpen ? 'open' : ''}`}
        aria-label="Sector Details Panel"
      >
        <div className="sector-panel-header">
          <div className="sector-panel-title-area">
            <h3>{ward}</h3>
            <span className="sector-panel-cell-id">{h3_cell}</span>
          </div>
          <button
            type="button"
            className="sector-close-btn"
            onClick={onClose}
            aria-label="Close Sector Panel"
          >
            &times;
          </button>
        </div>

        <div className="sector-panel-body">
          {/* Overall Risk Metric */}
          <div className="sector-risk-card">
            <div className="sector-risk-header">
              <span>Causal Vulnerability (z)</span>
              <span className="sector-confidence-pill">{confidence}</span>
            </div>
            <div className="sector-risk-value-row">
              <span className="sector-risk-big" style={{ color: getRiskColor(status) }}>
                {risk !== null ? `${riskPct}%` : 'UNKNOWN'}
              </span>
              <span
                style={{
                  textTransform: 'uppercase',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  color: getRiskColor(status),
                }}
              >
                {status} Risk
              </span>
            </div>
          </div>

          {/* Domain Stresses Breakdown (Task B2.9) */}
          <div className="sector-section-title">6-Domain Stress Vectors</div>
          <div className="domain-stress-list">
            {domain_stresses.map((item, idx) => (
              <div key={idx} className="domain-stress-item">
                <div className="domain-stress-label-row">
                  <span>{item.domain}</span>
                  <span style={{ color: item.color || '#38bdf8' }}>
                    {Math.round(item.stress * 100)}%
                  </span>
                </div>
                <div className="domain-stress-track">
                  <div
                    className="domain-stress-fill"
                    style={{
                      width: `${Math.min(100, Math.max(0, item.stress * 100))}%`,
                      backgroundColor: item.color || '#38bdf8',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Causal Driver Contributions */}
          <div className="sector-section-title">Root-Cause Drivers</div>
          <ul className="sector-drivers-list">
            {Array.isArray(drivers) && drivers.length > 0 ? (
              drivers.map((d, i) => <li key={i}>{d}</li>)
            ) : (
              <li>No significant anomaly driver identified</li>
            )}
          </ul>

          {/* Counterfactual What-If */}
          <div className="sector-whatif-card">
            <div className="sector-whatif-title">⚡ Counterfactual What-If</div>
            <div>{what_if}</div>
          </div>
        </div>
      </aside>
    </>
  );
}
