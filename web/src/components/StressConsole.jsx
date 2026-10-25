import React, { useState } from 'react';
import './StressConsole.css';

export default function StressConsole({ isOpen, onClose, onStressApplied }) {
  const [feedCut, setFeedCut] = useState(0);
  const [lossPattern, setLossPattern] = useState('random');
  const [conflictText, setConflictText] = useState('');
  const [activeConflicts, setActiveConflicts] = useState([]);

  if (!isOpen) return null;

  const handleApplyStress = () => {
    if (onStressApplied) {
      onStressApplied({ feedCut, lossPattern });
    }
  };

  const handleInjectConflict = (e) => {
    e.preventDefault();
    if (!conflictText.trim()) return;
    setActiveConflicts((prev) => [
      ...prev,
      {
        id: Date.now(),
        text: conflictText.trim(),
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    setConflictText('');
  };

  return (
    <div className="stress-modal-backdrop" onClick={onClose}>
      <div className="stress-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="dispatch-modal-header">
          <div className="dispatch-modal-title">
            <h2>Resilience & Stress Console (B3.9)</h2>
          </div>
          <button type="button" className="sector-close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="stress-modal-body">
          {/* Feed Cut Slider */}
          <div className="stress-group">
            <div className="stress-label-row">
              <span>Feed Loss Stressor</span>
              <span style={{ color: feedCut > 60 ? '#ef4444' : feedCut > 30 ? '#f59e0b' : '#38bdf8' }}>
                {feedCut}% Streams Cut
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={feedCut}
              onChange={(e) => setFeedCut(Number(e.target.value))}
              className="stress-slider"
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#64748b' }}>
              <span>0% (Full coverage)</span>
              <span>60% (Locked Target)</span>
              <span>80% (Extreme Stress)</span>
            </div>
          </div>

          {/* Loss Pattern Selector */}
          <div className="stress-group">
            <label className="stress-label-row">
              <span>Loss Pattern Architecture</span>
            </label>
            <select
              value={lossPattern}
              onChange={(e) => setLossPattern(e.target.value)}
              className="stress-select"
            >
              <option value="random">Pattern 1: Random Independent Stream Loss</option>
              <option value="domain">Pattern 2: Whole Domain Blackout (e.g., Transit down)</option>
              <option value="spatial">Pattern 3: Contiguous Geographic Area Severed</option>
            </select>
          </div>

          <button type="button" className="stress-action-btn" onClick={handleApplyStress}>
            ⚡ Apply Feed Degradation to Engine
          </button>

          {feedCut > 0 && (
            <div className="stress-applied-banner">
              <span>⚠️</span>
              <span>
                Simulating {feedCut}% feed loss under <strong>{lossPattern}</strong> mode. Stale cells will decay to 'Unknown' grey state.
              </span>
            </div>
          )}

          {/* Conflict Injector */}
          <div className="stress-group" style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
            <label className="stress-label-row">
              <span>Inject Ground-Truth Conflict (Official vs Crowd)</span>
            </label>
            <form onSubmit={handleInjectConflict} className="stress-input-row">
              <input
                type="text"
                placeholder="e.g. Official status: OK | Crowd: 50 explosion reports"
                value={conflictText}
                onChange={(e) => setConflictText(e.target.value)}
                className="stress-input"
              />
              <button type="submit" className="stress-action-btn" style={{ background: '#0284c7' }}>
                Inject
              </button>
            </form>
          </div>

          {activeConflicts.length > 0 && (
            <div style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
              <div style={{ fontWeight: 600, color: '#f59e0b', marginBottom: '0.35rem' }}>Active Injected Contradictions:</div>
              <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
                {activeConflicts.map((c) => (
                  <li key={c.id}>
                    [{c.timestamp}] {c.text}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
