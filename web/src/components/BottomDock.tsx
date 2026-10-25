import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../lib/api';
import type { DispatchItem } from '../types';
import CausalGraph from './CausalGraph';

const INITIAL_DISPATCHES: DispatchItem[] = [
  {
    id: 'dsp-001',
    priority: 'P1',
    zone: 'Prabhag 12 (Sitabuldi Central)',
    action: 'Reroute Bus Route 4 & deploy feeder transit',
    resource: 'NMC Transit Unit #14',
    trigger: 'Transit frequency deficit (-42%) + Substation drop',
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
    zone: 'Prabhag 7 (Dhantoli East)',
    action: 'Dispatch mobile diesel generator to Substation C',
    resource: 'MSEDCL Mobile DG #03',
    trigger: 'Voltage sag below 190V, hospital feeder isolation risk',
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
    zone: 'Prabhag 18 (Gandhibagh)',
    action: 'Water tanker diversion to municipal community taps',
    resource: 'OCW Water Tanker #08',
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
    zone: 'Prabhag 24 (Sadar West)',
    action: 'Cellular COW (Cell On Wheels) pre-positioning',
    resource: 'Telecom COW #02',
    trigger: 'Tower BTS #109 load surge + 30% packet loss',
    expected_risk_drop: 0.15,
    risk_after: 0.31,
    lo: 0.26,
    hi: 0.37,
    eta: '40 mins',
    status: 'proposed'
  }
];

export default function BottomDock() {
  const dockCollapsed = useAppStore((s) => s.dockCollapsed);
  const toggleDock = useAppStore((s) => s.toggleDock);
  const dockTab = useAppStore((s) => s.dockTab);
  const setDockTab = useAppStore((s) => s.setDockTab);
  const dispatches = useAppStore((s) => s.dispatches);
  const setDispatches = useAppStore((s) => s.setDispatches);
  const updateDispatchStatus = useAppStore((s) => s.updateDispatchStatus);

  const [loadingActionId, setLoadingActionId] = useState<string | null>(null);

  useEffect(() => {
    api.getDispatch()
      .then((items) => {
        if (items && items.length > 0) {
          setDispatches(items);
        } else if (dispatches.length === 0) {
          setDispatches(INITIAL_DISPATCHES);
        }
      })
      .catch(() => {
        if (dispatches.length === 0) {
          setDispatches(INITIAL_DISPATCHES);
        }
      });
  }, []);

  const handleApprove = async (id: string) => {
    setLoadingActionId(id);
    updateDispatchStatus(id, 'approved');
    try {
      await api.approveDispatch(id);
    } catch (err) {
      console.warn(`[API] Failed to post approve for ${id} (using local state):`, err);
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
      console.warn(`[API] Failed to post reject for ${id} (using local state):`, err);
    } finally {
      setLoadingActionId(null);
    }
  };

  const getPriorityBadge = (p: DispatchItem['priority']) => {
    switch (p) {
      case 'P1':
        return 'bg-red-500/15 text-red-400 border border-red-500/30';
      case 'P2':
        return 'bg-amber-500/15 text-amber-400 border border-amber-500/30';
      case 'P3':
        return 'bg-blue-500/15 text-blue-400 border border-blue-500/30';
      default:
        return 'bg-gray-500/15 text-gray-400 border border-gray-500/30';
    }
  };

  const getStatusBadge = (s: DispatchItem['status']) => {
    switch (s) {
      case 'approved':
        return 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30';
      case 'dispatched':
        return 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30';
      case 'rejected':
        return 'bg-rose-500/15 text-rose-400 border border-rose-500/30';
      case 'proposed':
      default:
        return 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30';
    }
  };

  return (
    <div
      className={`absolute bottom-0 left-0 right-0 z-20 flex flex-col transition-all duration-300 backdrop-blur-md shadow-2xl border-t`}
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        height: dockCollapsed ? '42px' : '310px'
      }}
    >
      {/* Dock Header & Tab Navigation */}
      <div
        className="flex items-center justify-between px-4 h-[42px] border-b select-none"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-[var(--color-muted)]">
            Intelligence Dock
          </span>
          <div className="flex items-center bg-[var(--color-raised)] p-0.5 rounded border border-[var(--color-border)] ml-3">
            <button
              type="button"
              onClick={() => { setDockTab('dispatch'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'dispatch'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              ⚡ Dispatch Actions ({dispatches.length})
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('causal'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'causal'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🕸️ Causal Graph
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('privacy'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'privacy'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🛡️ Privacy Red-Team
            </button>
            <button
              type="button"
              onClick={() => { setDockTab('evaluation'); if (dockCollapsed) toggleDock(); }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                dockTab === 'evaluation'
                  ? 'bg-[var(--color-surface)] text-[var(--color-accent)] shadow-sm'
                  : 'text-[var(--color-secondary)] hover:text-[var(--color-text)]'
              }`}
            >
              🎯 IoU Evaluation
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={toggleDock}
          className="text-xs font-medium px-2 py-1 rounded bg-[var(--color-raised)] text-[var(--color-secondary)] hover:text-[var(--color-text)] border border-[var(--color-border)] flex items-center gap-1.5 transition-colors"
          title={dockCollapsed ? 'Expand dock' : 'Collapse dock'}
        >
          {dockCollapsed ? '▲ Expand' : '▼ Collapse'}
        </button>
      </div>

      {/* Dock Content Body */}
      {!dockCollapsed && (
        <div className="flex-1 overflow-auto p-3 text-[var(--color-text)]">
          {dockTab === 'dispatch' && (
            <div className="h-full flex flex-col">
              <div className="overflow-x-auto flex-1 rounded border border-[var(--color-border)] bg-[var(--color-page)]/40">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[var(--color-raised)] text-[var(--color-secondary)] uppercase font-semibold sticky top-0 z-10 border-b border-[var(--color-border)]">
                    <tr>
                      <th className="py-2.5 px-3">Priority</th>
                      <th className="py-2.5 px-3">Zone</th>
                      <th className="py-2.5 px-3">Recommended Intervention</th>
                      <th className="py-2.5 px-3">Resource</th>
                      <th className="py-2.5 px-3">Trigger / Evidence</th>
                      <th className="py-2.5 px-3">Expected &Delta;z</th>
                      <th className="py-2.5 px-3">ETA</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Decision</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-border)]">
                    {dispatches.map((d) => (
                      <tr
                        key={d.id}
                        className="hover:bg-[var(--color-surface)]/60 transition-colors"
                      >
                        <td className="py-2 px-3 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${getPriorityBadge(d.priority)}`}>
                            {d.priority}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-medium whitespace-nowrap text-[var(--color-text)]">
                          {d.zone}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text)] min-w-[200px]">
                          {d.action}
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap font-mono text-[11px] text-[var(--color-secondary)]">
                          {d.resource}
                        </td>
                        <td className="py-2 px-3 text-[11px] text-[var(--color-muted)] max-w-[220px] truncate" title={d.trigger}>
                          {d.trigger}
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap">
                          <span className="text-emerald-400 font-semibold">
                            -{Math.round(d.expected_risk_drop * 100)}%
                          </span>
                          <span className="text-[10px] text-[var(--color-muted)] ml-1">
                            ({Math.round(d.risk_after * 100)}% CI [{Math.round(d.lo * 100)}-{Math.round(d.hi * 100)}])
                          </span>
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap text-[11px] text-[var(--color-secondary)]">
                          {d.eta}
                        </td>
                        <td className="py-2 px-3 whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize ${getStatusBadge(d.status)}`}>
                            {d.status}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            {d.status === 'proposed' ? (
                              <>
                                <button
                                  type="button"
                                  disabled={loadingActionId === d.id}
                                  onClick={() => handleApprove(d.id)}
                                  className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all disabled:opacity-50"
                                >
                                  ✓ Approve
                                </button>
                                <button
                                  type="button"
                                  disabled={loadingActionId === d.id}
                                  onClick={() => handleReject(d.id)}
                                  className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-600/80 hover:bg-rose-500 text-white shadow-sm transition-all disabled:opacity-50"
                                >
                                  ✕ Reject
                                </button>
                              </>
                            ) : (
                              <button
                                type="button"
                                onClick={() => updateDispatchStatus(d.id, 'proposed')}
                                className="text-[11px] text-[var(--color-muted)] hover:text-[var(--color-text)] underline transition-colors"
                              >
                                Reset
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {dockTab === 'causal' && (
            <div className="h-full w-full min-h-[220px]">
              <CausalGraph />
            </div>
          )}

          {dockTab === 'privacy' && (
            <div className="h-full flex items-center justify-center text-center p-6 bg-[var(--color-page)]/40 rounded border border-[var(--color-border)]">
              <div>
                <p className="text-sm font-medium text-[var(--color-text)]">
                  🛡️ Differential Privacy & Red-Team Audit Panel
                </p>
                <p className="text-xs text-[var(--color-muted)] mt-1">
                  k-anonymity bounds, noise calibration, and zero-PII guarantee monitors.
                </p>
              </div>
            </div>
          )}

          {dockTab === 'evaluation' && (
            <div className="h-full flex items-center justify-center text-center p-6 bg-[var(--color-page)]/40 rounded border border-[var(--color-border)]">
              <div>
                <p className="text-sm font-medium text-[var(--color-text)]">
                  🎯 Vulnerability IoU Evaluation Harness
                </p>
                <p className="text-xs text-[var(--color-muted)] mt-1">
                  Ground-truth intersection-over-union and causal attribution metrics.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
