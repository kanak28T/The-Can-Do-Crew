import { useEffect, useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { api } from '../lib/api';
import type { DispatchItem } from '../types';

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

export default function DispatchLog() {
  const dispatches = useAppStore((s) => s.dispatches);
  const setDispatches = useAppStore((s) => s.setDispatches);
  const updateDispatchStatus = useAppStore((s) => s.updateDispatchStatus);

  const [loadingActionId, setLoadingActionId] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState<string>('');

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

  const handleApprove = async (id: string, zone: string, action: string) => {
    setLoadingActionId(id);
    updateDispatchStatus(id, 'approved');
    setAnnouncement(`Approved emergency intervention for ${zone}: ${action}`);
    try {
      await api.approveDispatch(id);
    } catch (err) {
      console.warn(`[API] Failed to post approve for ${id} (using local state):`, err);
    } finally {
      setLoadingActionId(null);
    }
  };

  const handleReject = async (id: string, zone: string, action: string) => {
    setLoadingActionId(id);
    updateDispatchStatus(id, 'rejected');
    setAnnouncement(`Rejected emergency intervention for ${zone}: ${action}`);
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
        return 'bg-red-500/15 text-red-500 border border-red-500/30';
      case 'P2':
        return 'bg-amber-500/15 text-amber-500 border border-amber-500/30';
      case 'P3':
        return 'bg-blue-500/15 text-blue-500 border border-blue-500/30';
      default:
        return 'bg-gray-500/15 text-gray-400 border border-gray-500/30';
    }
  };

  const getStatusBadge = (s: DispatchItem['status']) => {
    switch (s) {
      case 'approved':
        return 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30';
      case 'dispatched':
        return 'bg-cyan-500/15 text-cyan-500 border border-cyan-500/30';
      case 'rejected':
        return 'bg-rose-500/15 text-rose-500 border border-rose-500/30';
      case 'proposed':
      default:
        return 'bg-yellow-500/15 text-yellow-500 border border-yellow-500/30';
    }
  };

  return (
    <div className="h-full flex flex-col" role="region" aria-label="Dispatch Log View">
      {/* Visually hidden screen reader announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      <div className="overflow-x-auto flex-1 rounded border border-[var(--color-border)] bg-[var(--color-page)]/40 focus:outline-none focus:ring-1 focus:ring-blue-500" tabIndex={0} aria-label="Scrollable dispatch table container">
        <table className="w-full text-left text-xs border-collapse" aria-label="Municipal Emergency Dispatch Recommendations">
          <caption className="sr-only">
            Active list of municipal emergency interventions, priority levels, trigger telemetry, projected risk reduction, and operator decision controls.
          </caption>
          <thead className="bg-[var(--color-raised)] text-[var(--color-secondary)] uppercase font-semibold sticky top-0 z-10 border-b border-[var(--color-border)]">
            <tr>
              <th scope="col" className="py-2.5 px-3">Priority</th>
              <th scope="col" className="py-2.5 px-3">Zone</th>
              <th scope="col" className="py-2.5 px-3">Recommended Intervention</th>
              <th scope="col" className="py-2.5 px-3">Resource</th>
              <th scope="col" className="py-2.5 px-3">Trigger / Evidence</th>
              <th scope="col" className="py-2.5 px-3">Expected &Delta;z</th>
              <th scope="col" className="py-2.5 px-3">ETA</th>
              <th scope="col" className="py-2.5 px-3">Status</th>
              <th scope="col" className="py-2.5 px-3 text-right">Decision</th>
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
                    <span className="sr-only">Priority level: </span>
                    {d.priority}
                  </span>
                </td>
                <th scope="row" className="py-2 px-3 font-medium whitespace-nowrap text-[var(--color-text)] text-left">
                  {d.zone}
                </th>
                <td className="py-2 px-3 text-[var(--color-text)] min-w-[200px]">
                  {d.action}
                </td>
                <td className="py-2 px-3 whitespace-nowrap font-mono text-[11px] text-[var(--color-secondary)]">
                  <span className="sr-only">Assigned resource: </span>
                  {d.resource}
                </td>
                <td className="py-2 px-3 text-[11px] text-[var(--color-muted)] max-w-[220px] truncate" title={d.trigger}>
                  {d.trigger}
                </td>
                <td className="py-2 px-3 whitespace-nowrap">
                  <span className="text-emerald-500 font-semibold">
                    -{Math.round(d.expected_risk_drop * 100)}%
                  </span>
                  <span className="text-[10px] text-[var(--color-muted)] ml-1">
                    <span className="sr-only">Projected risk after intervention: </span>
                    ({Math.round(d.risk_after * 100)}% CI [{Math.round(d.lo * 100)}-{Math.round(d.hi * 100)}])
                  </span>
                </td>
                <td className="py-2 px-3 whitespace-nowrap text-[11px] text-[var(--color-secondary)]">
                  <span className="sr-only">Estimated arrival time: </span>
                  {d.eta}
                </td>
                <td className="py-2 px-3 whitespace-nowrap">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize ${getStatusBadge(d.status)}`}>
                    <span className="sr-only">Current status: </span>
                    {d.status}
                  </span>
                </td>
                <td className="py-2 px-3 text-right whitespace-nowrap">
                  <div className="flex items-center justify-end gap-1.5" role="group" aria-label={`Actions for dispatch ${d.id}`}>
                    {d.status === 'proposed' ? (
                      <>
                        <button
                          type="button"
                          disabled={loadingActionId === d.id}
                          onClick={() => handleApprove(d.id, d.zone, d.action)}
                          aria-label={`Approve dispatch for ${d.zone}: ${d.action}`}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-all disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-400"
                        >
                          ✓ Approve
                        </button>
                        <button
                          type="button"
                          disabled={loadingActionId === d.id}
                          onClick={() => handleReject(d.id, d.zone, d.action)}
                          aria-label={`Reject dispatch for ${d.zone}: ${d.action}`}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-rose-600/80 hover:bg-rose-500 text-white shadow-sm transition-all disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-rose-400"
                        >
                          ✕ Reject
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          updateDispatchStatus(d.id, 'proposed');
                          setAnnouncement(`Reset status to proposed for ${d.zone}`);
                        }}
                        aria-label={`Reset status to proposed for ${d.zone}`}
                        className="text-[11px] text-[var(--color-muted)] hover:text-[var(--color-text)] underline transition-colors focus:outline-none focus:ring-1 focus:ring-blue-500 rounded px-1"
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
  );
}
