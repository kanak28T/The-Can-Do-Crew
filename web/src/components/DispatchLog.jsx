import React, { useState } from 'react';
import './DispatchLog.css';

const INITIAL_DISPATCHES = [
  {
    id: 'DISP-001',
    priority: 'P1',
    zone: 'Z07 (Sitabuldi)',
    action: 'Deploy Mobile Generator 250kVA',
    resource: 'Generator Unit #3',
    evidence: 'Substation C outage (1,400 households affected)',
    current_risk: 0.88,
    target_risk: 0.42,
    risk_drop: '-46%',
    eta: '25 mins',
    status: 'PROPOSED',
  },
  {
    id: 'DISP-002',
    priority: 'P1',
    zone: 'Z12 (Dharampeth)',
    action: 'Dispatch Clearance Crew & Shuttle R-14',
    resource: 'PWD Crew #12 + 2 Minibuses',
    evidence: 'Road R-14 closed; bus route 4 suspended',
    current_risk: 0.82,
    target_risk: 0.38,
    risk_drop: '-44%',
    eta: '18 mins',
    status: 'APPROVED',
  },
  {
    id: 'DISP-003',
    priority: 'P2',
    zone: 'Z04 (Mahal)',
    action: 'Emergency Water Tanker Deployment',
    resource: 'Water Tanker #8 (5,000 L)',
    evidence: 'Feeder F-12 pump failure; pressure depleted',
    current_risk: 0.68,
    target_risk: 0.35,
    risk_drop: '-33%',
    eta: '40 mins',
    status: 'DISPATCHED',
  },
  {
    id: 'DISP-004',
    priority: 'P2',
    zone: 'Z09 (Itwari)',
    action: 'Mobile Cellular Relay Van',
    resource: 'Telecom Unit #1',
    evidence: '300 emergency call drops over 48h; dead zone',
    current_risk: 0.64,
    target_risk: 0.31,
    risk_drop: '-33%',
    eta: '50 mins',
    status: 'PROPOSED',
  },
  {
    id: 'DISP-005',
    priority: 'P3',
    zone: 'Z15 (Sadar)',
    action: 'Field Verify Contradictory Report',
    resource: 'Municipal Patrol #4',
    evidence: 'Official status normal vs 42 crowd leak claims',
    current_risk: 0.45,
    target_risk: 0.22,
    risk_drop: '-23%',
    eta: '15 mins',
    status: 'APPROVED',
  },
];

export default function DispatchLog({ isOpen, onClose }) {
  const [dispatches, setDispatches] = useState(INITIAL_DISPATCHES);

  if (!isOpen) return null;

  const toggleStatus = (id) => {
    setDispatches((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const next =
            item.status === 'PROPOSED'
              ? 'APPROVED'
              : item.status === 'APPROVED'
              ? 'DISPATCHED'
              : 'PROPOSED';
          return { ...item, status: next };
        }
        return item;
      })
    );
  };

  const getPriorityClass = (p) => {
    switch (p) {
      case 'P1': return 'priority-p1';
      case 'P2': return 'priority-p2';
      default: return 'priority-p3';
    }
  };

  const getStatusClass = (s) => {
    switch (s) {
      case 'PROPOSED': return 'status-proposed';
      case 'APPROVED': return 'status-approved';
      default: return 'status-dispatched';
    }
  };

  return (
    <div className="dispatch-modal-backdrop" onClick={onClose}>
      <div className="dispatch-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="dispatch-modal-header">
          <div className="dispatch-modal-title">
            <h2>Automated Intervention Log (B3.10)</h2>
            <span className="dispatch-badge-count">{dispatches.length} Active Plans</span>
          </div>
          <button type="button" className="sector-close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="dispatch-modal-body">
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '1rem' }}>
            Resource-limited greedy allocation. Benefit = re-scored risk drop weighted by population exposure.
            <strong> Click any status badge to advance workflow.</strong>
          </p>

          <table className="dispatch-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Target Zone</th>
                <th>Recommended Action</th>
                <th>Assigned Resource</th>
                <th>Trigger Evidence</th>
                <th>Risk Drop</th>
                <th>ETA</th>
                <th>Status Toggle</th>
              </tr>
            </thead>
            <tbody>
              {dispatches.map((row) => (
                <tr key={row.id}>
                  <td>
                    <span className={`dispatch-priority ${getPriorityClass(row.priority)}`}>
                      {row.priority}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{row.zone}</td>
                  <td>{row.action}</td>
                  <td style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{row.resource}</td>
                  <td style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>{row.evidence}</td>
                  <td>
                    <div className="dispatch-risk-drop">
                      <span>{(row.current_risk * 100).toFixed(0)}% &rarr; {(row.target_risk * 100).toFixed(0)}%</span>
                      <span className="risk-drop-badge">{row.risk_drop}</span>
                    </div>
                  </td>
                  <td style={{ color: '#38bdf8', fontSize: '0.8rem' }}>{row.eta}</td>
                  <td>
                    <button
                      type="button"
                      className={`status-toggle-btn ${getStatusClass(row.status)}`}
                      onClick={() => toggleStatus(row.id)}
                      title="Click to advance status"
                    >
                      {row.status}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
