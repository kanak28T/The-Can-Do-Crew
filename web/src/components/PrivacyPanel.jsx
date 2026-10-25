import React from 'react';
import './PrivacyPanel.css';

export default function PrivacyPanel({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="stress-modal-backdrop" onClick={onClose}>
      <div className="privacy-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="dispatch-modal-header">
          <div className="dispatch-modal-title">
            <h2>Privacy & Anonymity Engine (B3.12)</h2>
          </div>
          <button type="button" className="sector-close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="stress-modal-body">
          <div className="privacy-grid">
            <div className="privacy-metric-box">
              <span className="privacy-metric-label">k-Anonymity Merge Threshold</span>
              <span className="privacy-metric-val">k = 5</span>
              <span className="privacy-metric-desc">
                Cells with &lt; 5 contributors automatically roll up into H3 res-8 parent hexagon.
              </span>
            </div>

            <div className="privacy-metric-box">
              <span className="privacy-metric-label">WorldPop Floor</span>
              <span className="privacy-metric-val">100 pop</span>
              <span className="privacy-metric-desc">
                Suppresses risk scores on unpopulated / near-empty cells to prevent individual tracking.
              </span>
            </div>

            <div className="privacy-metric-box">
              <span className="privacy-metric-label">Contribution Bound</span>
              <span className="privacy-metric-val">1 / cell / hr</span>
              <span className="privacy-metric-desc">
                Transient in-memory token bounds individual influence; deleted on 1-hour time bucket close.
              </span>
            </div>

            <div className="privacy-metric-box">
              <span className="privacy-metric-label">Differential Noise</span>
              <span className="privacy-metric-val">&epsilon; = 1.0</span>
              <span className="privacy-metric-desc">
                Calibrated Laplace noise added to published count tallies with bounded daily privacy budget.
              </span>
            </div>
          </div>

          {/* Red-Team Status Badge */}
          <div className="red-team-banner">
            <div>
              <div style={{ fontWeight: 700, color: '#f1f5f9', fontSize: '0.9rem' }}>
                Synthetic Adversarial Evaluation
              </div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                3-prong attack: membership inference, differencing &amp; synthetic public linkage.
              </div>
            </div>
            <span className="red-team-badge">Red-Team: Pending Day 4</span>
          </div>
        </div>
      </div>
    </div>
  );
}
