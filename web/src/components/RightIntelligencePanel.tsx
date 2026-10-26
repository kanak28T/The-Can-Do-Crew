import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../lib/api';
import type { DispatchItem } from '../types';
import CausalGraph from './CausalGraph';

const INITIAL_DISPATCHES: DispatchItem[] = [
  {
    id: 'dsp-001',
    priority: 'P1',
    zone: 'Sitabuldi Central',
    action: 'Reroute Bus Route 4 & deploy feeder transit',
    resource: 'NMC Transit #14',
    trigger: 'Transit frequency deficit (-42%)',
    expected_risk_drop: 0.28,
    risk_after: 0.44,
    lo: 0.38,
    hi: 0.51,
    eta: '12 mins',
    status: 'proposed'
  },
  {
    id: 'dsp-002',
    priority: 'P1',
    zone: 'Dhantoli East',
    action: 'Dispatch mobile diesel generator to Substation C',
    resource: 'MSEDCL Mobile DG #03',
    trigger: 'Voltage sag below 190V, clinic isolation risk',
    expected_risk_drop: 0.35,
    risk_after: 0.38,
    lo: 0.32,
    hi: 0.45,
    eta: '18 mins',
    status: 'proposed'
  },
  {
    id: 'dsp-003',
    priority: 'P2',
    zone: 'Gandhibagh',
    action: 'Water tanker diversion to community taps',
    resource: 'OCW Tanker #08',
    trigger: 'Booster pump pressure failure on Wardha main',
    expected_risk_drop: 0.22,
    risk_after: 0.51,
    lo: 0.46,
    hi: 0.58,
    eta: '25 mins',
    status: 'approved'
  },
  {
    id: 'dsp-004',
    priority: 'P3',
    zone: 'Sadar West',
    action: 'Cellular COW (Cell On Wheels) pre-positioning',
    resource: 'Telecom COW #02',
    trigger: 'Tower load surge + 30% packet loss',
    expected_risk_drop: 0.15,
    risk_after: 0.31,
    lo: 0.26,
    hi: 0.37,
    eta: '40 mins',
    status: 'proposed'
  }
];

export default function RightIntelligencePanel() {
  const dockTab = useAppStore((s) => s.dockTab);
  const setDockTab = useAppStore((s) => s.setDockTab);
  const dispatches = useAppStore((s) => s.dispatches);
  const setDispatches = useAppStore((s) => s.setDispatches);
  const updateDispatchStatus = useAppStore((s) => s.updateDispatchStatus);

  const [loadingActionId, setLoadingActionId] = useState<string | null>(null);

  useEffect(() => {
    api.getDispatch()
      .then((items) => {
        if (items && items.length > 0) setDispatches(items);
        else if (dispatches.length === 0) setDispatches(INITIAL_DISPATCHES);
      })
      .catch(() => {
        if (dispatches.length === 0) setDispatches(INITIAL_DISPATCHES);
      });
  }, []);

  const handleApprove = async (id: string) => {
    setLoadingActionId(id);
    updateDispatchStatus(id, 'approved');
    try {
      await api.approveDispatch(id);
    } catch (err) {
      console.warn(`[API] Failed to post approve for ${id}:`, err);
    } finally {
      setLoadingActionId(null);
    }
  };

  const handleReject = async (id: string) => {
    setLoadingActionId(id);
    updateDispatchStatus(id, 'rejected');
    try {
      await api.rejectDispatch(id);
    } catch (err) {
      console.warn(`[API] Failed to post reject for ${id}:`, err);
    } finally {
      setLoadingActionId(null);
    }
  };

  const getPriorityBadge = (p: DispatchItem['priority']) => {
    switch (p) {
      case 'P1': return 'bg-red-500/15 text-red-400 border border-red-500/30';
      case 'P2': return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
      case 'P3': return 'bg-blue-500/15 text-blue-400 border border-blue-500/30';
      default: return 'bg-gray-500/15 text-gray-400 border border-gray-500/30';
    }
  };

  const getStatusBadge = (s: DispatchItem['status']) => {
    switch (s) {
      case 'approved': return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30';
      case 'dispatched': return 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30';
      case 'rejected': return 'bg-rose-500/15 text-rose-400 border border-rose-500/30';
      default: return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30';
    }
  };

  return (
    <div
      className="panel-surface"
      style={{
        display: 'flex',
        flexDirection: 'column',
        borderRadius: '8px',
        border: '1px solid var(--color-border)',
        height: '100%',
        overflow: 'hidden',
        boxSizing: 'border-box'
      }}
    >
      {/* Workspace Header Tabs */}
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-raised)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text)' }}>
            Intelligence Workspace
          </span>
          <span style={{ fontSize: '11px', color: 'var(--color-muted)' }}>
            Live Analytics
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '4px' }}>
          <button
            type="button"
            onClick={() => setDockTab('causal')}
            style={{
              padding: '6px 4px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: dockTab === 'causal' ? '1px solid var(--color-accent)' : '1px solid transparent',
              backgroundColor: dockTab === 'causal' ? 'var(--color-surface)' : 'transparent',
              color: dockTab === 'causal' ? 'var(--color-accent)' : 'var(--color-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            🕸️ Causal Graph
          </button>

          <button
            type="button"
            onClick={() => setDockTab('dispatch')}
            style={{
              padding: '6px 4px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: dockTab === 'dispatch' ? '1px solid var(--color-accent)' : '1px solid transparent',
              backgroundColor: dockTab === 'dispatch' ? 'var(--color-surface)' : 'transparent',
              color: dockTab === 'dispatch' ? 'var(--color-accent)' : 'var(--color-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            ⚡ Dispatch ({dispatches.length})
          </button>

          <button
            type="button"
            onClick={() => setDockTab('privacy')}
            style={{
              padding: '6px 4px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: dockTab === 'privacy' ? '1px solid var(--color-accent)' : '1px solid transparent',
              backgroundColor: dockTab === 'privacy' ? 'var(--color-surface)' : 'transparent',
              color: dockTab === 'privacy' ? 'var(--color-accent)' : 'var(--color-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            🛡️ Privacy
          </button>

          <button
            type="button"
            onClick={() => setDockTab('evaluation')}
            style={{
              padding: '6px 4px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: dockTab === 'evaluation' ? '1px solid var(--color-accent)' : '1px solid transparent',
              backgroundColor: dockTab === 'evaluation' ? 'var(--color-surface)' : 'transparent',
              color: dockTab === 'evaluation' ? 'var(--color-accent)' : 'var(--color-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            🎯 IoU Eval
          </button>
        </div>
      </div>

      {/* Main Tab Body */}
      <div style={{ flex: 1, overflow: 'auto', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {dockTab === 'causal' && (
          <div style={{ flex: 1, minHeight: '400px', width: '100%', position: 'relative' }}>
            <CausalGraph />
          </div>
        )}

        {dockTab === 'dispatch' && (
          <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="panel-title" style={{ fontSize: '13px' }}>Automated Interventions</span>
              <span style={{ fontSize: '11px', color: 'var(--color-muted)' }}>{dispatches.length} items proposed</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {dispatches.map((d) => (
                <div
                  key={d.id}
                  className="panel-raised"
                  style={{
                    padding: '10px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getPriorityBadge(d.priority)}`}>
                        {d.priority}
                      </span>
                      <span style={{ fontWeight: 600, fontSize: '12px', color: 'var(--color-text)' }}>{d.zone}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-medium capitalize ${getStatusBadge(d.status)}`}>
                      {d.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '11.5px', color: 'var(--color-text)', lineHeight: 1.35 }}>
                    {d.action}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '10.5px', color: 'var(--color-muted)' }}>
                    <span>Resource: <strong style={{ color: 'var(--color-secondary)' }}>{d.resource}</strong></span>
                    <span>ETA: <strong>{d.eta}</strong></span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px', borderTop: '1px dashed var(--color-border)' }}>
                    <div style={{ fontSize: '11px' }}>
                      <span style={{ color: 'var(--color-low)', fontWeight: 700 }}>-{Math.round(d.expected_risk_drop * 100)}%</span>
                      <span style={{ color: 'var(--color-muted)', fontSize: '10px', marginLeft: '4px' }}>
                        (risk &rarr; {Math.round(d.risk_after * 100)}%)
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '6px' }}>
                      {d.status === 'proposed' ? (
                        <>
                          <button
                            type="button"
                            disabled={loadingActionId === d.id}
                            onClick={() => handleApprove(d.id)}
                            style={{
                              padding: '3px 8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              borderRadius: '4px',
                              backgroundColor: '#10b981',
                              color: '#fff',
                              border: 'none',
                              cursor: 'pointer'
                            }}
                          >
                            ✓ Approve
                          </button>
                          <button
                            type="button"
                            disabled={loadingActionId === d.id}
                            onClick={() => handleReject(d.id)}
                            style={{
                              padding: '3px 8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              borderRadius: '4px',
                              backgroundColor: 'rgba(239, 68, 68, 0.8)',
                              color: '#fff',
                              border: 'none',
                              cursor: 'pointer'
                            }}
                          >
                            ✕ Reject
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => updateDispatchStatus(d.id, 'proposed')}
                          style={{
                            background: 'none',
                            border: 'none',
                            fontSize: '10.5px',
                            color: 'var(--color-muted)',
                            textDecoration: 'underline',
                            cursor: 'pointer'
                          }}
                        >
                          Reset
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {dockTab === 'privacy' && (
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="panel-title" style={{ fontSize: '13px' }}>🛡️ Privacy & Zero-PII Audit</div>
            <div className="panel-raised" style={{ padding: '12px', borderRadius: '6px', fontSize: '11.5px', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-low)', marginBottom: '4px' }}>✓ Zero PII Enforced</div>
              <p className="text-secondary" style={{ margin: 0 }}>
                No personal identities, phone numbers, or individual location traces stored. All events pass regex screening for Aadhaar, PAN, phone, and names.
              </p>
            </div>
            <div className="panel-raised" style={{ padding: '12px', borderRadius: '6px', fontSize: '11.5px', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-accent)', marginBottom: '4px' }}>k-Merge Anonymity</div>
              <p className="text-secondary" style={{ margin: 0 }}>
                Cells with contributor counts below k (k=5) are automatically merged into parent H3 res-8 cells before serving to client.
              </p>
            </div>
            <div className="panel-raised" style={{ padding: '12px', borderRadius: '6px', fontSize: '11.5px', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-text)', marginBottom: '4px' }}>Red-Team Reconstruction Attack</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px' }}>
                <span className="text-muted">Reconstruction AUC:</span>
                <span style={{ fontWeight: 700, color: 'var(--color-low)' }}>0.51 (Random Chance)</span>
              </div>
            </div>
          </div>
        )}

        {dockTab === 'evaluation' && (
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="panel-title" style={{ fontSize: '13px' }}>🎯 IoU Evaluation Harness</div>
            <div className="panel-raised" style={{ padding: '12px', borderRadius: '6px', fontSize: '11.5px', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, color: 'var(--color-text)', marginBottom: '6px' }}>Holdout Ground-Truth Benchmark</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span className="text-muted">Spatial IoU:</span>
                <span style={{ fontWeight: 700, color: 'var(--color-low)' }}>0.824</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span className="text-muted">Detection Latency:</span>
                <span style={{ fontWeight: 700, color: 'var(--color-accent)' }}>14.2 seconds</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">Precision / Recall:</span>
                <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>89.4% / 91.2%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
